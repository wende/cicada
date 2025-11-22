"""Comprehensive tests for cicada/utils/index_lookup.py"""

import pytest

from cicada.utils.index_lookup import (
    get_function_documentation,
    get_function_signature,
    lookup_by_location,
    lookup_function,
    lookup_module,
)


@pytest.fixture
def sample_index():
    """Create a sample index for testing."""
    return {
        "modules": {
            "Calculator": {
                "name": "Calculator",
                "file": "lib/calculator.py",
                "line": 1,
                "doc": "A simple calculator module",
                "functions": [
                    {
                        "name": "add",
                        "arity": 2,
                        "line": 7,
                        "doc": "Add two numbers",
                        "signature": "def add(x: int, y: int) -> int:",
                    },
                    {
                        "name": "subtract",
                        "arity": 2,
                        "line": 15,
                        "doc": "Subtract two numbers",
                        "signature": "def subtract(x: int, y: int) -> int:",
                    },
                    {
                        "name": "multiply",
                        "arity": 2,
                        "line": 23,
                        "doc": None,  # No documentation
                        "signature": "def multiply(x, y):",
                    },
                ],
            },
            "StringUtils": {
                "name": "StringUtils",
                "file": "lib/string_utils.py",
                "line": 1,
                "doc": "String utility functions",
                "functions": [
                    {
                        "name": "uppercase",
                        "arity": 1,
                        "line": 5,
                        "doc": "Convert string to uppercase",
                        "signature": "def uppercase(s: str) -> str:",
                    },
                    {
                        "name": "add",  # Same name as in Calculator
                        "arity": 2,
                        "line": 12,
                        "doc": "Concatenate two strings",
                        "signature": "def add(s1: str, s2: str) -> str:",
                    },
                ],
            },
            "_file_lib/helpers.py": {
                "name": "_file_lib/helpers.py",
                "file": "lib/helpers.py",
                "line": 1,
                "doc": None,
                "functions": [
                    {
                        "name": "helper_func",
                        "arity": 1,
                        "line": 5,
                        "doc": "A helper function",
                        "signature": None,
                    }
                ],
            },
        }
    }


class TestLookupModule:
    """Tests for lookup_module function."""

    def test_lookup_existing_module(self, sample_index):
        """Should find and return existing module."""
        result = lookup_module(sample_index, "Calculator")

        assert result is not None
        assert result["name"] == "Calculator"
        assert result["file"] == "lib/calculator.py"
        assert result["doc"] == "A simple calculator module"

    def test_lookup_nonexistent_module(self, sample_index):
        """Should return None for non-existent module."""
        result = lookup_module(sample_index, "NonExistent")

        assert result is None

    def test_lookup_module_case_sensitive(self, sample_index):
        """Lookup should be case-sensitive."""
        result = lookup_module(sample_index, "calculator")  # lowercase

        assert result is None

    def test_lookup_module_without_modules_key(self):
        """Should handle index without 'modules' key."""
        empty_index = {}
        result = lookup_module(empty_index, "Calculator")

        assert result is None

    def test_lookup_module_with_empty_modules(self):
        """Should handle empty modules dictionary."""
        empty_index = {"modules": {}}
        result = lookup_module(empty_index, "Calculator")

        assert result is None

    def test_lookup_module_file_prefix(self, sample_index):
        """Should lookup modules with _file_ prefix."""
        result = lookup_module(sample_index, "_file_lib/helpers.py")

        assert result is not None
        assert result["file"] == "lib/helpers.py"


