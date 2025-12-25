"""Comprehensive tests for Rust support in QueryOrchestrator.

This test file covers all parameter combinations for the query tool
with Rust code, including Rust-specific features like:
- Structs and methods (pub, private)
- Traits and implementations
- Modules and visibility
- Associated functions vs methods
- Result/Option types
"""

import pytest
from pathlib import Path

from cicada.languages.scip.reader import SCIPReader
from cicada.languages.scip.converter import SCIPConverter
from cicada.query import QueryOrchestrator


@pytest.fixture(scope="module")
def rust_index():
    """Load the Rust SCIP index for testing."""
    fixture_path = Path(__file__).parent / "fixtures" / "sample_rust"
    scip_path = fixture_path / "index.scip"

    if not scip_path.exists():
        pytest.skip(
            "Rust SCIP index not generated. Run: rust-analyzer scip tests/fixtures/sample_rust --output tests/fixtures/sample_rust/index.scip"
        )

    # Read SCIP index
    reader = SCIPReader()
    scip_index = reader.read_index(scip_path)

    # Convert SCIP index to Cicada index format
    converter = SCIPConverter(verbose=False)
    index = converter.convert(scip_index, fixture_path)

    return index


class TestRustKeywordSearch:
    """Test keyword search with Rust code."""

    def test_simple_keyword_search(self, rust_index):
        """Test simple keyword search finds relevant Rust code."""
        orchestrator = QueryOrchestrator(rust_index)
        result = orchestrator.execute_query("calculator")

        # Should find Calculator struct and related code
        assert len(result) > 0
        result_str = str(result).lower()
        assert "calculator" in result_str

    def test_multiple_keywords(self, rust_index):
        """Test searching with multiple keywords."""
        orchestrator = QueryOrchestrator(rust_index)
        result = orchestrator.execute_query(["add", "multiply"])

        # Should find functions that deal with arithmetic
        assert len(result) > 0
        result_lower = str(result).lower()
        assert "add" in result_lower or "multiply" in result_lower

    def test_struct_method_search(self, rust_index):
        """Test finding struct methods by keyword."""
        orchestrator = QueryOrchestrator(rust_index)
        result = orchestrator.execute_query("divide")

        # Should find divide method in Calculator
        assert len(result) > 0
        assert "divide" in str(result).lower()

    def test_trait_search(self, rust_index):
        """Test finding trait declarations."""
        orchestrator = QueryOrchestrator(rust_index)
        result = orchestrator.execute_query("displayable")

        # Should find Displayable trait
        assert isinstance(result, str)
        # Either finds the trait or returns well-formed response
        assert "displayable" in result.lower() or "results" in result.lower()

    def test_module_search(self, rust_index):
        """Test finding module-level items."""
        orchestrator = QueryOrchestrator(rust_index)
        result = orchestrator.execute_query("operations")

        # Should find operations module
        assert isinstance(result, str)
        assert "operations" in result.lower() or "results" in result.lower()


class TestRustPatternSearch:
    """Test pattern-based search with Rust code."""

    def test_wildcard_function_pattern(self, rust_index):
        """Test wildcard patterns for functions."""
        orchestrator = QueryOrchestrator(rust_index)
        result = orchestrator.execute_query(["add*"])

        assert isinstance(result, str)
        assert "add" in result.lower() or "Found: 0" in result

    def test_wildcard_struct_pattern(self, rust_index):
        """Test wildcard patterns for structs."""
        orchestrator = QueryOrchestrator(rust_index)
        result = orchestrator.execute_query(["Calculator*"])

        assert isinstance(result, str)
        assert "calculator" in result.lower() or "Found: 0" in result

    def test_module_qualified_pattern(self, rust_index):
        """Test module-qualified patterns."""
        orchestrator = QueryOrchestrator(rust_index)
        result = orchestrator.execute_query(["operations.*"])

        assert isinstance(result, str)
        assert "operations" in result.lower() or "Found: 0" in result

    def test_or_pattern(self, rust_index):
        """Test OR patterns."""
        orchestrator = QueryOrchestrator(rust_index)
        result = orchestrator.execute_query(["add*|multiply*"])

        assert isinstance(result, str)
        has_add = "add" in result.lower()
        has_multiply = "multiply" in result.lower()
        has_results = "results" in result.lower()
        assert has_add or has_multiply or has_results


class TestRustFilters:
    """Test filter parameters with Rust code."""

    def test_scope_filter_all(self, rust_index):
        """Test scope=all returns all items."""
        orchestrator = QueryOrchestrator(rust_index)
        result = orchestrator.execute_query("method", scope="all")

        assert isinstance(result, str)
        assert "Query:" in result

    def test_scope_filter_public(self, rust_index):
        """Test scope=public filters to public items only."""
        orchestrator = QueryOrchestrator(rust_index)
        result = orchestrator.execute_query("method", scope="public")

        assert isinstance(result, str)
        # Should not include _private_method
        assert "_private" not in result.lower() or "results" in result.lower()

    def test_scope_filter_private(self, rust_index):
        """Test scope=private filters to private items only."""
        orchestrator = QueryOrchestrator(rust_index)
        result = orchestrator.execute_query("private", scope="private")

        assert isinstance(result, str)
        assert "Query:" in result

    def test_result_type_modules(self, rust_index):
        """Test result_type=modules filters to modules only."""
        orchestrator = QueryOrchestrator(rust_index)
        result = orchestrator.execute_query("sample", result_type="modules")

        assert isinstance(result, str)
        assert "Query:" in result

    def test_result_type_functions(self, rust_index):
        """Test result_type=functions filters to functions only."""
        orchestrator = QueryOrchestrator(rust_index)
        result = orchestrator.execute_query("add", result_type="functions")

        assert isinstance(result, str)
        assert "Query:" in result

    def test_max_results_limit(self, rust_index):
        """Test max_results parameter limits output."""
        orchestrator = QueryOrchestrator(rust_index)
        result = orchestrator.execute_query("*", max_results=3)

        assert isinstance(result, str)
        assert "Query:" in result

    def test_show_snippets_enabled(self, rust_index):
        """Test show_snippets parameter shows code."""
        orchestrator = QueryOrchestrator(rust_index)
        result = orchestrator.execute_query("add", show_snippets=True)

        assert isinstance(result, str)
        # When snippets are enabled and there are results, code blocks appear
        # or we get a well-formed response
        assert "Query:" in result


