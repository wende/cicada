"""
Author: Cursor(Auto)

File evolution scenarios for line mapping tests.

Provides sample file content at different commits to test line mapping
algorithms and file evolution tracking.
"""

from typing import Any


def get_file_evolution_scenarios() -> dict[str, dict[str, list[str]]]:
    """
    Get file evolution scenarios for testing line mapping.

    Returns:
        Dictionary mapping scenario names to file versions
    """
    return {
        "simple_addition": {
            "original": [
                "def hello():",
                "    print('Hello')",
                "",
                "def world():",
                "    print('World')",
            ],
            "modified": [
                "def hello():",
                "    print('Hello')",
                "",
                "# New function added",
                "def goodbye():",
                "    print('Goodbye')",
                "",
                "def world():",
                "    print('World')",
            ],
        },
        "complex_refactoring": {
            "original": [
                "class User:",
                "    def __init__(self, name):",
                "        self.name = name",
                "",
                "    def get_name(self):",
                "        return self.name",
                "",
                "    def set_name(self, name):",
                "        self.name = name",
            ],
            "modified": [
                "class User:",
                "    def __init__(self, name, email=None):",
                "        self.name = name",
                "        self.email = email",
                "",
                "    def get_name(self):",
                "        return self.name",
                "",
                "    def get_email(self):",
                "        return self.email",
                "",
                "    def set_name(self, name):",
                "        self.name = name",
                "",
                "    def set_email(self, email):",
                "        self.email = email",
            ],
        },
        "line_deletion": {
            "original": [
                "def process_data(data):",
                "    # Step 1: Validate input",
                "    if not data:",
                "        return None",
                "",
                "    # Step 2: Process data",
                "    result = []",
                "    for item in data:",
                "        result.append(item * 2)",
                "",
                "    # Step 3: Return result",
                "    return result",
            ],
            "modified": [
                "def process_data(data):",
                "    # Step 1: Validate input",
                "    if not data:",
                "        return None",
                "",
                "    # Step 2: Process data (simplified)",
                "    return [item * 2 for item in data]",
            ],
        },
        "whitespace_changes": {
            "original": [
                "def format_text(text):",
                "    return text.strip().lower()",
                "",
                "def validate_input(value):",
                "    return value is not None",
            ],
            "modified": [
                "def format_text(text):",
                "    # Add input validation",
                "    if not text:",
                "        return ''",
                "    return text.strip().lower()",
                "",
                "def validate_input(value):",
                "    return value is not None and value != ''",
            ],
        },
        "large_file_evolution": {
            "original": [
                "#!/usr/bin/env python3",
                '"""Module for data processing."""',
                "",
                "import os",
                "import json",
                "",
                "class DataProcessor:",
                "    def __init__(self):",
                "        self.data = []",
                "",
                "    def load_data(self, filename):",
                "        with open(filename, 'r') as f:",
                "            self.data = json.load(f)",
                "",
                "    def process(self):",
                "        return [item for item in self.data if item]",
                "",
                "    def save(self, filename):",
                "        with open(filename, 'w') as f:",
                "            json.dump(self.data, f)",
            ],
            "modified": [
                "#!/usr/bin/env python3",
                '"""Module for data processing with enhanced features."""',
                "",
                "import os",
                "import json",
                "import logging",
                "",
                "logger = logging.getLogger(__name__)",
                "",
                "class DataProcessor:",
                "    def __init__(self, config=None):",
                "        self.data = []",
                "        self.config = config or {}",
                "",
                "    def load_data(self, filename):",
                "        try:",
                "            with open(filename, 'r') as f:",
                "                self.data = json.load(f)",
                "            logger.info(f'Loaded {len(self.data)} items from {filename}')",
                "        except FileNotFoundError:",
                "            logger.error(f'File not found: {filename}')",
                "            raise",
                "",
                "    def process(self):",
                "        if not self.data:",
                "            logger.warning('No data to process')",
                "            return []",
                "        ",
                "        # Apply filters if configured",
                "        if 'filter' in self.config:",
                "            return self._apply_filter(self.data)",
                "        ",
                "        return [item for item in self.data if item]",
                "",
                "    def _apply_filter(self, data):",
                "        filter_func = self.config['filter']",
                "        return [item for item in data if filter_func(item)]",
                "",
                "    def save(self, filename):",
                "        try:",
                "            with open(filename, 'w') as f:",
                "                json.dump(self.data, f, indent=2)",
                "            logger.info(f'Saved {len(self.data)} items to {filename}')",
                "        except Exception as e:",
                "            logger.error(f'Failed to save data: {e}')",
                "            raise",
            ],
        },
    }


