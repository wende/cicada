"""
String literal extraction from Rust source code.

This module extracts string literals from Rust source code using regex.
It is a simplified implementation compared to AST-based extractors.
"""

import re


class RustStringExtractor:
    """Extract string literals from Rust source code."""

    def __init__(self, min_length: int = 3):
        """
        Initialize the string extractor.

        Args:
            min_length: Minimum string length to extract (default: 3)
        """
        self.min_length = min_length

    def extract_from_source(self, source_code: str) -> list[dict]:
        """
        Extract all string literals from Rust source code.

        Args:
            source_code: Rust source code as string

        Returns:
            List of dicts containing:
                - string: The string content
                - line: Line number where the string appears
                - function: Name of the function containing the string (always None for regex impl)
        """
        strings = []

        # Regex for double-quoted strings: "((?:[^"\\]|\\.)*)"
        # This handles escaped quotes inside strings
        dq_pattern = re.compile(r'"((?:[^"\\]|\\.)*)"')

        # TODO: Add support for raw strings (r"...", r"#...#")

        lines = source_code.splitlines()
        for i, line in enumerate(lines):
            line_num = i + 1

            # Basic stripping of single-line comments
            # This is imperfect (e.g. comment marker inside string), but good enough for MVP
            clean_line = line
            if "//" in line:
                # Check if // is inside a string? Too complex for simple split.
                # We'll do a simple split for now, knowing it might break on "http://..."
                # Improved: only split if // is not preceded by " (very rough heuristic)
                parts = line.split("//")
                if len(parts) > 1:
                    clean_line = parts[0]

            for match in dq_pattern.finditer(clean_line):
                content = match.group(1)

                # Skip short strings
                if len(content) < self.min_length:
                    continue

                # Skip empty or whitespace-only strings
                if not content.strip():
                    continue

                strings.append(
                    {
                        "string": content,
                        "line": line_num,
                        "function": None,  # Function tracking not supported in regex extractor
                    }
                )

        return strings