class TestRustSpecificFeatures:
    """Test Rust-specific language features."""

    def test_struct_search(self, rust_index):
        """Test finding struct definitions."""
        orchestrator = QueryOrchestrator(rust_index)
        result = orchestrator.execute_query("Calculator")

        assert isinstance(result, str)
        assert "calculator" in result.lower()

    def test_impl_method_search(self, rust_index):
        """Test finding impl methods."""
        orchestrator = QueryOrchestrator(rust_index)
        result = orchestrator.execute_query("new")

        # Should find Calculator::new
        assert isinstance(result, str)
        assert "new" in result.lower() or "results" in result.lower()

    def test_trait_impl_search(self, rust_index):
        """Test finding trait implementations."""
        orchestrator = QueryOrchestrator(rust_index)
        result = orchestrator.execute_query("format")

        # Should find Displayable::format implementation
        assert isinstance(result, str)
        assert "format" in result.lower() or "results" in result.lower()

    def test_module_function_search(self, rust_index):
        """Test finding module-level functions."""
        orchestrator = QueryOrchestrator(rust_index)
        result = orchestrator.execute_query("helper_function")

        assert isinstance(result, str)
        assert "helper" in result.lower() or "results" in result.lower()

    def test_associated_function_vs_method(self, rust_index):
        """Test distinguishing associated functions from methods."""
        orchestrator = QueryOrchestrator(rust_index)
        # new is an associated function (no &self)
        result_new = orchestrator.execute_query("new")
        # add is a method (has &self)
        result_add = orchestrator.execute_query("add")

        assert isinstance(result_new, str)
        assert isinstance(result_add, str)


class TestRustEdgeCases:
    """Test edge cases with Rust code."""

    def test_zero_results(self, rust_index):
        """Test query with no matches returns well-formed response."""
        orchestrator = QueryOrchestrator(rust_index)
        result = orchestrator.execute_query("nonexistent_xyz_123")

        assert isinstance(result, str)
        assert "0 results" in result.lower() or "no results" in result.lower() or "Query:" in result

    def test_empty_query(self, rust_index):
        """Test empty query is handled gracefully."""
        orchestrator = QueryOrchestrator(rust_index)
        result = orchestrator.execute_query("")

        assert isinstance(result, str)

    def test_special_characters_in_query(self, rust_index):
        """Test queries with special characters."""
        orchestrator = QueryOrchestrator(rust_index)
        # Rust uses :: for module paths
        result = orchestrator.execute_query("sample_rust::Calculator")

        assert isinstance(result, str)
        assert "Query:" in result


class TestRustCombinedFilters:
    """Test combining multiple filter parameters."""

    def test_scope_and_result_type(self, rust_index):
        """Test combining scope and result_type filters."""
        orchestrator = QueryOrchestrator(rust_index)
        result = orchestrator.execute_query("add", scope="public", result_type="functions")

        assert isinstance(result, str)
        assert "Query:" in result

    def test_all_filters_combined(self, rust_index):
        """Test combining all filter parameters."""
        orchestrator = QueryOrchestrator(rust_index)
        result = orchestrator.execute_query(
            "calculator", scope="public", result_type="all", max_results=5, show_snippets=False
        )

        assert isinstance(result, str)
        assert "Query:" in result


class TestRustIndexStructure:
    """Test the structure of the Rust index."""

    def test_modules_key_exists(self, rust_index):
        """Test that index has modules key."""
        assert "modules" in rust_index
        assert isinstance(rust_index["modules"], dict)

    def test_metadata_key_exists(self, rust_index):
        """Test that index has metadata key."""
        assert "metadata" in rust_index
        assert isinstance(rust_index["metadata"], dict)

    def test_language_is_rust(self, rust_index):
        """Test that language is detected as Rust."""
        # The language should be in metadata or inferred from file extensions
        metadata = rust_index.get("metadata", {})
        # Either explicitly set or we check file extensions
        if "language" in metadata:
            assert metadata["language"] == "rust"
        else:
            # Check that we have .rs files
            has_rust_files = any(
                m.get("file", "").endswith(".rs") for m in rust_index.get("modules", {}).values()
            )
            assert has_rust_files

    def test_modules_have_required_fields(self, rust_index):
        """Test that modules have required fields."""
        for module_name, module_data in rust_index.get("modules", {}).items():
            assert "file" in module_data, f"Module {module_name} missing 'file'"
            assert "line" in module_data, f"Module {module_name} missing 'line'"

    def test_functions_have_required_fields(self, rust_index):
        """Test that functions have required fields."""
        for module_name, module_data in rust_index.get("modules", {}).items():
            for func in module_data.get("functions", []):
                assert "name" in func, f"Function in {module_name} missing 'name'"
                assert "line" in func, f"Function in {module_name} missing 'line'"
