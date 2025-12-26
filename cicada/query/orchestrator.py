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

    def __init__(
        self,
        index: dict[str, Any],
        repo_path: str | None = None,
        use_embeddings: bool = False,
    ):
        """
        Initialize the query orchestrator.

        Args:
            index: The Cicada index dictionary containing modules and metadata
            repo_path: Optional repository path for embeddings search
            use_embeddings: Whether to use embeddings-based semantic search
        """
        self.index = index
        self.repo_path = repo_path
        self.use_embeddings = use_embeddings
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

    def _analyze_query(self, query: str | list[str | list[str]]) -> QueryStrategy:
        """
        Analyze query to determine search strategy.

        String queries are tokenized by whitespace (supports quoted phrases),
        UNLESS they contain pattern syntax (wildcards, OR, module qualifiers),
        in which case they are preserved as-is to avoid breaking patterns.

        Supports synonym groups: [["login", "authenticate"], "user"] means
        "login OR authenticate" AND "user".

        Examples:
        - "agent execution" → ["agent", "execution"] (two keywords)
        - ["agent", "execution"] → ["agent", "execution"] (two keywords)
        - [["login", "auth"], "user"] → [["login", "auth"], "user"] (synonyms)
        - '"agent execution"' → ["agent execution"] (one exact phrase keyword)
        - "login | auth" → ["login | auth"] (OR pattern, not tokenized)
        - "ThenvoiCom.Agent*" → ["ThenvoiCom.Agent*"] (wildcard pattern, not tokenized)

        Args:
            query: Query string, list of query strings, or list with synonym groups

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
            if has_pattern_syntax:
                queries: list[str | list[str]] = [query]
            else:
                # _tokenize_query returns list[str], convert to list[str | list[str]]
                queries = list(self._tokenize_query(query))  # type: ignore[assignment]
        else:
            queries = query

        use_keyword_search = False
        use_pattern_search = False
        search_keywords: list[str | list[str]] = []
        search_patterns: list[str] = []

        for q in queries:
            # Handle synonym groups (lists of strings)
            if isinstance(q, list):
                # This is a synonym group - all items are keywords
                normalized_synonyms = [s.strip() for s in q if s.strip()]
                if normalized_synonyms:
                    use_keyword_search = True
                    search_keywords.append(normalized_synonyms)
                continue

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

        # Keyword search (always run when requested)
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

        # Embeddings-based semantic search (hybrid: merges with keyword results)
        if self.use_embeddings and strategy.use_keyword_search and self.repo_path:
            try:
                from cicada.embeddings.searcher import EmbeddingsSearcher

                embeddings_searcher = EmbeddingsSearcher(self.repo_path)
                # Combine keywords into a query string
                query_str = " ".join(
                    str(k) if isinstance(k, str) else " ".join(k) for k in strategy.search_keywords
                )
                embedding_results = embeddings_searcher.search(
                    query=query_str,
                    top_n=QueryConfig.INTERNAL_SEARCH_LIMIT,
                    filter_type=filter_type,
                )
                semantic_results = [self._dict_to_search_result(r) for r in embedding_results]
                # Hybrid merge with percentile ranking and boost
                results = self._merge_hybrid_results(results, semantic_results)
            except FileNotFoundError:
                # Embeddings not available, continue with keyword results only
                pass

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
            search_source=result_dict.get("search_source", "keyword"),
        )

    def _merge_hybrid_results(
        self,
        keyword_results: list[SearchResult],
        semantic_results: list[SearchResult],
    ) -> list[SearchResult]:
        """
        Merge keyword and semantic search results for hybrid search.

        Uses percentile ranking for score normalization and applies a 1.5x boost
        to results appearing in both search sources.

        Args:
            keyword_results: Results from keyword search
            semantic_results: Results from semantic/embeddings search

        Returns:
            Merged and ranked results with search_source indicators
        """
        # Handle edge cases
        if not keyword_results and not semantic_results:
            return []
        if not semantic_results:
            for r in keyword_results:
                r.search_source = "keyword"
            return keyword_results
        if not keyword_results:
            for r in semantic_results:
                r.search_source = "semantic"
            return semantic_results

        # Convert to percentile ranks (0-100)
        keyword_ranked = self._to_percentile_ranks(keyword_results, "keyword")
        semantic_ranked = self._to_percentile_ranks(semantic_results, "semantic")

        # Build lookup by unique key (name+file+line)
        merged: dict[tuple[str, str, int], SearchResult] = {}

        # Add keyword results first
        for r in keyword_ranked:
            key = (r.name, r.file, r.line)
            merged[key] = r

        # Merge semantic results, boosting duplicates
        for r in semantic_ranked:
            key = (r.name, r.file, r.line)
            if key in merged:
                # Found in both - apply 1.5x boost, mark as "both"
                existing = merged[key]
                existing.confidence = min(100.0, existing.confidence * 1.5)
                existing.search_source = "both"
            else:
                merged[key] = r

        # Update score field with normalized confidence so _rank_and_dedupe
        # and other downstream consumers use the hybrid-weighted ranking
        for r in merged.values():
            r.score = r.confidence

        # Sort by confidence descending
        return sorted(merged.values(), key=lambda r: r.confidence, reverse=True)

    def _to_percentile_ranks(self, results: list[SearchResult], source: str) -> list[SearchResult]:
        """
        Convert raw scores to percentile ranks (0-100).

        Args:
            results: List of search results with raw scores
            source: Search source to set ("keyword" or "semantic")

        Returns:
            Same results with confidence set to percentile rank
        """
        if not results:
            return []

        # Sort by score ascending for percentile calculation
        sorted_results = sorted(results, key=lambda r: r.score)
        n = len(sorted_results)

        for i, r in enumerate(sorted_results):
            # Percentile: position / total * 100
            r.confidence = ((i + 1) / n) * 100
            r.search_source = source  # type: ignore[assignment]

        return sorted_results

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

        # Glob pattern filter (path_pattern is deprecated alias)
        if config.glob:
            filtered = [r for r in filtered if matches_glob_pattern(r.file, config.glob)]

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
        self, query: str | list[str | list[str]], results: list[SearchResult]
    ) -> list[str]:
        """
        Generate smart next-step suggestions based on results.

        Prioritizes contextual, actionable suggestions over generic fillers.

        Args:
            query: Original query
            results: Search results

        Returns:
            List of suggestion strings (max 2)
        """
        suggestions = []

        # Always suggest detailed analysis of top result
        if results:
            top = results[0]
            if top.is_function() and top.function:
                suggestions.append(f"search_function('{top.function}', module_path='{top.module}')")
            suggestions.append(f"search_module('{top.module}')")

        # Contextual suggestion: many results in same module
        if len(
            suggestions
        ) < QueryConfig.MAX_SUGGESTIONS and self._has_multiple_results_in_same_module(results):
            common_module = self._get_most_common_module(results)
            suggestions.append(f"search_module('{common_module}', what_calls_it=True)")

        # Contextual suggestion: SQL/database keywords warrant string search
        query_text = self._normalize_query_text(query)
        if len(suggestions) < QueryConfig.MAX_SUGGESTIONS and self._is_sql_related_query(
            query_text
        ):
            suggestions.append("query(..., match_source='strings')")

        # Skip generic fillers like "query(..., recent=true)" and "query(..., filter_type='functions')"

        return suggestions[: QueryConfig.MAX_SUGGESTIONS]

    def _normalize_query_text(self, query: str | list[str | list[str]]) -> str:
        """Convert query to normalized lowercase text."""
        if isinstance(query, str):
            return query.lower()
        # Flatten nested lists (synonym groups)
        flat_terms: list[str] = []
        for q in query:
            if isinstance(q, list):
                flat_terms.extend(q)
            else:
                flat_terms.append(q)
        return " ".join(t.lower() for t in flat_terms)

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
        query: str | list[str | list[str]],
        show_snippets: bool = False,
        verbose: bool = False,
        offset: int = 0,
        context_lines: int = 2,
        context_before: int | None = None,
        context_after: int | None = None,
        fallback_note: str | None = None,
        pr_results: list[Any] | None = None,
        zero_result_hints: list[str] | None = None,
    ) -> str:
        """
        Format final report with results and suggestions.

        Args:
            results: Search results
            suggestions: Suggested next steps (shown with header for results with matches)
            max_results: Maximum number of results to show
            query: Original query
            show_snippets: Whether to show code snippet previews
            verbose: Whether to show verbose output
            offset: Number of results to skip (pagination)
            context_lines: Number of context lines in snippets (symmetric, like -C)
            context_before: Override for lines before match (like -B)
            context_after: Override for lines after match (like -A)
            fallback_note: Note explaining what fallback was applied (if any)
            pr_results: Optional list of PR search results (semantic)
            zero_result_hints: Hints for zero results (shown inline without header)

        Returns:
            Markdown formatted report
        """
        lines = []
        pr_results = pr_results or []

        # Apply offset and limit pagination
        paginated_results = results[offset : offset + max_results]

        # Header - compact format
        query_display = query if isinstance(query, str) else ", ".join(f'"{q}"' for q in query)
        total = len(results)
        showing = len(paginated_results)

        # Include offset info in header if pagination is active
        if offset > 0:
            if showing == 0:
                lines.append(
                    f"Query: {query_display} | {total} result{'s' if total != 1 else ''} "
                    f"(no results at offset {offset})\n\n"
                )
            else:
                lines.append(
                    f"Query: {query_display} | {total} result{'s' if total != 1 else ''} "
                    f"(showing {offset + 1}-{offset + showing})\n\n"
                )
        else:
            lines.append(
                f"Query: {query_display} | {total} result{'s' if total != 1 else ''} "
                f"(showing {showing})\n\n"
            )

        # Show fallback note if results came from a fallback search
        if fallback_note and results:
            lines.append(f"*Note: {fallback_note}*\n\n")

        # Results
        for i, result in enumerate(paginated_results, offset + 1):
            lines.append(
                self._format_result_snippet(
                    result, i, show_snippets, verbose, context_lines, context_before, context_after
                )
            )

        # Related PRs (from semantic search)
        if pr_results:
            lines.append("\n## Related PRs (semantic)\n\n")
            for pr in pr_results:
                state_icon = "✓" if pr.state == "merged" else "○" if pr.state == "open" else "×"
                lines.append(f"- {state_icon} **PR #{pr.pr_number}**: {pr.title}\n")
                if verbose and pr.author:
                    lines.append(f"  by {pr.author}")
                    if pr.merged_at:
                        lines.append(" (merged)")
                    elif pr.state:
                        lines.append(f" ({pr.state})")
                    lines.append("\n")

        # Zero-result hints (inline, no header)
        if zero_result_hints:
            lines.append("\n")
            for hint in zero_result_hints:
                lines.append(f"{hint}\n")

        # Suggestions for drilldown (with header, for results with matches)
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
        self,
        result: SearchResult,
        index: int,
        show_snippets: bool = False,
        verbose: bool = False,
        context_lines: int = 2,
        context_before: int | None = None,
        context_after: int | None = None,
    ) -> str:
        """
        Format a single result as a snippet (compact by default).

        Args:
            result: SearchResult to format
            index: Result number (1-indexed)
            show_snippets: Whether to show code snippet previews
            verbose: Whether to show full details (confidence %, docs, full context)
            context_lines: Number of context lines in snippets (symmetric, like -C)
            context_before: Override for lines before match (like -B)
            context_after: Override for lines after match (like -A)

        Returns:
            Formatted snippet
        """
        lines = []

        # Compact header: number, name, source indicator, and confidence on first line
        source_indicators = {"keyword": "(k)", "semantic": "(s)", "both": "(k+s)"}
        source_indicator = source_indicators.get(result.search_source, "")

        header_parts = [f"{index}. {result.name}"]
        if source_indicator:
            header_parts[0] += f" {source_indicator}"

        # Add confidence % by default, include tier label in verbose mode
        if result.percentile is not None:
            if verbose and result.tier_label:
                header_parts.append(f"({result.percentile:.0f}%) [{result.tier_label}]")
            else:
                header_parts.append(f"({result.percentile:.0f}%)")

        lines.append(" | ".join(header_parts) + "\n")

        # Path on second line
        lines.append(f"   {result.file}:{result.line}\n")

        # Documentation preview (only in verbose mode)
        if verbose and result.doc:
            doc = result.doc.strip().split("\n")[0]
            if len(doc) > 100:
                doc = doc[:100] + "..."
            lines.append(f"   {doc}\n")

        # Last modified timestamp - compact format
        if result.last_modified_at:
            try:
                dt = datetime.fromisoformat(result.last_modified_at.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                delta = datetime.now(timezone.utc) - dt
                time_ago = self._get_relative_time_string(delta)

                git_info = []
                if result.last_modified_pr:
                    git_info.append(f"#{result.last_modified_pr}")

                if git_info:
                    lines.append(f"   {time_ago} old ({' '.join(git_info)})\n")
                else:
                    lines.append(f"   {time_ago} old\n")
            except (ValueError, AttributeError):
                pass

        # Matched keywords indicator - compact single line
        if result.matched_keywords:
            context = None
            if verbose:
                # Full context in verbose mode
                context = format_matched_context(
                    matched_keywords=result.matched_keywords,
                    keyword_sources=result.keyword_sources,
                    doc_text=result.doc,
                    string_sources=result.string_sources,
                    use_ansi=True,
                )

            if context:
                lines.append(f"\n{context}\n")
            else:
                # Compact: just list keywords with source indicators
                self._append_keyword_list(lines, result)

        # Code snippet preview
        if show_snippets:
            # Full context when show_snippets is enabled
            snippet = self._extract_code_snippet(
                result.file, result.line, context_lines, context_before, context_after
            )
            if snippet:
                lines.append(f"\n```\n{snippet}\n```\n")
        else:
            # Show code line for pattern matches, doc excerpt for keyword matches
            if result.pattern_match:
                # Pattern match - show the code definition line
                single_line = self._extract_code_snippet(result.file, result.line, 0, 0, 0)
                if single_line:
                    lines.append(f"   {single_line}\n")
            elif result.doc and result.matched_keywords:
                # Keyword match from docs - show doc excerpt with keyword
                excerpt = self._extract_doc_excerpt(result.doc, result.matched_keywords)
                if excerpt:
                    lines.append(f'   "{excerpt}"\n')

        lines.append("\n")  # Blank line between results

        return "".join(lines)

    def _extract_doc_excerpt(self, doc: str, keywords: list[str], max_len: int = 80) -> str | None:
        """Extract a short excerpt from documentation containing the first matched keyword."""
        if not doc or not keywords:
            return None

        doc_lower = doc.lower()

        # Find the first keyword that appears in the doc
        for kw in keywords:
            kw_lower = kw.lower()
            pos = doc_lower.find(kw_lower)
            if pos >= 0:
                # Extract context around the keyword
                start = max(0, pos - 30)
                end = min(len(doc), pos + len(kw) + 50)
                excerpt = doc[start:end].strip()

                # Clean up: replace newlines, collapse whitespace
                excerpt = " ".join(excerpt.split())

                # Add ellipsis if truncated
                if start > 0:
                    excerpt = "..." + excerpt
                if end < len(doc):
                    excerpt = excerpt + "..."

                # Truncate if still too long
                if len(excerpt) > max_len:
                    excerpt = excerpt[: max_len - 3] + "..."

                return excerpt

        return None

    def _append_keyword_list(self, lines: list[str], result: SearchResult) -> None:
        """Append compact keyword list to lines."""
        kw_with_sources: list[str] = []
        source_suffixes = {"docs": "(d)", "strings": "(s)", "both": "(d+s)"}
        for kw in result.matched_keywords[: QueryConfig.MAX_KEYWORDS_TO_SHOW]:
            source = result.keyword_sources.get(kw, "")
            suffix = source_suffixes.get(source, "")
            kw_with_sources.append(f"{kw}{suffix}")

        matched_str = ", ".join(kw_with_sources)
        if len(result.matched_keywords) > QueryConfig.MAX_KEYWORDS_TO_SHOW:
            matched_str += f" +{len(result.matched_keywords) - QueryConfig.MAX_KEYWORDS_TO_SHOW}"
        lines.append(f"   {matched_str}\n")

    def _resolve_file_path(self, file_path: str) -> str:
        """Resolve a relative file path using the repo_path from index metadata."""
        import os

        # If already absolute, use as-is
        if os.path.isabs(file_path):
            return file_path

        repo_path = self.index.get("metadata", {}).get("repo_path")
        if not repo_path:
            return file_path

        # Try repo root first
        full_path = os.path.join(repo_path, file_path)
        if os.path.exists(full_path):
            return full_path

        # Try common source directories (SCIP indexers often store relative to src root)
        # Check for package directories (e.g., cicada/) and common patterns
        for subdir in ["cicada", "src", "lib", "app"]:
            candidate = os.path.join(repo_path, subdir, file_path)
            if os.path.exists(candidate):
                return candidate

        # Fall back to original path
        return file_path

    def _extract_code_snippet(
        self,
        file_path: str,
        line: int,
        context_lines: int = QueryConfig.DEFAULT_CONTEXT_LINES,
        context_before: int | None = None,
        context_after: int | None = None,
    ) -> str | None:
        """
        Extract code snippet from file with context lines.

        Args:
            file_path: Path to the file
            line: Target line number (1-indexed)
            context_lines: Number of context lines before and after (default: 2, like -C)
            context_before: Override for lines before match (like -B)
            context_after: Override for lines after match (like -A)

        Returns:
            Formatted code snippet with line numbers, or None if file not readable
        """
        try:
            resolved_path = self._resolve_file_path(file_path)
            with open(resolved_path, encoding="utf-8") as f:
                lines = f.readlines()

            # Convert to 0-indexed
            target_idx = line - 1

            # Resolve actual before/after values (overrides take precedence)
            before = context_before if context_before is not None else context_lines
            after = context_after if context_after is not None else context_lines

            # Calculate range
            start_idx = max(0, target_idx - before)
            end_idx = min(len(lines), target_idx + after + 1)

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

    def _find_related_terms(
        self,
        query: str,
        max_terms: int = QueryConfig.MAX_RELATED_TERMS,
        match_source: str = "all",
    ) -> list[str]:
        """
        Find related terms from the index using substring matching.

        Args:
            query: Query string
            max_terms: Maximum number of related terms to return
            match_source: Filter by keyword source ('all', 'docs', 'strings', 'comments')

        Returns:
            List of related terms found in the index
        """
        query_lower = query.lower()
        related = []

        # Collect keywords from the index based on match_source filter
        all_keywords = set()
        for module in self.index.get("modules", {}).values():
            # Only collect keywords from the relevant source
            if match_source in ["all", "docs"] and module.get("keywords"):
                all_keywords.update(k.lower() for k in module["keywords"])
            if match_source in ["all", "strings"] and module.get("string_keywords"):
                all_keywords.update(k.lower() for k in module["string_keywords"])
            if match_source in ["all", "comments"] and module.get("comment_keywords"):
                all_keywords.update(k.lower() for k in module["comment_keywords"])

            for func in module.get("functions", []):
                if match_source in ["all", "docs"] and func.get("keywords"):
                    all_keywords.update(k.lower() for k in func["keywords"])
                if match_source in ["all", "strings"] and func.get("string_keywords"):
                    all_keywords.update(k.lower() for k in func["string_keywords"])
                if match_source in ["all", "comments"] and func.get("comment_keywords"):
                    all_keywords.update(k.lower() for k in func["comment_keywords"])

        # Find terms where query is a substring of the keyword
        # (i.e., keyword contains the query, suggesting more specific terms)
        for keyword in all_keywords:
            if query_lower in keyword and keyword != query_lower:
                related.append(keyword)

        return related[:max_terms]

    def _search_prs_semantically(
        self, query: str | list[str | list[str]], max_results: int = 5
    ) -> list[Any]:
        """
        Search PRs semantically using embeddings.

        Args:
            query: Query string or list
            max_results: Maximum number of PR results

        Returns:
            List of PRSearchResult objects
        """
        if not self.repo_path:
            return []

        try:
            from cicada.embeddings.searcher import search_prs_semantically

            query_str = self._normalize_query_text(query)
            return search_prs_semantically(self.repo_path, query_str, top_n=max_results)
        except Exception:
            return []

    def _generate_zero_result_suggestions(
        self, query: str | list[str | list[str]], filters_applied: dict[str, Any]
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

        # Convert query to string for analysis (flatten nested lists)
        query_str = self._normalize_query_text(query)

        # 1. Find similar terms from index (substring matching only)
        match_source = filters_applied.get("match_source", "all")
        similar = self._find_related_terms(query_str, match_source=match_source)
        if similar:
            suggestions.append(f"Did you mean: {', '.join(f'`{t}`' for t in similar)}?")

        # 2. Suggest removing/broadening filters
        active_filters = []
        if filters_applied.get("scope") != "all":
            active_filters.append(f"scope='{filters_applied['scope']}'")
        if filters_applied.get("recent"):
            active_filters.append("recent=true")
        if filters_applied.get("result_type") != "all":
            active_filters.append(f"result_type='{filters_applied['result_type']}'")
        if filters_applied.get("glob"):
            active_filters.append(f"glob='{filters_applied['glob']}'")

        if active_filters:
            suggestions.append(f"Try broadening: Remove filters ({', '.join(active_filters)})")

        # 3. Suggest trying pattern search if keyword search
        if isinstance(query, str) and not self._is_pattern_query(query):
            suggestions.append(f"Try pattern search: `{query}*` or `*.{query}*`")

        return suggestions

    def execute_query(
        self,
        query: str | list[str | list[str]],
        scope: str = "all",
        recent: bool = False,
        result_type: str = "all",
        match_source: str = "all",
        max_results: int = 10,
        glob: str | None = None,
        arity: int | None = None,
        show_snippets: bool = False,
        verbose: bool = False,
        offset: int = 0,
        context_lines: int = 2,
        context_before: int | None = None,
        context_after: int | None = None,
    ) -> str:
        """
        Execute a query and return formatted results.

        Args:
            query: Query string or list of strings
            scope: Scope filter ("all", "public", "private")
            recent: Filter to recently changed code only (last 14 days)
            result_type: Type filter ("all", "modules", "functions")
            match_source: Match source filter ("all", "docs", "strings", "comments")
            max_results: Maximum number of results to show
            glob: Optional glob pattern for file paths
            arity: Optional arity filter for functions
            show_snippets: Whether to show code snippet previews (default: False)
            verbose: Whether to show verbose output (default: False)
            offset: Number of results to skip (pagination, default: 0)
            context_lines: Number of context lines in snippets (default: 2, like -C)
            context_before: Override for lines before match (like -B)
            context_after: Override for lines after match (like -A)

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
            result_type=result_type,  # type: ignore
            match_source=match_source,  # type: ignore
            max_results=max_results,
            glob=glob,
            arity=arity,
            show_snippets=show_snippets,
            offset=offset,
            context_lines=context_lines,
            context_before=context_before,
            context_after=context_after,
        )

        # Analyze query
        strategy = self._analyze_query(query)

        # Call tools
        raw_results = self._call_tools(strategy, options.result_type, options.match_source)

        # Apply filters
        filter_config = options.to_filter_config()
        filtered_results = self._apply_filters(raw_results, filter_config)

        # Rank and deduplicate
        ranked_results = self._rank_and_dedupe(filtered_results)

        # Attach tier information based on score distribution
        ranked_results = self._attach_tier_info(ranked_results)

        # Check for zero results - try fallbacks first, then generate suggestions
        fallback_note: str | None = None
        if len(ranked_results) == 0:
            # Try fallback strategies before giving up
            from cicada.mcp.fallbacks import apply_query_fallbacks

            def search_with_options(fallback_options: QueryOptions) -> list[SearchResult]:
                """Execute search with given options."""
                fallback_raw = self._call_tools(
                    strategy, fallback_options.result_type, fallback_options.match_source
                )
                fallback_filter_config = fallback_options.to_filter_config()
                fallback_filtered = self._apply_filters(fallback_raw, fallback_filter_config)
                return self._rank_and_dedupe(fallback_filtered)

            fallback_result = apply_query_fallbacks(options, search_with_options)
            if fallback_result.results:
                ranked_results = self._attach_tier_info(fallback_result.results)
                fallback_note = fallback_result.note

        # Generate suggestions based on final results
        zero_result_hints: list[str] = []
        suggestions: list[str] = []
        if len(ranked_results) == 0:
            # Generate zero-result hints (shown inline, not as "next steps")
            filters_applied = {
                "scope": options.scope,
                "recent": options.recent,
                "result_type": options.result_type,
                "match_source": options.match_source,
                "glob": options.glob,
            }
            zero_result_hints = self._generate_zero_result_suggestions(query, filters_applied)
        else:
            # Generate normal suggestions based on results
            suggestions = self._generate_suggestions(query, ranked_results)

        # Search PRs semantically if embeddings mode is enabled
        pr_results = []
        if self.use_embeddings and self.repo_path:
            pr_results = self._search_prs_semantically(query)

        # Format report with offset and context_lines
        return self._format_report(
            ranked_results,
            suggestions,
            options.max_results,
            query,
            options.show_snippets,
            verbose,
            options.offset,
            options.context_lines,
            options.context_before,
            options.context_after,
            fallback_note,
            pr_results,
            zero_result_hints,
        )
