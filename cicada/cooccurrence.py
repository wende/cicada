"""
Co-occurrence analysis for keyword suggestions.

Tracks which keywords appear together in the same context (function docs + signatures)
to provide context-aware keyword suggestions.

Author: Cicada Team
"""

from collections import defaultdict
from typing import Any


class CooccurrenceAnalyzer:
    """
    Analyzes keyword co-occurrences to suggest related keywords.

    Co-occurrences are tracked at the function/module level - keywords that appear
    together in the same documentation or function signature are considered co-occurring.
    """

    def __init__(self, index: dict[str, Any]):
        """
        Initialize the analyzer with an index.

        Args:
            index: The Cicada index dictionary containing modules and metadata
        """
        self.index = index
        self.cooccurrence_matrix = self._build_cooccurrence_matrix()

    def _build_cooccurrence_matrix(self) -> dict[str, dict[str, int]]:
        """
        Build a co-occurrence matrix from the index.

        For each keyword, tracks how many times it appears together with other keywords
        in the same context (function doc/signature or module doc).

        Returns:
            Dict mapping keyword -> {co-occurring_keyword -> count}
        """
        matrix: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        # Process all modules
        for module_data in self.index.get("modules", {}).values():
            # Get module-level keywords (pre-expansion only)
            module_keywords = self._extract_all_keywords(
                module_data.get("extracted_keywords"),
                module_data.get("extracted_string_keywords"),
                module_data.get("extracted_comment_keywords"),
            )

            # Record module-level co-occurrences
            self._record_cooccurrences(matrix, module_keywords)

            # Process all functions in the module
            for func in module_data.get("functions", []):
                # Get function-level keywords (pre-expansion only)
                func_keywords = self._extract_all_keywords(
                    func.get("extracted_keywords"),
                    func.get("extracted_string_keywords"),
                    func.get("extracted_comment_keywords"),
                )

                # Also include function name components as implicit keywords
                # e.g., "validate_provider_key" -> ["validate", "provider", "key"]
                func_name = func.get("name", "")
                name_parts = self._split_identifier(func_name)
                func_keywords.update(name_parts)

                # Record function-level co-occurrences
                self._record_cooccurrences(matrix, func_keywords)

        return dict(matrix)

    def _extract_all_keywords(
        self,
        doc_keywords: dict | list | None,
        string_keywords: dict | list | None,
        comment_keywords: dict | list | None = None,
    ) -> set[str]:
        """
        Extract all keywords from doc, string, and comment sources.

        Args:
            doc_keywords: Keywords from documentation (dict or list)
            string_keywords: Keywords from string literals (dict or list)
            comment_keywords: Keywords from inline comments (dict or list)

        Returns:
            Set of lowercase keywords
        """
        keywords = set()

        for source in (doc_keywords, string_keywords, comment_keywords):
            if not source:
                continue
            if isinstance(source, list):
                keywords.update(kw.lower() for kw in source)
            else:
                keywords.update(k.lower() for k in source)

        return keywords

    def _split_identifier(self, identifier: str) -> set[str]:
        """
        Split an identifier into component words.

        Handles snake_case, camelCase, and PascalCase.

        Args:
            identifier: The identifier to split (e.g., "validate_provider_key")

        Returns:
            Set of lowercase component words
        """
        if not identifier:
            return set()

        # Replace underscores with spaces
        identifier = identifier.replace("_", " ")

        # Insert spaces before capital letters (for camelCase/PascalCase)
        result: list[str] = []
        for i, char in enumerate(identifier):
            if char.isupper() and i > 0 and identifier[i - 1].islower():
                result.append(" ")
            result.append(str(char))

        identifier = "".join(result)

        # Split on spaces and filter out short words
        parts = identifier.lower().split()
        return {p for p in parts if len(p) >= 3}

    def _record_cooccurrences(self, matrix: dict[str, dict[str, int]], keywords: set[str]) -> None:
        """
        Record co-occurrences for a set of keywords that appear together.

        Args:
            matrix: The co-occurrence matrix to update
            keywords: Set of keywords that appear in the same context
        """
        # Convert to sorted list for consistent ordering
        keyword_list = sorted(keywords)

        # Record bidirectional co-occurrences
        for i, kw1 in enumerate(keyword_list):
            for kw2 in keyword_list[i + 1 :]:
                matrix[kw1][kw2] += 1
                matrix[kw2][kw1] += 1

    def suggest_related_keywords(
        self,
        query_keywords: list[str],
        top_n: int = 5,
        min_cooccurrence: int = 1,
    ) -> list[dict[str, Any]]:
        """
        Suggest related keywords based on co-occurrence patterns.

        Args:
            query_keywords: Keywords to find related terms for
            top_n: Maximum number of suggestions to return
            min_cooccurrence: Minimum co-occurrence count to consider

        Returns:
            List of suggestion dicts with:
            - keyword: The suggested keyword
            - cooccurrence_count: Number of times it co-occurs with query keywords
            - cooccurs_with: List of query keywords it co-occurs with
        """
        if not query_keywords:
            return []

        # Normalize query keywords to lowercase
        query_keywords_lower = [kw.lower() for kw in query_keywords]

        # Aggregate co-occurrence counts across all query keywords
        suggestion_counts: dict[str, int] = defaultdict(int)
        suggestion_sources: dict[str, set[str]] = defaultdict(set)

        for query_kw in query_keywords_lower:
            if query_kw in self.cooccurrence_matrix:
                for related_kw, count in self.cooccurrence_matrix[query_kw].items():
                    # Don't suggest keywords that are already in the query
                    if related_kw not in query_keywords_lower:
                        suggestion_counts[related_kw] += count
                        suggestion_sources[related_kw].add(query_kw)

        # Filter by minimum co-occurrence count
        suggestions = [
            {
                "keyword": kw,
                "cooccurrence_count": count,
                "cooccurs_with": sorted(suggestion_sources[kw]),
            }
            for kw, count in suggestion_counts.items()
            if count >= min_cooccurrence
        ]

        # Sort by co-occurrence count (descending)
        suggestions.sort(key=lambda x: (-x["cooccurrence_count"], x["keyword"]))

        return suggestions[:top_n]

    def suggest_narrowing_keywords(
        self,
        query_keywords: list[str],
        search_results: list[dict[str, Any]],
        top_n: int = 5,
        min_result_count: int = 2,
    ) -> list[dict[str, Any]]:
        """
        Suggest keywords to narrow down search results.

        Analyzes the current search results to find keywords that appear frequently
        in the results and could help narrow the search.

        Args:
            query_keywords: Original query keywords
            search_results: Current search results to analyze
            top_n: Maximum number of suggestions to return
            min_result_count: Minimum number of results a keyword must appear in

        Returns:
            List of suggestion dicts with:
            - keyword: The suggested keyword
            - result_count: Number of results containing this keyword
            - cooccurs_with: List of query keywords it co-occurs with
        """
        if not search_results:
            return []

        # Normalize query keywords
        query_keywords_lower = {kw.lower() for kw in query_keywords}

        # Count keyword occurrences across search results
        keyword_counts: dict[str, int] = defaultdict(int)
        keyword_sources: dict[str, set[str]] = defaultdict(set)

        for result in search_results:
            # Get all keywords from this result
            result_keywords = set()
            if result.get("keywords"):
                result_keywords.update(k.lower() for k in result["keywords"])

            # For each result keyword, track which query keywords it co-occurs with
            for result_kw in result_keywords:
                if result_kw not in query_keywords_lower:
                    keyword_counts[result_kw] += 1

                    # Check which query keywords this result keyword co-occurs with
                    for query_kw in query_keywords_lower:
                        if query_kw in self.cooccurrence_matrix.get(result_kw, {}):
                            keyword_sources[result_kw].add(query_kw)

        # Create suggestions
        suggestions = [
            {
                "keyword": kw,
                "result_count": count,
                "cooccurs_with": sorted(keyword_sources[kw]) if keyword_sources[kw] else [],
            }
            for kw, count in keyword_counts.items()
            if count >= min_result_count
        ]

        # Sort by result count (descending)
        suggestions.sort(key=lambda x: (-x["result_count"], x["keyword"]))

        return suggestions[:top_n]

    def get_cooccurrence_count(self, keyword1: str, keyword2: str) -> int:
        """
        Get the co-occurrence count between two keywords.

        Args:
            keyword1: First keyword
            keyword2: Second keyword

        Returns:
            Number of times the keywords co-occur
        """
        kw1_lower = keyword1.lower()
        kw2_lower = keyword2.lower()

        if kw1_lower in self.cooccurrence_matrix:
            return self.cooccurrence_matrix[kw1_lower].get(kw2_lower, 0)
        return 0

    def get_statistics(self) -> dict[str, Any]:
        """
        Get statistics about the co-occurrence matrix.

        Returns:
            Dict with statistics including:
            - total_keywords: Number of unique keywords tracked
            - total_cooccurrences: Total number of co-occurrence relationships
            - avg_cooccurrences_per_keyword: Average number of co-occurring keywords
            - most_connected_keywords: Top 10 keywords by number of co-occurrences
        """
        if not self.cooccurrence_matrix:
            return {
                "total_keywords": 0,
                "total_cooccurrences": 0,
                "avg_cooccurrences_per_keyword": 0.0,
                "most_connected_keywords": [],
            }

        total_keywords = len(self.cooccurrence_matrix)
        total_cooccurrences = sum(
            len(cooccurring) for cooccurring in self.cooccurrence_matrix.values()
        )

        # Find most connected keywords
        keyword_connections = [
            (kw, len(cooccurring)) for kw, cooccurring in self.cooccurrence_matrix.items()
        ]
        keyword_connections.sort(key=lambda x: -x[1])

        return {
            "total_keywords": total_keywords,
            "total_cooccurrences": total_cooccurrences,
            "avg_cooccurrences_per_keyword": (
                round(total_cooccurrences / total_keywords, 2) if total_keywords else 0.0
            ),
            "most_connected_keywords": keyword_connections[:10],
        }
