"""
Fallback Search Strategies.

Provides automatic fallback searches when primary searches fail to find results.
Each fallback strategy transforms the original search patterns and attempts
to find results with relaxed constraints.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any

from cicada.mcp.pattern_utils import FunctionPattern

if TYPE_CHECKING:
    from cicada.query.types import QueryOptions, SearchResult


@dataclass
class FallbackResult:
    """Result of a fallback search attempt."""

    results: list[dict[str, Any]]
    note: str | None = None


# =============================================================================
# Function Fallback Strategies
# =============================================================================


class FallbackStrategy:
    """Base class for fallback search strategies."""

    def should_try(self, patterns: list[FunctionPattern], context: dict[str, Any]) -> bool:
        """Return True if this fallback should be attempted."""
        raise NotImplementedError

    def transform_patterns(self, patterns: list[FunctionPattern]) -> list[FunctionPattern]:
        """Transform patterns for fallback search."""
        raise NotImplementedError

    def get_note(self, patterns: list[FunctionPattern]) -> str:
        """Return a note describing what fallback was used."""
        raise NotImplementedError


class WithoutModuleFallback(FallbackStrategy):
    """Try searching without module qualifier when Module.func not found."""

    def should_try(self, patterns: list[FunctionPattern], context: dict[str, Any]) -> bool:
        # Skip if module_path was explicitly provided (user wants constrained search)
        if context.get("module_path"):
            return False
        return any(p.module is not None for p in patterns)

    def transform_patterns(self, patterns: list[FunctionPattern]) -> list[FunctionPattern]:
        return [
            FunctionPattern(file=p.file, module=None, name=p.name, arity=p.arity) for p in patterns
        ]

    def get_note(self, patterns: list[FunctionPattern]) -> str:
        # Find first pattern with a non-None module
        orig_module = next((p.module for p in patterns if p.module), "")
        orig_module = orig_module.replace("*.", "")  # Remove wildcard prefix
        return f"no matches in `{orig_module}`" if orig_module else "no matches with module"


class WithoutArityFallback(FallbackStrategy):
    """Try searching without arity when func/N not found."""

    def should_try(self, patterns: list[FunctionPattern], context: dict[str, Any]) -> bool:
        return any(p.arity is not None for p in patterns)

    def transform_patterns(self, patterns: list[FunctionPattern]) -> list[FunctionPattern]:
        return [
            FunctionPattern(file=p.file, module=p.module, name=p.name, arity=None) for p in patterns
        ]

    def get_note(self, patterns: list[FunctionPattern]) -> str:
        orig_arities = [str(p.arity) for p in patterns if p.arity is not None]
        return f"no matches with arity /{'/'.join(orig_arities)}"


class PrivateFunctionFallback(FallbackStrategy):
    """Try searching for private function (_func) when public func not found."""

    def should_try(self, patterns: list[FunctionPattern], context: dict[str, Any]) -> bool:
        return any(p.name and not p.name.startswith("_") and "*" not in p.name for p in patterns)

    def transform_patterns(self, patterns: list[FunctionPattern]) -> list[FunctionPattern]:
        return [
            FunctionPattern(file=p.file, module=p.module, name=f"_{p.name}", arity=p.arity)
            for p in patterns
            if p.name and not p.name.startswith("_")
        ]

    def get_note(self, patterns: list[FunctionPattern]) -> str:
        return "showing private functions"


# Default fallback strategies in priority order
# Note: CamelSnakeFallback and PrefixWildcardFallback are defined later in file
# They're added to this list at module load time (see bottom of file)
DEFAULT_FUNCTION_FALLBACKS: list[FallbackStrategy] = [
    WithoutModuleFallback(),
    WithoutArityFallback(),
    PrivateFunctionFallback(),
]


def apply_fallbacks(
    patterns: list[FunctionPattern],
    search_fn: Callable[[list[FunctionPattern]], list[dict[str, Any]]],
    context: dict[str, Any] | None = None,
    strategies: list[FallbackStrategy] | None = None,
) -> FallbackResult:
    """
    Apply fallback strategies until results are found or all strategies exhausted.

    Args:
        patterns: Original search patterns that returned no results
        search_fn: Function that executes a search with given patterns
        context: Optional context dict (e.g., {"module_path": "MyApp.User"})
        strategies: List of fallback strategies to try (defaults to DEFAULT_FUNCTION_FALLBACKS)

    Returns:
        FallbackResult with any found results and combined notes
    """
    if strategies is None:
        strategies = DEFAULT_FUNCTION_FALLBACKS
    if context is None:
        context = {}

    notes: list[str] = []

    for strategy in strategies:
        if not strategy.should_try(patterns, context):
            continue

        fallback_patterns = strategy.transform_patterns(patterns)
        if not fallback_patterns:
            continue

        results = search_fn(fallback_patterns)
        # Record note for this attempt (whether successful or not)
        notes.append(strategy.get_note(patterns))
        if results:
            # Return results with accumulated notes from all tried strategies
            return FallbackResult(results=results, note=", ".join(notes))

    return FallbackResult(results=[], note=None)


# =============================================================================
# Module Fallback Strategies
# =============================================================================


class ModuleFallbackStrategy:
    """Base class for module fallback search strategies."""

    def should_try(self, module_name: str, context: dict[str, Any]) -> bool:
        """Return True if this fallback should be attempted."""
        raise NotImplementedError

    def transform_pattern(self, module_name: str) -> str:
        """Transform module pattern for fallback search."""
        raise NotImplementedError

    def get_note(self, module_name: str) -> str:
        """Return a note describing what fallback was used."""
        raise NotImplementedError


class LastSegmentFallback(ModuleFallbackStrategy):
    """Try searching with just the last segment when A.B.C.D not found.

    For single-segment modules like "User", tries *.User to find nested modules.
    For multi-segment modules like "A.B.C.User", extracts just "User" and tries *.User.
    """

    def should_try(self, module_name: str, context: dict[str, Any]) -> bool:
        # Always try - works for both single and multi-segment modules
        return True

    def transform_pattern(self, module_name: str) -> str:
        # Extract last segment and add wildcard prefix
        last_segment = module_name.rsplit(".", 1)[-1]
        return f"*.{last_segment}"

    def get_note(self, module_name: str) -> str:
        last_segment = module_name.rsplit(".", 1)[-1]
        if "." in module_name:
            return (
                f"no exact match for `{module_name}`, showing modules ending with `{last_segment}`"
            )
        return f"showing modules ending with `{last_segment}`"


# Default module fallback strategies in priority order
DEFAULT_MODULE_FALLBACKS: list[ModuleFallbackStrategy] = [
    LastSegmentFallback(),
]


@dataclass
class ModuleFallbackResult:
    """Result of a module fallback search attempt."""

    results: list[tuple[str, dict[str, Any]]]
    note: str | None = None


def apply_module_fallbacks(
    module_name: str,
    search_fn: Callable[[str], list[tuple[str, dict[str, Any]]]],
    context: dict[str, Any] | None = None,
    strategies: list[ModuleFallbackStrategy] | None = None,
) -> ModuleFallbackResult:
    """
    Apply module fallback strategies until results are found or all strategies exhausted.

    Args:
        module_name: Original module name that returned no results
        search_fn: Function that executes a search with given pattern, returns list of (module_name, data) tuples
        context: Optional context dict
        strategies: List of fallback strategies to try (defaults to DEFAULT_MODULE_FALLBACKS)

    Returns:
        ModuleFallbackResult with any found results and combined notes
    """
    if strategies is None:
        strategies = DEFAULT_MODULE_FALLBACKS
    if context is None:
        context = {}

    notes: list[str] = []

    for strategy in strategies:
        if not strategy.should_try(module_name, context):
            continue

        fallback_pattern = strategy.transform_pattern(module_name)
        results = search_fn(fallback_pattern)
        # Record note for this attempt (whether successful or not)
        notes.append(strategy.get_note(module_name))
        if results:
            # Return results with accumulated notes from all tried strategies
            return ModuleFallbackResult(results=results, note=", ".join(notes))

    return ModuleFallbackResult(results=[], note=None)


# =============================================================================
# Query Fallback Strategies
# =============================================================================


@dataclass
class QueryFallbackResult:
    """Result of a query fallback search attempt."""

    results: list["SearchResult"]
    note: str | None = None


class QueryFallbackStrategy:
    """Base class for query fallback search strategies."""

    def should_try(self, options: "QueryOptions", context: dict[str, Any]) -> bool:
        """Return True if this fallback should be attempted."""
        raise NotImplementedError

    def transform_options(self, options: "QueryOptions") -> "QueryOptions":
        """Transform options for fallback search."""
        raise NotImplementedError

    def get_note(self, options: "QueryOptions") -> str:
        """Return a note describing what fallback was used."""
        raise NotImplementedError


class MatchSourceFallback(QueryFallbackStrategy):
    """Broaden from specific match_source to 'all' when no results."""

    def should_try(self, options: "QueryOptions", context: dict[str, Any]) -> bool:
        return options.match_source in ("strings", "docs", "comments")

    def transform_options(self, options: "QueryOptions") -> "QueryOptions":
        return replace(options, match_source="all")

    def get_note(self, options: "QueryOptions") -> str:
        return f"no matches in {options.match_source}, showing all sources"


class ScopeFallback(QueryFallbackStrategy):
    """Broaden from public/private scope to 'all' when no results."""

    def should_try(self, options: "QueryOptions", context: dict[str, Any]) -> bool:
        return options.scope in ("public", "private")

    def transform_options(self, options: "QueryOptions") -> "QueryOptions":
        return replace(options, scope="all")

    def get_note(self, options: "QueryOptions") -> str:
        return f"no {options.scope} matches, showing all visibility"


class RecentFallback(QueryFallbackStrategy):
    """Include older code when recent=true returns no results."""

    def should_try(self, options: "QueryOptions", context: dict[str, Any]) -> bool:
        return options.recent is True

    def transform_options(self, options: "QueryOptions") -> "QueryOptions":
        return replace(options, recent=False)

    def get_note(self, options: "QueryOptions") -> str:
        return "no recent matches, showing older code"


class RipgrepFallbackStrategy(QueryFallbackStrategy):
    """Fallback to ripgrep text search when keyword/pattern search finds nothing.

    This strategy searches raw file content using ripgrep and enriches results
    with module/function metadata from the index.
    """

    def should_try(self, options: "QueryOptions", context: dict[str, Any]) -> bool:
        """Try ripgrep when no results and query is not a pattern."""
        # Only if no results from previous searches
        if context.get("has_results", False):
            return False

        # Only for keyword-style queries (not patterns with wildcards)
        original_query = context.get("original_query", "")
        if isinstance(original_query, str):
            # Skip pattern queries (wildcards, OR, module qualifiers, arity)
            if any(c in original_query for c in "*|/"):
                return False
            # Skip module qualifiers (Capitalized.Name)
            if "." in original_query and original_query[0:1].isupper():
                return False

        # Need index to perform search
        return bool(context.get("index"))

    def transform_options(self, options: "QueryOptions") -> "QueryOptions":
        """Mark options for ripgrep search."""
        # Create a copy with ripgrep flag
        new_options = replace(options)
        object.__setattr__(new_options, "_use_ripgrep", True)
        return new_options

    def get_note(self, options: "QueryOptions") -> str:
        return "no index matches, showing ripgrep content search results"


# Default query fallback strategies in priority order
DEFAULT_QUERY_FALLBACKS: list[QueryFallbackStrategy] = [
    MatchSourceFallback(),
    ScopeFallback(),
    RecentFallback(),
    RipgrepFallbackStrategy(),
]


def apply_query_fallbacks(
    options: "QueryOptions",
    search_fn: Callable[["QueryOptions"], list["SearchResult"]],
    context: dict[str, Any] | None = None,
    strategies: list[QueryFallbackStrategy] | None = None,
) -> QueryFallbackResult:
    """
    Apply query fallback strategies until results are found or all strategies exhausted.

    Args:
        options: Original query options that returned no results
        search_fn: Function that executes a search with given options
        context: Optional context dict
        strategies: List of fallback strategies to try (defaults to DEFAULT_QUERY_FALLBACKS)

    Returns:
        QueryFallbackResult with any found results and combined notes
    """
    if strategies is None:
        strategies = DEFAULT_QUERY_FALLBACKS
    if context is None:
        context = {}

    notes: list[str] = []

    for strategy in strategies:
        if not strategy.should_try(options, context):
            continue

        # Handle ripgrep strategy specially
        if isinstance(strategy, RipgrepFallbackStrategy):
            results = _execute_ripgrep_fallback(options, context)
        else:
            fallback_options = strategy.transform_options(options)
            results = search_fn(fallback_options)

        # Record note for this attempt (whether successful or not)
        notes.append(strategy.get_note(options))
        if results:
            # Return results with accumulated notes from all tried strategies
            return QueryFallbackResult(results=results, note=", ".join(notes))

    return QueryFallbackResult(results=[], note=None)


def _execute_ripgrep_fallback(
    options: "QueryOptions", context: dict[str, Any]
) -> list["SearchResult"]:
    """Execute ripgrep search for fallback.

    Args:
        options: Query options
        context: Context dict with index and original_query

    Returns:
        List of search results from ripgrep
    """
    index = context.get("index", {})
    original_query = context.get("original_query", "")

    # Convert query to string if it's a list
    if isinstance(original_query, list):
        # For list queries, use the first term or join them
        if len(original_query) == 1:
            query_str = str(original_query[0])
        else:
            # Multiple terms - ripgrep works better with single patterns
            # Use the most specific term (longest)
            query_str = max((str(q) for q in original_query), key=len)
    else:
        query_str = str(original_query)

    # Build globs from options
    globs = []
    if options.glob:
        globs.append(options.glob)

    # Add type-based globs if specified
    if hasattr(options, "type") and options.type:
        type_to_glob = {
            "py": "*.py",
            "ex": "*.{ex,exs}",
            "ts": "*.{ts,tsx}",
            "js": "*.{js,jsx}",
            "rs": "*.rs",
            "go": "*.go",
            "java": "*.java",
        }
        if options.type in type_to_glob:
            globs.append(type_to_glob[options.type])

    return _ripgrep_search_with_index(
        query=query_str,
        index=index,
        globs=globs if globs else None,
        max_results=options.max_results if hasattr(options, "max_results") else 10,
    )


# =============================================================================
# Additional Function Fallback Strategies
# =============================================================================


class CamelSnakeFallback(FallbackStrategy):
    """Try snake_case when camelCase not found (and vice versa)."""

    def should_try(self, patterns: list[FunctionPattern], context: dict[str, Any]) -> bool:
        # Only for exact names (no wildcards)
        return any(
            p.name and "*" not in p.name and (self._is_camel(p.name) or "_" in p.name)
            for p in patterns
        )

    def transform_patterns(self, patterns: list[FunctionPattern]) -> list[FunctionPattern]:
        return [
            FunctionPattern(
                file=p.file, module=p.module, name=self._convert_case(p.name), arity=p.arity
            )
            for p in patterns
            if p.name and "*" not in p.name
        ]

    def _is_camel(self, name: str) -> bool:
        """Check if name is camelCase."""
        return any(c.isupper() for c in name[1:]) and "_" not in name

    def _convert_case(self, name: str) -> str:
        """Convert between camelCase and snake_case."""
        if "_" in name:
            # snake_case → camelCase
            parts = name.split("_")
            return parts[0] + "".join(p.capitalize() for p in parts[1:])
        else:
            # camelCase → snake_case
            return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()

    def get_note(self, patterns: list[FunctionPattern]) -> str:
        return "showing alternate case style"


class PrefixWildcardFallback(FallbackStrategy):
    """Add wildcards when exact function name not found."""

    def should_try(self, patterns: list[FunctionPattern], context: dict[str, Any]) -> bool:
        # Only for exact names without wildcards, and at least 4 chars
        return any(p.name and "*" not in p.name and len(p.name) >= 4 for p in patterns)

    def transform_patterns(self, patterns: list[FunctionPattern]) -> list[FunctionPattern]:
        return [
            FunctionPattern(file=p.file, module=p.module, name=f"*{p.name}*", arity=p.arity)
            for p in patterns
            if p.name and "*" not in p.name and len(p.name) >= 4
        ]

    def get_note(self, patterns: list[FunctionPattern]) -> str:
        return "showing partial name matches"


# Add new function fallbacks to the default list
DEFAULT_FUNCTION_FALLBACKS.extend(
    [
        CamelSnakeFallback(),
        PrefixWildcardFallback(),
    ]
)


# =============================================================================
# Ripgrep Search Integration
# =============================================================================


def _ripgrep_search_with_index(
    query: str,
    index: dict[str, Any],
    globs: list[str] | None = None,
    repo_path: str | None = None,
    max_results: int = 20,
) -> list["SearchResult"]:
    """Search using ripgrep and enrich results with index metadata.

    Args:
        query: Search query string (literal text to find)
        index: Cicada index with module/function metadata
        globs: Optional file glob patterns to limit search
        repo_path: Repository path (defaults to index metadata)
        max_results: Maximum number of results to return

    Returns:
        List of SearchResult-compatible dictionaries
    """
    try:
        from python_ripgrep import search as ripgrep_search
    except ImportError:
        return []

    # Get repo path from index if not provided
    if not repo_path:
        repo_path = index.get("metadata", {}).get("repo_path", ".")

    # Build file to module/function mapping from index
    file_to_module = _build_file_to_module_map(index)

    # Perform ripgrep search
    try:
        raw_results = ripgrep_search(
            patterns=[query],
            paths=[repo_path] if repo_path else None,
            globs=globs,
            line_number=True,
            after_context=2,
            before_context=2,
        )
    except Exception:
        # Ripgrep may fail for various reasons (no matches, path issues, etc.)
        return []

    # Parse and enrich results
    enriched_results: list[SearchResult] = []
    for raw_line in raw_results[:max_results]:
        parsed = _parse_ripgrep_line(raw_line)
        if not parsed:
            continue

        # Enrich with metadata from index
        module_info = file_to_module.get(parsed["file"], {})
        containing_func = _find_containing_function(parsed["file"], parsed["line"], module_info)

        result = _create_ripgrep_search_result(
            file_path=parsed["file"],
            line=parsed["line"],
            match_text=parsed.get("text", ""),
            module=module_info.get("module_name"),
            function=containing_func,
            context_before=parsed.get("context_before", []),
            context_after=parsed.get("context_after", []),
        )
        enriched_results.append(result)

    return enriched_results


def _build_file_to_module_map(index: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Build a mapping from file paths to module info.

    Returns:
        Dict mapping file path to dict with module_name and functions list
    """
    file_map = {}

    for module_name, module_data in index.get("modules", {}).items():
        file_path = module_data.get("file", "")
        if not file_path:
            continue

        file_map[file_path] = {
            "module_name": module_name,
            "functions": module_data.get("functions", []),
        }

    return file_map


