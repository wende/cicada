"""
Fallback Search Strategies.

Provides automatic fallback searches when primary searches fail to find results.
Each fallback strategy transforms the original search patterns and attempts
to find results with relaxed constraints.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from cicada.mcp.pattern_utils import FunctionPattern


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
