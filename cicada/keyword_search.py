"""
Keyword-based search for modules and functions.

Provides semantic search capabilities by matching query keywords
against extracted keywords in the index using BM25 ranking.

Identifier names (function/module names) are given much higher weight than keywords.

Author: Cursor(Auto)
"""

import re
import fnmatch
from typing import List, Dict, Any
from rank_bm25 import BM25Okapi

from cicada.utils import split_identifier


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

        # If no documents were created (no keywords extracted), create documents using identifier names
        if not documents:
            for module_name, module_data in self.index.get("modules", {}).items():
                # Add module as a document using its name as keywords
                module_keywords = split_identifier(module_name)
                documents.append(module_keywords)
                document_map.append(
                    {
                        "type": "module",
                        "name": module_name,
                        "module": module_name,
                        "file": module_data["file"],
                        "line": module_data["line"],
                        "doc": module_data.get("moduledoc"),
                        "keywords": module_keywords,
                    }
                )

                # Add functions as documents
                for func in module_data.get("functions", []):
                    # Use extracted keywords if available, otherwise fall back to split identifier
                    if func.get("keywords"):
                        func_keywords = [kw.lower() for kw in func["keywords"]]
                    else:
                        func_keywords = split_identifier(func["name"])

                    documents.append(func_keywords)
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
                            "keywords": func_keywords,
                        }
                    )

        # Initialize BM25 with all documents
        # Use b=0.4 (lower than default 0.75) to reduce length normalization penalty
        # This is appropriate for code search where longer names are more specific, not verbose
        bm25 = BM25Okapi(documents, b=0.4) if documents else None
        return bm25, document_map

    def _match_wildcard(self, pattern: str, text: str) -> bool:
        """
        Check if text matches a wildcard pattern.

        Supports * (matches any characters) only.

        Args:
            pattern: Wildcard pattern (e.g., "create*", "test_*")
            text: Text to match against

        Returns:
            True if text matches the pattern
        """
        # Only support * wildcard, not ?
        if "?" in pattern:
            return False
        return fnmatch.fnmatch(text.lower(), pattern.lower())

    def _expand_wildcard_keywords(
        self, query_keywords: List[str], document_keywords: List[str]
    ) -> List[str]:
        """
        Expand wildcard patterns to actual matching keywords from the document.

        Args:
            query_keywords: List of query keywords (may contain wildcards)
            document_keywords: List of keywords from a document

        Returns:
            List of actual matching keywords found in the document
        """
        matched_keywords = []
        for query_kw in query_keywords:
            for doc_kw in document_keywords:
                if self._match_wildcard(query_kw, doc_kw):
                    matched_keywords.append(query_kw)
        return matched_keywords

    def _expand_wildcard_keywords_with_identifier(
        self,
        query_keywords: List[str],
        document_keywords: List[str],
        identifier_name: str,
    ) -> List[str]:
        """
        Expand wildcard patterns to actual matching keywords from the document and identifier name.

        Args:
            query_keywords: List of query keywords (may contain wildcards)
            document_keywords: List of keywords from a document
            identifier_name: The full identifier name (function/module name)

        Returns:
            List of actual matching keywords found in the document or identifier
        """
        matched_keywords = []
        for query_kw in query_keywords:
            # Check against individual keywords
            for doc_kw in document_keywords:
                if self._match_wildcard(query_kw, doc_kw):
                    matched_keywords.append(query_kw)
                    break  # Only add each query keyword once

            # Also check against the full identifier name
            if query_kw not in matched_keywords and self._match_wildcard(
                query_kw, identifier_name
            ):
                matched_keywords.append(query_kw)
        return matched_keywords

    def _get_wildcard_scores(self, query_keywords: List[str]) -> List[float]:
        """
        Calculate BM25-like scores for wildcard matching.

        Args:
            query_keywords: List of query keywords (may contain wildcards)

        Returns:
            List of scores for each document
        """
        scores = []

        for _, doc_info in enumerate(self.document_map):
            doc_keywords = [kw.lower() for kw in doc_info["keywords"]]
            identifier_name = self._extract_identifier_name(doc_info)

            # Find matching keywords using wildcard patterns
            # Check both individual keywords and full identifier name
            matched_keywords = self._expand_wildcard_keywords_with_identifier(
                query_keywords, doc_keywords, identifier_name
            )

            if matched_keywords:
                # Calculate a simple score based on number of matches
                # This is a simplified version of BM25 for wildcard matching
                score = len(matched_keywords) / len(query_keywords)
                scores.append(score)
            else:
                scores.append(0.0)

        return scores

    def _has_wildcards(self, keywords: List[str]) -> bool:
        """Check if any keywords contain wildcard patterns."""
        return any("*" in keyword for keyword in keywords)

    def search(self, query_keywords: List[str], top_n: int = 5) -> List[Dict[str, Any]]:
        """
        Search for modules and functions matching the given keywords.

        Uses BM25 ranking to score documents based on keyword relevance.
        Identifier names (function/module names) are boosted significantly
        when they match query keywords.

        Automatically detects wildcard patterns (* supported) in keywords.

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

        # Check if wildcards are present
        enable_wildcards = self._has_wildcards(query_keywords_lower)

        # Get BM25 scores for all documents
        if enable_wildcards:
            # For wildcard matching, we need to manually score documents
            bm25_scores = self._get_wildcard_scores(query_keywords_lower)
        else:
            bm25_scores = self.bm25.get_scores(query_keywords_lower)

        results = []

        # Build results with scores
        for doc_idx, bm25_score in enumerate(bm25_scores):
            # BM25 can produce negative scores for small corpuses
            # We check matched keywords instead to filter relevance
            doc_info = self.document_map[doc_idx]

            # Check if there are any matching keywords first
            if enable_wildcards:
                identifier_name = self._extract_identifier_name(doc_info)
                matched = self._count_wildcard_matches(
                    query_keywords_lower, doc_info["keywords"], identifier_name
                )
            else:
                matched = self._count_matches(
                    query_keywords_lower, doc_info["keywords"]
                )

            # Only include documents that match at least one query keyword
            if matched["score"] > 0:
                # Apply identifier name boost
                if enable_wildcards:
                    final_score = self._apply_identifier_boost_wildcard(
                        bm25_score, query_keywords_lower, doc_info
                    )
                else:
                    final_score = self._apply_identifier_boost(
                        bm25_score, query_keywords_lower, doc_info
                    )

                # Apply name coverage penalty (penalize functions with extra words not in query)
                coverage_penalty = self._calculate_name_coverage_penalty(
                    query_keywords_lower, doc_info
                )
                # For negative scores, divide by penalty instead of multiply
                # This ensures penalty always makes the score worse regardless of sign
                if final_score < 0 and coverage_penalty < 1.0:
                    final_score = final_score / coverage_penalty
                else:
                    final_score = final_score * coverage_penalty

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
        identifier_words = split_identifier(identifier_name)

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

    def _count_wildcard_matches(
        self,
        query_keywords: List[str],
        item_keywords: List[str],
        identifier_name: str | None = None,
    ) -> Dict[str, Any]:
        """
        Count matching keywords between query and item using wildcard patterns.

        Args:
            query_keywords: Query keywords (may contain wildcards, normalized to lowercase)
            item_keywords: Keywords from module/function
            identifier_name: The full identifier name (function/module name)

        Returns:
            Dictionary with:
            - score: Number of matching keywords
            - confidence: Percentage match (score / len(query_keywords) * 100)
            - matched_keywords: List of matched keywords
        """
        # Normalize item keywords to lowercase
        item_keywords_lower = [kw.lower() for kw in item_keywords]

        # Find matches using wildcard patterns
        if identifier_name:
            matched_keywords = self._expand_wildcard_keywords_with_identifier(
                query_keywords, item_keywords_lower, identifier_name
            )
        else:
            matched_keywords = self._expand_wildcard_keywords(
                query_keywords, item_keywords_lower
            )

        score = len(matched_keywords)
        confidence = (score / len(query_keywords)) * 100 if query_keywords else 0

        return {
            "score": score,
            "confidence": round(confidence, 1),
            "matched_keywords": matched_keywords,
        }

    def _apply_identifier_boost_wildcard(
        self, bm25_score: float, query_keywords: List[str], doc_info: Dict[str, Any]
    ) -> float:
        """
        Apply boost to BM25 score if query keywords match the identifier name using wildcards.

        Identifier names (function/module names) are given much higher weight.
        If any query keyword matches a word in the identifier name using wildcard patterns,
        the score is multiplied by IDENTIFIER_MATCH_BOOST.

        Args:
            bm25_score: The original BM25 score
            query_keywords: Query keywords (may contain wildcards, normalized to lowercase)
            doc_info: Document information with function/module name

        Returns:
            Final score (boosted if identifier matches)
        """
        # Extract the identifier name (module name or function name)
        identifier_name = self._extract_identifier_name(doc_info)

        # Split identifier into words
        identifier_words = split_identifier(identifier_name)

        # Check if any query keyword matches any word in the identifier using wildcards
        for query_kw in query_keywords:
            for identifier_word in identifier_words:
                if self._match_wildcard(query_kw, identifier_word):
                    # Apply significant boost for identifier match
                    return bm25_score * self.IDENTIFIER_MATCH_BOOST

        return bm25_score

    def _calculate_name_coverage_penalty(
        self, query_keywords: List[str], doc_info: Dict[str, Any]
    ) -> float:
        """
        Calculate penalty for functions whose names contain words NOT in the query.

        This helps rank exact matches higher than functions with extra words in their names.
        For example, searching "create user" should rank "create_user" higher than
        "create_invalid_user" because "invalid" is not in the query.

        Args:
            query_keywords: Normalized query keywords (lowercase)
            doc_info: Document information with function/module name

        Returns:
            Penalty multiplier between 0.1 and 1.0:
            - 1.0 = no penalty (exact match or all extra words in query)
            - 0.7 = 1 extra word not in query (30% penalty)
            - 0.4 = 2 extra words not in query (60% penalty)
            - 0.1 = 3+ extra words not in query (90% penalty cap)
        """
        # Only apply to functions (not modules)
        if doc_info["type"] != "function":
            return 1.0

        # Get function name and split it
        func_name = doc_info["function"]
        func_words = set(split_identifier(func_name))

        # Find words in function name that are NOT in query
        query_set = set(query_keywords)
        extra_words = func_words - query_set

        # No penalty if all function name words are in query (exact match)
        if not extra_words:
            return 1.0

        # Apply 30% penalty per extra word, with a floor of 0.1 (max 90% penalty)
        # This penalty is strong enough to overcome BM25 length normalization bias
        penalty_per_word = 0.3
        total_penalty = min(len(extra_words) * penalty_per_word, 0.9)

        return 1.0 - total_penalty
