"""
Analysis Tool Handlers.

Handles query tool and dead code detection tools.
"""

from typing import Any

from mcp.types import TextContent


class AnalysisHandler:
    """Handler for analysis-related tools (query, dead code detection)."""

    def __init__(self, index: dict[str, Any], has_keywords: bool):
        """
        Initialize the analysis handler.

        Args:
            index: The code index containing modules and functions
            has_keywords: Whether keywords are available in the index
        """
        self.index = index
        self.has_keywords = has_keywords

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

    async def query(
        self,
        query: str | list[str],
        scope: str = "all",
        filter_type: str = "all",
        match_source: str = "all",
        max_results: int = 10,
        path_pattern: str | None = None,
        include_tests: bool = True,
        show_snippets: bool = False,
    ) -> list[TextContent]:
        """
        Smart code discovery - intelligently search by keywords or patterns.

        Args:
            query: Query string or list of strings (keywords OR patterns)
            scope: Scope filter ('all', 'recent', 'public', 'private')
            filter_type: Type filter ('all', 'modules', 'functions')
            match_source: Match source filter ('all', 'docs', 'strings')
            max_results: Maximum number of results to show
            path_pattern: Optional glob pattern for file paths
            include_tests: Whether to include test files
            show_snippets: Whether to show code snippet previews (default: False)

        Returns:
            TextContent with formatted query results and suggestions
        """
        from cicada.query import QueryOrchestrator

        # Check if keywords are available (if using keyword search)
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

        # Create orchestrator and execute query
        orchestrator = QueryOrchestrator(self.index)

        result = orchestrator.execute_query(
            query=query,
            scope=scope,
            filter_type=filter_type,
            match_source=match_source,
            max_results=max_results,
            path_pattern=path_pattern,
            include_tests=include_tests,
            show_snippets=show_snippets,
        )

        return [TextContent(type="text", text=result)]