def get_line_mapping_test_cases() -> list[dict[str, Any]]:
    """
    Get specific test cases for line mapping algorithm.

    Returns:
        List of test case dictionaries
    """
    return [
        {
            "name": "exact_match",
            "original_line": 2,
            "original_content": "    print('Hello')",
            "current_line": 2,
            "current_content": "    print('Hello')",
            "should_match": True,
        },
        {
            "name": "moved_down_by_one",
            "original_line": 2,
            "original_content": "    print('Hello')",
            "current_line": 3,
            "current_content": "    print('Hello')",
            "should_match": True,
        },
        {
            "name": "moved_up_by_one",
            "original_line": 5,
            "original_content": "    print('World')",
            "current_line": 4,
            "current_content": "    print('World')",
            "should_match": True,
        },
        {
            "name": "moved_within_range",
            "original_line": 3,
            "original_content": "    return 'test'",
            "current_line": 6,
            "original_content": "    return 'test'",
            "should_match": True,
        },
        {
            "name": "deleted_line",
            "original_line": 3,
            "original_content": "    # This line was deleted",
            "current_line": None,
            "current_content": None,
            "should_match": False,
        },
        {
            "name": "empty_line",
            "original_line": 3,
            "original_content": "",
            "current_line": None,
            "current_content": None,
            "should_match": False,
        },
        {
            "name": "whitespace_changed",
            "original_line": 2,
            "original_content": "    print('Hello')",
            "current_line": 2,
            "current_content": "    print('Hello')  # Added comment",
            "should_match": False,
        },
        {
            "name": "content_changed",
            "original_line": 2,
            "original_content": "    print('Hello')",
            "current_line": 2,
            "current_content": "    print('Goodbye')",
            "should_match": False,
        },
    ]


def get_file_content_samples() -> dict[str, list[str]]:
    """
    Get sample file contents for various testing scenarios.

    Returns:
        Dictionary mapping file types to content
    """
    return {
        "simple_python": [
            "#!/usr/bin/env python3",
            '"""Simple Python module."""',
            "",
            "def main():",
            '    """Main function."""',
            '    print("Hello, World!")',
            "",
            "if __name__ == '__main__':",
            "    main()",
        ],
        "python_with_imports": [
            "import os",
            "import sys",
            "from pathlib import Path",
            "",
            "def process_file(filepath):",
            "    if not os.path.exists(filepath):",
            "        return None",
            "    ",
            "    with open(filepath, 'r') as f:",
            "        return f.read()",
            "",
            "def main():",
            "    if len(sys.argv) > 1:",
            "        filepath = sys.argv[1]",
            "        content = process_file(filepath)",
            "        if content:",
            "            print(content)",
            "",
            "if __name__ == '__main__':",
            "    main()",
        ],
        "python_class": [
            "class Calculator:",
            "    def __init__(self):",
            "        self.history = []",
            "",
            "    def add(self, a, b):",
            "        result = a + b",
            "        self.history.append(f'{a} + {b} = {result}')",
            "        return result",
            "",
            "    def subtract(self, a, b):",
            "        result = a - b",
            "        self.history.append(f'{a} - {b} = {result}')",
            "        return result",
            "",
            "    def get_history(self):",
            "        return self.history.copy()",
        ],
        "empty_file": [],
        "single_line": ["print('Hello, World!')"],
        "whitespace_only": ["", "   ", "\t", "", "  \t  "],
    }


def get_git_show_scenarios() -> dict[str, dict[str, str]]:
    """
    Get scenarios for testing git show command responses.

    Returns:
        Dictionary mapping scenario names to git show outputs
    """
    return {
        "file_exists": {
            "HEAD": "def hello():\n    print('Hello')\n",
            "abc123": "def hello():\n    print('Hello, World!')\n",
            "def456": "def hello():\n    print('Hello')\n    print('World')\n",
        },
        "file_not_found": {"HEAD": "", "abc123": "", "def456": ""},
        "empty_file": {"HEAD": "", "abc123": "", "def456": ""},
        "binary_file": {
            "HEAD": "Binary file content (not text)",
            "abc123": "Binary file content (not text)",
            "def456": "Binary file content (not text)",
        },
    }


def get_ls_files_scenarios() -> dict[str, str]:
    """
    Get scenarios for testing git ls-files command responses.

    Returns:
        Dictionary mapping scenario names to ls-files outputs
    """
    return {
        "file_exists": "src/main.py\ntests/test_main.py\nREADME.md",
        "file_not_found": "",
        "multiple_files": "src/main.py\nsrc/utils.py\ntests/test_main.py\ntests/test_utils.py\nREADME.md\n.gitignore",
        "single_file": "src/main.py",
        "nested_files": "src/main.py\nsrc/utils/helpers.py\nsrc/utils/validators.py\ntests/test_main.py\ntests/utils/test_helpers.py",
    }
