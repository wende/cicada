"""
Comprehensive tests for cicada/utils/index_lookup.py
"""

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
    """Sample index with modules and functions for testing"""
    return {
        "modules": {
            "Calculator": {
                "file": "lib/calculator.ex",
                "line": 1,
                "functions": [
                    {
                        "name": "add",
                        "arity": 2,
                        "args": ["x", "y"],
                        "type": "def",
                        "line": 5,
                        "signature": "def add(x, y)",
                        "doc": "Adds two numbers together",
                    },
                    {
                        "name": "subtract",
                        "arity": 2,
                        "args": ["x", "y"],
                        "type": "def",
                        "line": 10,
                        "signature": "def subtract(x, y)",
                        "doc": "Subtracts y from x",
                    },
                ],
            },
            "Math.Utils": {
                "file": "lib/math/utils.ex",
                "line": 1,
                "functions": [
                    {
                        "name": "add",
                        "arity": 3,
                        "args": ["x", "y", "z"],
                        "type": "def",
                        "line": 3,
                        "signature": "def add(x, y, z)",
                        "doc": "Adds three numbers",
                    },
                    {
                        "name": "multiply",
                        "arity": 2,
                        "args": ["x", "y"],
                        "type": "def",
                        "line": 8,
                        "signature": "def multiply(x, y)",
                    },
                ],
            },
            "_file_helpers": {
                "file": "lib/helpers.ex",
                "line": 1,
                "functions": [
                    {
                        "name": "helper_func",
                        "arity": 1,
                        "args": ["input"],
                        "type": "def",
                        "line": 2,
                        "signature": "def helper_func(input)",
                    }
                ],
            },
        }
    }


@pytest.fixture
def empty_index():
    """Index with no modules"""
    return {}


@pytest.fixture
def modules_empty_functions_index():
    """Index with modules but no functions"""
    return {
        "modules": {
            "EmptyModule": {
                "file": "lib/empty.ex",
                "line": 1,
            }
        }
    }


class TestLookupModule:
    """Tests for lookup_module function"""

    def test_lookup_existing_module(self, sample_index):
        """Should find existing module by name"""
        module = lookup_module(sample_index, "Calculator")

        assert module is not None
        assert module["file"] == "lib/calculator.ex"
        assert module["line"] == 1

    def test_lookup_nested_module(self, sample_index):
        """Should find nested module by name"""
        module = lookup_module(sample_index, "Math.Utils")

        assert module is not None
        assert module["file"] == "lib/math/utils.ex"

    def test_lookup_nonexistent_module(self, sample_index):
        """Should return None for nonexistent module"""
        module = lookup_module(sample_index, "NonExistent")

        assert module is None

    def test_lookup_module_empty_index(self, empty_index):
        """Should return None when index has no modules"""
        module = lookup_module(empty_index, "Calculator")

        assert module is None

    def test_lookup_module_with_empty_modules(self):
        """Should return None when modules dict is empty"""
        index = {"modules": {}}
        module = lookup_module(index, "Calculator")

        assert module is None


