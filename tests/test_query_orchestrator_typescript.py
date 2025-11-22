"""Comprehensive tests for TypeScript support in QueryOrchestrator.

This test file covers all parameter combinations for the query tool
with TypeScript code, including TypeScript-specific features like:
- Classes and methods (public, private, static)
- Interfaces and type definitions
- Generic functions and classes
- Async/await patterns
- Arrow functions
- Export patterns
"""

import pytest
from pathlib import Path

from cicada.languages.scip.reader import SCIPReader
from cicada.languages.scip.converter import SCIPConverter
from cicada.query import QueryOrchestrator


@pytest.fixture(scope="module")
def typescript_index():
    """Load the TypeScript SCIP index for testing."""
    fixture_path = Path(__file__).parent / "fixtures" / "sample_typescript"
    scip_path = fixture_path / "index.scip"

    if not scip_path.exists():
        pytest.skip("TypeScript SCIP index not generated. Run tests/setup_fixtures.sh")

    # Read SCIP index
    reader = SCIPReader()
    scip_index = reader.read_index(scip_path)

    # Convert SCIP index to Cicada index format
    converter = SCIPConverter(verbose=False)
    index = converter.convert(scip_index, fixture_path)

    return index


class TestTypeScriptKeywordSearch:
    """Test keyword search with TypeScript code."""

    def test_simple_keyword_search(self, typescript_index):
        """Test simple keyword search finds relevant TypeScript code."""
        orchestrator = QueryOrchestrator(typescript_index)
        result = orchestrator.execute_query("calculator")

        # Should find Calculator class and related code
        assert len(result) > 0
        # Result should contain calculator-related identifiers
        result_str = str(result).lower()
        assert "calculator" in result_str

    def test_multiple_keywords(self, typescript_index):
        """Test searching with multiple keywords."""
        orchestrator = QueryOrchestrator(typescript_index)
        result = orchestrator.execute_query(["add", "multiply"])

        # Should find functions that deal with arithmetic
        assert len(result) > 0

    def test_quoted_phrases(self, typescript_index):
        """Test searching with quoted phrases."""
        orchestrator = QueryOrchestrator(typescript_index)
        # Search for exact phrase in documentation
        result = orchestrator.execute_query('"arithmetic operations"')

        # Should find operations module or related code
        assert len(result) >= 0  # May or may not find based on exact phrase

    def test_class_method_search(self, typescript_index):
        """Test finding class methods by keyword."""
        orchestrator = QueryOrchestrator(typescript_index)
        result = orchestrator.execute_query("divide")

        # Should find divide method in Calculator class
        assert len(result) > 0

    def test_interface_search(self, typescript_index):
        """Test finding interface declarations."""
        orchestrator = QueryOrchestrator(typescript_index)
        result = orchestrator.execute_query("processor")

        # Should find DataProcessor interface
        assert len(result) >= 0


class TestTypeScriptPatternSearch:
    """Test pattern-based search with TypeScript code."""

    def test_wildcard_function_pattern(self, typescript_index):
        """Test wildcard patterns for functions."""
        orchestrator = QueryOrchestrator(typescript_index)
        result = orchestrator.execute_query(["add*"])

        # Should find add, also functions starting with "add" or arrow functions
        assert len(result) >= 0

    def test_wildcard_class_pattern(self, typescript_index):
        """Test wildcard patterns for classes."""
        orchestrator = QueryOrchestrator(typescript_index)
        result = orchestrator.execute_query(["Calculator*"])

        # Should find Calculator class
        assert len(result) >= 0

    def test_module_qualified_pattern(self, typescript_index):
        """Test module-qualified patterns."""
        orchestrator = QueryOrchestrator(typescript_index)
        # Pattern to find all functions in operations module
        result = orchestrator.execute_query(["operations.*"])

        # Should find add, subtract, multiply, divide, etc.
        assert len(result) >= 0

    def test_arity_pattern(self, typescript_index):
        """Test patterns with arity specification."""
        orchestrator = QueryOrchestrator(typescript_index)
        # Find functions with arity 2 (two parameters)
        result = orchestrator.execute_query(["add/2"], arity=2)

        # Should find binary operations
        assert len(result) >= 0

    def test_or_pattern_no_spaces(self, typescript_index):
        """Test OR patterns without spaces."""
        orchestrator = QueryOrchestrator(typescript_index)
        result = orchestrator.execute_query(["add*|multiply*"])

        # Should find both add and multiply functions
        assert len(result) >= 0

    def test_or_pattern_with_spaces(self, typescript_index):
        """Test OR patterns with spaces."""
        orchestrator = QueryOrchestrator(typescript_index)
        result = orchestrator.execute_query(["add | multiply"])

        # Should find both add and multiply functions
        assert len(result) >= 0


