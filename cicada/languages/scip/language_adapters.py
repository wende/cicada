"""Language-specific hooks for the SCIP converter.

The converter currently behaves like a Python-first implementation. This module starts
introducing a strategy layer so new languages (Rust, etc.) can supply their own alias
handling, builtin detection, and other quirks without hard-coding them directly in the
converter. For now we only expose alias extraction – future commits will add more
callbacks as we peel logic out of the converter.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path
from typing import Any

from cicada.languages.rust.alias_extractor import RustAliasExtractor


class BaseSCIPLanguageAdapter(ABC):
    """Defines language-specific extension points for SCIP conversion."""

    @abstractmethod
    def extract_aliases(self, doc: Any, repo_path: Path) -> dict[str, str]:
        """Return import alias mappings for the provided document."""


class PythonSCIPAdapter(BaseSCIPLanguageAdapter):
    """Adapter that mirrors the historical Python-only converter behavior."""

    def extract_aliases(self, doc: Any, repo_path: Path) -> dict[str, str]:
        from cicada.languages.python.alias_extractor import PythonAliasExtractor

        full_path = _resolve_file_path(doc, repo_path)
        if not full_path:
            return {}

        alias_extractor = PythonAliasExtractor()
        return alias_extractor.extract_aliases(full_path)


class RustSCIPAdapter(BaseSCIPLanguageAdapter):
    """Adapter entry point for Rust integration."""

    def __init__(self):
        self._extractor = RustAliasExtractor()

    def extract_aliases(self, doc: Any, repo_path: Path) -> dict[str, str]:
        full_path = _resolve_file_path(doc, repo_path)
        if not full_path:
            return {}

        return self._extractor.extract_aliases(full_path)


def _resolve_file_path(doc: Any, repo_path: Path) -> Path | None:
    """Best-effort resolution of a SCIP document to a file."""
    relative = getattr(doc, "relative_path", None)
    if not relative:
        return None
    return (Path(repo_path) / relative).resolve()


_REGISTRY: dict[str, Callable[[], BaseSCIPLanguageAdapter]] = {
    "python": PythonSCIPAdapter,
    "typescript": PythonSCIPAdapter,  # temporary: TS reuses python-ish logic today
    "rust": RustSCIPAdapter,
}
_CACHE: dict[str, BaseSCIPLanguageAdapter] = {}


def register_language_adapter(
    language: str, factory: Callable[[], BaseSCIPLanguageAdapter]
) -> None:
    _REGISTRY[language] = factory
    _CACHE.pop(language, None)


def get_language_adapter(language: str) -> BaseSCIPLanguageAdapter:
    try:
        adapter = _CACHE[language]
    except KeyError:
        if language not in _REGISTRY:
            raise KeyError(language) from None
        adapter = _REGISTRY[language]()
        _CACHE[language] = adapter
    return adapter


__all__ = [
    "BaseSCIPLanguageAdapter",
    "PythonSCIPAdapter",
    "RustSCIPAdapter",
    "get_language_adapter",
    "register_language_adapter",
]
