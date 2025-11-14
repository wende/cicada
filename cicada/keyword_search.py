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

    def __init__(self, index: dict[str, Any], match_source: str = "all"):
        """
        Initialize the keyword searcher.

        Args:
            index: The Cicada index dictionary containing modules and metadata
            match_source: Filter by keyword source ('all', 'docs', 'strings'). Defaults to 'all'.
        """
        self.index = index
        self.match_source = match_source
        self.documents = self._build_document_map()

    def _merge_keywords(
        self, doc_keywords: dict | list | None, string_keywords: dict | list | None
    ) -> tuple[dict[str, float], dict[str, str]]:
        """
        Merge documentation and string keywords based on match_source filter.

        Args:
            doc_keywords: Keywords from documentation (dict or list)
            string_keywords: Keywords from string literals (dict or list)

        Returns:
            Tuple of (merged_keywords_dict, keyword_sources_dict) where:
            - merged_keywords_dict: Combined keywords with scores
            - keyword_sources_dict: Maps each keyword to its source ('docs', 'strings', or 'both')
        """
        # Normalize to dict format
        doc_kw_dict = {}
        if doc_keywords:
            if isinstance(doc_keywords, list):
                doc_kw_dict = {kw.lower(): 1.0 for kw in doc_keywords}
            else:
                doc_kw_dict = {k.lower(): v for k, v in doc_keywords.items()}

        string_kw_dict = {}
        if string_keywords:
            if isinstance(string_keywords, list):
                string_kw_dict = {kw.lower(): 1.0 for kw in string_keywords}
            else:
                string_kw_dict = {k.lower(): v for k, v in string_keywords.items()}

        # Filter and merge based on match_source
        merged = {}
        sources = {}

        if self.match_source == "docs":
            merged = doc_kw_dict
            sources = dict.fromkeys(doc_kw_dict, "docs")
        elif self.match_source == "strings":
            merged = string_kw_dict
            sources = dict.fromkeys(string_kw_dict, "strings")
        else:  # 'all'
            # Merge both, keeping higher score for duplicates
            for k, v in doc_kw_dict.items():
                merged[k] = v
                sources[k] = "docs"
            for k, v in string_kw_dict.items():
                if k in merged:
                    merged[k] = max(merged[k], v)
                    sources[k] = "both"
                else:
                    merged[k] = v
                    sources[k] = "strings"

        return merged, sources

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
        # Merge doc keywords and string keywords based on match_source
        keywords_dict, keyword_sources = self._merge_keywords(
            module_data.get("keywords"), module_data.get("string_keywords")
        )

        # Skip if no keywords after filtering
        if not keywords_dict:
            return None

        document = {
            "type": "module",
            "name": module_name,
            "module": module_name,
            "file": module_data["file"],
            "line": module_data["line"],
            "doc": module_data.get("moduledoc"),
            "keywords": keywords_dict,
            "keyword_sources": keyword_sources,
        }

        # Include string sources if available and relevant
        if module_data.get("string_sources") and self.match_source in ["all", "strings"]:
            document["string_sources"] = module_data["string_sources"]

        return document

    def _create_function_document(
        self, module_name: str, module_data: dict[str, Any], func: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Create a searchable document for a function."""
        # Merge doc keywords and string keywords based on match_source
        keywords_dict, keyword_sources = self._merge_keywords(
            func.get("keywords"), func.get("string_keywords")
        )

        # Skip if no keywords after filtering
        if not keywords_dict:
            return None

        full_name = f"{module_name}.{func['name']}/{func['arity']}"

        document = {
            "type": "function",
            "name": full_name,
            "module": module_name,
            "function": func["name"],
            "arity": func["arity"],
            "file": module_data["file"],
            "line": func["line"],
            "doc": func.get("doc"),
            "keywords": keywords_dict,
            "keyword_sources": keyword_sources,
        }

        # Include string sources if available and relevant
        if func.get("string_sources") and self.match_source in ["all", "strings"]:
            document["string_sources"] = func["string_sources"]

        return document

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

    def _extract_module_patterns(self, keywords: list[str]) -> list[str]:
        """
        Extract module patterns from keywords containing dots.

        If a keyword contains a ".", split it and extract the module part(s).
        Supports wildcards and nested modules.

        Args:
            keywords: List of keywords (e.g., ["ApiKeys.create_user", "MyApp.User.update"])

        Returns:
            List of module patterns extracted (e.g., ["ApiKeys", "MyApp.User", "MyApp.*"])

        Examples:
            - "ApiKeys.create_user" -> ["ApiKeys"]
            - "MyApp.User.create_user" -> ["MyApp.User", "MyApp.*"]
            - "MyApp.*.create_user" -> ["MyApp.*"]
        """
        module_patterns = set()

        for keyword in keywords:
            # Skip keywords without dots (they're not module-qualified)
            if "." not in keyword:
                continue

            # Split on the last dot to separate module from function/keyword
            module_pattern = keyword.rsplit(".", 1)[0]
            module_patterns.add(module_pattern)

            # If it's a nested module (multiple dots), also add wildcard patterns
            # e.g., "MyApp.User" -> also try "MyApp.*"
            if "." in module_pattern and "*" not in module_pattern:
                prefix = module_pattern.split(".", 1)[0]
                module_patterns.add(f"{prefix}.*")

        return list(module_patterns)

    def _match_module_name(self, module_pattern: str, doc_module: str) -> bool:
        """
        Check if a document's module name matches a module pattern.

        Supports wildcards (*) for pattern matching.

        Args:
            module_pattern: Module pattern (e.g., "ApiKeys", "MyApp.*", "*.User")
            doc_module: Document's module name (e.g., "ApiKeys", "MyApp.User")

        Returns:
            True if the module name matches the pattern
        """
        if "*" in module_pattern:
            return self._match_wildcard(module_pattern, doc_module)
        return module_pattern.lower() == doc_module.lower()

    def search(
        self, query_keywords: list[str], top_n: int = 5, filter_type: str = "all"
    ) -> list[dict[str, Any]]:
        """
        Search for modules and functions matching the given keywords.

        Uses pre-weighted keyword scores calculated during extraction/expansion.
        The score for each result is the sum of weights of matched keywords.

        Automatically detects wildcard patterns (* supported) and OR patterns (| supported) in keywords.

        When keywords contain dots (e.g., "ApiKeys.create_user"), the module part is extracted
        and matched against the document's module name for additional scoring.

        Args:
            query_keywords: List of keywords to search for (supports "create*|update*" for OR patterns,
                           and "Module.keyword" for module-qualified searches)
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

        # Extract module patterns from keywords with dots (e.g., "ApiKeys.create_user" -> "ApiKeys")
        module_patterns = self._extract_module_patterns(query_keywords_lower)

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

            # Check for module name match if module patterns were extracted
            module_matched = False
            if module_patterns:
                for module_pattern in module_patterns:
                    if self._match_module_name(module_pattern, doc["module"]):
                        # Boost score for module match (substantial boost to prioritize module-qualified searches)
                        result_data["score"] += 2.0
                        module_matched = True
                        break

            # Only include results with at least one matched keyword OR a module match
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

                # Add module match indicator if applicable
                if module_matched:
                    result["module_matched"] = True

                # Add type-specific fields
                if doc["type"] == "function":
                    result["function"] = doc["function"]
                    result["arity"] = doc["arity"]

                # Add documentation if available
                if doc.get("doc"):
                    result["doc"] = doc["doc"]

                # Add keyword sources for matched keywords
                if doc.get("keyword_sources"):
                    matched_sources = {
                        kw: doc["keyword_sources"].get(kw, "unknown")
                        for kw in result_data["matched_keywords"]
                        if kw in doc["keyword_sources"]
                    }
                    if matched_sources:
                        result["keyword_sources"] = matched_sources

                # Add string sources if available
                if doc.get("string_sources"):
                    result["string_sources"] = doc["string_sources"]

                results.append(result)

        # Apply type filter
        if filter_type == "modules":
            results = [r for r in results if r["type"] == "module"]
        elif filter_type == "functions":
            results = [r for r in results if r["type"] == "function"]

        # Sort by score (descending), then by name for stable results
        results.sort(key=lambda x: (-x["score"], x["name"]))

        return results[:top_n]
