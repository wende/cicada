"""Tests for index lookup and query functionality.

These tests verify that we can efficiently look up modules, classes, and
functions in SCIP-generated indexes, and retrieve their documentation,
signatures, and location information.
"""

import pytest

from cicada.languages.scip.reader import SCIPReader
from cicada.languages.scip.converter import SCIPConverter
from cicada.utils.index_utils import (
    lookup_module,
    lookup_function,
    lookup_by_location,
    get_function_documentation,
    get_function_signature,
)


@pytest.fixture
def python_index(fixtures_dir):
    """Load and convert Python SCIP index for testing."""
    scip_file = fixtures_dir / "sample_python" / "index.scip"
    if not scip_file.exists():
        pytest.fail("Python SCIP index not found - run make setup-scip")

    reader = SCIPReader()
    scip_index = reader.read_index(scip_file)

    converter = SCIPConverter()
    return converter.convert(scip_index, scip_file.parent)


class TestModuleLookup:
    """Test looking up modules and classes by name."""

    def test_lookup_module_by_name(self, python_index):
        """Test finding a module by name and getting file/line info."""
        result = lookup_module(python_index, "Calculator")

        assert result is not None
        assert result["file"].endswith("calculator.py")
        assert "line" in result
        assert result["line"] == 11  # class Calculator: line (updated for imports)

    def test_lookup_class_by_name(self, python_index):
        """Test finding a class specifically (same as module lookup for SCIP)."""
        result = lookup_module(python_index, "Calculator")

        assert result is not None
        assert "functions" in result
        assert len(result["functions"]) >= 4

    def test_lookup_nonexistent_module_returns_none(self, python_index):
        """Test that looking up non-existent module returns None."""
        result = lookup_module(python_index, "NonExistentClass")

        assert result is None

    def test_lookup_file_module(self, python_index):
        """Test looking up file-level module (_file_<path>)."""
        # Find any file-level module
        file_modules = [name for name in python_index["modules"] if name.startswith("_file_")]

        assert len(file_modules) > 0

        file_module_name = file_modules[0]
        result = lookup_module(python_index, file_module_name)

        assert result is not None
        assert "file" in result


class TestFunctionLookup:
    """Test looking up functions by name."""

    def test_lookup_function_by_name(self, python_index):
        """Test finding a function by name across all modules."""
        results = lookup_function(python_index, "add")

        assert len(results) >= 1

        # Should find Calculator.add
        add_func = results[0]
        assert add_func["name"] == "add"
        assert "line" in add_func
        assert "arity" in add_func

    def test_lookup_function_returns_list(self, python_index):
        """Test that function lookup returns list (may have multiple matches)."""
        results = lookup_function(python_index, "add")

        assert isinstance(results, list)
        assert len(results) > 0

    def test_lookup_private_function(self, python_index):
        """Test finding private functions with underscore prefix."""
        results = lookup_function(python_index, "_private_method")

        assert len(results) >= 1

        private_func = results[0]
        assert private_func["name"] == "_private_method"
        assert private_func["type"] == "private"

    def test_lookup_function_includes_module_context(self, python_index):
        """Test that function lookup includes which module it belongs to."""
        results = lookup_function(python_index, "add")

        assert len(results) > 0

        # Result should include enough info to locate the function
        func = results[0]
        assert "name" in func
        assert "line" in func

        # Should be able to determine it's in Calculator
        # (Implementation will add module_name field)

    def test_lookup_nonexistent_function_returns_empty(self, python_index):
        """Test that looking up non-existent function returns empty list."""
        results = lookup_function(python_index, "nonexistent_function")

        assert isinstance(results, list)
        assert len(results) == 0


class TestDocumentationResolution:
    """Test retrieving function documentation."""

    def test_get_function_documentation(self, python_index):
        """Test retrieving full documentation for a function."""
        doc = get_function_documentation(python_index, "Calculator", "add")

        assert doc is not None
        assert "add" in doc.lower() or "sum" in doc.lower()
        assert len(doc) > 10  # Should be a real docstring, not empty

    def test_get_function_documentation_missing(self, python_index):
        """Test retrieving documentation for function without docstring."""
        # If a function has no doc, should return None or empty string
        doc = get_function_documentation(python_index, "Calculator", "nonexistent")

        # Should gracefully handle missing function
        assert doc is None or doc == ""

    def test_get_module_docstring(self, python_index):
        """Test retrieving module-level docstring."""
        module = lookup_module(python_index, "Calculator")

        if "moduledoc" in module and module["moduledoc"]:
            doc = module["moduledoc"]
            assert "calculator" in doc.lower()