def _parse_ripgrep_line(line: str) -> dict[str, Any] | None:
    """Parse a ripgrep output line.

    Ripgrep output format with context:
        file.ts:10:    match text here
        file.ts-9:    context before
        file.ts-11:    context after

    Returns:
        Dict with file, line, text, and optional context lines
    """
    # Find the first colon separator
    if ":" not in line:
        return None

    # Handle context lines (marked with -) vs match lines (marked with :)
    # Format: path:line:text or path-line:text
    first_colon = line.find(":")

    # Check if this is actually a context separator (--)
    if line.startswith("--"):
        return None

    # Try to find line number
    path_part = line[:first_colon]
    rest = line[first_colon + 1 :]

    # Check if path_part ends with - or : (context vs match)
    if path_part.endswith(("-", ":")):
        is_context = path_part.endswith("-")
        path = path_part[:-1]
    else:
        # Try to parse line number from rest
        path = path_part
        is_context = False

    # Find line number (next colon)
    if ":" not in rest:
        return None

    line_num_str, text = rest.split(":", 1)

    try:
        line_num = int(line_num_str.replace("-", "").replace(":", ""))
    except ValueError:
        return None

    return {
        "file": path,
        "line": line_num,
        "text": text.strip(),
        "is_context": is_context,
    }