class TestLookupFunction:
    """Tests for lookup_function function."""

    @staticmethod
    def _result_for_module(results, module_name):
        return next((r for r in results if r["module_name"] == module_name), None)

    def test_lookup_function_single_match(self, sample_index):
        """Should find function with unique name."""
        results = lookup_function(sample_index, "uppercase")

        assert len(results) == 1
        assert results[0]["name"] == "uppercase"
        assert results[0]["module_name"] == "StringUtils"
        assert results[0]["file"] == "lib/string_utils.py"
        assert results[0]["line"] == 5

    def test_lookup_function_multiple_matches(self, sample_index):
        """Should find all functions with same name across modules."""
        results = lookup_function(sample_index, "add")

        assert len(results) == 2

        # Find Calculator.add
        calc_add = self._result_for_module(results, "Calculator")
        assert calc_add is not None
        assert calc_add["doc"] == "Add two numbers"
        assert calc_add["line"] == 7

        # Find StringUtils.add
        string_add = self._result_for_module(results, "StringUtils")
        assert string_add is not None
        assert string_add["doc"] == "Concatenate two strings"
        assert string_add["line"] == 12

    def test_lookup_function_nonexistent(self, sample_index):
        """Should return empty list for non-existent function."""
        results = lookup_function(sample_index, "nonexistent")

        assert results == []

    def test_lookup_function_case_sensitive(self, sample_index):
        """Lookup should be case-sensitive."""
        results = lookup_function(sample_index, "ADD")  # uppercase

        assert results == []

    def test_lookup_function_without_modules_key(self):
        """Should handle index without 'modules' key."""
        empty_index = {}
        results = lookup_function(empty_index, "add")

        assert results == []

    def test_lookup_function_module_without_functions(self):
        """Should handle module without functions key."""
        index = {"modules": {"Empty": {"name": "Empty", "file": "empty.py"}}}
        results = lookup_function(index, "any_func")

        assert results == []

    def test_lookup_function_includes_module_context(self, sample_index):
        """Results should include module context."""
        results = lookup_function(sample_index, "subtract")

        assert len(results) == 1
        result = results[0]

        # Original function data
        assert result["name"] == "subtract"
        assert result["arity"] == 2
        assert result["line"] == 15

        # Added context
        assert result["module_name"] == "Calculator"
        assert result["file"] == "lib/calculator.py"

    def test_lookup_function_empty_modules(self):
        """Should handle empty modules dictionary."""
        index = {"modules": {}}
        results = lookup_function(index, "add")

        assert results == []


class TestLookupByLocation:
    """Tests for lookup_by_location function."""

    def test_lookup_module_by_location(self, sample_index):
        """Should find module at specific location."""
        result = lookup_by_location(sample_index, "lib/calculator.py", 1)

        assert result is not None
        assert result["type"] == "class"
        assert result["name"] == "Calculator"
        assert result["data"]["file"] == "lib/calculator.py"

    def test_lookup_function_by_location(self, sample_index):
        """Should find function at specific location."""
        result = lookup_by_location(sample_index, "lib/calculator.py", 7)

        assert result is not None
        assert result["type"] == "function"
        assert result["name"] == "add"
        assert result["module"] == "Calculator"
        assert result["data"]["doc"] == "Add two numbers"

    def test_lookup_by_location_nonexistent_line(self, sample_index):
        """Should return None for line with no definition."""
        result = lookup_by_location(sample_index, "lib/calculator.py", 99)

        assert result is None

    def test_lookup_by_location_nonexistent_file(self, sample_index):
        """Should return None for non-existent file."""
        result = lookup_by_location(sample_index, "lib/nonexistent.py", 1)

        assert result is None

    def test_lookup_by_location_partial_path_match(self, sample_index):
        """Should match by filename when full path not provided."""
        result = lookup_by_location(sample_index, "calculator.py", 7)

        assert result is not None
        assert result["name"] == "add"

    def test_lookup_by_location_file_prefix(self, sample_index):
        """Should identify module vs file correctly for _file_ prefix."""
        result = lookup_by_location(sample_index, "lib/helpers.py", 1)

        assert result is not None
        assert result["type"] == "module"
        assert result["name"] == "_file_lib/helpers.py"

    def test_lookup_by_location_class_type(self, sample_index):
        """Should identify class (non _file_ module) correctly."""
        result = lookup_by_location(sample_index, "lib/calculator.py", 1)

        assert result is not None
        assert result["type"] == "class"
        assert result["name"] == "Calculator"

    def test_lookup_by_location_without_modules_key(self):
        """Should handle index without 'modules' key."""
        empty_index = {}
        result = lookup_by_location(empty_index, "lib/test.py", 1)

        assert result is None

    def test_lookup_by_location_normalizes_paths(self, sample_index):
        """Should normalize Windows and Unix paths for comparison."""
        # Test with Windows-style backslashes
        result = lookup_by_location(sample_index, "lib\\calculator.py", 7)

        assert result is not None
        assert result["name"] == "add"

    def test_lookup_by_location_function_in_different_module(self, sample_index):
        """Should find correct function when same line exists in different files."""
        result = lookup_by_location(sample_index, "lib/string_utils.py", 5)

        assert result is not None
        assert result["name"] == "uppercase"
        assert result["module"] == "StringUtils"

    def test_lookup_by_location_includes_data(self, sample_index):
        """Should include complete function/module data."""
        result = lookup_by_location(sample_index, "lib/calculator.py", 15)

        assert result is not None
        assert result["type"] == "function"
        assert "data" in result
        assert result["data"]["signature"] == "def subtract(x: int, y: int) -> int:"


