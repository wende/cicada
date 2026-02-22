"""Regex-based string literal extraction for SCIP-indexed languages.

Extracts string literals from source code using regex patterns.
Supports per-language string syntax (double-quoted, single-quoted, backtick).
"""

import re

# Universal double-quoted string pattern (works for all languages)
_DQ_PATTERN = re.compile(r'"((?:[^"\\]|\\.)*)"')

# Single-quoted string pattern (JS, TS, Ruby, Dart, etc.)
_SQ_PATTERN = re.compile(r"'((?:[^'\\]|\\.)*)'")

# Backtick/raw string pattern for Go (single-line only)
_BT_PATTERN = re.compile(r"`([^`]*)`")

# Languages that support single-quoted strings
_SINGLE_QUOTE_LANGUAGES = {"typescript", "javascript", "ruby", "dart"}

# Languages that support backtick raw strings
_BACKTICK_LANGUAGES = {"go"}

# Comment markers per language (shared with indexer.py comment extraction)
COMMENT_MARKERS: dict[str, str] = {
    "ruby": "#",
}

DEFAULT_COMMENT_MARKER = "//"


def get_comment_marker(language: str) -> str:
    """Return the line comment marker for a language."""
    return COMMENT_MARKERS.get(language, DEFAULT_COMMENT_MARKER)


class RegexStringExtractor:
    """Extract string literals from source code using regex patterns."""

    def __init__(self, language: str, min_length: int = 3):
        self.language = language
        self.min_length = min_length
        self._comment_marker = get_comment_marker(language)

    def extract_from_source(self, source_code: str) -> list[dict]:
        """Extract string literals from source code.

        Returns:
            List of dicts with keys: string, line, function (always None).
        """
        strings: list[dict] = []
        use_sq = self.language in _SINGLE_QUOTE_LANGUAGES
        use_bt = self.language in _BACKTICK_LANGUAGES

        for i, line in enumerate(source_code.splitlines()):
            line_num = i + 1
            clean = self._strip_full_line_comment(line)

            self._collect_matches(clean, line_num, _DQ_PATTERN, strings)
            if use_sq:
                self._collect_matches(clean, line_num, _SQ_PATTERN, strings)
            if use_bt:
                self._collect_matches(clean, line_num, _BT_PATTERN, strings)

        return strings

    def _strip_full_line_comment(self, line: str) -> str:
        """Strip full-line comments only (line starts with comment marker).

        Only strips lines where the comment marker appears at the start
        (after optional whitespace). This avoids incorrectly truncating
        strings containing comment-like markers (e.g., "http://example.com").
        """
        stripped = line.lstrip()
        if stripped.startswith(self._comment_marker):
            return ""
        return line

    def _collect_matches(
        self,
        line: str,
        line_num: int,
        pattern: re.Pattern,
        out: list[dict],
    ) -> None:
        for match in pattern.finditer(line):
            content = match.group(1)
            if len(content) >= self.min_length and content.strip():
                out.append({"string": content, "line": line_num, "function": None})
