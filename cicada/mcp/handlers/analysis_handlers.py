"""
Analysis Tool Handlers.

Handles keyword/feature search and dead code detection tools.
"""

from typing import Any

from mcp.types import TextContent


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
            msg = (
                "Co-occurrence data not available in the index.\n"
                "Co-occurrence tracking is built during indexing when keyword extraction is enabled.\n"
                "To enable:\n"
                "1. Run: cicada index --extract-keywords\n"
                "2. The index will automatically include co-occurrence data"
            )
            return [TextContent(type="text", text=msg)]

        # Initialize searcher to get access to co-occurrence suggestions
        searcher = KeywordSearcher(self.index)

        if mode == "expand":
            # Suggest related keywords to expand the search
            suggestions = searcher.suggest_related_keywords(
                keywords, top_n=top_n, min_cooccurrence=min_cooccurrence
            )

            if not suggestions:
                msg = f"No keyword suggestions found for: {', '.join(keywords)}\n"
                msg += "\nThis may happen if:\n"
                msg += "• The keywords don't appear in the codebase\n"
                msg += "• The keywords don't co-occur with other keywords\n"
                msg += "• The min_cooccurrence threshold is too high"
                return [TextContent(type="text", text=msg)]

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
                msg = f"No narrowing keywords found for: {', '.join(keywords)}\n"
                msg += "\nThis may happen if:\n"
                msg += "• The search results don't have common keywords\n"
                msg += "• The min_result_count threshold is too high"
                return [TextContent(type="text", text=msg)]

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