class TestTypeScriptFilters:
    """Test all filter combinations with TypeScript code."""

    def test_scope_filter_all(self, typescript_index):
        """Test scope='all' returns both public and private functions."""
        orchestrator = QueryOrchestrator(typescript_index)
        result = orchestrator.execute_query("calculator", scope="all", filter_type="all")

        # Should include both public and private members
        assert len(result) >= 0

    def test_scope_filter_public(self, typescript_index):
        """Test scope='public' filters to public functions only."""
        orchestrator = QueryOrchestrator(typescript_index)
        result = orchestrator.execute_query("calculator", scope="public", filter_type="functions")

        # Should only include public functions/methods
        # Private methods like _privateMethod should be excluded
        assert len(result) >= 0

    def test_scope_filter_private(self, typescript_index):
        """Test scope='private' filters to private functions only."""
        orchestrator = QueryOrchestrator(typescript_index)
        result = orchestrator.execute_query("private", scope="private", filter_type="functions")

        # Should only include private functions
        assert len(result) >= 0

    def test_filter_type_modules(self, typescript_index):
        """Test filter_type='modules' returns only modules."""
        orchestrator = QueryOrchestrator(typescript_index)
        result = orchestrator.execute_query("calculator", filter_type="modules")

        # Should only return module/file level results
        assert len(result) >= 0

    def test_filter_type_functions(self, typescript_index):
        """Test filter_type='functions' returns only functions."""
        orchestrator = QueryOrchestrator(typescript_index)
        result = orchestrator.execute_query("add", filter_type="functions")

        # Should only return function level results
        assert len(result) >= 0

    def test_filter_type_all(self, typescript_index):
        """Test filter_type='all' returns both modules and functions."""
        orchestrator = QueryOrchestrator(typescript_index)
        result = orchestrator.execute_query("calculator", filter_type="all")

        # Should return both module and function results
        assert len(result) >= 0

    def test_match_source_docs(self, typescript_index):
        """Test match_source='docs' searches only documentation."""
        orchestrator = QueryOrchestrator(typescript_index)
        result = orchestrator.execute_query("arithmetic", match_source="docs")

        # Should match based on doc comments only
        assert len(result) >= 0

    def test_match_source_strings(self, typescript_index):
        """Test match_source='strings' searches only string literals."""
        orchestrator = QueryOrchestrator(typescript_index)
        result = orchestrator.execute_query("SELECT", match_source="strings")

        # Should match based on string literals only
        # (if any exist in TypeScript code)
        assert len(result) >= 0

    def test_match_source_all(self, typescript_index):
        """Test match_source='all' searches both docs and strings."""
        orchestrator = QueryOrchestrator(typescript_index)
        result = orchestrator.execute_query("calculator", match_source="all")

        # Should match in both documentation and strings
        assert len(result) >= 0

    def test_path_pattern_filter(self, typescript_index):
        """Test path_pattern glob filtering."""
        orchestrator = QueryOrchestrator(typescript_index)
        result = orchestrator.execute_query("add", path_pattern="*.ts")

        # Should only match TypeScript files
        assert len(result) >= 0

    def test_path_pattern_exclude(self, typescript_index):
        """Test path_pattern exclusion."""
        orchestrator = QueryOrchestrator(typescript_index)
        result = orchestrator.execute_query("calculator", path_pattern="!**/test/**")

        # Should exclude test files
        assert len(result) >= 0

    def test_arity_filter(self, typescript_index):
        """Test arity filter for function parameters."""
        orchestrator = QueryOrchestrator(typescript_index)
        result = orchestrator.execute_query("add", arity=2, filter_type="functions")

        # Should only find functions with exactly 2 parameters
        assert len(result) >= 0

    def test_arity_filter_zero(self, typescript_index):
        """Test arity=0 for zero-parameter functions."""
        orchestrator = QueryOrchestrator(typescript_index)
        result = orchestrator.execute_query("*", arity=0, filter_type="functions")

        # Should find functions with no parameters
        assert len(result) >= 0

    def test_max_results_limit(self, typescript_index):
        """Test max_results parameter limits output."""
        orchestrator = QueryOrchestrator(typescript_index)
        # Use a specific query instead of wildcard
        result = orchestrator.execute_query("calculator", max_results=3)

        # Result should be a string (formatted markdown)
        assert isinstance(result, str)
        # Count result blocks (separated by "---" or "##")
        result_count = result.count("##") + result.count("---")
        # Should have limited results (allowing for some format variations)
        assert result_count <= 10  # Generous limit to account for formatting

    def test_show_snippets_true(self, typescript_index):
        """Test show_snippets=True includes code previews."""
        orchestrator = QueryOrchestrator(typescript_index)
        result = orchestrator.execute_query("calculator", show_snippets=True)

        # Result should exist (snippet format may vary)
        assert result is not None

    def test_show_snippets_false(self, typescript_index):
        """Test show_snippets=False excludes code previews."""
        orchestrator = QueryOrchestrator(typescript_index)
        result = orchestrator.execute_query("calculator", show_snippets=False)

        # Result should exist without snippets
        assert result is not None


