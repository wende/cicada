"""
Query Orchestrator for Cicada - Smart code discovery tool.

Intelligently analyzes queries and calls appropriate existing tools to provide
broad, shallow overviews with smart suggestions for deep-dive analysis.

Author: Cicada Team
"""

import re
import shlex
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from cicada.keyword_search import KeywordSearcher
from cicada.mcp.pattern_utils import (
    has_wildcards,
    match_any_pattern,
    matches_pattern,
    parse_function_patterns,
    split_or_patterns,
)
from cicada.query.context_extractor import format_matched_context
from cicada.query.types import FilterConfig, QueryConfig, QueryOptions, QueryStrategy, SearchResult
from cicada.scoring import calculate_score_distribution_with_tiers
from cicada.utils.path_utils import matches_glob_pattern


class QueryOrchestrator:
    """Intelligent orchestrator for broad code discovery."""

    def __init__(self, index: dict[str, Any]):
        """
        Initialize the query orchestrator.

        Args:
            index: The Cicada index dictionary containing modules and metadata
        """
        self.index = index
        # Will create keyword searcher on demand with appropriate match_source

    def _is_recent(self, result: SearchResult, cutoff: datetime) -> bool:
        """
        Check if a result is recent (modified after cutoff).

        Args:
            result: SearchResult to check
            cutoff: Datetime cutoff - results must be newer than this

        Returns:
            True if result is recent, False if no timestamp or too old
        """
        # Use SearchResult's built-in get_last_modified method
        last_modified = result.get_last_modified()
        if last_modified:
            # Ensure last_modified is timezone-aware for comparison
            if last_modified.tzinfo is None:
                last_modified = last_modified.replace(tzinfo=timezone.utc)
            return last_modified >= cutoff

        # If no timestamp available, exclude from "recent" filter
        return False

    def _tokenize_query(self, query: str) -> list[str]:
        """
        Tokenize a query string into individual keywords.

        Supports quoted phrases for exact matching:
        - "agent execution" → ["agent", "execution"]
        - '"exact phrase" other' → ["exact phrase", "other"]
        - "agent" → ["agent"]

        Args:
            query: Query string

        Returns:
            List of keywords/phrases
        """
        try:
            # Use shlex to handle quoted phrases
            tokens = shlex.split(query)
        except ValueError:
            # If shlex fails (unmatched quotes), fall back to simple split
            tokens = query.split()

        return [t.strip() for t in tokens if t.strip()]

    def _analyze_query(self, query: str | list[str]) -> QueryStrategy:
        """
        Analyze query to determine search strategy.

        String queries are tokenized by whitespace (supports quoted phrases),
        UNLESS they contain pattern syntax (wildcards, OR, module qualifiers),
        in which case they are preserved as-is to avoid breaking patterns.

        Examples:
        - "agent execution" → ["agent", "execution"] (two keywords)
        - ["agent", "execution"] → ["agent", "execution"] (two keywords)
        - '"agent execution"' → ["agent execution"] (one exact phrase keyword)
        - "login | auth" → ["login | auth"] (OR pattern, not tokenized)
        - "ThenvoiCom.Agent*" → ["ThenvoiCom.Agent*"] (wildcard pattern, not tokenized)

        Args:
            query: Query string or list of query strings

        Returns:
            QueryStrategy with search configuration
        """
        # For string queries, check if they contain pattern syntax before tokenizing
        if isinstance(query, str):
            # Detect pattern syntax that would break if tokenized
            has_pattern_syntax = (
                "|" in query  # OR patterns
                or "*" in query  # Wildcards
                or "/" in query  # Arity specs
                or (":" in query and (".ex" in query or ".exs" in query))  # File paths
                or (query and query[0].isupper() and "." in query)  # Module qualifiers
            )

            # If pattern syntax detected, don't tokenize to preserve the pattern
            queries = [query] if has_pattern_syntax else self._tokenize_query(query)
        else:
            queries = query

        use_keyword_search = False
        use_pattern_search = False
        search_keywords: list[str] = []
        search_patterns: list[str] = []

        for q in queries:
            q_normalized = q.strip()
            if not q_normalized:
                continue

            # Skip standalone OR tokens that can appear when queries are pre-tokenized
            # (e.g., ["login", "|", "auth"]). Treating these as patterns would
            # match everything.
            if set(q_normalized) == {"|"}:
                continue

            # Detect if this is a pattern (has wildcards, module qualifiers, arity)
            if self._is_pattern_query(q_normalized):
                use_pattern_search = True
                search_patterns.append(q_normalized)
            else:
                # Treat as keyword
                use_keyword_search = True
                search_keywords.append(q_normalized)

        return QueryStrategy(
            use_keyword_search=use_keyword_search,
            use_pattern_search=use_pattern_search,
            search_keywords=search_keywords,
            search_patterns=search_patterns,
        )

    def _is_pattern_query(self, query: str) -> bool:
        """
        Determine if a query string is a pattern rather than a keyword.

        Pattern indicators:
        - Contains wildcards (*) or OR patterns (|)
        - Contains module qualifiers (Capitalized.Name)
        - Contains arity (/N)
        - Contains file paths (file.ex:)

        Args:
            query: Query string

        Returns:
            True if this looks like a pattern query
        """
        # Check for wildcards or OR
        if has_wildcards(query):
            return True

        # Check for arity specification (/N)
        if re.search(r"/\d+$", query):
            return True

        # Check for file path prefix (path.ex:)
        if ":" in query and (".ex" in query or ".exs" in query):
            return True

        # Check for module qualifier (Capital.Qualified.Name)
        # Must start with capital and have dots
        return bool("." in query and query[0].isupper())

    def _pattern_search(
        self, pattern: str, filter_type: str, match_source: str
    ) -> list[SearchResult]:
        """
        Execute pattern-based search using function pattern matching.

        Args:
            pattern: Pattern string (e.g., "create*", "MyApp.User.*", "create_user/2")
            filter_type: Type filter ("all", "modules", "functions")
            match_source: Match source filter ("all", "docs", "strings")

        Returns:
            List of matching SearchResult objects
        """
        results: list[SearchResult] = []

        # Check if this is a pure name pattern (no dots, just wildcards/OR)
        # Examples: "*Analyzer", "User|Post", "*Service*", "execute*", "foo|bar"
        # These can match both module names and function names (depending on filter_type)
        has_no_dots = "." not in pattern
        has_pattern_chars = has_wildcards(pattern)

        if has_no_dots and has_pattern_chars:
            # This is a pure name pattern - match against module/function names directly
            # Split by OR if present
            name_patterns = split_or_patterns(pattern)

            # Match modules if requested
            if filter_type in ["all", "modules"]:
                for module_name, module_data in self.index.get("modules", {}).items():
                    if match_any_pattern(name_patterns, module_name):
                        results.append(
                            SearchResult(
                                type="module",
                                name=module_name,
                                module=module_name,
                                file=module_data.get("file", ""),
                                line=module_data.get("line", 1),
                                doc=module_data.get("moduledoc"),
                                score=1.0,  # Pattern match = full score
                                confidence=100.0,
                                matched_keywords=[],
                                pattern_match=True,
                            )
                        )

            # Match functions if requested
            if filter_type in ["all", "functions"]:
                for module_name, module_data in self.index.get("modules", {}).items():
                    file_path = module_data.get("file", "")
                    for func in module_data.get("functions", []):
                        if match_any_pattern(name_patterns, func["name"]):
                            full_name = f"{module_name}.{func['name']}/{func['arity']}"
                            results.append(
                                SearchResult(
                                    type="function",
                                    name=full_name,
                                    module=module_name,
                                    function=func["name"],
                                    arity=func["arity"],
                                    file=file_path,
                                    line=func.get("line", 1),
                                    doc=func.get("doc"),
                                    signature=func.get("signature"),
                                    visibility=func.get("type", "def"),
                                    score=1.0,
                                    confidence=100.0,
                                    matched_keywords=[],
                                    pattern_match=True,
                                    last_modified_at=func.get("last_modified_at"),
                                )
                            )

            return results

        # Parse the pattern for function/qualified module searches
        patterns = parse_function_patterns(pattern)

        # Search through all modules
        for module_name, module_data in self.index.get("modules", {}).items():
            file_path = module_data.get("file", "")

            # For each pattern alternative (OR patterns)
            for func_pattern in patterns:
                # Check if this is a module-level search
                # Two cases:
                # 1. Function name is "*" (e.g., "MyApp.User.*")
                # 2. Function name has no wildcards and could be the module suffix (e.g., "ThenvoiCom.Context")
                is_module_search = func_pattern.name == "*"

                # Check if the "function name" is actually a module suffix
                # This handles queries like "ThenvoiCom.Context" which get parsed as module="*.ThenvoiCom", name="Context"
                module_tail = module_name.rsplit(".", 1)[-1]
                module_matches = matches_pattern(func_pattern.module, module_name)
                if (
                    not is_module_search
                    and "*" not in func_pattern.name
                    and "|" not in func_pattern.name
                    and func_pattern.module
                ):
                    module_base = (
                        func_pattern.module[2:]
                        if func_pattern.module.startswith("*.")
                        else func_pattern.module
                    )

                    if matches_pattern(f"*.{module_base}.{func_pattern.name}", module_name):
                        is_module_search = True

                if (
                    is_module_search
                    and filter_type in ["all", "modules"]
                    and module_matches
                    and (
                        func_pattern.name == "*" or matches_pattern(func_pattern.name, module_tail)
                    )
                ):
                    # Add module as result
                    results.append(
                        SearchResult(
                            type="module",
                            name=module_name,
                            module=module_name,
                            file=file_path,
                            line=module_data.get("line", 1),
                            doc=module_data.get("moduledoc"),
                            score=1.0,  # Pattern match = full score
                            confidence=100.0,
                            matched_keywords=[],
                            pattern_match=True,
                        )
                    )

                # Search functions in module
                if filter_type in ["all", "functions"]:
                    for func in module_data.get("functions", []):
                        if func_pattern.matches(module_name, file_path, func):
                            # Function matches the pattern
                            full_name = f"{module_name}.{func['name']}/{func['arity']}"
                            results.append(
                                SearchResult(
                                    type="function",
                                    name=full_name,
                                    module=module_name,
                                    function=func["name"],
                                    arity=func["arity"],
                                    file=file_path,
                                    line=func.get("line", 1),
                                    doc=func.get("doc"),
                                    signature=func.get("signature"),
                                    visibility=func.get("type", "def"),  # "def" or "defp"
                                    score=1.0,  # Pattern match = full score
                                    confidence=100.0,
                                    matched_keywords=[],
                                    pattern_match=True,
                                    last_modified_at=func.get("last_modified_at"),
                                )
                            )

        return results

    def _call_tools(
        self, strategy: QueryStrategy, filter_type: str, match_source: str
    ) -> list[SearchResult]:
        """
        Call appropriate tools based on search strategy.

        Args:
            strategy: Search strategy from _analyze_query
            filter_type: Type filter ("all", "modules", "functions")
            match_source: Match source filter ("all", "docs", "strings")

        Returns:
            Combined results from all tool calls
        """
        results: list[SearchResult] = []

        # Keyword search
        if strategy.use_keyword_search:
            searcher = KeywordSearcher(self.index, match_source=match_source)
            keyword_results = searcher.search(
                query_keywords=strategy.search_keywords,
                top_n=QueryConfig.INTERNAL_SEARCH_LIMIT,
                filter_type=filter_type,
            )
            # Convert dict results to SearchResult objects
            for result in keyword_results:
                results.append(self._dict_to_search_result(result))

        # Pattern search
        if strategy.use_pattern_search:
            for pattern in strategy.search_patterns:
                pattern_results = self._pattern_search(pattern, filter_type, match_source)
                results.extend(pattern_results)

        return results

    def _dict_to_search_result(self, result_dict: dict[str, Any]) -> SearchResult:
        """Convert dictionary result to SearchResult object."""
        return SearchResult(
            type=result_dict["type"],
            name=result_dict["name"],
            module=result_dict["module"],
            file=result_dict["file"],
            line=result_dict.get("line", 1),
            score=result_dict.get("score", 0.0),
            confidence=result_dict.get("confidence", 0.0),
            matched_keywords=result_dict.get("matched_keywords", []),
            pattern_match=result_dict.get("pattern_match", False),
            doc=result_dict.get("doc"),
            keyword_sources=result_dict.get("keyword_sources", {}),
            string_sources=result_dict.get("string_sources", []),
            function=result_dict.get("function"),
            arity=result_dict.get("arity"),
            signature=result_dict.get("signature"),
            visibility=result_dict.get("visibility"),
            last_modified_at=result_dict.get("last_modified_at"),
        )

    def _apply_filters(
        self, results: list[SearchResult], config: FilterConfig
    ) -> list[SearchResult]:
        """
        Apply scope, path, test, and arity filters to results.

        Args:
            results: List of search results
            config: Filter configuration

        Returns:
            Filtered list of results
        """
        filtered = results

        # Recent filter
        if config.recent:
            cutoff = datetime.now(timezone.utc) - timedelta(days=QueryConfig.RECENT_DAYS_THRESHOLD)
            filtered = [r for r in filtered if self._is_recent(r, cutoff)]

        # Scope filter
        if config.scope == "public":
            # Only include public functions and all modules
            filtered = [r for r in filtered if r.is_module() or r.is_public()]
        elif config.scope == "private":
            # Only include private functions
            filtered = [r for r in filtered if r.is_private()]

        # Path pattern filter
        if config.path_pattern:
            filtered = [r for r in filtered if matches_glob_pattern(r.file, config.path_pattern)]

        # Arity filter (only for functions)
        if config.arity is not None:
            filtered = [r for r in filtered if r.is_module() or r.arity == config.arity]

        return filtered

    def _rank_and_dedupe(self, results: list[SearchResult]) -> list[SearchResult]:
        """
        Rank results by score and remove duplicates.

        Args:
            results: List of search results

        Returns:
            Deduplicated and ranked results
        """
        # Group by unique identifier
        by_name: dict[str, SearchResult] = {}

        for result in results:
            # Use full name as unique key
            key = result.name

            if key in by_name:
                # Keep result with higher score
                if result.score > by_name[key].score:
                    by_name[key] = result
            else:
                by_name[key] = result

        # Sort by score (descending), then by name for stable results
        ranked = sorted(by_name.values(), key=lambda x: (-x.score, x.name))

        return ranked

    def _attach_tier_info(self, results: list[SearchResult]) -> list[SearchResult]:
        """
        Calculate score distribution and attach tier information to each result.

        Args:
            results: List of search results with scores

        Returns:
            Results with tier information attached
        """
        if not results:
            return results

        # Extract scores from results
        scores = [r.score for r in results]

        # Calculate distribution with tiers
        distribution = calculate_score_distribution_with_tiers(scores)

        # Attach tier info to each result
        # distribution['distribution'] is sorted by z-score (descending)
        # but we need to match by score value
        # Round scores to 6 decimal places to handle floating-point precision issues
        score_precision = 6
        score_to_tier = {
            round(d["score"], score_precision): d for d in distribution["distribution"]
        }

        for result in results:
            tier_data = score_to_tier.get(round(result.score, score_precision))
            if tier_data:
                result.z_score = tier_data["z_score"]
                result.percentile = tier_data["percentile"]
                result.normalized_score = tier_data["normalized"]
                result.tier = tier_data["tier"]
                result.tier_label = tier_data["tier_label"]
                result.tier_description = tier_data["tier_description"]
                result.tier_rank = tier_data["tier_rank"]

        return results

    def _generate_suggestions(
        self, query: str | list[str], results: list[SearchResult]
    ) -> list[str]:
        """
        Generate smart next-step suggestions based on results.

        Args:
            query: Original query
            results: Search results

        Returns:
            List of suggestion strings
        """
        suggestions = []

        # Always suggest detailed analysis of top result
        if results:
            top = results[0]
            if top.is_function() and top.function:
                suggestions.append(
                    f"search_function('{top.function}', module_path='{top.module}', "
                    "include_usage_examples=true) - See how this function is used"
                )
            suggestions.append(f"search_module('{top.module}') - View complete {top.module} API")

        # Query-specific suggestions based on content
        query_text = self._normalize_query_text(query)

        # SQL/database keywords
        if self._is_sql_related_query(query_text):
            suggestions.append("Try match_source='strings' to find SQL queries in code strings")

        # Many results in same module
        if self._has_multiple_results_in_same_module(results):
            common_module = self._get_most_common_module(results)
            suggestions.append(
                f"search_module('{common_module}', what_calls_it=True) - See where this module is used"
            )

        # Results have recent changes
        if self._has_recent_changes(results):
            suggestions.append("Try recent=true to focus on recently changed code")

        # Module-level results
        if self._has_many_module_results(results):
            suggestions.append("Try filter_type='functions' to see only function-level matches")

        return suggestions[: QueryConfig.MAX_SUGGESTIONS]

    def _normalize_query_text(self, query: str | list[str]) -> str:
        """Convert query to normalized lowercase text."""
        queries = [query] if isinstance(query, str) else query
        return " ".join(str(q).lower() for q in queries)

    def _is_sql_related_query(self, query_text: str) -> bool:
        """Check if query contains SQL-related keywords."""
        sql_keywords = ["select", "insert", "update", "delete", "sql", "query"]
        return any(keyword in query_text for keyword in sql_keywords)

    def _has_multiple_results_in_same_module(self, results: list[SearchResult]) -> bool:
        """Check if many results come from the same module."""
        if len(results) < QueryConfig.MIN_RESULTS_FOR_CLUSTERING:
            return False
        module_counts = Counter(r.module for r in results[:10])
        if not module_counts:
            return False
        most_common_count = module_counts.most_common(1)[0][1]
        return most_common_count >= QueryConfig.MIN_SAME_MODULE_FOR_SUGGESTION

    def _get_most_common_module(self, results: list[SearchResult]) -> str:
        """Get the most frequently occurring module in results."""
        module_counts = Counter(r.module for r in results[:10])
        return module_counts.most_common(1)[0][0]

    def _has_recent_changes(self, results: list[SearchResult]) -> bool:
        """Check if results contain recently modified code."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=QueryConfig.RECENT_DAYS_THRESHOLD)
        recent_count = sum(1 for r in results[:10] if self._is_recent(r, cutoff))
        return recent_count >= 2

    def _has_many_module_results(self, results: list[SearchResult]) -> bool:
        """Check if results contain multiple module-level matches."""
        module_results = [r for r in results[:10] if r.is_module()]
        return len(module_results) >= 2

    def _format_report(
        self,
        results: list[SearchResult],
        suggestions: list[str],
        max_results: int,
        query: str | list[str],
        show_snippets: bool = False,
    ) -> str:
        """
        Format final report with results and suggestions.

        Args:
            results: Search results
            suggestions: Suggested next steps
            max_results: Maximum number of results to show
            query: Original query
            show_snippets: Whether to show code snippet previews

        Returns:
            Markdown formatted report
        """
        lines = []

        # Header - compact format
        query_display = query if isinstance(query, str) else ", ".join(f'"{q}"' for q in query)
        total = len(results)
        showing = min(total, max_results)
        lines.append(
            f"Query: {query_display} | {total} result{'s' if total != 1 else ''} (showing {showing})\n\n"
        )

        # Results
        for i, result in enumerate(results[:max_results], 1):
            lines.append(self._format_result_snippet(result, i, show_snippets))

        # Suggestions
        if suggestions:
            lines.append("\n## Suggested Next Steps\n\n")
            for suggestion in suggestions:
                lines.append(f"- {suggestion}\n")

        return "".join(lines)

    def _get_relative_time_string(self, delta) -> str:
        """
        Convert a timedelta to a human-readable relative time string.

        Args:
            delta: timedelta representing time difference from now

        Returns:
            Relative time string (e.g., "today", "2 days ago", "3 months ago")
        """
        if delta.days == 0:
            return "today"
        elif delta.days == 1:
            return "yesterday"
        elif delta.days < 7:
            return f"{delta.days} days ago"
        elif delta.days < 30:
            weeks = delta.days // 7
            return f"{weeks} week{'s' if weeks > 1 else ''} ago"
        elif delta.days < 365:
            months = delta.days // 30
            return f"{months} month{'s' if months > 1 else ''} ago"
        else:
            years = delta.days // 365
            return f"{years} year{'s' if years > 1 else ''} ago"

    def _format_result_snippet(
        self, result: SearchResult, index: int, show_snippets: bool = False
    ) -> str:
        """
        Format a single result as a snippet (compact format).

        Args:
            result: SearchResult to format
            index: Result number (1-indexed)
            show_snippets: Whether to show code snippet previews

        Returns:
            Compact formatted snippet
        """
        lines = []

        # Compact header: number, name, and tier on first line
        header_parts = [f"{index}. {result.name}"]

        # Add tier label if available
        if result.tier_label:
            header_parts.append(f"[{result.tier_label}]")

        lines.append(" | ".join(header_parts) + "\n")

        # Path on second line
        lines.append(f"{result.file}:{result.line}\n")

        # Confidence on third line (if available)
        if result.percentile is not None:
            lines.append(f"Confidence: {result.percentile:.1f}%\n")

        # First line of documentation (wrapped nicely)
        if result.doc:
            doc = result.doc.strip().split("\n")[0]
            # Wrap at ~100 characters
            if len(doc) > 100:
                doc = doc[:100] + "..."
            lines.append(f"{doc}\n")

        # Last modified timestamp (if available)
        if result.last_modified_at:
            try:
                # Parse ISO format timestamp
                dt = datetime.fromisoformat(result.last_modified_at.replace("Z", "+00:00"))
                # Ensure timezone-aware datetime for consistent comparisons
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)

                now = datetime.now(timezone.utc)
                delta = now - dt
                time_ago = self._get_relative_time_string(delta)

                # Include commit hash and PR if available
                git_info = []
                if result.last_modified_sha:
                    git_info.append(result.last_modified_sha)
                if result.last_modified_pr:
                    git_info.append(f"#{result.last_modified_pr}")

                if git_info:
                    lines.append(f"Last modified: {time_ago} ({' '.join(git_info)})\n")
                else:
                    lines.append(f"Last modified: {time_ago}\n")
            except (ValueError, AttributeError):
                pass

        # Matched context (documentation and string excerpts with highlighted keywords)
        if result.matched_keywords:
            context = format_matched_context(
                matched_keywords=result.matched_keywords,
                keyword_sources=result.keyword_sources,
                doc_text=result.doc,
                string_sources=result.string_sources,
                use_ansi=True,  # Use ANSI colors for terminal output
            )

            if context:
                lines.append(f"\n{context}\n")
            else:
                # Fallback to simple keyword list if no context available
                kw_with_sources: list[str] = []
                source_suffixes = {
                    "docs": " (in docs)",
                    "strings": " (in strings)",
                    "both": " (in docs+strings)",
                }
                for kw in result.matched_keywords[:5]:
                    source = result.keyword_sources.get(kw, "")
                    suffix = source_suffixes.get(source, "")
                    kw_with_sources.append(kw + suffix)

                matched_str = ", ".join(kw_with_sources)
                if len(result.matched_keywords) > 5:
                    matched_str += f" (+{len(result.matched_keywords) - 5} more)"
                lines.append(f"Matched keywords: {matched_str}\n")

        # Code snippet preview (if enabled)
        if show_snippets:
            snippet = self._extract_code_snippet(result.file, result.line)
            if snippet:
                lines.append(f"\n```elixir\n{snippet}\n```\n")

        lines.append("\n")  # Blank line between results

        return "".join(lines)

    def _extract_code_snippet(
        self, file_path: str, line: int, context_lines: int = QueryConfig.DEFAULT_CONTEXT_LINES
    ) -> str | None:
        """
        Extract code snippet from file with context lines.

        Args:
            file_path: Path to the file
            line: Target line number (1-indexed)
            context_lines: Number of context lines before and after (default: 2)

        Returns:
            Formatted code snippet with line numbers, or None if file not readable
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                lines = f.readlines()

            # Convert to 0-indexed
            target_idx = line - 1

            # Calculate range
            start_idx = max(0, target_idx - context_lines)
            end_idx = min(len(lines), target_idx + context_lines + 1)

            # Extract snippet with line numbers
            snippet_lines: list[str] = []
            for i in range(start_idx, end_idx):
                line_num = i + 1
                line_content = lines[i].rstrip("\n")
                # pyrefly: disable[bad-argument-type]
                snippet_lines.append(f"{line_num}: {line_content}")

            return "\n".join(snippet_lines)

        except (OSError, UnicodeDecodeError, IndexError):
            # File doesn't exist, not readable, or line out of range
            return None

    def _generate_query_variants(self, query: str) -> list[str]:
        """
        Generate structural formatting variants of a query term.

        Since keyword search is case-insensitive, only suggests variants that differ
        in structure (e.g., "openrouter" → "open_router"), not case-only variants.

        Args:
            query: Query string

        Returns:
            List of structurally different variant strings, deduplicated case-insensitively
        """
        variants = []
        seen_normalized = {query.lower()}  # Track case-insensitive duplicates

        # snake_case variant (with underscores)
        snake = query.lower().replace(" ", "_").replace("-", "_")
        if snake.lower() not in seen_normalized:
            variants.append(snake)
            seen_normalized.add(snake.lower())

        # PascalCase variant (for module names)
        # Only suggest if the original didn't have underscores (structural difference)
        if "_" not in query and "-" not in query:
            parts = query.replace("_", " ").replace("-", " ").split()
            if parts and len(parts) > 1:  # Only for multi-word terms
                pascal = "".join(word.capitalize() for word in parts)
                if pascal.lower() not in seen_normalized:
                    variants.append(pascal)
                    seen_normalized.add(pascal.lower())

        # hyphen-case variant (another common format)
        hyphen = query.lower().replace(" ", "-").replace("_", "-")
        if hyphen.lower() not in seen_normalized and hyphen != query.lower():
            variants.append(hyphen)
            seen_normalized.add(hyphen.lower())

        return variants[: QueryConfig.MAX_QUERY_VARIANTS]

    def _find_related_terms(
        self, query: str, max_terms: int = QueryConfig.MAX_RELATED_TERMS
    ) -> list[str]:
        """
        Find related terms from the index using simple string similarity.

        Args:
            query: Query string
            max_terms: Maximum number of related terms to return

        Returns:
            List of related terms found in the index
        """
        query_lower = query.lower()
        related = []

        # Collect all keywords from the index
        all_keywords = set()
        for module in self.index.get("modules", {}).values():
            if module.get("keywords"):
                all_keywords.update(k.lower() for k in module["keywords"])
            if module.get("string_keywords"):
                all_keywords.update(k.lower() for k in module["string_keywords"])

            for func in module.get("functions", []):
                if func.get("keywords"):
                    all_keywords.update(k.lower() for k in func["keywords"])
                if func.get("string_keywords"):
                    all_keywords.update(k.lower() for k in func["string_keywords"])

        # Find terms with simple similarity (substring match or character overlap)
        for keyword in all_keywords:
            # Substring match
            if query_lower in keyword or keyword in query_lower:
                if keyword != query_lower:
                    related.append(keyword)
            # Simple character overlap check
            elif (
                len(query_lower) > QueryConfig.MIN_TERM_LENGTH_FOR_SIMILARITY
                and len(keyword) > QueryConfig.MIN_TERM_LENGTH_FOR_SIMILARITY
            ):
                # Check if significant overlap
                overlap = sum(1 for c in query_lower if c in keyword)
                if (
                    overlap >= len(query_lower) * QueryConfig.RELATED_TERM_SIMILARITY_THRESHOLD
                    and keyword not in related
                ):
                    related.append(keyword)

        return related[:max_terms]

    def _generate_zero_result_suggestions(
        self, query: str | list[str], filters_applied: dict[str, Any]
    ) -> list[str]:
        """
        Generate helpful suggestions when query returns zero results.

        Args:
            query: Original query (string or list)
            filters_applied: Dictionary of filters that were applied

        Returns:
            List of suggestion strings
        """
        suggestions = []

        # Convert query to string for analysis
        query_str = query if isinstance(query, str) else " ".join(query)

        # 1. Suggest case/formatting variants
        variants = self._generate_query_variants(query_str)
        if variants:
            suggestions.append(f"Try variants: {', '.join(f'`{v}`' for v in variants)}")

        # 2. Find related terms from index
        related = self._find_related_terms(query_str)
        if related:
            suggestions.append(f"Related terms in codebase: {', '.join(f'`{t}`' for t in related)}")

        # 3. Suggest removing/broadening filters
        active_filters = []
        if filters_applied.get("scope") != "all":
            active_filters.append(f"scope='{filters_applied['scope']}'")
        if filters_applied.get("recent"):
            active_filters.append("recent=true")
        if filters_applied.get("filter_type") != "all":
            active_filters.append(f"filter_type='{filters_applied['filter_type']}'")
        if filters_applied.get("path_pattern"):
            active_filters.append(f"path_pattern='{filters_applied['path_pattern']}'")

        if active_filters:
            suggestions.append(f"Try broadening: Remove filters ({', '.join(active_filters)})")

        # 4. Suggest trying pattern search if keyword search
        if isinstance(query, str) and not self._is_pattern_query(query):
            suggestions.append(f"Try pattern search: `{query}*` or `*.{query}*`")

        return suggestions

    def execute_query(
        self,
        query: str | list[str],
        scope: str = "all",
        recent: bool = False,
        filter_type: str = "all",
        match_source: str = "all",
        max_results: int = 10,
        path_pattern: str | None = None,
        arity: int | None = None,
        show_snippets: bool = False,
    ) -> str:
        """
        Execute a query and return formatted results.

        Args:
            query: Query string or list of strings
            scope: Scope filter ("all", "public", "private")
            recent: Filter to recently changed code only (last 14 days)
            filter_type: Type filter ("all", "modules", "functions")
            match_source: Match source filter ("all", "docs", "strings")
            max_results: Maximum number of results to show
            path_pattern: Optional glob pattern for file paths
            arity: Optional arity filter for functions
            show_snippets: Whether to show code snippet previews (default: False)

        Returns:
            Markdown formatted report
        """
        # Normalize query
        if not query:
            return "Error: Query cannot be empty"

        # Create options object for internal use
        options = QueryOptions(
            scope=scope,  # type: ignore
            recent=recent,
            filter_type=filter_type,  # type: ignore
            match_source=match_source,  # type: ignore
            max_results=max_results,
            path_pattern=path_pattern,
            arity=arity,
            show_snippets=show_snippets,
        )

        # Analyze query
        strategy = self._analyze_query(query)

        # Call tools
        raw_results = self._call_tools(strategy, options.filter_type, options.match_source)

        # Apply filters
        filter_config = options.to_filter_config()
        filtered_results = self._apply_filters(raw_results, filter_config)

        # Rank and deduplicate
        ranked_results = self._rank_and_dedupe(filtered_results)

        # Attach tier information based on score distribution
        ranked_results = self._attach_tier_info(ranked_results)

        # Check for zero results and generate appropriate suggestions
        if len(ranked_results) == 0:
            # Generate zero-result suggestions
            filters_applied = {
                "scope": options.scope,
                "recent": options.recent,
                "filter_type": options.filter_type,
                "path_pattern": options.path_pattern,
            }
            suggestions = self._generate_zero_result_suggestions(query, filters_applied)
        else:
            # Generate normal suggestions based on results
            suggestions = self._generate_suggestions(query, ranked_results)

        # Format report
        return self._format_report(
            ranked_results, suggestions, options.max_results, query, options.show_snippets
        )