class TestLookupFunction:
    """Tests for lookup_function function"""

    def test_lookup_function_single_match(self, sample_index):
        """Should find function in single module"""
        results = lookup_function(sample_index, "subtract")

        assert len(results) == 1
        assert results[0]["name"] == "subtract"
        assert results[0]["module_name"] == "Calculator"
        assert results[0]["file"] == "lib/calculator.ex"
        assert results[0]["line"] == 10

    def test_lookup_function_multiple_matches(self, sample_index):
        """Should find function in multiple modules"""
        results = lookup_function(sample_index, "add")

        assert len(results) == 2
        module_names = {r["module_name"] for r in results}
        assert module_names == {"Calculator", "Math.Utils"}

        # Verify both have correct data
        for result in results:
            assert result["name"] == "add"
            assert "file" in result
            assert "line" in result
            assert "module_name" in result

    def test_lookup_function_no_match(self, sample_index):
        """Should return empty list for nonexistent function"""
        results = lookup_function(sample_index, "nonexistent")

        assert results == []

    def test_lookup_function_empty_index(self, empty_index):
        """Should return empty list when index has no modules"""
        results = lookup_function(empty_index, "add")

        assert results == []

    def test_lookup_function_module_without_functions(self, modules_empty_functions_index):
        """Should handle modules without functions field"""
        results = lookup_function(modules_empty_functions_index, "add")

        assert results == []

    def test_lookup_function_includes_all_function_data(self, sample_index):
        """Should include all function data in results"""
        results = lookup_function(sample_index, "add")

        for result in results:
            assert "name" in result
            assert "arity" in result
            assert "args" in result
            assert "type" in result
            assert "line" in result
            assert "signature" in result
            assert "module_name" in result
            assert "file" in result


class TestLookupByLocation:
    """Tests for lookup_by_location function"""

    def test_lookup_module_at_location(self, sample_index):
        """Should find module at specific location"""
        result = lookup_by_location(sample_index, "lib/calculator.ex", 1)

        assert result is not None
        assert result["type"] == "class"
        assert result["name"] == "Calculator"
        assert "data" in result

    def test_lookup_function_at_location(self, sample_index):
        """Should find function at specific location"""
        result = lookup_by_location(sample_index, "lib/calculator.ex", 5)

        assert result is not None
        assert result["type"] == "function"
        assert result["name"] == "add"
        assert result["module"] == "Calculator"
        assert "data" in result

    def test_lookup_with_filename_only(self, sample_index):
        """Should match with just filename (no path)"""
        result = lookup_by_location(sample_index, "calculator.ex", 5)

        assert result is not None
        assert result["type"] == "function"
        assert result["name"] == "add"

    def test_lookup_with_windows_path(self, sample_index):
        """Should handle Windows-style paths"""
        result = lookup_by_location(sample_index, "lib\\calculator.ex", 5)

        assert result is not None
        assert result["name"] == "add"

    def test_lookup_nonexistent_file(self, sample_index):
        """Should return None for nonexistent file"""
        result = lookup_by_location(sample_index, "nonexistent.ex", 1)

        assert result is None

    def test_lookup_wrong_line_number(self, sample_index):
        """Should return None for wrong line number"""
        result = lookup_by_location(sample_index, "lib/calculator.ex", 999)

        assert result is None

    def test_lookup_empty_index(self, empty_index):
        """Should return None when index has no modules"""
        result = lookup_by_location(empty_index, "calculator.ex", 1)

        assert result is None

    def test_lookup_file_module_prefix(self, sample_index):
        """Should return type 'module' for _file_ prefixed modules"""
        result = lookup_by_location(sample_index, "lib/helpers.ex", 1)

        assert result is not None
        assert result["type"] == "module"
        assert result["name"] == "_file_helpers"

    def test_lookup_nested_module_path(self, sample_index):
        """Should find module in nested directory"""
        result = lookup_by_location(sample_index, "lib/math/utils.ex", 1)

        assert result is not None
        assert result["type"] == "class"
        assert result["name"] == "Math.Utils"


class TestGetFunctionDocumentation:
    """Tests for get_function_documentation function"""

    def test_get_existing_documentation(self, sample_index):
        """Should return documentation for existing function"""
        doc = get_function_documentation(sample_index, "Calculator", "add")

        assert doc == "Adds two numbers together"

    def test_get_documentation_for_different_function(self, sample_index):
        """Should return correct documentation for each function"""
        doc = get_function_documentation(sample_index, "Calculator", "subtract")

        assert doc == "Subtracts y from x"

    def test_get_documentation_nonexistent_module(self, sample_index):
        """Should return None for nonexistent module"""
        doc = get_function_documentation(sample_index, "NonExistent", "add")

        assert doc is None

    def test_get_documentation_nonexistent_function(self, sample_index):
        """Should return None for nonexistent function"""
        doc = get_function_documentation(sample_index, "Calculator", "nonexistent")

        assert doc is None

    def test_get_documentation_function_without_doc(self, sample_index):
        """Should return None when function has no doc field"""
        doc = get_function_documentation(sample_index, "Math.Utils", "multiply")

        assert doc is None

    def test_get_documentation_empty_index(self, empty_index):
        """Should return None when index is empty"""
        doc = get_function_documentation(empty_index, "Calculator", "add")

        assert doc is None


