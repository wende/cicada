"""
Analysis Tool Handlers.

Handles keyword/feature search tools.
"""

import asyncio
import json
from typing import TYPE_CHECKING, Any

import jq  # type: ignore[import-untyped]
from mcp.types import TextContent

if TYPE_CHECKING:
    from cicada.mcp.handlers.index_manager import IndexManager

# Maximum result size for jq queries before truncation.
# Set to 1MB to balance between useful results and preventing memory issues
# when queries return large portions of the index. Results exceeding this
# limit are truncated with a helpful message suggesting query refinement.
MAX_JQ_RESULT_SIZE_BYTES = 1024 * 1024

# Maximum execution time for jq queries before timeout.
# 30 seconds allows for complex queries on large indices while preventing
# runaway queries from blocking the server. Most queries complete in < 1 second.
MAX_JQ_QUERY_TIMEOUT_SECONDS = 30.0


def _format_error_sections(prefix: str, error: Exception, sections: dict[str, list[str]]) -> str:
    """Format error message with structured sections."""
    parts = [f"{prefix}:\n\n{str(error)}\n"]
    for section_name, bullets in sections.items():
        parts.append(f"{section_name}:")
        parts.extend(f"  • {bullet}" for bullet in bullets)
        parts.append("")
    return "\n".join(parts).rstrip()