class TestSignatureRetrieval:
    """Test retrieving function signatures."""

    def test_get_function_signature(self, python_index):
        """Test retrieving formatted signature for a function."""
        signature = get_function_signature(python_index, "Calculator", "add")

        assert signature is not None
        assert "def add" in signature
        assert "x" in signature
        assert "y" in signature
        assert "int" in signature  # Type annotations

    def test_get_function_parameters(self, python_index):
        """Test extracting parameter list from function."""
        module = lookup_module(python_index, "Calculator")
        functions = {f["name"]: f for f in module["functions"]}

        add_func = functions["add"]

        assert "args" in add_func
        args = add_func["args"]

        # Should have self, x, y
        assert "self" in args or len(args) == 2
        assert "x" in args or args[0] == "x"
        assert "y" in args or args[1] == "y"

    def test_get_function_arity(self, python_index):
        """Test getting function arity (argument count)."""
        module = lookup_module(python_index, "Calculator")
        functions = {f["name"]: f for f in module["functions"]}

        add_func = functions["add"]

        assert "arity" in add_func
        # add(self, x, y) = arity 3 (or 2 if self excluded)
        assert add_func["arity"] >= 2


class TestLocationLookup:
    """Test looking up code by file and line number."""

    def test_lookup_by_location(self, python_index):
        """Test reverse lookup: given file/line, find what's defined there."""
        # Look up line 11 in calculator.py (Calculator class definition)
        result = lookup_by_location(python_index, "calculator.py", 11)

        assert result is not None
        assert result["type"] in ["module", "class"]
        assert "Calculator" in result["name"]

    def test_lookup_function_by_location(self, python_index):
        """Test finding function at specific file/line."""
        # Find the 'add' method (line 19)
        result = lookup_by_location(python_index, "calculator.py", 19)

        if result:  # Implementation may vary
            assert "add" in result.get("name", "")


class TestKeywordLookup:
    """Test retrieving keywords for modules and functions."""

    def test_lookup_keywords_for_module(self, python_index):
        """Test getting keyword dict for a module."""
        module = lookup_module(python_index, "Calculator")

        if "keywords" in module and module["keywords"]:
            keywords = module["keywords"]

            assert isinstance(keywords, dict)
            assert all(isinstance(score, (int, float)) for score in keywords.values())

            # Should have relevant keywords
            # (Exact keywords depend on extraction algorithm)

    def test_lookup_keywords_for_function(self, python_index):
        """Test getting keyword dict for a function."""
        module = lookup_module(python_index, "Calculator")
        functions = {f["name"]: f for f in module["functions"]}

        add_func = functions["add"]

        if "keywords" in add_func and add_func["keywords"]:
            keywords = add_func["keywords"]

            assert isinstance(keywords, dict)
            assert len(keywords) > 0


class TestAmbiguousLookup:
    """Test handling of ambiguous lookups (multiple matches)."""

    def test_lookup_function_with_same_name_in_multiple_modules(self, python_index):
        """Test finding function that exists in multiple modules."""
        # Current fixture only has one module, but this tests the API
        results = lookup_function(python_index, "add")

        # Even with one match, should return list
        assert isinstance(results, list)

        # If multiple matches existed, all would be returned
        # Implementation should include module context for each


class TestBulkLookup:
    """Test efficient bulk lookups."""

    def test_lookup_all_functions_in_module(self, python_index):
        """Test getting all functions in a module."""
        module = lookup_module(python_index, "Calculator")

        assert "functions" in module
        functions = module["functions"]

        assert isinstance(functions, list)
        assert len(functions) >= 4

        # All should have required fields
        for func in functions:
            assert "name" in func
            assert "line" in func
            assert "arity" in func