class TestGetFunctionDocumentation:
    """Tests for get_function_documentation function."""

    def test_get_existing_documentation(self, sample_index):
        """Should return documentation for function with doc."""
        doc = get_function_documentation(sample_index, "Calculator", "add")

        assert doc == "Add two numbers"

    def test_get_documentation_no_doc(self, sample_index):
        """Should return None for function without documentation."""
        doc = get_function_documentation(sample_index, "Calculator", "multiply")

        assert doc is None

    def test_get_documentation_nonexistent_module(self, sample_index):
        """Should return None for non-existent module."""
        doc = get_function_documentation(sample_index, "NonExistent", "add")

        assert doc is None

    def test_get_documentation_nonexistent_function(self, sample_index):
        """Should return None for non-existent function."""
        doc = get_function_documentation(sample_index, "Calculator", "nonexistent")

        assert doc is None

    def test_get_documentation_case_sensitive(self, sample_index):
        """Should be case-sensitive for both module and function names."""
        doc = get_function_documentation(sample_index, "calculator", "add")
        assert doc is None

        doc = get_function_documentation(sample_index, "Calculator", "Add")
        assert doc is None

    def test_get_documentation_from_different_modules(self, sample_index):
        """Should get correct documentation from specified module."""
        calc_doc = get_function_documentation(sample_index, "Calculator", "add")
        string_doc = get_function_documentation(sample_index, "StringUtils", "add")

        assert calc_doc == "Add two numbers"
        assert string_doc == "Concatenate two strings"

    def test_get_documentation_missing_modules_key(self):
        """Should return None when index has no 'modules' key."""
        doc = get_function_documentation({}, "M", "f")

        assert doc is None

    def test_get_documentation_empty_modules(self):
        """Should return None when 'modules' is present but empty."""
        doc = get_function_documentation({"modules": {}}, "M", "f")

        assert doc is None