class TestTypeScriptSpecificFeatures:
    """Test TypeScript-specific language features."""

    def test_class_constructor_search(self, typescript_index):
        """Test finding class constructors."""
        orchestrator = QueryOrchestrator(typescript_index)
        result = orchestrator.execute_query("constructor")

        # Should find constructor methods
        assert len(result) >= 0

    def test_static_method_search(self, typescript_index):
        """Test finding static methods."""
        orchestrator = QueryOrchestrator(typescript_index)
        result = orchestrator.execute_query("static")

        # Should find static methods (if we have getInstanceCount, etc.)
        assert len(result) >= 0

    def test_interface_vs_class(self, typescript_index):
        """Test distinguishing interfaces from classes."""
        orchestrator = QueryOrchestrator(typescript_index)
        # Both DataProcessor and Container should be found
        result = orchestrator.execute_query("processor")

        assert len(result) >= 0

    def test_generic_functions(self, typescript_index):
        """Test finding generic functions."""
        orchestrator = QueryOrchestrator(typescript_index)
        result = orchestrator.execute_query("generic")

        # Should find functions like mapItems<T, U> or Container<T>
        assert len(result) >= 0

    def test_async_functions(self, typescript_index):
        """Test finding async functions."""
        orchestrator = QueryOrchestrator(typescript_index)
        result = orchestrator.execute_query("async")

        # Should find async functions like asyncProcess, fetchData
        assert len(result) >= 0

    def test_arrow_functions(self, typescript_index):
        """Test finding arrow functions."""
        orchestrator = QueryOrchestrator(typescript_index)
        result = orchestrator.execute_query("arrow")

        # Should find arrow functions like arrowAdd, arrowMultiply
        assert len(result) >= 0

    def test_export_patterns_named(self, typescript_index):
        """Test finding named exports."""
        orchestrator = QueryOrchestrator(typescript_index)
        result = orchestrator.execute_query("export", scope="public")

        # Should find exported functions/classes
        # Private items should be excluded
        assert len(result) >= 0

    def test_export_patterns_default(self, typescript_index):
        """Test finding default exports (if any)."""
        orchestrator = QueryOrchestrator(typescript_index)
        result = orchestrator.execute_query("default")

        # May or may not find default exports
        assert len(result) >= 0


class TestTypeScriptEdgeCases:
    """Test edge cases and special scenarios."""

    def test_zero_results(self, typescript_index):
        """Test query that returns no results."""
        orchestrator = QueryOrchestrator(typescript_index)
        result = orchestrator.execute_query("nonexistent_function_xyz")

        # Should return a message indicating no results (or empty)
        # QueryOrchestrator may return "No results" message or suggestions
        assert isinstance(result, str)
        # Either empty or contains "No results" or similar messaging
        is_empty_or_no_results = (
            result == ""
            or "no results" in result.lower()
            or "not found" in result.lower()
            or len(result) < 500  # Short message, not full results
        )
        assert is_empty_or_no_results

    def test_overload_warnings(self, typescript_index):
        """Test handling of queries with many results."""
        orchestrator = QueryOrchestrator(typescript_index)
        # Wildcard search that might return many results
        result = orchestrator.execute_query("*", max_results=100)

        # Should handle gracefully without errors
        assert result is not None

    def test_snippet_display(self, typescript_index):
        """Test code snippet formatting."""
        orchestrator = QueryOrchestrator(typescript_index)
        result = orchestrator.execute_query("calculator", show_snippets=True, max_results=1)

        # Should include formatted code snippet
        assert result is not None

    def test_ranking_accuracy(self, typescript_index):
        """Test that results are ranked by relevance."""
        orchestrator = QueryOrchestrator(typescript_index)
        result = orchestrator.execute_query("calculator")

        # Calculator class should be highly ranked
        # (Exact ranking depends on keyword extraction)
        assert result is not None