def _find_containing_function(file_path: str, line: int, module_info: dict[str, Any]) -> str | None:
    """Find which function contains the given line.

    Args:
        file_path: Path to the file
        line: Line number to check
        module_info: Module info dict with functions list

    Returns:
        Function name if found, None otherwise
    """
    functions = module_info.get("functions", [])
    if not functions:
        return None

    # Sort functions by line number
    sorted_funcs = sorted(functions, key=lambda f: f.get("line", 0))

    # Find the function whose line range contains the target line
    containing_func = None
    for i, func in enumerate(sorted_funcs):
        func_line = func.get("line", 0)

        # Check if this function starts before or at the target line
        if func_line <= line:
            # Check if next function starts after the target line
            if i + 1 < len(sorted_funcs):
                next_func_line = sorted_funcs[i + 1].get("line", float("inf"))
                if line < next_func_line:
                    containing_func = func.get("name")
            else:
                # This is the last function, it contains the line
                containing_func = func.get("name")

    return containing_func


def _create_ripgrep_search_result(
    file_path: str,
    line: int,
    match_text: str,
    module: str | None = None,
    function: str | None = None,
    context_before: list[str] | None = None,
    context_after: list[str] | None = None,
) -> "SearchResult":
    """Create a SearchResult from ripgrep match.

    Ripgrep results have lower scores than index matches since they're
    not based on semantic keyword extraction.
    """
    from cicada.query.types import SearchResult

    # Build a descriptive name
    if module and function:
        name = f"{module}.{function}"
    elif module:
        name = module
    else:
        name = file_path.split("/")[-1] if "/" in file_path else file_path

    # Build snippet from context (stored in doc field)
    snippet_lines = []
    if context_before:
        snippet_lines.extend(context_before)
    snippet_lines.append(match_text)
    if context_after:
        snippet_lines.extend(context_after)

    snippet = "\n".join(snippet_lines) if snippet_lines else match_text

    return SearchResult(
        type="function" if function else "module",
        name=name,
        module=module or "",
        file=file_path,
        line=line,
        score=0.5,  # Lower score than index matches
        confidence=50.0,
        matched_keywords=[],  # Ripgrep doesn't extract keywords
        pattern_match=False,
        search_source="keyword",  # Use keyword as base type
        function=function,
        doc=snippet,  # Store snippet in doc field
    )