class AnalysisHandler:
    """Handler for analysis-related tools (keyword search, dead code detection)."""

    def __init__(self, index_manager: "IndexManager"):
        """
        Initialize the analysis handler.

        Args:
            index_manager: The index manager providing access to the code index
        """
        self.index_manager = index_manager

    @property
    def index(self) -> dict[str, Any]:
        """Get the current index from the index manager."""
        return self.index_manager.index

    @property
    def has_keywords(self) -> bool:
        """Check if keywords are available in the current index."""
        return self.index_manager.has_keywords

    @property
    def has_embeddings(self) -> bool:
        """Check if embeddings are available for this repository."""
        return self.index_manager.has_embeddings

    @property
    def indexing_mode(self) -> str:
        """Get the configured indexing mode."""
        return self.index_manager.indexing_mode

    @property
    def repo_path(self):
        """Get the repository path."""
        return self.index_manager.repo_path

    async def search_by_keywords(
        self,
        keywords: list[str | list[str]],
        filter_type: str = "all",
        min_score: float = 0.0,
        match_source: str = "all",
        cochange_boost: float = 0.5,
    ) -> list[TextContent]:
        """
        Search for modules and functions by keywords.

        Args:
            keywords: List of keywords to search for
            filter_type: Filter results by type ('all', 'modules', 'functions'). Defaults to 'all'.
            min_score: Minimum relevance score threshold (0.0 to 1.0). Defaults to 0.0.
            match_source: Filter by keyword source ('all', 'docs', 'strings'). Defaults to 'all'.
            cochange_boost: Boost factor for co-change relationships (default: 0.5, set to 0.0 to disable).

        Returns:
            TextContent with formatted search results
        """
        from cicada.format import ModuleFormatter
        from cicada.keyword_search import KeywordSearcher
        from cicada.mcp.filter_utils import filter_by_score_threshold

        # Check if keywords are available (cached at initialization)
        if not self.has_keywords:
            return [
                TextContent(type="text", text="No keywords in index. Run 'cicada index' to enable.")
            ]

        # Perform the search with match_source filtering and co-change boosting
        searcher = KeywordSearcher(
            self.index, match_source=match_source, cochange_boost=cochange_boost
        )
        results = searcher.search(keywords, top_n=20, filter_type=filter_type)

        # Apply score threshold filter
        if min_score > 0.0:
            results = filter_by_score_threshold(results, min_score)

        if not results:
            # Format keywords for display (handling mixed lists)
            kw_display_parts: list[str] = []
            for k in keywords:
                if isinstance(k, list):
                    kw_display_parts.append(f"[{'|'.join(str(sub) for sub in k)}]")
                else:
                    kw_display_parts.append(str(k))
            kw_display = ", ".join(kw_display_parts)

            if min_score > 0.0:
                result = (
                    f"No results found for keywords: {kw_display} with min_score >= {min_score}"
                )
            else:
                result = f"No results found for keywords: {kw_display}"
            return [TextContent(type="text", text=result)]

        # Format results
        language = self.index.get("metadata", {}).get("language", "elixir")
        formatted_result = ModuleFormatter.format_keyword_search_results_markdown(
            results, show_scores=True, language=language
        )

        return [TextContent(type="text", text=formatted_result)]

    async def suggest_keywords(
        self,
        keywords: list[str],
        mode: str,
        search_results: list | None = None,
        top_n: int = 5,
        min_cooccurrence: int = 1,
        min_result_count: int = 2,
    ) -> list[TextContent]:
        """
        Suggest related keywords based on co-occurrence patterns.

        Args:
            keywords: Original query keywords
            mode: 'expand' for related keywords, 'narrow' for filtering keywords
            search_results: Optional search results for narrow mode
            top_n: Maximum number of suggestions to return
            min_cooccurrence: Minimum co-occurrence count (for expand mode)
            min_result_count: Minimum result count (for narrow mode)

        Returns:
            TextContent with formatted keyword suggestions
        """
        from cicada.keyword_search import KeywordSearcher

        # Check if co-occurrence data is available
        if not self.index.get("cooccurrences"):
            return [
                TextContent(
                    type="text", text="No co-occurrence data. Run 'cicada index' to enable."
                )
            ]

        # Initialize searcher to get access to co-occurrence suggestions
        searcher = KeywordSearcher(self.index)

        if mode == "expand":
            # Suggest related keywords to expand the search
            suggestions = searcher.suggest_related_keywords(
                keywords, top_n=top_n, min_cooccurrence=min_cooccurrence
            )

            if not suggestions:
                return [TextContent(type="text", text=f"No suggestions for: {', '.join(keywords)}")]

            # Format suggestions for expand mode
            msg = f"Related keywords for: {', '.join(keywords)}\n\n"
            msg += "These keywords frequently appear together in your codebase:\n\n"
            for i, suggestion in enumerate(suggestions, 1):
                kw = suggestion["keyword"]
                count = suggestion["cooccurrence_count"]
                cooccurs_with = ", ".join(f"'{w}'" for w in suggestion["cooccurs_with"])
                msg += f"{i}. **{kw}** (co-occurs {count}x with {cooccurs_with})\n"

            msg += "\nTry searching with: " + ", ".join(
                [f"'{s['keyword']}'" for s in suggestions[:3]]
            )

            return [TextContent(type="text", text=msg)]

        else:  # mode == "narrow"
            # Suggest keywords to narrow down results
            if not search_results:
                msg = "search_results is required for mode='narrow'"
                return [TextContent(type="text", text=msg)]

            suggestions = searcher.suggest_narrowing_keywords(
                keywords, search_results, top_n=top_n, min_result_count=min_result_count
            )

            if not suggestions:
                return [
                    TextContent(
                        type="text", text=f"No narrowing keywords for: {', '.join(keywords)}"
                    )
                ]

            # Format suggestions for narrow mode
            msg = f"Add these keywords to narrow down {len(search_results)} results:\n\n"
            for i, suggestion in enumerate(suggestions, 1):
                kw = suggestion["keyword"]
                count = suggestion["result_count"]
                cooccurs_info = ""
                if suggestion.get("cooccurs_with"):
                    cooccurs_with = ", ".join(f"'{w}'" for w in suggestion["cooccurs_with"])
                    cooccurs_info = f" (related to {cooccurs_with})"
                msg += f"{i}. **{kw}** (appears in {count}/{len(search_results)} results){cooccurs_info}\n"

            msg += "\nTry searching with: " + ", ".join(
                keywords + [f"'{s['keyword']}'" for s in suggestions[:2]]
            )

            return [TextContent(type="text", text=msg)]

    async def query(
        self,
        query: str | list[str | list[str]],
        scope: str = "all",
        recent: bool = False,
        result_type: str = "all",
        match_source: str = "all",
        max_results: int = 10,
        glob: str | None = None,
        show_snippets: bool = False,
        verbose: bool = False,
        offset: int = 0,
        context_lines: int = 2,
        context_before: int | None = None,
        context_after: int | None = None,
    ) -> list[TextContent]:
        """
        Smart code discovery - intelligently search by keywords or patterns.

        Args:
            query: Query string or list of strings (keywords OR patterns)
            scope: Scope filter ('all', 'public', 'private')
            recent: Filter to recently changed code only (last 14 days)
            result_type: Type filter ('all', 'modules', 'functions')
            match_source: Match source filter ('all', 'docs', 'strings', 'comments')
            max_results: Maximum number of results to show
            glob: Optional glob pattern for file paths
            show_snippets: Whether to show code snippet previews (default: False)
            verbose: Whether to show verbose output with docs and confidence (default: False)
            offset: Number of results to skip (for pagination, default: 0)
            context_lines: Number of context lines in snippets (default: 2, like -C)
            context_before: Override for lines before match (like -B)
            context_after: Override for lines after match (like -A)

        Returns:
            TextContent with formatted query results and suggestions
        """
        from cicada.query import QueryOrchestrator

        # Check if search capability is available
        use_embeddings = self.indexing_mode == "embeddings" and self.has_embeddings
        if not use_embeddings and not self.has_keywords:
            return [
                TextContent(
                    type="text", text="No search index available. Run 'cicada index' to enable."
                )
            ]

        # Create orchestrator and execute query
        orchestrator = QueryOrchestrator(
            self.index,
            repo_path=str(self.repo_path),
            use_embeddings=use_embeddings,
        )

        result = orchestrator.execute_query(
            query=query,
            scope=scope,
            recent=recent,
            result_type=result_type,
            match_source=match_source,
            max_results=max_results,
            glob=glob,
            show_snippets=show_snippets,
            verbose=verbose,
            offset=offset,
            context_lines=context_lines,
            context_before=context_before,
            context_after=context_after,
        )

        return [TextContent(type="text", text=result)]

    async def query_jq(
        self, query: str, output_format: str = "json", sample: bool = False
    ) -> list[TextContent]:
        """
        Execute a jq query against the index.

        Args:
            query: jq query expression
            output_format: Output format ('json', 'compact', 'pretty')
            sample: If True, automatically limit results to first 5 items (default: False)

        Returns:
            TextContent with jq query results
        """
        try:
            # Handle schema discovery
            query = self._handle_schema_query(query)

            # Apply sample mode if requested
            if sample:
                query = self._apply_sample_mode(query)

            result = await self._execute_jq_query(query)

            if result is None:
                return [
                    TextContent(
                        type="text",
                        text="Query returned null. The field doesn't exist or filter matched nothing.",
                    )
                ]

            # Early size estimation before formatting
            early_warning = self._estimate_result_size(result, query, sample)
            if early_warning:
                return [TextContent(type="text", text=early_warning)]

            output = self._format_result(result, output_format)
            return self._handle_result_size(output)

        except asyncio.TimeoutError:
            return [
                TextContent(
                    type="text",
                    text=(
                        f"jq query timed out after {MAX_JQ_QUERY_TIMEOUT_SECONDS:.0f} seconds.\n\n"
                        "The query may be too complex or the index too large. "
                        "Try simplifying your query or filtering the data first:\n\n"
                        "Examples:\n"
                        "  • Instead of: '.modules[]'\n"
                        "    Try: '.modules | to_entries | .[0:10]'\n"
                        "  • Use 'select()' to filter early: '.modules | to_entries | map(select(.value.keywords))'\n"
                        "  • Access specific fields: '.modules.MyModule' instead of '.modules[]'"
                    ),
                )
            ]
        except ValueError as e:
            return self._create_jq_syntax_error_response(e, query)
        except Exception as e:
            sections = {
                "This may indicate": [
                    "Malformed index data",
                    "Very large intermediate data structures",
                    "Python jq library issue",
                ],
                "Try": [
                    "Simplifying your query",
                    "Testing with a simpler query first (e.g., '.modules | keys')",
                    "Checking if the index is corrupted (try rebuilding)",
                ],
            }
            error_msg = _format_error_sections("Unexpected error executing jq query", e, sections)
            return [TextContent(type="text", text=error_msg)]

    async def _execute_jq_query(self, query: str) -> Any:
        """
        Execute jq query with timeout protection.

        Args:
            query: jq query expression

        Returns:
            Query result (can be any JSON-serializable type)
        """

        def run_jq() -> Any:
            compiled = jq.compile(query)
            result = compiled.input(self.index)
            results = list(result)
            return results[0] if len(results) == 1 else results

        return await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(None, run_jq),  # type: ignore[arg-type]
            timeout=MAX_JQ_QUERY_TIMEOUT_SECONDS,
        )

    def _format_result(self, result: Any, output_format: str) -> str:
        """Format query result as JSON string."""
        return json.dumps(
            result,
            separators=(",", ":") if output_format == "compact" else None,
            indent=None if output_format == "compact" else 2,
        )

    def _handle_result_size(self, output: str) -> list[TextContent]:
        """
        Check result size and truncate if needed.

        Args:
            output: Formatted query result

        Returns:
            TextContent with result or truncated result with warning
        """
        if len(output) <= MAX_JQ_RESULT_SIZE_BYTES:
            return [TextContent(type="text", text=output)]

        truncated = self._truncate_at_newline(output)
        message = self._create_truncation_message(len(output))
        return [TextContent(type="text", text=truncated + message)]

    def _truncate_at_newline(self, text: str) -> str:
        """
        Truncate text at last complete line within size limit.

        Args:
            text: Text to truncate

        Returns:
            Truncated text ending at a complete line
        """
        truncated = text[:MAX_JQ_RESULT_SIZE_BYTES]
        last_newline = truncated.rfind("\n")
        return truncated[:last_newline] if last_newline > 0 else truncated

    def _create_truncation_message(self, original_size: int) -> str:
        """
        Create truncation warning message.

        Args:
            original_size: Original result size in bytes

        Returns:
            Formatted truncation warning
        """
        return (
            f"\n\n--- RESULT TRUNCATED ---\n"
            f"Result size: {original_size:,} bytes (limit: {MAX_JQ_RESULT_SIZE_BYTES:,} bytes)\n"
            f"Consider adding filters to your query to limit results:\n"
            f"  • Add '| .[0:10]' to get first 10 items\n"
            f"  • Use 'select()' to filter data\n"
            f"  • Request specific fields instead of entire objects"
        )

    def _handle_schema_query(self, query: str) -> str:
        """
        Handle schema discovery queries by replacing '| schema' with appropriate jq.

        Args:
            query: Original jq query

        Returns:
            Modified query with schema discovery replaced
        """
        import re

        # Match '| schema' at the end of the query (with optional whitespace)
        schema_pattern = r"\|\s*schema\s*$"

        if re.search(schema_pattern, query):
            # Remove '| schema' and replace with structure analysis
            base_query = re.sub(schema_pattern, "", query).rstrip()

            # Add logic to detect array vs object and show appropriate structure
            # For arrays: show keys of first element
            # For objects: show keys directly
            schema_query = (
                f"({base_query}) | "
                f'if type == "array" then '
                f'(if length > 0 then .[0] | keys else "Empty array" end) '
                f"else "
                f"keys "
                f"end"
            )
            return schema_query

        return query

    def _apply_sample_mode(self, query: str) -> str:
        """
        Apply sample mode to limit query results.

        Args:
            query: Original jq query

        Returns:
            Modified query with result limiting
        """
        # Wrap query to limit results to first 5 items
        # This works for both arrays and object entries
        return f'({query}) | if type == "array" then .[0:5] else . | to_entries | .[0:5] | from_entries end'

    def _estimate_result_size(self, result: Any, query: str, sample: bool) -> str | None:
        """
        Estimate result size before formatting and provide early warning if too large.

        Args:
            result: Query result from jq
            query: Original query string
            sample: Whether sample mode is enabled

        Returns:
            Warning message if result is too large, None otherwise
        """
        # Quick size estimation using compact JSON
        try:
            compact_size = len(json.dumps(result, separators=(",", ":")))
        except (TypeError, ValueError):
            # Can't estimate, let it proceed
            return None

        # If size is very large (>500KB), warn before formatting
        size_threshold = 500 * 1024  # 500KB
        if compact_size > size_threshold:
            size_mb = compact_size / (1024 * 1024)

            msg = f"Query result is very large (~{size_mb:.1f}MB, limit: ~1MB).\n\n"
            msg += "The result will be truncated. Consider:\n"

            # Provide specific suggestions based on the query
            if ".modules" in query and "to_entries" not in query:
                msg += "  • Preview count: .modules | keys | length\n"
                msg += "  • List modules: .modules | keys\n"
                msg += "  • Preview 10: .modules | to_entries | .[0:10]\n"
            elif "functions" in query:
                msg += "  • Count functions: .modules[].functions | length\n"
                msg += "  • Preview 5: .modules[].functions[0:5]\n"
            else:
                msg += "  • Use 'sample: true' parameter for auto-limiting\n"
                msg += "  • Add '| .[0:10]' to preview first 10 items\n"
                msg += "  • Use 'select()' to filter data\n"

            if not sample:
                msg += "\nTip: Set 'sample: true' to automatically limit to 5 results\n"

            return msg

        return None

    def _create_jq_syntax_error_response(self, error: ValueError, query: str) -> list[TextContent]:
        """Create helpful syntax error response with hints and visual error pointer."""
        import re

        error_str = str(error)
        error_str_lower = error_str.lower()

        # Try to extract line and column information from the error message
        # Format: "jq: error (at <stdin>:0): compile error near line 1, column 29: ..."
        # or: "jq: parse error: ..."
        match = re.search(r"line (\d+), column (\d+)", error_str)

        if match:
            line_num = int(match.group(1))
            col_num = int(match.group(2))

            # Get the specific line from the query
            query_lines = query.split("\n")
            # Use ternary for cleaner code
            error_line = (
                query_lines[line_num - 1]
                if 1 <= line_num <= len(query_lines)
                else query  # Single-line query or line number out of range
            )

            # Format error message with visual pointer
            msg = f"jq: error: syntax error at line {line_num}, column {col_num}:\n"
            msg += f"    {error_line}\n"
            msg += " " * (4 + col_num - 1) + "^\n\n"
        else:
            # No line/column info, just show the error and query
            msg = f"jq query failed: {error}\n\n"
            msg += f"Query: {query}\n\n"

        msg += "Common issues:\n"
        msg += "  • Check jq syntax\n"
        msg += "  • Use '?' for optional fields: '.functions[]?'\n"
        msg += "  • Verify operations match data types\n\n"

        if "iterate" in error_str_lower and "null" in error_str_lower:
            msg += "HINT: You're iterating over null. Use '.functions[]?' instead of '.functions[]'\n\n"
        elif "unexpected" in error_str_lower or "invalid" in error_str_lower:
            msg += "HINT: Check for missing quotes, unbalanced brackets, or undefined functions\n\n"

        msg += "Quick reference:\n"
        msg += "  • List keys: '.modules | keys'\n"
        msg += "  • Filter: '.modules | map(select(.keywords))'\n"
        msg += "  • See CLAUDE.md for complete schema\n"

        return [TextContent(type="text", text=msg)]