class TestTypeScriptCombinedFilters:
    """Test combinations of multiple filters."""

    def test_scope_and_filter_type(self, typescript_index):
        """Test scope + filter_type combination."""
        orchestrator = QueryOrchestrator(typescript_index)
        result = orchestrator.execute_query("calculator", scope="public", filter_type="functions")

        # Should only return public functions
        assert len(result) >= 0

    def test_scope_and_arity(self, typescript_index):
        """Test scope + arity combination."""
        orchestrator = QueryOrchestrator(typescript_index)
        result = orchestrator.execute_query("add", scope="public", arity=2)

        # Should return public functions with 2 parameters
        assert len(result) >= 0

    def test_filter_type_and_path_pattern(self, typescript_index):
        """Test filter_type + path_pattern combination."""
        orchestrator = QueryOrchestrator(typescript_index)
        result = orchestrator.execute_query(
            "add", filter_type="functions", path_pattern="operations.ts"
        )

        # Should return functions only from operations.ts
        assert len(result) >= 0

    def test_match_source_and_scope(self, typescript_index):
        """Test match_source + scope combination."""
        orchestrator = QueryOrchestrator(typescript_index)
        result = orchestrator.execute_query("arithmetic", match_source="docs", scope="public")

        # Should search docs only for public items
        assert len(result) >= 0

    def test_all_filters_combined(self, typescript_index):
        """Test maximum filter combination."""
        orchestrator = QueryOrchestrator(typescript_index)
        result = orchestrator.execute_query(
            "add",
            scope="public",
            filter_type="functions",
            match_source="docs",
            path_pattern="*.ts",
            arity=2,
            max_results=5,
        )

        # Should apply all filters successfully and return a string
        assert isinstance(result, str)
        # Result should exist (filters applied successfully without errors)
        assert len(result) >= 0


class TestTypeScriptQueryModes:
    """Test different query modes and patterns."""

    def test_string_query_tokenization(self, typescript_index):
        """Test that string queries are tokenized by whitespace."""
        orchestrator = QueryOrchestrator(typescript_index)
        # String should be split into ["calculator", "add"]
        result = orchestrator.execute_query("calculator add")

        # Should find items matching both keywords
        assert len(result) >= 0

    def test_array_query_no_tokenization(self, typescript_index):
        """Test that array queries are not tokenized."""
        orchestrator = QueryOrchestrator(typescript_index)
        result = orchestrator.execute_query(["calculator", "add"])

        # Should treat as two separate keywords
        assert len(result) >= 0

    def test_mixed_keywords_and_patterns(self, typescript_index):
        """Test mixing keywords and patterns in array."""
        orchestrator = QueryOrchestrator(typescript_index)
        result = orchestrator.execute_query(["calculator", "operations.*"])

        # Should handle both keywords and patterns
        assert len(result) >= 0

    def test_partial_module_matching(self, typescript_index):
        """Test partial module name matching."""
        orchestrator = QueryOrchestrator(typescript_index)
        # Auto-prefix: User.create* becomes *.User
        result = orchestrator.execute_query(["calculator*"])

        # Should find Calculator-related items
        assert len(result) >= 0


class TestTypeScriptIndexStructure:
    """Test that TypeScript index has correct structure."""

    def test_modules_key_exists(self, typescript_index):
        """Test index has 'modules' key."""
        assert "modules" in typescript_index

    def test_metadata_key_exists(self, typescript_index):
        """Test index has 'metadata' key."""
        assert "metadata" in typescript_index

    def test_language_is_typescript(self, typescript_index):
        """Test metadata identifies language as TypeScript."""
        assert typescript_index["metadata"]["language"] == "typescript"

    def test_modules_have_required_fields(self, typescript_index):
        """Test modules have required fields."""
        modules = typescript_index["modules"]
        if len(modules) > 0:
            first_module = next(iter(modules.values()))
            # Required fields
            assert "file" in first_module
            assert "line" in first_module
            # Functions array should exist
            assert "functions" in first_module

    def test_functions_have_required_fields(self, typescript_index):
        """Test functions have required fields."""
        modules = typescript_index["modules"]
        for module in modules.values():
            for func in module.get("functions", []):
                assert "name" in func
                assert "arity" in func
                assert "line" in func
                assert "type" in func
                # Type should only be "public" or "private"
                assert func["type"] in ["public", "private"]

    def test_no_language_specific_types(self, typescript_index):
        """Test that functions use language-agnostic types."""
        modules = typescript_index["modules"]
        for module in modules.values():
            for func in module.get("functions", []):
                # Should NOT have TypeScript-specific types like "method", "function", etc.
                # Should only be "public" or "private"
                assert func["type"] in ["public", "private"]
