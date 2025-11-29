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
