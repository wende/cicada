#!/usr/bin/env python3
"""
Automated import fixing script for Cicada refactoring.

This script updates all import statements to reflect the new language-specific structure:
- cicada.parser -> cicada.languages.elixir.parser
- cicada.indexer -> cicada.languages.elixir.indexer
- cicada.extractors -> cicada.languages.elixir.extractors
"""

import re
from pathlib import Path

# Define import replacements (old_pattern, new_replacement)
IMPORT_REPLACEMENTS = [
    # Parser imports
    (
        r"from cicada\.parser import ElixirParser",
        "from cicada.languages.elixir.parser import ElixirParser",
    ),
    (r"from cicada import parser", "from cicada.languages.elixir import parser"),
    (r"import cicada\.parser", "import cicada.languages.elixir.parser"),
    # Indexer imports
    (
        r"from cicada\.indexer import ElixirIndexer",
        "from cicada.languages.elixir.indexer import ElixirIndexer",
    ),
    (r"from cicada\.indexer import", "from cicada.languages.elixir.indexer import"),
    (r"import cicada\.indexer", "import cicada.languages.elixir.indexer"),
    # Extractor imports - specific functions
    (
        r"from cicada\.extractors\.base import",
        "from cicada.languages.elixir.extractors.base import",
    ),
    (
        r"from cicada\.extractors\.module import",
        "from cicada.languages.elixir.extractors.module import",
    ),
    (
        r"from cicada\.extractors\.function import",
        "from cicada.languages.elixir.extractors.function import",
    ),
    (
        r"from cicada\.extractors\.call import",
        "from cicada.languages.elixir.extractors.call import",
    ),
    (
        r"from cicada\.extractors\.dependency import",
        "from cicada.languages.elixir.extractors.dependency import",
    ),
    (
        r"from cicada\.extractors\.spec import",
        "from cicada.languages.elixir.extractors.spec import",
    ),
    (r"from cicada\.extractors\.doc import", "from cicada.languages.elixir.extractors.doc import"),
    # General extractors import
    (r"from cicada\.extractors import", "from cicada.languages.elixir.extractors import"),
    (r"import cicada\.extractors", "import cicada.languages.elixir.extractors"),
]


def fix_imports_in_file(file_path: Path) -> tuple[bool, int]:
    """
    Fix imports in a single Python file.

    Args:
        file_path: Path to the Python file

    Returns:
        Tuple of (was_modified, replacement_count)
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        original_content = content
        replacement_count = 0

        # Apply all replacements
        for old_pattern, new_replacement in IMPORT_REPLACEMENTS:
            if re.search(old_pattern, content):
                content = re.sub(old_pattern, new_replacement, content)
                replacement_count += 1

        # Write back if modified
        if content != original_content:
            file_path.write_text(content, encoding="utf-8")
            return (True, replacement_count)

        return (False, 0)

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return (False, 0)


def find_python_files(directory: Path, exclude_dirs: list[str] = None) -> list[Path]:
    """
    Find all Python files in a directory recursively.

    Args:
        directory: Root directory to search
        exclude_dirs: List of directory names to exclude

    Returns:
        List of Python file paths
    """
    if exclude_dirs is None:
        exclude_dirs = [
            "__pycache__",
            ".venv",
            "venv",
            ".git",
            "node_modules",
            "dist",
            "build",
            ".pytest_cache",
            ".mypy_cache",
        ]

    python_files = []
    for file_path in directory.rglob("*.py"):
        # Check if any parent directory is in exclude list
        if any(excluded in file_path.parts for excluded in exclude_dirs):
            continue
        python_files.append(file_path)

    return python_files


def main():
    """Main entry point for the import fixer."""
    print("🔧 Cicada Import Fixer")
    print("=" * 60)
    print()

    # Get project root (assuming script is in root)
    project_root = Path(__file__).parent

    # Find all Python files in cicada/ and tests/
    directories_to_process = [
        project_root / "cicada",
        project_root / "tests",
    ]

    all_files = []
    for directory in directories_to_process:
        if directory.exists():
            files = find_python_files(directory)
            all_files.extend(files)
            print(f"📁 Found {len(files)} Python files in {directory.relative_to(project_root)}/")

    print(f"\n📝 Total files to process: {len(all_files)}")
    print()

    # Process each file
    modified_count = 0
    total_replacements = 0

    for file_path in all_files:
        was_modified, replacement_count = fix_imports_in_file(file_path)
        if was_modified:
            modified_count += 1
            total_replacements += replacement_count
            rel_path = file_path.relative_to(project_root)
            print(f"✓ {rel_path} ({replacement_count} replacement(s))")

    print()
    print("=" * 60)
    print("✅ Complete!")
    print(f"   Modified files: {modified_count}/{len(all_files)}")
    print(f"   Total replacements: {total_replacements}")
    print()

    if modified_count == 0:
        print("   No import statements needed updating.")
    else:
        print("   All import statements have been updated to the new structure.")


if __name__ == "__main__":
    main()
