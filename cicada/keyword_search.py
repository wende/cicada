"""
Keyword-based search for modules and functions.

Provides simple keyword search by summing weights of matched keywords.
Keywords are pre-weighted during extraction/expansion based on frequency,
code identifier presence, semantic similarity, etc.

Author: Cicada Team
"""

import fnmatch
from typing import Any


class KeywordSearcher:
    """Search for modules and functions by keywords using pre-weighted keyword scores."""

    def __init__(self, index: dict[str, Any]):
        """
        Initialize the keyword searcher.

        Args:
            index: The Cicada index dictionary containing modules and metadata
        """
        self.index = index
        self.documents = self._build_document_map()

    def _build_document_map(self) -> list[dict[str, Any]]:
        """
        Build a list of searchable documents from the index.

        Returns:
            List of document dicts with type, name, module, keywords, etc.
        """
        documents = []

        # Process all modules and their functions
        for module_name, module_data in self.index.get("modules", {}).items():
            # Add module as a document
            module_doc = self._create_module_document(module_name, module_data)
            if module_doc:
                documents.append(module_doc)

            # Add functions as documents
            for func in module_data.get("functions", []):
                func_doc = self._create_function_document(module_name, module_data, func)
                if func_doc:
                    documents.append(func_doc)

        return documents

    def _create_module_document(
        self, module_name: str, module_data: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Create a searchable document for a module."""
        if not module_data.get("keywords"):
            return None

        # Keywords can be either dict {word: score} or list [words]
        # If list, convert to dict with uniform scores
        keywords_dict = module_data["keywords"]
        if isinstance(keywords_dict, list):
            keywords_dict = {kw.lower(): 1.0 for kw in keywords_dict}
        else:
            keywords_dict = {k.lower(): v for k, v in keywords_dict.items()}

        return {
            "type": "module",
            "name": module_name,
            "module": module_name,
            "file": module_data["file"],
            "line": module_data["line"],
            "doc": module_data.get("moduledoc"),
            "keywords": keywords_dict,
        }

    def _create_function_document(
        self, module_name: str, module_data: dict[str, Any], func: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Create a searchable document for a function."""
        if not func.get("keywords"):
            return None

        # Keywords can be either dict {word: score} or list [words]
        # If list, convert to dict with uniform scores
        keywords_dict = func["keywords"]
        if isinstance(keywords_dict, list):
            keywords_dict = {kw.lower(): 1.0 for kw in keywords_dict}
        else:
            keywords_dict = {k.lower(): v for k, v in keywords_dict.items()}

        full_name = f"{module_name}.{func['name']}/{func['arity']}"

        return {
            "type": "function",
            "name": full_name,
            "module": module_name,
            "function": func["name"],
            "arity": func["arity"],
            "file": module_data["file"],
            "line": func["line"],
            "doc": func.get("doc"),
            "keywords": keywords_dict,
        }

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

    def _calculate_score(
        self,
        query_keywords: list[str],
        keyword_groups: list[int],
        total_terms: int,
        doc_keywords: dict[str, float],
    ) -> dict[str, Any]:
        """
        Calculate the search score by summing weights of matched keywords.

        Args:
            query_keywords: Query keywords (normalized to lowercase)
            doc_keywords: Document keywords with their scores

        Returns:
            Dictionary with:
            - score: Sum of matched keyword weights
            - matched_keywords: List of matched keywords
            - confidence: Percentage of query keywords that matched
        """
        matched_keywords = []
        matched_groups: set[int] = set()
        total_score = 0.0

        for query_kw, group_idx in zip(query_keywords, keyword_groups, strict=False):
            if query_kw in doc_keywords:
                matched_keywords.append(query_kw)
                matched_groups.add(group_idx)
                total_score += doc_keywords[query_kw]

        denominator = total_terms if total_terms else len(query_keywords)
        confidence = (len(matched_groups) / denominator * 100) if denominator else 0

        return {
            "score": total_score,
            "matched_keywords": matched_keywords,
            "confidence": round(confidence, 1),
        }

    def _calculate_wildcard_score(
        self,
        query_keywords: list[str],
        keyword_groups: list[int],
        total_terms: int,
        doc_keywords: dict[str, float],
    ) -> dict[str, Any]:
        """
        Calculate the search score using wildcard pattern matching.

        Args:
            query_keywords: Query keywords with potential wildcards (normalized to lowercase)
            doc_keywords: Document keywords with their scores

        Returns:
            Dictionary with:
            - score: Sum of matched keyword weights
            - matched_keywords: List of matched query patterns
            - confidence: Percentage of query keywords that matched
        """
        matched_keywords = []
        matched_groups: set[int] = set()
        total_score = 0.0

        for query_kw, group_idx in zip(query_keywords, keyword_groups, strict=False):
            # Find all doc keywords matching this pattern
            for doc_kw, weight in doc_keywords.items():
                if self._match_wildcard(query_kw, doc_kw):
                    # Add query keyword to matched list (not the doc keyword)
                    if query_kw not in matched_keywords:
                        matched_keywords.append(query_kw)
                        matched_groups.add(group_idx)
                    # Add the weight only once per query keyword
                    total_score += weight
                    break

        denominator = total_terms if total_terms else len(query_keywords)
        confidence = (len(matched_groups) / denominator * 100) if denominator else 0

        return {
            "score": total_score,
            "matched_keywords": matched_keywords,
            "confidence": round(confidence, 1),
        }

    def _has_wildcards(self, keywords: list[str]) -> bool:
        """Check if any keywords contain wildcard patterns (* or |)."""
        return any("*" in keyword or "|" in keyword for keyword in keywords)

    def _expand_or_patterns(self, keywords: list[str]) -> tuple[list[str], list[int]]:
        """
        Expand OR patterns (|) in keywords.

        Args:
            keywords: List of keywords that may contain | for OR logic

        Returns:
            Tuple of:
            - Expanded list of keywords with OR patterns split out
            - Parallel list of group indexes mapping each expanded keyword back to the
              original keyword position. This lets us compute confidence using the
              number of user-supplied keywords rather than the expanded variants.

        Example:
            ["create*|update*", "user"] -> (["create*", "update*", "user"], [0, 0, 1])
        """
        expanded: list[str] = []
        groups: list[int] = []
        for idx, keyword in enumerate(keywords):
            parts = [p.strip() for p in keyword.split("|")] if "|" in keyword else [keyword]
            for part in parts:
                expanded.append(part)
                groups.append(idx)
        return expanded, groups

    def search(
        self, query_keywords: list[str], top_n: int = 5, filter_type: str = "all"
    ) -> list[dict[str, Any]]:
        """
        Search for modules and functions matching the given keywords.

        Uses pre-weighted keyword scores calculated during extraction/expansion.
        The score for each result is the sum of weights of matched keywords.

        Automatically detects wildcard patterns (* supported) and OR patterns (| supported) in keywords.

        Args:
            query_keywords: List of keywords to search for (supports "create*|update*" for OR patterns)
            top_n: Maximum number of results to return
            filter_type: Filter results by type ('all', 'modules', 'functions'). Defaults to 'all'.

        Returns:
            List of result dictionaries sorted by score (descending), each containing:
            - type: 'module' or 'function'
            - name: Full name (e.g., 'MyApp.User' or 'MyApp.User.create/2')
            - module: Module name
            - file: File path
            - line: Line number
            - score: Sum of matched keyword weights (float)
            - confidence: Percentage of query keywords matched
            - matched_keywords: List of matched keywords
            - doc: Documentation string (if available)
        """
        if not query_keywords or not self.documents:
            return []

        # Normalize query keywords to lowercase
        query_keywords_lower = [kw.lower() for kw in query_keywords]

        # Expand OR patterns (e.g., "create*|update*" -> ["create*", "update*"])
        query_keywords_expanded, keyword_groups = self._expand_or_patterns(query_keywords_lower)

        # Check if wildcards are present
        enable_wildcards = self._has_wildcards(query_keywords_expanded)

        results = []

        # Search all documents
        for doc in self.documents:
            # Calculate score
            if enable_wildcards:
                result_data = self._calculate_wildcard_score(
                    query_keywords_expanded,
                    keyword_groups,
                    len(query_keywords_lower),
                    doc["keywords"],
                )
            else:
                result_data = self._calculate_score(
                    query_keywords_expanded,
                    keyword_groups,
                    len(query_keywords_lower),
                    doc["keywords"],
                )

            # Only include results with at least one matched keyword
            if result_data["score"] > 0:
                result = {
                    "type": doc["type"],
                    "name": doc["name"],
                    "module": doc["module"],
                    "file": doc["file"],
                    "line": doc["line"],
                    "score": round(result_data["score"], 4),
                    "confidence": result_data["confidence"],
                    "matched_keywords": result_data["matched_keywords"],
                }

                # Add type-specific fields
                if doc["type"] == "function":
                    result["function"] = doc["function"]
                    result["arity"] = doc["arity"]

                # Add documentation if available
                if doc.get("doc"):
                    result["doc"] = doc["doc"]

                results.append(result)

        # Apply type filter
        if filter_type == "modules":
            results = [r for r in results if r["type"] == "module"]
        elif filter_type == "functions":
            results = [r for r in results if r["type"] == "function"]

        # Sort by score (descending), then by name for stable results
        results.sort(key=lambda x: (-x["score"], x["name"]))

        return results[:top_n]