class TestGetFunctionSignature:
    """Tests for get_function_signature function."""

    def test_get_existing_signature(self, sample_index):
        """Should return signature for function."""
        sig = get_function_signature(sample_index, "Calculator", "add")

        assert sig == "def add(x: int, y: int) -> int:"

    def test_get_signature_without_types(self, sample_index):
        """Should return signature even without type annotations."""
        sig = get_function_signature(sample_index, "Calculator", "multiply")

        assert sig == "def multiply(x, y):"

    def test_get_signature_no_signature_field(self, sample_index):
        """Should return None when signature field is missing."""
        sig = get_function_signature(sample_index, "_file_lib/helpers.py", "helper_func")

        assert sig is None

    def test_get_signature_nonexistent_module(self, sample_index):
        """Should return None for non-existent module."""
        sig = get_function_signature(sample_index, "NonExistent", "add")

        assert sig is None

    def test_get_signature_nonexistent_function(self, sample_index):
        """Should return None for non-existent function."""
        sig = get_function_signature(sample_index, "Calculator", "nonexistent")

        assert sig is None

    def test_get_signature_case_sensitive(self, sample_index):
        """Should be case-sensitive for both module and function names."""
        sig = get_function_signature(sample_index, "calculator", "add")
        assert sig is None

        sig = get_function_signature(sample_index, "Calculator", "Add")
        assert sig is None

    def test_get_signature_from_different_modules(self, sample_index):
        """Should get correct signature from specified module."""
        calc_sig = get_function_signature(sample_index, "Calculator", "add")
        string_sig = get_function_signature(sample_index, "StringUtils", "add")

        assert calc_sig == "def add(x: int, y: int) -> int:"
        assert string_sig == "def add(s1: str, s2: str) -> str:"

    def test_get_signature_missing_modules_key(self):
        """Should return None when index has no 'modules' key."""
        sig = get_function_signature({}, "M", "f")

        assert sig is None

    def test_get_signature_empty_modules(self):
        """Should return None when 'modules' is present but empty."""
        sig = get_function_signature({"modules": {}}, "M", "f")

        assert sig is None


class TestEdgeCases:
    """Edge case tests for index lookup utilities."""

    def test_lookup_with_none_index(self):
        """Functions should handle None gracefully."""
        # lookup_module would raise AttributeError, but we expect that
        # since the function signature expects a dict

        # For functions that check for 'modules' key first
        assert lookup_function({}, "test") == []
        assert lookup_by_location({}, "test.py", 1) is None

    def test_lookup_with_malformed_module_data(self):
        """Should handle modules with missing required fields."""
        index = {
            "modules": {
                "Broken": {
                    "name": "Broken"
                    # Missing 'file' field
                }
            }
        }

        result = lookup_module(index, "Broken")
        assert result is not None
        assert result.get("file") is None

    def test_lookup_function_with_malformed_function_data(self):
        """Should handle functions with missing fields."""
        index = {
            "modules": {
                "Test": {
                    "name": "Test",
                    "file": "test.py",
                    "functions": [
                        {"name": "func"}  # Missing many fields
                    ],
                }
            }
        }

        results = lookup_function(index, "func")
        assert len(results) == 1
        assert results[0]["name"] == "func"
        assert results[0]["module_name"] == "Test"

    def test_lookup_by_location_with_missing_line_field(self):
        """Should handle modules/functions without line field."""
        index = {
            "modules": {
                "NoLine": {
                    "name": "NoLine",
                    "file": "noLine.py"
                    # Missing 'line' field
                }
            }
        }

        result = lookup_by_location(index, "noLine.py", 1)
        # Should not match since module has no line field
        assert result is None

    def test_empty_function_name_lookup(self, sample_index):
        """Should handle empty function name."""
        results = lookup_function(sample_index, "")

        assert results == []

    def test_unicode_in_module_names(self):
        """Should handle unicode in module and function names."""
        index = {
            "modules": {
                "Módulo": {
                    "name": "Módulo",
                    "file": "módulo.py",
                    "line": 1,
                    "functions": [{"name": "función", "line": 5}],
                }
            }
        }

        result = lookup_module(index, "Módulo")
        assert result is not None

        results = lookup_function(index, "función")
        assert len(results) == 1

    def test_special_characters_in_paths(self):
        """Should handle special characters in file paths."""
        index = {
            "modules": {
                "Test": {
                    "name": "Test",
                    "file": "lib/my-project/test_file.py",
                    "line": 1,
                }
            }
        }

        result = lookup_by_location(index, "lib/my-project/test_file.py", 1)
        assert result is not None
        assert result["name"] == "Test"

    def test_whitespace_in_lookups(self, sample_index):
        """Should not trim whitespace (exact match required)."""
        # Function names with whitespace should not match
        results = lookup_function(sample_index, " add ")
        assert results == []

        # Module names with whitespace should not match
        result = lookup_module(sample_index, " Calculator ")
        assert result is None
