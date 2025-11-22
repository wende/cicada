"""
Helper utilities for wildcard and OR pattern handling within MCP tools.
"""

from __future__ import annotations

import contextlib
import fnmatch
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

__all__ = [
    "FunctionPattern",
    "has_wildcards",
    "match_any_pattern",
    "match_wildcard",
    "matches_pattern",
    "parse_function_patterns",
    "split_or_patterns",
]


def has_wildcards(pattern: str) -> bool:
    """Return True if the supplied pattern contains wildcard characters."""
    return "*" in pattern or "|" in pattern


def match_wildcard(pattern: str, text: str) -> bool:
    """
    Check if text matches a wildcard pattern.

    Supports * (matches any characters) only, not ?.
    """
    if "?" in pattern:
        return False
    return fnmatch.fnmatch(text.lower(), pattern.lower())


def matches_pattern(pattern: str | None, text: str) -> bool:
    """
    Evaluate whether text satisfies a (possibly wildcard) pattern.

    Special handling for *.Prefix patterns:
    - *.Something matches: Something, X.Something, X.Y.Something
    - *.Something.* matches: Something.Z, X.Something.Z
    - *.Something* matches: SomethingElse, X.SomethingElse
    """
    if not pattern or pattern == "*":
        return True
    if "*" in pattern:
        # Special case: *.Something should match both "X.Something" AND "Something"
        if pattern.startswith("*."):
            suffix = pattern[2:]  # Remove "*."

            # Check if suffix has wildcards
            if "*" in suffix:
                # Suffix has wildcards - need to use fnmatch
                # Match both "Something*" and "X.Something*" patterns
                if match_wildcard(suffix, text):
                    return True  # Direct match without prefix

                # Try matching with any prefix: split text by dots and check if suffix matches tail
                # e.g., "ThenvoiCom.AgentModule" split by "." → check if "Agent*" matches "AgentModule"
                text_parts = text.lower().split(".")
                # Try matching suffix against progressively shorter tails without
                # repeatedly joining the full tail string on each iteration.
                tail = ""
                for part in reversed(text_parts):
                    tail = f"{part}.{tail}" if tail else part
                    if match_wildcard(suffix, tail):
                        return True
                return False
            else:
                # Suffix has no wildcards - use exact matching
                text_lower = text.lower()
                suffix_lower = suffix.lower()

                # 1. Exact match: "Something"
                if text_lower == suffix_lower:
                    return True

                # 2. Suffix match: "X.Something"
                if text_lower.endswith("." + suffix_lower):
                    return True

                # 3. Prefix match: "Something.X" (for patterns like ThenvoiCom.Agents.*)
                if text_lower.startswith(suffix_lower + "."):
                    return True

                # 4. Contains match: "X.Something.Y" (component match)
                # Check if suffix appears as a complete component path
                return ("." + suffix_lower + ".") in ("." + text_lower + ".")
        return match_wildcard(pattern, text)
    return pattern.lower() == text.lower()


def match_any_pattern(patterns: Iterable[str], text: str) -> bool:
    """Return True if the text matches any of the provided patterns."""
    return any(matches_pattern(pattern.strip(), text) for pattern in patterns if pattern.strip())


def split_or_patterns(pattern: str) -> list[str]:
    """Split a pattern by the OR symbol (|)."""
    return [p.strip() for p in pattern.split("|")]


@dataclass(frozen=True)
class FunctionPattern:
    """Structured representation of a parsed function search pattern."""

    file: str | None = None
    module: str | None = None
    name: str = "*"
    arity: int | None = None

    @classmethod
    def from_string(cls, pattern: str) -> FunctionPattern:
        """Parse a raw pattern string into a `FunctionPattern` instance."""
        raw = pattern.strip()
        if not raw:
            raw = "*"

        file_pattern: str | None = None
        module_pattern: str | None = None
        name_pattern = raw
        arity: int | None = None

        if ":" in name_pattern:
            file_candidate, remainder = name_pattern.split(":", 1)
            if "/" in file_candidate or file_candidate.endswith((".ex", ".exs")):
                file_pattern = file_candidate
                name_pattern = remainder

        if "." in name_pattern:
            module_pattern, name_pattern = name_pattern.rsplit(".", 1)
            # Add wildcard prefix to module pattern if it doesn't have one
            # This allows "SomeModule.func" to match "MyProject.SomeModule.func"
            if module_pattern and "*" not in module_pattern and "|" not in module_pattern:
                module_pattern = f"*.{module_pattern}"

        if "/" in name_pattern:
            name_part, arity_part = name_pattern.rsplit("/", 1)
            with contextlib.suppress(ValueError):
                arity = int(arity_part)
            name_pattern = name_part

        if not name_pattern:
            name_pattern = "*"

        return cls(file=file_pattern, module=module_pattern, name=name_pattern, arity=arity)

    def matches(self, module_name: str, file_path: str, func: dict[str, Any]) -> bool:
        """Return True if the function entry satisfies this pattern."""
        return (
            matches_pattern(self.module, module_name)
            and matches_pattern(self.file, file_path)
            and matches_pattern(self.name, func["name"])
            and (self.arity is None or func["arity"] == self.arity)
        )


def parse_function_patterns(raw: str | None) -> list[FunctionPattern]:
    """Split and parse a compound OR pattern string into FunctionPattern objects."""
    if not raw:
        return [FunctionPattern()]

    patterns = [
        FunctionPattern.from_string(part) for part in split_or_patterns(raw) if part.strip()
    ]
    return patterns or [FunctionPattern()]
