"""
Keyword-based search for modules and functions.

Provides semantic search capabilities by matching query keywords
against extracted keywords in the index using BM25 ranking.

Identifier names (function/module names) are given much higher weight than keywords.
"""

import re
from typing import List, Dict, Any
from rank_bm25 import BM25Okapi


class KeywordSearcher:
    """Search for modules and functions by keywords using BM25 ranking."""

    # Boost multiplier for identifier name matches
    # When query keyword matches the function/module name, multiply the score by this
    IDENTIFIER_MATCH_BOOST = 10.0

    def __init__(self, index: Dict[str, Any]):
        """
        Initialize the keyword searcher.

        Args:
            index: The Cicada index dictionary containing modules and metadata
        """
        self.index = index
        self.bm25, self.document_map = self._initialize_bm25()

    @staticmethod
    def _split_identifier(identifier: str) -> List[str]:
        """
        Split an identifier by camelCase, PascalCase, and snake_case.

        Args:
            identifier: The identifier to split (e.g., 'createUserProfile', 'create_user_profile')

        Returns:
            List of words in the identifier
        """
        # Handle snake_case
        if "_" in identifier:
            return [word.lower() for word in identifier.split("_")]

        # Handle camelCase/PascalCase with regex
        # Insert space before uppercase letters and digits
        spaced = re.sub(r"([A-Z])", r" \1", identifier)
        words = spaced.split()
        return [word.lower() for word in words if word]

    @staticmethod
    def _extract_identifier_name(document_info: Dict[str, Any]) -> str:
        """
        Extract the core identifier name from document info.

        For modules: returns the module name
        For functions: returns the function name (without arity)

        Args:
            document_info: Document information dictionary

        Returns:
            The identifier name
        """
        if document_info["type"] == "module":
            return document_info["name"]
        else:
            return document_info["function"]

    def _initialize_bm25(self) -> tuple:
        """
        Initialize BM25 calculator with all documents in the index.

        Returns:
            Tuple of (BM25Okapi instance, document_map dict)
            - document_map maps document index to (type, module_name, location_info)
        """
        documents = []
        document_map = []

        # Collect all documents (modules and functions with keywords)
        for module_name, module_data in self.index.get("modules", {}).items():
            # Add module as a document
            if module_data.get("keywords"):
                doc_keywords = [kw.lower() for kw in module_data["keywords"]]
                documents.append(doc_keywords)
                document_map.append(
                    {
                        "type": "module",
                        "name": module_name,
                        "module": module_name,
                        "file": module_data["file"],
                        "line": module_data["line"],
                        "doc": module_data.get("moduledoc"),
                        "keywords": module_data["keywords"],
                    }
                )

            # Add functions as documents
            for func in module_data.get("functions", []):
                if func.get("keywords"):
                    doc_keywords = [kw.lower() for kw in func["keywords"]]
                    documents.append(doc_keywords)
                    full_name = f"{module_name}.{func['name']}/{func['arity']}"
                    document_map.append(
                        {
                            "type": "function",
                            "name": full_name,
                            "module": module_name,
                            "function": func["name"],
                            "arity": func["arity"],
                            "file": module_data["file"],
                            "line": func["line"],
                            "doc": func.get("doc"),
                            "keywords": func["keywords"],
                        }
                    )

        # Initialize BM25 with all documents
        bm25 = BM25Okapi(documents) if documents else None
        return bm25, document_map

    def search(
        self, query_keywords: List[str], top_n: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for modules and functions matching the given keywords.

        Uses BM25 ranking to score documents based on keyword relevance.
        Identifier names (function/module names) are boosted significantly
        when they match query keywords.

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
            - score: BM25 score (float), boosted if identifier matches query
            - confidence: Percentage of query keywords matched
            - matched_keywords: List of matched keywords
            - doc: Documentation string (if available)
        """
        if not query_keywords or self.bm25 is None or not self.document_map:
            return []

        # Normalize query keywords to lowercase
        query_keywords_lower = [kw.lower() for kw in query_keywords]

        # Get BM25 scores for all documents
        bm25_scores = self.bm25.get_scores(query_keywords_lower)

        results = []

        # Build results with scores
        for doc_idx, bm25_score in enumerate(bm25_scores):
            if bm25_score > 0:  # Only include documents with non-zero score
                doc_info = self.document_map[doc_idx]
                matched = self._count_matches(
                    query_keywords_lower, doc_info["keywords"]
                )

                # Apply identifier name boost
                final_score = self._apply_identifier_boost(
                    bm25_score, query_keywords_lower, doc_info
                )

                result = {
                    "type": doc_info["type"],
                    "name": doc_info["name"],
                    "module": doc_info["module"],
                    "file": doc_info["file"],
                    "line": doc_info["line"],
                    "score": round(final_score, 4),
                    "confidence": matched["confidence"],
                    "matched_keywords": matched["matched_keywords"],
                }

                # Add type-specific fields
                if doc_info["type"] == "function":
                    result["function"] = doc_info["function"]
                    result["arity"] = doc_info["arity"]

                # Add documentation if available
                if doc_info.get("doc"):
                    result["doc"] = doc_info["doc"]

                results.append(result)

        # Sort by final score (descending), then by name for stable results
        results.sort(key=lambda x: (-x["score"], x["name"]))

        return results[:top_n]

    def _apply_identifier_boost(
        self, bm25_score: float, query_keywords: List[str], doc_info: Dict[str, Any]
    ) -> float:
        """
        Apply boost to BM25 score if query keywords match the identifier name.

        Identifier names (function/module names) are given much higher weight.
        If any query keyword matches a word in the identifier name, the score
        is multiplied by IDENTIFIER_MATCH_BOOST.

        Args:
            bm25_score: The original BM25 score
            query_keywords: Normalized query keywords (lowercase)
            doc_info: Document information with function/module name

        Returns:
            Final score (boosted if identifier matches)
        """
        # Extract the identifier name (module name or function name)
        identifier_name = self._extract_identifier_name(doc_info)

        # Split identifier into words
        identifier_words = self._split_identifier(identifier_name)

        # Check if any query keyword matches any word in the identifier
        for query_kw in query_keywords:
            if query_kw in identifier_words:
                # Apply significant boost for identifier match
                return bm25_score * self.IDENTIFIER_MATCH_BOOST

        return bm25_score

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
