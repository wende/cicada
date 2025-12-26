"""
Domain types for query orchestration.

Type-safe representations of queries, results, and configurations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, TypedDict


class StringSource(TypedDict, total=False):
    """Structure for string literal matches."""

    string: str
    line: int
    function: str
    module: str
    file: str


@dataclass
class SearchResult:
    """Type-safe search result from pattern or keyword search."""

    type: Literal["module", "function"]
    name: str
    module: str
    file: str
    line: int
    score: float
    confidence: float
    matched_keywords: list[str]
    pattern_match: bool
    doc: str | None = None
    keyword_sources: dict[str, str] = field(default_factory=dict)
    string_sources: list[StringSource] = field(default_factory=list)

    # Function-specific fields
    function: str | None = None
    arity: int | None = None
    signature: str | None = None
    visibility: Literal["def", "defp"] | None = None
    last_modified_at: str | None = None
    last_modified_sha: str | None = None
    last_modified_pr: int | None = None

    # Statistical scoring fields (added by score distribution analysis)
    z_score: float | None = None
    percentile: float | None = None
    normalized_score: float | None = None
    tier: str | None = None
    tier_label: str | None = None
    tier_description: str | None = None
    tier_rank: int | None = None

    # Hybrid search source tracking
    search_source: Literal["keyword", "semantic", "both"] = "keyword"

    def is_function(self) -> bool:
        """Check if this result is a function."""
        return self.type == "function"

    def is_module(self) -> bool:
        """Check if this result is a module."""
        return self.type == "module"

    def is_public(self) -> bool:
        """Check if this is a public function."""
        # Only functions have visibility; modules are always considered "public" for filtering
        if self.is_module():
            return True
        # Support both Elixir ('def') and SCIP ('public') visibility strings
        return self.visibility in ("def", "public")

    def is_private(self) -> bool:
        """Check if this is a private function."""
        # Support both Elixir ('defp') and SCIP ('private') visibility strings
        return self.visibility in ("defp", "private")

    def get_last_modified(self) -> datetime | None:
        """Get the last modified timestamp if available."""
        if not self.last_modified_at:
            return None
        try:
            return datetime.fromisoformat(self.last_modified_at.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format for backward compatibility."""
        result: dict[str, Any] = {
            "type": self.type,
            "name": self.name,
            "module": self.module,
            "file": self.file,
            "line": self.line,
            "score": self.score,
            "confidence": self.confidence,
            "matched_keywords": self.matched_keywords,
            "pattern_match": self.pattern_match,
            "keyword_sources": self.keyword_sources,
        }

        if self.doc is not None:
            result["doc"] = self.doc

        if self.string_sources:
            result["string_sources"] = self.string_sources

        # Function-specific fields
        if self.is_function():
            if self.function is not None:
                result["function"] = self.function
            if self.arity is not None:
                result["arity"] = self.arity
            if self.signature is not None:
                result["signature"] = self.signature
            if self.visibility is not None:
                result["visibility"] = self.visibility
            if self.last_modified_at is not None:
                result["last_modified_at"] = self.last_modified_at
            if self.last_modified_sha is not None:
                result["last_modified_sha"] = self.last_modified_sha
            if self.last_modified_pr is not None:
                result["last_modified_pr"] = self.last_modified_pr

        # Statistical scoring fields
        if self.z_score is not None:
            result["z_score"] = self.z_score
        if self.percentile is not None:
            result["percentile"] = self.percentile
        if self.normalized_score is not None:
            result["normalized_score"] = self.normalized_score
        if self.tier is not None:
            result["tier"] = self.tier
        if self.tier_label is not None:
            result["tier_label"] = self.tier_label
        if self.tier_description is not None:
            result["tier_description"] = self.tier_description
        if self.tier_rank is not None:
            result["tier_rank"] = self.tier_rank

        return result


@dataclass
class QueryStrategy:
    """Search strategy determined by query analysis."""

    use_keyword_search: bool
    use_pattern_search: bool
    search_keywords: list[str | list[str]]
    search_patterns: list[str]


@dataclass
class FilterConfig:
    """Configuration for result filtering."""

    scope: Literal["all", "public", "private"] = "all"
    recent: bool = False
    result_type: Literal["all", "modules", "functions"] = "all"
    match_source: Literal["all", "docs", "strings", "comments"] = "all"
    glob: str | None = None  # Glob pattern for file filtering (renamed from path_pattern)
    arity: int | None = None

    # Aliases for backward compatibility (not used in filtering, just for API compat)
    # filter_type is an alias for result_type
    # path_pattern is an alias for glob


@dataclass
class QueryOptions:
    """Options for query execution."""

    scope: Literal["all", "public", "private"] = "all"
    recent: bool = False
    result_type: Literal["all", "modules", "functions"] = "all"
    match_source: Literal["all", "docs", "strings", "comments"] = "all"
    max_results: int = 10
    glob: str | None = None  # Glob pattern for file filtering
    arity: int | None = None
    show_snippets: bool = False
    offset: int = 0  # Skip first N results (pagination)
    context_lines: int = 2  # Lines of context in snippets (symmetric, like -C)
    context_before: int | None = None  # Override for lines before match (-B)
    context_after: int | None = None  # Override for lines after match (-A)

    # Deprecated aliases (kept for backward compatibility)
    # filter_type -> result_type (no-op, always "all")
    # path_pattern -> glob

    def to_filter_config(self) -> FilterConfig:
        """Convert to FilterConfig for filtering operations."""
        return FilterConfig(
            scope=self.scope,
            recent=self.recent,
            result_type=self.result_type,
            match_source=self.match_source,
            glob=self.glob,
            arity=self.arity,
        )


class QueryConfig:
    """Configuration constants for query orchestration."""

    # Recency filter
    RECENT_DAYS_THRESHOLD = 14  # Consider code "recent" if modified in last N days

    # Search limits
    INTERNAL_SEARCH_LIMIT = 100  # Fetch this many from search, then filter/rank
    MAX_SUGGESTIONS = 2  # Maximum suggestions to show (keep focused)

    # Snippet extraction
    DEFAULT_CONTEXT_LINES = 2  # Lines of context around target line

    # Display limits for compact output
    MAX_KEYWORDS_TO_SHOW = 3  # Maximum matched keywords to show before truncating

    # Module clustering
    MIN_RESULTS_FOR_CLUSTERING = 3  # Minimum results to consider clustering
    MIN_SAME_MODULE_FOR_SUGGESTION = (
        3  # Suggest module usage when this many results from same module
    )

    # Zero-result suggestions
    MAX_RELATED_TERMS = 5  # Maximum related terms to suggest
