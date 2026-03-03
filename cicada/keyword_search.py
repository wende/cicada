"""
Keyword-based search for modules and functions.

Provides simple keyword search by summing weights of matched keywords.
Keywords are pre-weighted during extraction/expansion based on frequency,
code identifier presence, semantic similarity, etc.

Author: Cicada Team
"""

import fnmatch
from typing import Any

from cicada.scoring import (
    apply_module_boost,
    build_zipf_table,
    calculate_score,
    calculate_wildcard_score,
)


class KeywordSearcher:
    """Search for modules and functions by keywords using pre-weighted keyword scores."""

    VALID_SOURCES = ["all", "docs", "strings", "comments"]

    def __init__(
        self, index: dict[str, Any], match_source: str = "all", cochange_boost: float = 0.5
    ):
        """
        Initialize the keyword searcher.

        Args:
            index: The Cicada index dictionary containing modules and metadata
            match_source: Filter by keyword source ('all', 'docs', 'strings', 'comments'). Defaults to 'all'.
            cochange_boost: Boost factor for co-change relationships (0.0 to disable). Defaults to 0.5.
        """
        self.index = index

        # Validate match_source
        if match_source not in self.VALID_SOURCES:
            raise ValueError(
                f"match_source must be one of {self.VALID_SOURCES}, got '{match_source}'"
            )

        self.match_source = match_source
        self.cochange_boost = cochange_boost
        self.documents = self._build_document_map()
        self.zipf_table = build_zipf_table(self.documents)

        # Initialize co-occurrence analyzer if data is available
        from cicada.cooccurrence import CooccurrenceAnalyzer

        self.cooccurrence_analyzer: CooccurrenceAnalyzer | None = None
        if index.get("cooccurrences"):
            # Silently fail if co-occurrence data is invalid - analyzer stays None
            with __import__("contextlib").suppress(Exception):
                self.cooccurrence_analyzer = CooccurrenceAnalyzer(index)

    def _merge_keywords(
        self,
        doc_keywords: dict | list | None,
        string_keywords: dict | list | None,
        comment_keywords: dict | list | None = None,
    ) -> tuple[dict[str, float], dict[str, str]]:
        """
        Merge documentation, string, and comment keywords based on match_source filter.

        Args:
            doc_keywords: Keywords from documentation (dict or list)
            string_keywords: Keywords from string literals (dict or list)
            comment_keywords: Keywords from inline comments (dict or list)

        Returns:
            Tuple of (merged_keywords_dict, keyword_sources_dict) where:
            - merged_keywords_dict: Combined keywords with scores
            - keyword_sources_dict: Maps each keyword to its source ('docs', 'strings', 'comments', or combinations)
        """
        # Normalize to dict format
        doc_kw_dict = self._normalize_keywords(doc_keywords)
        string_kw_dict = self._normalize_keywords(string_keywords)
        comment_kw_dict = self._normalize_keywords(comment_keywords)

        # Filter and merge based on match_source
        if self.match_source == "docs":
            return doc_kw_dict, dict.fromkeys(doc_kw_dict, "docs")
        if self.match_source == "strings":
            return string_kw_dict, dict.fromkeys(string_kw_dict, "strings")
        if self.match_source == "comments":
            return comment_kw_dict, dict.fromkeys(comment_kw_dict, "comments")

        merged: dict[str, float] = {}
        source_sets: dict[str, set[str]] = {}

        for label, kw_dict in (
            ("docs", doc_kw_dict),
            ("strings", string_kw_dict),
            ("comments", comment_kw_dict),
        ):
            for keyword, score in kw_dict.items():
                if keyword in merged:
                    merged[keyword] = max(merged[keyword], score)
                else:
                    merged[keyword] = score

                if keyword not in source_sets:
                    source_sets[keyword] = set()
                source_sets[keyword].add(label)

        # Convert source sets to stable strings (e.g., docs+comments+strings)
        sources = {keyword: "+".join(sorted(labels)) for keyword, labels in source_sets.items()}

        return merged, sources

    def _normalize_keywords(self, keywords: dict | list | None) -> dict[str, float]:
        """Normalize keyword inputs to a lowercase->score dict."""
        if not keywords:
            return {}
        if isinstance(keywords, list):
            return {kw.lower(): 1.0 for kw in keywords}
        return {k.lower(): v for k, v in keywords.items()}

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
        # Merge doc keywords, string keywords, and comment keywords based on match_source
        keywords_dict, keyword_sources = self._merge_keywords(
            module_data.get("keywords"),
            module_data.get("string_keywords"),
            module_data.get("comment_keywords"),
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

        # Include timestamp fields if available
        if module_data.get("last_modified_at"):
            document["last_modified_at"] = module_data["last_modified_at"]
        if module_data.get("last_modified_sha"):
            document["last_modified_sha"] = module_data["last_modified_sha"]
        if module_data.get("last_modified_pr"):
            document["last_modified_pr"] = module_data["last_modified_pr"]

        # Fall back to most recent function timestamp if module doesn't have one
        if not module_data.get("last_modified_at"):
            # This allows modules to be filtered by scope="recent" even if
            # the module itself doesn't have a timestamp
            functions = module_data.get("functions", [])
            functions_with_timestamps = [f for f in functions if f.get("last_modified_at")]
            if functions_with_timestamps:
                # Find function with most recent timestamp
                most_recent = max(functions_with_timestamps, key=lambda f: f["last_modified_at"])
                document["last_modified_at"] = most_recent["last_modified_at"]
                # Also use its commit hash and PR
                if most_recent.get("last_modified_sha"):
                    document["last_modified_sha"] = most_recent["last_modified_sha"]
                if most_recent.get("last_modified_pr"):
                    document["last_modified_pr"] = most_recent["last_modified_pr"]

        return document

    def _create_function_document(
        self, module_name: str, module_data: dict[str, Any], func: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Create a searchable document for a function."""
        # Merge doc keywords, string keywords, and comment keywords based on match_source
        keywords_dict, keyword_sources = self._merge_keywords(
            func.get("keywords"),
            func.get("string_keywords"),
            func.get("comment_keywords"),
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

        # Include signature and visibility if available
        if func.get("signature"):
            document["signature"] = func["signature"]
        if func.get("type"):
            document["visibility"] = func["type"]

        # Include string sources if available and relevant
        if func.get("string_sources") and self.match_source in ["all", "strings"]:
            document["string_sources"] = func["string_sources"]

        # Include comment sources if available and relevant
        if func.get("comment_sources") and self.match_source in ["all", "comments"]:
            document["comment_sources"] = func["comment_sources"]

        # Include timestamp fields if available
        if func.get("last_modified_at"):
            document["last_modified_at"] = func["last_modified_at"]
        if func.get("last_modified_sha"):
            document["last_modified_sha"] = func["last_modified_sha"]
        if func.get("last_modified_pr"):
            document["last_modified_pr"] = func["last_modified_pr"]

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

    def _analyze_match_details(
        self,
        query_keywords: list[str],
        doc: dict[str, Any],
    ) -> dict[str, dict[str, Any]]:
        """
        Analyze WHERE each keyword matched and HOW MANY times.

        Args:
            query_keywords: List of matched query keywords (lowercase)
            doc: Document dictionary with type, name, keywords, doc, string_sources, etc.

        Returns:
            Dictionary mapping keyword -> match details:
            {
                "keyword": {
                    "total_count": int,
                    "locations": [
                        {"type": "name"|"doc"|"string", "count": int, "lines": [...]},
                        ...
                    ]
                }
            }
        """
        match_details: dict[str, dict[str, Any]] = {}

        for keyword in query_keywords:
            details: dict[str, Any] = {"total_count": 0, "locations": []}

            # Check if keyword appears in the name (module or function name)
            name = doc.get("name", "").lower()
            if keyword in name:
                # Count occurrences in name
                count = name.count(keyword)
                details["locations"].append({"type": "name", "count": count})
                details["total_count"] += count

            # Check if keyword appears in documentation
            doc_text = doc.get("doc", "")
            if doc_text:
                doc_lower = doc_text.lower()
                count = doc_lower.count(keyword)
                if count > 0:
                    details["locations"].append({"type": "doc", "count": count})
                    details["total_count"] += count

            # Check if keyword appears in string literals
            string_sources = doc.get("string_sources", [])
            if string_sources:
                string_matches = []
                string_count = 0
                for src in string_sources:
                    src_lower = src["string"].lower()
                    kw_count = src_lower.count(keyword)
                    if kw_count > 0:
                        string_matches.append(src["line"])
                        string_count += kw_count

                if string_matches:
                    details["locations"].append(
                        {"type": "string", "count": string_count, "lines": string_matches}
                    )
                    details["total_count"] += string_count

            # Only add to results if we found matches
            if details["total_count"] > 0:
                match_details[keyword] = details

        return match_details

    def _calculate_score(
        self,
        query_keywords: list[str],
        keyword_groups: list[int],
        total_terms: int,
        doc_keywords: dict[str, float],
        doc: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Calculate the search score by summing weights of matched keywords.

        Args:
            query_keywords: Query keywords (normalized to lowercase)
            keyword_groups: Group indexes mapping each keyword to original position
            total_terms: Total number of original query terms (before OR expansion)
            doc_keywords: Document keywords with their scores
            doc: Optional document dict for match detail analysis

        Returns:
            Dictionary with:
            - score: Sum of matched keyword weights
            - matched_keywords: List of matched keywords
            - confidence: Percentage of query keywords that matched
            - match_details: Detailed location and frequency info (if doc provided)
        """
        # Extract document name for function/module name matching
        doc_name = doc.get("name") if doc else None

        result = calculate_score(
            query_keywords,
            keyword_groups,
            total_terms,
            doc_keywords,
            doc_name=doc_name,
            zipf_weights=self.zipf_table,
        )

        # Add match details if document provided
        if doc and result.get("matched_keywords"):
            result["match_details"] = self._analyze_match_details(result["matched_keywords"], doc)

        return result

    def _calculate_wildcard_score(
        self,
        query_keywords: list[str],
        keyword_groups: list[int],
        total_terms: int,
        doc_keywords: dict[str, float],
        doc: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Calculate the search score using wildcard pattern matching.

        Args:
            query_keywords: Query keywords with potential wildcards (normalized to lowercase)
            keyword_groups: Group indexes mapping each keyword to original position
            total_terms: Total number of original query terms (before OR expansion)
            doc_keywords: Document keywords with their scores
            doc: Optional document dict for match detail analysis

        Returns:
            Dictionary with:
            - score: Sum of matched keyword weights
            - matched_keywords: List of matched query patterns
            - confidence: Percentage of query keywords that matched
            - match_details: Detailed location and frequency info (if doc provided)
        """
        # Extract document name for function/module name matching
        doc_name = doc.get("name") if doc else None

        result = calculate_wildcard_score(
            query_keywords,
            keyword_groups,
            total_terms,
            doc_keywords,
            self._match_wildcard,
            doc_name=doc_name,
            zipf_weights=self.zipf_table,
        )

        # Add match details if document provided
        if doc and result.get("matched_keywords"):
            result["match_details"] = self._analyze_match_details(result["matched_keywords"], doc)

        return result

    def _has_wildcards(self, keywords: list[str]) -> bool:
        """Check if any keywords contain wildcard patterns (*)."""
        return any("*" in keyword for keyword in keywords)

    def _process_keyword_groups(
        self, keywords: list[str | list[str]]
    ) -> tuple[list[str], list[int]]:
        """
        Process keywords, handling both OR patterns (|) and nested lists (synonyms).

        Args:
            keywords: List of keywords. Elements can be strings (supporting | for OR)
                     or lists of strings (treated as synonym groups).

        Returns:
            Tuple of:
            - Expanded list of keywords (flat strings)
            - Parallel list of group indexes mapping each expanded keyword back to the
              original keyword position/group.

        Example:
            ["user", ["auth", "login"]] -> (["user", "auth", "login"], [0, 1, 1])
            ["create*|update*", "user"] -> (["create*", "update*", "user"], [0, 0, 1])
        """
        expanded: list[str] = []
        groups: list[int] = []
        for idx, keyword in enumerate(keywords):
            if isinstance(keyword, list):
                # Process nested list items (synonyms)
                for item in keyword:
                    # Also support | inside nested items
                    parts = [p.strip() for p in item.split("|")] if "|" in item else [item]
                    for part in parts:
                        expanded.append(part)
                        groups.append(idx)
            else:
                # Process string keyword
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

    def _apply_cochange_boost(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Apply co-change boosting to search results and populate co-change information.

        Results get a score boost proportional to their co-change relationship strength.
        Boost is applied based on total co-change frequency (sum of all co-change counts).

        Also adds 'cochange_info' field to results containing related files and functions.

        Args:
            results: List of search results

        Returns:
            Results with boosted scores and co-change information
        """
        if not results:
            return results

        # Apply boosts
        for result in results:
            boost_amount = 0.0

            # Get co-change data from the index
            module_data = self.index["modules"].get(result["module"])
            if not module_data:
                continue

            if result["type"] == "module":
                # File-level co-change boost
                # Boost based on total co-change activity
                cochange_files = module_data.get("cochange_files", [])
                total_cochange_count = sum(c["count"] for c in cochange_files)
                # Boost is proportional to total co-change activity and current score
                boost_amount += total_cochange_count * self.cochange_boost * 0.01 * result["score"]

                # Add co-change information to result
                if cochange_files:
                    result["cochange_info"] = {
                        "related_files": self._resolve_cochange_files(cochange_files),
                    }

            else:  # function
                # Function-level co-change boost
                func_data = None
                for func in module_data.get("functions", []):
                    if func["name"] == result["function"] and func.get("arity") == result["arity"]:
                        func_data = func
                        break

                if func_data:
                    # Function-level co-changes
                    cochange_functions = func_data.get("cochange_functions", [])
                    total_func_cochange = sum(c["count"] for c in cochange_functions)
                    boost_amount += (
                        total_func_cochange * self.cochange_boost * 0.02 * result["score"]
                    )

                    # File-level co-changes (weaker boost for functions)
                    cochange_files = module_data.get("cochange_files", [])
                    total_file_cochange = sum(c["count"] for c in cochange_files)
                    boost_amount += (
                        total_file_cochange * self.cochange_boost * 0.005 * result["score"]
                    )

                    # Add co-change information to result
                    cochange_info = {}

                    if cochange_files:
                        cochange_info["related_files"] = self._resolve_cochange_files(
                            cochange_files
                        )

                    if cochange_functions:
                        cochange_info["related_functions"] = cochange_functions

                    if cochange_info:
                        result["cochange_info"] = cochange_info

            # Apply the boost
            result["score"] += boost_amount

        return results

    def _find_module_by_file(self, file_path: str) -> str | None:
        """
        Find the module name for a given file path.

        Args:
            file_path: File path (relative or absolute)

        Returns:
            Module name or None if not found
        """
        for module_name, module_data in self.index["modules"].items():
            module_file = module_data.get("file", "")
            # Normalize paths for comparison
            if file_path in module_file or module_file.endswith(file_path):
                return module_name
        return None

    def _resolve_cochange_files(self, cochange_files: list[dict]) -> list[dict]:
        """
        Resolve module names for co-changed files.

        Args:
            cochange_files: List of co-change file dictionaries with 'file' and 'count' keys

        Returns:
            List of dictionaries with 'file', 'count', and 'module' keys
        """
        return [
            {
                "file": cochange["file"],
                "count": cochange["count"],
                "module": self._find_module_by_file(cochange["file"]),
            }
            for cochange in cochange_files
        ]

    def search(
        self,
        query_keywords: list[str | list[str]],
        top_n: int = 5,
        filter_type: str = "all",
    ) -> list[dict[str, Any]]:
        """
        Search for modules and functions matching the given keywords.

        Uses pre-weighted keyword scores calculated during extraction/expansion.
        The score for each result is the sum of weights of matched keywords.

        Automatically detects wildcard patterns (* supported) and OR patterns (| supported) in keywords.
        Supports nested lists for synonyms (e.g., ["user", ["auth", "login"]]).

        When keywords contain dots (e.g., "ApiKeys.create_user"), the module part is extracted
        and matched against the document's module name for additional scoring.

        Args:
            query_keywords: List of keywords to search for. Can be strings (support | for OR)
                           or nested lists of strings (treated as synonym groups).
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

        # Normalize query keywords to lowercase, preserving structure
        query_keywords_lower: list[str | list[str]] = []
        for kw in query_keywords:
            if isinstance(kw, list):
                query_keywords_lower.append([k.lower() for k in kw])
            else:
                query_keywords_lower.append(kw.lower())

        # Expand/process groups to get a flat list of all terms and their group indices
        query_keywords_expanded, keyword_groups = self._process_keyword_groups(query_keywords_lower)

        # Extract module patterns from the expanded flat list
        # This handles cases like ["ApiKeys.create|Auth.login"] -> ["ApiKeys", "Auth"]
        module_patterns = self._extract_module_patterns(query_keywords_expanded)

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
                    doc=doc,
                )
            else:
                result_data = self._calculate_score(
                    query_keywords_expanded,
                    keyword_groups,
                    len(query_keywords_lower),
                    doc["keywords"],
                    doc=doc,
                )

            # Check for module name match if module patterns were extracted
            module_matched = False
            if module_patterns:
                for module_pattern in module_patterns:
                    if self._match_module_name(module_pattern, doc["module"]):
                        # Boost score for module match (substantial boost to prioritize module-qualified searches)
                        result_data["score"] = apply_module_boost(result_data["score"], True)
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
                    # Add visibility and signature if available
                    if doc.get("visibility"):
                        result["visibility"] = doc["visibility"]
                    if doc.get("signature"):
                        result["signature"] = doc["signature"]

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

                # Add timestamp fields if available
                if doc.get("last_modified_at"):
                    result["last_modified_at"] = doc["last_modified_at"]
                if doc.get("last_modified_sha"):
                    result["last_modified_sha"] = doc["last_modified_sha"]
                if doc.get("last_modified_pr"):
                    result["last_modified_pr"] = doc["last_modified_pr"]

                results.append(result)

        # Apply type filter
        if filter_type == "modules":
            results = [r for r in results if r["type"] == "module"]
        elif filter_type == "functions":
            results = [r for r in results if r["type"] == "function"]

        # Apply co-change boosting if enabled
        if self.cochange_boost > 0:
            results = self._apply_cochange_boost(results)

        # Sort by score (descending), then by name for stable results
        results.sort(key=lambda x: (-x["score"], x["name"]))

        return results[:top_n]

    def suggest_related_keywords(
        self,
        query_keywords: list[str],
        top_n: int = 5,
        min_cooccurrence: int = 1,
    ) -> list[dict[str, Any]]:
        """
        Suggest related keywords based on co-occurrence patterns.

        Useful when a search returns no results or too few results.

        Args:
            query_keywords: Keywords from the original query
            top_n: Maximum number of suggestions to return
            min_cooccurrence: Minimum co-occurrence count to consider

        Returns:
            List of suggestion dicts with:
            - keyword: The suggested keyword
            - cooccurrence_count: Number of times it co-occurs with query keywords
            - cooccurs_with: List of query keywords it co-occurs with
        """
        if not self.cooccurrence_analyzer:
            return []

        return self.cooccurrence_analyzer.suggest_related_keywords(
            query_keywords, top_n=top_n, min_cooccurrence=min_cooccurrence
        )

    def suggest_narrowing_keywords(
        self,
        query_keywords: list[str],
        search_results: list[dict[str, Any]],
        top_n: int = 5,
        min_result_count: int = 2,
    ) -> list[dict[str, Any]]:
        """
        Suggest keywords to narrow down search results.

        Useful when a search returns too many results.

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
        if not self.cooccurrence_analyzer:
            return []

        return self.cooccurrence_analyzer.suggest_narrowing_keywords(
            query_keywords, search_results, top_n=top_n, min_result_count=min_result_count
        )
