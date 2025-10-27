"""
Author: Cursor(Auto)

Mock Git command responses for testing.

Provides response builders for git operations that can be customized
for different test scenarios while maintaining realistic output formats.
"""

from typing import List, Dict, Any, Optional


def create_file_content_response(lines: List[str], _file_path: str = "test.py") -> str:
    """
    Create mock file content response.

    Args:
        lines: File lines as list of strings
        file_path: Path to the file

    Returns:
        File content as single string with newlines
    """
    return "\n".join(lines)


def create_git_show_response(
    _ref: str = "HEAD", file_path: str = "test.py", content: Optional[List[str]] = None
) -> str:
    """
    Create mock git show output.

    Args:
        ref: Git reference (commit SHA, branch, etc.)
        file_path: File path
        content: File content lines (uses default if None)

    Returns:
        Git show output string
    """
    if content is None:
        content = [
            "def hello_world():",
            "    print('Hello, World!')",
            "",
            "def main():",
            "    hello_world()",
            "",
            "if __name__ == '__main__':",
            "    main()",
        ]

    return create_file_content_response(content, file_path)


def create_git_ls_files_response(file_paths: List[str], exists: bool = True) -> str:
    """
    Create mock git ls-files output.

    Args:
        file_paths: List of file paths
        exists: Whether files exist (affects output)

    Returns:
        Git ls-files output string
    """
    if exists and file_paths:
        return "\n".join(file_paths)
    return ""


def create_git_log_response(
    commits: List[Dict[str, str]], format_string: str = "%H %s"
) -> str:
    """
    Create mock git log output.

    Args:
        commits: List of commit dictionaries with 'hash' and 'message'
        format_string: Git log format string

    Returns:
        Git log output string
    """
    lines = []
    for commit in commits:
        if format_string == "%H %s":
            lines.append(f"{commit['hash']} {commit['message']}")
        elif format_string == "%H":
            lines.append(commit["hash"])
        else:
            # Simple format handling
            line = format_string
            line = line.replace("%H", commit["hash"])
            line = line.replace("%s", commit["message"])
            lines.append(line)

    return "\n".join(lines)


def create_git_diff_response(
    file_path: str = "test.py", added_lines: int = 2, removed_lines: int = 1
) -> str:
    """
    Create mock git diff output.

    Args:
        file_path: File being diffed
        added_lines: Number of added lines
        removed_lines: Number of removed lines

    Returns:
        Git diff output string
    """
    diff_lines = [
        f"diff --git a/{file_path} b/{file_path}",
        "index 1234567..abcdefg 100644",
        f"--- a/{file_path}",
        f"+++ b/{file_path}",
        "@@ -1,5 +1,6 @@",
    ]

    # Add some context lines
    for i in range(removed_lines):
        diff_lines.append(f"-old line {i + 1}")

    for i in range(added_lines):
        diff_lines.append(f"+new line {i + 1}")

    return "\n".join(diff_lines)


def create_git_status_response(
    modified_files: List[str] = None,
    untracked_files: List[str] = None,
    staged_files: List[str] = None,
) -> str:
    """
    Create mock git status output.

    Args:
        modified_files: List of modified files
        untracked_files: List of untracked files
        staged_files: List of staged files

    Returns:
        Git status output string
    """
    if modified_files is None:
        modified_files = []
    if untracked_files is None:
        untracked_files = []
    if staged_files is None:
        staged_files = []

    lines = ["On branch main"]

    if staged_files:
        lines.append("Changes to be committed:")
        for file in staged_files:
            lines.append(f"  modified:   {file}")

    if modified_files:
        lines.append("Changes not staged for commit:")
        for file in modified_files:
            lines.append(f"  modified:   {file}")

    if untracked_files:
        lines.append("Untracked files:")
        for file in untracked_files:
            lines.append(f"  {file}")

    return "\n".join(lines)


# File evolution scenarios for line mapping tests


def create_file_evolution_scenario() -> Dict[str, List[str]]:
    """
    Create a file evolution scenario for testing line mapping.

    Returns:
        Dictionary with file content at different commits
    """
    return {
        "original": [
            "def function_a():",
            "    return 'a'",
            "",
            "def function_b():",
            "    return 'b'",
            "",
            "def function_c():",
            "    return 'c'",
        ],
        "modified": [
            "def function_a():",
            "    return 'a'",
            "",
            "# New comment added",
            "def function_b():",
            "    return 'b'",
            "",
            "def function_c():",
            "    return 'c'",
            "",
            "def function_d():",
            "    return 'd'",
        ],
        "refactored": [
            "def function_a():",
            "    return 'a'",
            "",
            "# New comment added",
            "def function_b():",
            "    return 'b'",
            "",
            "def function_c():",
            "    return 'c'",
            "",
            "def function_d():",
            "    return 'd'",
            "",
            "def function_e():",
            "    return 'e'",
        ],
    }


def create_line_mapping_test_data() -> Dict[str, Any]:
    """
    Create test data for line mapping scenarios.

    Returns:
        Dictionary with various line mapping test cases
    """
    return {
        "exact_match": {
            "original_line": 2,
            "original_content": "    return 'a'",
            "current_line": 2,
            "current_content": "    return 'a'",
        },
        "moved_down": {
            "original_line": 2,
            "original_content": "    return 'a'",
            "current_line": 3,
            "current_content": "    return 'a'",
        },
        "moved_up": {
            "original_line": 5,
            "original_content": "    return 'b'",
            "current_line": 4,
            "current_content": "    return 'b'",
        },
        "deleted": {
            "original_line": 2,
            "original_content": "    return 'a'",
            "current_line": None,
            "current_content": None,
        },
        "empty_line": {
            "original_line": 3,
            "original_content": "",
            "current_line": None,
            "current_content": None,
        },
    }


def create_git_error_response(
    error_message: str = "fatal: not a git repository",
) -> str:
    """
    Create mock git error output.

    Args:
        error_message: Error message to return

    Returns:
        Error output string
    """
    return error_message


def create_git_not_found_response() -> str:
    """
    Create response for when file is not found in git.

    Returns:
        Empty string (file not found)
    """
    return ""


# Helper functions for specific test scenarios


def create_simple_python_file() -> List[str]:
    """Create a simple Python file for testing."""
    return [
        "#!/usr/bin/env python3",
        '"""Simple test module."""',
        "",
        "def hello():",
        '    """Print hello message."""',
        '    print("Hello, World!")',
        "",
        "def add(a, b):",
        '    """Add two numbers."""',
        "    return a + b",
        "",
        "if __name__ == '__main__':",
        "    hello()",
        "    print(add(1, 2))",
    ]


def create_file_with_comments() -> List[str]:
    """Create a file with various comment types for testing."""
    return [
        "def function_with_comments():",
        "    # This is a regular comment",
        "    result = 42",
        "",
        "    # Another comment",
        "    return result",
        "",
        "    # This comment is unreachable",
        "    print('Never executed')",
    ]


def create_large_file(lines: int = 100) -> List[str]:
    """Create a large file for performance testing."""
    file_lines = [
        '"""Large test file."""',
        "",
        "import os",
        "import sys",
        "",
        "def main():",
        "    pass",
        "",
    ]

    for i in range(lines - len(file_lines)):
        file_lines.append(f"    # Line {i + 1}")

    return file_lines
