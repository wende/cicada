"""
Tests for cicada/utils/index_lookup.py
"""

import pytest
from cicada.utils.index_lookup import (
    lookup_module,
    lookup_function,
    lookup_by_location,
    get_function_documentation,
    get_function_signature,
)


@pytest.fixture
def sample_index():
    """Sample index for testing lookup functions."""
    return {
        "modules": {
            "TestApp.Calculator": {
                "file": "lib/test_app/calculator.ex",
                "line": 1,
                "functions": [
                    {
                        "name": "add",
                        "arity": 2,
                        "line": 10,
                        "doc": "Adds two numbers.",
                        "signature": "add(x, y)",
                    },
                    {
                        "name": "subtract",
                        "arity": 2,
                        "line": 15,
                        "doc": "Subtracts two numbers.",
                        "signature": "subtract(x, y)",
                    },
                ],
            },
            "TestApp.Formatter": {
                "file": "lib/test_app/formatter.ex",
                "line": 1,
                "functions": [
                    {
                        "name": "format",
                        "arity": 1,
                        "line": 5,
                        "doc": "Formats output.",
                        "signature": "format(data)",
                    },
                    {
                        "name": "add",  # Same function name as in Calculator
                        "arity": 1,
                        "line": 20,
                        "doc": "Adds formatting.",
                        "signature": "add(config)",
                    },
                ],
            },
            "_file_lib/test_app/helper.ex": {
                "file": "lib/test_app/helper.ex",
                "line": 1,
                "functions": [],
            },
        }
    }


class TestLookupModule:
    """Tests for lookup_module function."""

    def test_lookup_existing_module(self, sample_index):
        """Test looking up an existing module."""
        module = lookup_module(sample_index, "TestApp.Calculator")
        assert module is not None
        assert module["file"] == "lib/test_app/calculator.ex"

    def test_lookup_nonexistent_module(self, sample_index):
        """Test looking up a module that doesn't exist."""
        module = lookup_module(sample_index, "NonExistent")
        assert module is None

    def test_lookup_in_empty_index(self):
        """Test looking up in an empty index."""
        module = lookup_module({}, "TestApp")
        assert module is None

    def test_lookup_index_without_modules(self):
        """Test looking up in an index without 'modules' key."""
        module = lookup_module({"metadata": {}}, "TestApp")
        assert module is None


class TestLookupFunction:
    """Tests for lookup_function function."""

    def test_lookup_existing_function(self, sample_index):
        """Test looking up an existing function."""
        results = lookup_function(sample_index, "add")
        assert len(results) == 2

        # Verify we got results from both modules
        modules = {r["module_name"] for r in results}
        assert "TestApp.Calculator" in modules
        assert "TestApp.Formatter" in modules

        # Verify context is added
        for res in results:
            assert "module_name" in res
            assert "file" in res

    def test_lookup_unique_function(self, sample_index):
        """Test looking up a function that only exists in one module."""
        results = lookup_function(sample_index, "subtract")
        assert len(results) == 1
        assert results[0]["module_name"] == "TestApp.Calculator"
        assert results[0]["name"] == "subtract"

    def test_lookup_nonexistent_function(self, sample_index):
        """Test looking up a function that doesn't exist."""
        results = lookup_function(sample_index, "multiply")
        assert len(results) == 0

    def test_lookup_function_empty_index(self):
        """Test looking up function in empty index."""
        results = lookup_function({}, "add")
        assert results == []

    def test_lookup_module_without_functions(self, sample_index):
        """Test lookup when a module has no functions key."""
        # Add a malformed module to the index
        sample_index["modules"]["Malformed"] = {"file": "bad.ex"}
        results = lookup_function(sample_index, "add")
        # Should still find the valid ones and not crash
        assert len(results) == 2


class TestLookupByLocation:
    """Tests for lookup_by_location function."""

    def test_lookup_module_definition(self, sample_index):
        """Test looking up a module definition by location."""
        result = lookup_by_location(sample_index, "lib/test_app/calculator.ex", 1)
        assert result is not None
        assert result["type"] == "class"  # The code returns "class" for modules not starting with _file_
        assert result["name"] == "TestApp.Calculator"

    def test_lookup_function_definition(self, sample_index):
        """Test looking up a function definition by location."""
        result = lookup_by_location(sample_index, "lib/test_app/calculator.ex", 10)
        assert result is not None
        assert result["type"] == "function"
        assert result["name"] == "add"
        assert result["module"] == "TestApp.Calculator"

    def test_lookup_file_module(self, sample_index):
        """Test looking up a file module (starts with _file_)."""
        result = lookup_by_location(sample_index, "lib/test_app/helper.ex", 1)
        assert result is not None
        assert result["type"] == "module"  # Code returns "module" for _file_ prefix
        assert result["name"] == "_file_lib/test_app/helper.ex"

    def test_lookup_partial_path_match(self, sample_index):
        """Test looking up with partial path."""
        # Should match suffix
        result = lookup_by_location(sample_index, "calculator.ex", 10)
        assert result is not None
        assert result["name"] == "add"

    def test_lookup_wrong_line(self, sample_index):
        """Test looking up at a line with no definition."""
        result = lookup_by_location(sample_index, "lib/test_app/calculator.ex", 99)
        assert result is None

    def test_lookup_wrong_file(self, sample_index):
        """Test looking up in a non-existent file."""
        result = lookup_by_location(sample_index, "nonexistent.ex", 1)
        assert result is None

    def test_lookup_empty_index(self):
        """Test lookup in empty index."""
        result = lookup_by_location({}, "file.ex", 1)
        assert result is None

    def test_lookup_windows_path(self, sample_index):
        """Test lookup with Windows-style path separators."""
        result = lookup_by_location(sample_index, "lib\\test_app\\calculator.ex", 10)
        assert result is not None
        assert result["name"] == "add"


class TestGetFunctionDocumentation:
    """Tests for get_function_documentation function."""

    def test_get_doc_existing(self, sample_index):
        """Test getting documentation for existing function."""
        doc = get_function_documentation(sample_index, "TestApp.Calculator", "add")
        assert doc == "Adds two numbers."

    def test_get_doc_nonexistent_module(self, sample_index):
        """Test getting documentation from non-existent module."""
        doc = get_function_documentation(sample_index, "NonExistent", "add")
        assert doc is None

    def test_get_doc_nonexistent_function(self, sample_index):
        """Test getting documentation for non-existent function."""
        doc = get_function_documentation(sample_index, "TestApp.Calculator", "multiply")
        assert doc is None

    def test_get_doc_no_doc_field(self, sample_index):
        """Test getting documentation when field is missing."""
        # Modify index to remove doc
        sample_index["modules"]["TestApp.Calculator"]["functions"][0].pop("doc")
        doc = get_function_documentation(sample_index, "TestApp.Calculator", "add")
        assert doc is None


class TestGetFunctionSignature:
    """Tests for get_function_signature function."""

    def test_get_sig_existing(self, sample_index):
        """Test getting signature for existing function."""
        sig = get_function_signature(sample_index, "TestApp.Calculator", "add")
        assert sig == "add(x, y)"

    def test_get_sig_nonexistent_module(self, sample_index):
        """Test getting signature from non-existent module."""
        sig = get_function_signature(sample_index, "NonExistent", "add")
        assert sig is None

    def test_get_sig_nonexistent_function(self, sample_index):
        """Test getting signature for non-existent function."""
        sig = get_function_signature(sample_index, "TestApp.Calculator", "multiply")
        assert sig is None