class TestGetFunctionSignature:
    """Tests for get_function_signature function"""

    def test_get_existing_signature(self, sample_index):
        """Should return signature for existing function"""
        sig = get_function_signature(sample_index, "Calculator", "add")

        assert sig == "def add(x, y)"

    def test_get_signature_for_different_function(self, sample_index):
        """Should return correct signature for each function"""
        sig = get_function_signature(sample_index, "Math.Utils", "add")

        assert sig == "def add(x, y, z)"

    def test_get_signature_nonexistent_module(self, sample_index):
        """Should return None for nonexistent module"""
        sig = get_function_signature(sample_index, "NonExistent", "add")

        assert sig is None

    def test_get_signature_nonexistent_function(self, sample_index):
        """Should return None for nonexistent function"""
        sig = get_function_signature(sample_index, "Calculator", "nonexistent")

        assert sig is None

    def test_get_signature_function_without_signature(self):
        """Should return None when function has no signature field"""
        index = {
            "modules": {
                "TestModule": {
                    "file": "test.ex",
                    "line": 1,
                    "functions": [
                        {
                            "name": "test_func",
                            "line": 2,
                        }
                    ],
                }
            }
        }
        sig = get_function_signature(index, "TestModule", "test_func")

        assert sig is None

    def test_get_signature_empty_index(self, empty_index):
        """Should return None when index is empty"""
        sig = get_function_signature(empty_index, "Calculator", "add")

        assert sig is None


class TestEdgeCases:
    """Tests for edge cases and error conditions"""

    def test_none_index(self):
        """Should handle None index gracefully"""
        # lookup_module with None - will raise AttributeError due to "modules" not in None
        # This is acceptable behavior as the function expects a dict
        with pytest.raises((TypeError, AttributeError)):
            lookup_module(None, "test")

    def test_malformed_index_structure(self):
        """Should handle malformed index structures"""
        index = {"modules": "not a dict"}

        # This will raise AttributeError as string doesn't have .get()
        with pytest.raises(AttributeError):
            lookup_module(index, "test")

    def test_lookup_with_special_characters_in_name(self, sample_index):
        """Should handle module names with special characters"""
        # Add a module with special characters
        sample_index["modules"]["Special.Module!"] = {
            "file": "lib/special.ex",
            "line": 1,
            "functions": [],
        }

        module = lookup_module(sample_index, "Special.Module!")

        assert module is not None
        assert module["file"] == "lib/special.ex"

    def test_lookup_by_location_with_unicode_path(self):
        """Should handle unicode characters in paths"""
        index = {
            "modules": {
                "TestModule": {
                    "file": "lib/tëst/módulé.ex",
                    "line": 1,
                    "functions": [],
                }
            }
        }

        result = lookup_by_location(index, "tëst/módulé.ex", 1)

        assert result is not None
        assert result["name"] == "TestModule"

    def test_function_with_null_values(self):
        """Should handle functions with null/missing values"""
        index = {
            "modules": {
                "TestModule": {
                    "file": "test.ex",
                    "line": 1,
                    "functions": [
                        {
                            "name": "test_func",
                            "line": None,  # null line
                        }
                    ],
                }
            }
        }

        results = lookup_function(index, "test_func")
        assert len(results) == 1
        assert results[0]["line"] is None
