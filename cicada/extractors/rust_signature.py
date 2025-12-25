"""Rust function signature extractor.

Extracts function signatures from Rust source code for co-change analysis.
"""

import re
from pathlib import Path

from cicada.extractors.base_signature import (
    FunctionSignatureExtractor,
    SignatureExtractorRegistry,
)

# Regex patterns for parsing Rust code
# Matches: fn func_name(params), pub fn func_name(params), async fn, etc.
RUST_FUNCTION_PATTERN = re.compile(
    r"^\s*(?:pub(?:\s*\([^)]*\))?\s+)?(?:async\s+)?(?:unsafe\s+)?(?:extern\s+\"[^\"]*\"\s+)?"
    r"fn\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:<[^>]*>)?\s*\(([^)]*)\)",
    re.MULTILINE,
)

# Matches: struct Name, pub struct Name
RUST_STRUCT_PATTERN = re.compile(
    r"^\s*(?:pub(?:\s*\([^)]*\))?\s+)?struct\s+([A-Z][a-zA-Z0-9_]*)", re.MULTILINE
)

# Matches: impl Name { or impl Trait for Name {
RUST_IMPL_PATTERN = re.compile(
    r"^\s*impl(?:<[^>]*>)?\s+(?:([A-Z][a-zA-Z0-9_]*)\s+for\s+)?([A-Z][a-zA-Z0-9_]*)",
    re.MULTILINE,
)

# Matches: mod name
RUST_MOD_PATTERN = re.compile(
    r"^\s*(?:pub(?:\s*\([^)]*\))?\s+)?mod\s+([a-z_][a-z0-9_]*)", re.MULTILINE
)


class RustSignatureExtractor(FunctionSignatureExtractor):
    """Extract function signatures from Rust source code."""

    def get_file_extensions(self) -> list[str]:
        """Return Rust file extensions.

        Returns:
            List containing .rs extension
        """
        return [".rs"]

    def extract_module_name(self, content: str, file_path: str) -> str | None:
        """Extract the module/struct name from Rust source code.

        For Rust, we prioritize:
        1. First struct definition (most common for impl blocks)
        2. Mod name from file path

        Args:
            content: Rust source code
            file_path: Path to file

        Returns:
            Module/struct name or None if not found
        """
        # First try to find a struct definition
        struct_match = RUST_STRUCT_PATTERN.search(content)
        if struct_match:
            return struct_match.group(1)

        # Fall back to file-based module name
        path = Path(file_path)
        if path.suffix == ".rs":
            # lib.rs and main.rs use the crate/package name
            if path.stem in ("lib", "main", "mod"):
                # Use parent directory name
                if path.parent.name and path.parent.name != "src":
                    return f"_file_{path.parent.name}"
                return "_file_crate"

            # Regular files use their stem
            return f"_file_{path.stem}"

        return None

    def extract_function_signatures(self, content: str, module_name: str) -> set[str]:
        """Extract all function signatures from Rust source code.

        Args:
            content: Rust source code
            module_name: Module/struct name for qualifying functions

        Returns:
            Set of function signatures (e.g., {"Calculator.add/2"})
        """
        if not module_name:
            return set()

        signatures = set()

        # Track current impl block context
        current_impl_type: str | None = None
        lines = content.split("\n")
        impl_depth = 0

        for _i, line in enumerate(lines):
            # Check for impl block start
            impl_match = RUST_IMPL_PATTERN.match(line)
            if impl_match:
                # Group 2 is the type being implemented
                current_impl_type = impl_match.group(2)
                impl_depth = line.count("{") - line.count("}")
                continue

            # Track brace depth to know when impl block ends
            if current_impl_type:
                impl_depth += line.count("{") - line.count("}")
                if impl_depth <= 0:
                    current_impl_type = None

            # Find function definitions
            func_match = RUST_FUNCTION_PATTERN.match(line)
            if func_match:
                func_name = func_match.group(1)

                # Skip private functions (starting with _) for co-change analysis
                if func_name.startswith("_"):
                    continue

                # Skip test functions
                if func_name.startswith("test_"):
                    continue

                params = func_match.group(2)
                arity = self._calculate_arity(params)

                # Use impl type if inside an impl block, otherwise use module name
                context = current_impl_type or module_name
                signatures.add(f"{context}.{func_name}/{arity}")

        return signatures

    def _calculate_arity(self, params: str) -> int:
        """Calculate function arity from parameter string.

        Handles Rust-specific cases like &self, &mut self.

        Args:
            params: Function parameter string from regex match

        Returns:
            Approximate arity (parameter count excluding self)
        """
        if not params.strip():
            return 0

        parts = [p.strip() for p in params.split(",") if p.strip()]
        # Exclude self/&self/&mut self from count
        parts = [p for p in parts if not p.startswith(("self", "&self", "&mut self", "mut self"))]
        return len(parts)


# Register the extractor
SignatureExtractorRegistry.register("rust", RustSignatureExtractor)
