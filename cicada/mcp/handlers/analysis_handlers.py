"""
Analysis Tool Handlers.

Handles keyword/feature search and dead code detection tools.
"""

import asyncio
import json
from typing import Any

import jq  # type: ignore[import-untyped]
from mcp.types import TextContent

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

    def __init__(self, index: dict[str, Any], has_keywords: bool):
        """
        Initialize the analysis handler.

        Args:
            index: The code index containing modules and functions
            has_keywords: Whether keywords are available in the index
        """
        self.index = index
        self.has_keywords = has_keywords

    async def search_by_keywords(
        self,
        keywords: list[str],
        filter_type: str = "all",
        min_score: float = 0.0,
        match_source: str = "all",
    ) -> list[TextContent]:
        """
        Search for modules and functions by keywords.

        Args:
            keywords: List of keywords to search for
            filter_type: Filter results by type ('all', 'modules', 'functions'). Defaults to 'all'.
            min_score: Minimum relevance score threshold (0.0 to 1.0). Defaults to 0.0.
            match_source: Filter by keyword source ('all', 'docs', 'strings'). Defaults to 'all'.

        Returns:
            TextContent with formatted search results
        """
        from cicada.elixir.format import ModuleFormatter
        from cicada.keyword_search import KeywordSearcher
        from cicada.mcp.filter_utils import filter_by_score_threshold

        # Check if keywords are available (cached at initialization)
        if not self.has_keywords:
            error_msg = (
                "No keywords found in index. Please rebuild the index with keyword extraction:\n\n"
                "  cicada index           # Default: reuse configured tier\n"
                "  cicada index --force --regular   # BERT + GloVe (regular tier)\n"
                "  cicada index --force --fast      # Fast: Token-based + lemminflect\n"
                "  cicada index --force --max       # Max: BERT + FastText\n\n"
                "This will extract keywords from documentation for semantic search."
            )
            return [TextContent(type="text", text=error_msg)]

        # Perform the search with match_source filtering
        searcher = KeywordSearcher(self.index, match_source=match_source)
        results = searcher.search(keywords, top_n=20, filter_type=filter_type)

        # Apply score threshold filter
        if min_score > 0.0:
            results = filter_by_score_threshold(results, min_score)

        if not results:
            if min_score > 0.0:
                result = f"No results found for keywords: {', '.join(keywords)} with min_score >= {min_score}"
            else:
                result = f"No results found for keywords: {', '.join(keywords)}"
            return [TextContent(type="text", text=result)]

        # Format results
        formatted_result = ModuleFormatter.format_keyword_search_results_markdown(
            results, show_scores=True
        )

        return [TextContent(type="text", text=formatted_result)]

    async def find_dead_code(self, min_confidence: str, output_format: str) -> list[TextContent]:
        """
        Find potentially unused public functions.

        Args:
            min_confidence: Minimum confidence level ('high', 'medium', or 'low')
            output_format: Output format ('markdown' or 'json')

        Returns:
            TextContent with formatted dead code analysis
        """
        from cicada.dead_code.analyzer import DeadCodeAnalyzer
        from cicada.dead_code.finder import (
            filter_by_confidence,
            format_json,
            format_markdown,
        )

        # Run analysis
        analyzer = DeadCodeAnalyzer(self.index)
        results = analyzer.analyze()

        # Filter by confidence
        results = filter_by_confidence(results, min_confidence)

        # Format output
        output = format_json(results) if output_format == "json" else format_markdown(results)

        return [TextContent(type="text", text=output)]

    async def query_jq(self, query: str, output_format: str = "json") -> list[TextContent]:
        """
        Execute a jq query against the index.

        Args:
            query: jq query expression
            output_format: Output format ('json', 'compact', 'pretty')

        Returns:
            TextContent with jq query results
        """
        try:
            result = await self._execute_jq_query(query)

            if result is None:
                return [
                    TextContent(
                        type="text",
                        text="Query returned null. The field doesn't exist or filter matched nothing.",
                    )
                ]

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
            return self._create_jq_syntax_error_response(e)
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

    def _create_jq_syntax_error_response(self, error: ValueError) -> list[TextContent]:
        """Create helpful syntax error response with hints."""
        error_str = str(error).lower()

        msg = f"jq query failed: {error}\n\nCommon issues:\n"
        msg += "  • Check jq syntax\n"
        msg += "  • Use '?' for optional fields: '.functions[]?'\n"
        msg += "  • Verify operations match data types\n\n"

        if "iterate" in error_str and "null" in error_str:
            msg += "HINT: You're iterating over null. Use '.functions[]?' instead of '.functions[]'\n\n"
        elif "unexpected" in error_str or "invalid" in error_str:
            msg += "HINT: Check for missing quotes, unbalanced brackets, or undefined functions\n\n"

        msg += "Quick reference:\n"
        msg += "  • List keys: '.modules | keys'\n"
        msg += "  • Filter: '.modules | map(select(.keywords))'\n"
        msg += "  • See CLAUDE.md for complete schema\n"

        return [TextContent(type="text", text=msg)]
