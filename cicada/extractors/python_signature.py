"""Python function signature extractor.

Extracts function signatures from Python source code for co-change analysis.
"""

import re
from pathlib import Path

from cicada.extractors.base_signature import (
    FunctionSignatureExtractor,
    SignatureExtractorRegistry,
)

# Regex patterns for parsing Python code
# Matches: def func_name(params):, async def func_name(params):
PYTHON_FUNCTION_PATTERN = re.compile(
    r"^\s*(?:async\s+)?def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)\s*(?:->.*)?:", re.MULTILINE
)
# Matches: class ClassName:, class ClassName(Parent):
PYTHON_CLASS_PATTERN = re.compile(
    r"^\s*class\s+([A-Z][a-zA-Z0-9_]*)\s*(?:\([^)]*\))?\s*:", re.MULTILINE
)


class PythonSignatureExtractor(FunctionSignatureExtractor):
    """Extract function signatures from Python source code."""

    def get_file_extensions(self) -> list[str]:
        """Return Python file extensions.

        Returns:
            List containing .py extension
        """
        return [".py"]

    def extract_module_name(self, content: str, file_path: str) -> str | None:
        """Extract the module/class name from Python source code.

        For Python, we use the first class name found, or derive
        a module name from the file path.

        Args:
            content: Python source code
            file_path: Path to file

        Returns:
            Module/class name or None if not found
        """
        # First try to find a class definition
        class_match = PYTHON_CLASS_PATTERN.search(content)
        if class_match:
            return class_match.group(1)

        # Fall back to file-based module name
        # Convert path like "lib/my_app/user.py" to "_file_my_app.user"
        path = Path(file_path)
        if path.suffix == ".py":
            # Remove .py extension and convert path separators to dots
            parts = list(path.parts)
            if parts and parts[-1].endswith(".py"):
                parts[-1] = parts[-1][:-3]  # Remove .py

            # Skip common directory prefixes
            skip_prefixes = {"lib", "src", "app", "tests"}
            while parts and parts[0] in skip_prefixes:
                parts = parts[1:]

            if parts:
                return "_file_" + ".".join(parts)

        return None

    def extract_function_signatures(self, content: str, module_name: str) -> set[str]:
        """Extract all function signatures from Python source code.

        Args:
            content: Python source code
            module_name: Module/class name for qualifying functions

        Returns:
            Set of function signatures (e.g., {"ClassName.method_name/2"})
        """
        if not module_name:
            return set()

        signatures = set()
        for match in PYTHON_FUNCTION_PATTERN.finditer(content):
            func_name = match.group(1)
            # Skip private methods for co-change (they're internal details)
            # but keep single underscore (protected) methods
            if func_name.startswith("__") and not func_name.endswith("__"):
                continue

            arity = self._calculate_arity(match.group(2))
            signatures.add(f"{module_name}.{func_name}/{arity}")

        return signatures

    def _calculate_arity(self, params: str) -> int:
        """Calculate function arity from parameter string.

        Handles Python-specific cases like self, *args, **kwargs.

        Args:
            params: Function parameter string from regex match

        Returns:
            Approximate arity (parameter count excluding self/cls)
        """
        if not params.strip():
            return 0

        parts = [p.strip() for p in params.split(",") if p.strip()]
        # Exclude self/cls from count (they're implicit)
        parts = [p for p in parts if not p.startswith(("self", "cls"))]
        # Count *args and **kwargs as 1 each if present
        return len(parts)


# Register the extractor
SignatureExtractorRegistry.register("python", PythonSignatureExtractor)
