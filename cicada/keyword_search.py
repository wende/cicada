"""
Keyword-based search for modules and functions.

Provides semantic search capabilities by matching query keywords
against extracted keywords in the index.
"""

from typing import List, Dict, Any


class KeywordSearcher:
    """Search for modules and functions by keywords."""

    def __init__(self, index: Dict[str, Any]):
        """
        Initialize the keyword searcher.

        Args:
            index: The Cicada index dictionary containing modules and metadata
        """
        self.index = index

    def search(
        self, query_keywords: List[str], top_n: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for modules and functions matching the given keywords.

        Args:
            query_keywords: List of keywords to search for
            top_n: Maximum number of results to return

        Returns:
            List of result dictionaries sorted by score (descending), each containing:
            - type: 'module' or 'function'
            - name: Full name (e.g., 'MyApp.User' or 'MyApp.User.create/2')
            - module: Module name
            - file: File path
            - line: Line number
            - score: Number of matching keywords
            - confidence: Percentage (score / total query keywords * 100)
            - matched_keywords: List of matched keywords
            - doc: Documentation string (if available)
        """
        if not query_keywords:
            return []

        # Normalize query keywords to lowercase for matching
        query_keywords_lower = [kw.lower() for kw in query_keywords]

        results = []

        # Search through all modules
        for module_name, module_data in self.index.get("modules", {}).items():
            # Check module-level keywords
            module_keywords = module_data.get("keywords", [])
            if module_keywords:
                matched = self._count_matches(query_keywords_lower, module_keywords)
                if matched["score"] > 0:
                    results.append(
                        {
                            "type": "module",
                            "name": module_name,
                            "module": module_name,
                            "file": module_data["file"],
                            "line": module_data["line"],
                            "score": matched["score"],
                            "confidence": matched["confidence"],
                            "matched_keywords": matched["matched_keywords"],
                            "doc": module_data.get("moduledoc"),
                        }
                    )

            # Check function-level keywords
            for func in module_data.get("functions", []):
                func_keywords = func.get("keywords", [])
                if func_keywords:
                    matched = self._count_matches(query_keywords_lower, func_keywords)
                    if matched["score"] > 0:
                        full_name = f"{module_name}.{func['name']}/{func['arity']}"
                        results.append(
                            {
                                "type": "function",
                                "name": full_name,
                                "module": module_name,
                                "function": func["name"],
                                "arity": func["arity"],
                                "file": module_data["file"],
                                "line": func["line"],
                                "score": matched["score"],
                                "confidence": matched["confidence"],
                                "matched_keywords": matched["matched_keywords"],
                                "doc": func.get("doc"),
                            }
                        )

        # Sort by score (descending), then by name for stable results
        results.sort(key=lambda x: (-x["score"], x["name"]))

        return results[:top_n]

    def _count_matches(
        self, query_keywords: List[str], item_keywords: List[str]
    ) -> Dict[str, Any]:
        """
        Count matching keywords between query and item.

        Args:
            query_keywords: Query keywords (normalized to lowercase)
            item_keywords: Keywords from module/function

        Returns:
            Dictionary with:
            - score: Number of matching keywords
            - confidence: Percentage match (score / len(query_keywords) * 100)
            - matched_keywords: List of matched keywords
        """
        # Normalize item keywords to lowercase
        item_keywords_lower = [kw.lower() for kw in item_keywords]

        # Find matches
        matched_keywords = []
        for query_kw in query_keywords:
            if query_kw in item_keywords_lower:
                matched_keywords.append(query_kw)

        score = len(matched_keywords)
        confidence = (score / len(query_keywords)) * 100 if query_keywords else 0

        return {
            "score": score,
            "confidence": round(confidence, 1),
            "matched_keywords": matched_keywords,
        }
