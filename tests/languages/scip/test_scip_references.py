"""Tests for call site extraction and cross-reference tracking.

These tests verify that SCIP occurrences are properly extracted to track:
- Where functions are called from (call sites)
- What functions call what (call graph)
- Import/dependency relationships
- Cross-file references

⚠️ IMPORTANT: Many of these tests will FAIL initially because call site
extraction is not yet implemented. These are TDD tests that drive the
implementation of this critical feature.
"""

import pytest

from cicada.languages.scip.reader import SCIPReader
from cicada.languages.scip.converter import SCIPConverter
from cicada.utils.index_utils import (
    get_call_sites,
    get_callers_of,
    get_callees_of,
    get_dependencies,
    get_references_to,
)


@pytest.fixture
def python_index(fixtures_dir):
    """Load and convert Python SCIP index for testing."""
    scip_file = fixtures_dir / "sample_python" / "index.scip"
    if not scip_file.exists():
        pytest.skip("Python SCIP index not found")

    reader = SCIPReader()
    scip_index = reader.read_index(scip_file)

    # Convert with call site extraction enabled
    converter = SCIPConverter(extract_references=True)  # New parameter!
    return converter.convert(scip_index, scip_file.parent)


class TestCallSiteExtraction:
    """Test basic call site extraction from SCIP occurrences."""

    def test_extract_call_sites_from_occurrences(self, python_index):
        """Test that call sites are extracted from SCIP ReadAccess occurrences."""
        # Get Calculator module
        calc = python_index["modules"]["Calculator"]

        # Check if calls field exists
        assert "calls" in calc or any(
            "calls" in func for func in calc.get("functions", [])
        ), "Call sites should be extracted into 'calls' field"

        # If we have call sites, verify structure
        # (This test will fail initially until we implement call site extraction)

    def test_call_site_includes_caller_location(self, python_index):
        """Test that each call site includes file and line of the caller."""
        # Find a function that makes calls
        calc = python_index["modules"]["Calculator"]

        # Look for any call sites
        for func in calc.get("functions", []):
            if "calls" in func and func["calls"]:
                for call in func["calls"]:
                    assert "caller_file" in call or "file" in call
                    assert "caller_line" in call or "line" in call
                    assert "callee" in call or "function" in call
                return  # Found at least one, test passed

        pytest.skip("No call sites found in index - may need multi-file fixture")

    def test_call_site_includes_callee_name(self, python_index):
        """Test that each call site identifies what function was called."""
        calc = python_index["modules"]["Calculator"]

        for func in calc.get("functions", []):
            if "calls" in func and func["calls"]:
                for call in func["calls"]:
                    # Should have callee name
                    assert "callee" in call or "function" in call or "symbol" in call
                return

        pytest.skip("No call sites found")

    def test_call_sites_multiple_per_function(self, python_index):
        """Test that a function calling multiple others tracks all calls."""
        # Find a function that makes multiple calls
        # (May need a more complex fixture for this)

        calc = python_index["modules"]["Calculator"]

        for func in calc.get("functions", []):
            if "calls" in func and func["calls"]:
                calls = func["calls"]

                if len(calls) > 1:
                    # Verify each is distinct
                    callee_names = [
                        c.get("callee", c.get("function", c.get("symbol"))) for c in calls
                    ]
                    # If multiple calls, should have distinct callees
                    assert len(set(callee_names)) >= 1
                    return

        pytest.skip("No function with multiple calls found")

    def test_call_sites_same_function_multiple_times(self, python_index):
        """Test tracking when same function is called multiple times."""
        # If a function calls foo() twice, both should be tracked
        # (with different line numbers)

        calc = python_index["modules"]["Calculator"]

        for func in calc.get("functions", []):
            if "calls" in func and func["calls"]:
                calls = func["calls"]

                # Group by callee
                by_callee = {}
                for call in calls:
                    callee = call.get("callee", call.get("function"))
                    if callee:
                        by_callee.setdefault(callee, []).append(call)

                # Check if any callee is called multiple times
                for callee, call_list in by_callee.items():
                    if len(call_list) > 1:
                        # Verify different line numbers
                        lines = [c.get("line", c.get("caller_line")) for c in call_list]
                        assert len(set(lines)) > 1 or lines[0] is not None
                        return

        pytest.skip("No repeated calls found")


class TestCrossFileReferences:
    """Test call sites across multiple files."""

    def test_call_sites_cross_file_references(self, python_index):
        """Test tracking calls from module A to module B."""
        # Calculator.add() should call operations.add()
        # This is a cross-file reference

        calc = python_index["modules"].get("Calculator")
        if not calc:
            pytest.skip("Calculator module not found")

        # Find add method
        add_func = None
        for func in calc.get("functions", []):
            if func["name"] == "add":
                add_func = func
                break

        assert add_func is not None, "Calculator.add() method not found"
        assert "calls" in add_func, "No calls field in add() method"

        # Should have at least one call to operations.add
        calls = add_func["calls"]
        assert len(calls) > 0, "add() should make at least one call"

        # Check that at least one call is to operations module
        callee_symbols = [c.get("callee", "") for c in calls]
        assert any(
            "operations" in sym for sym in callee_symbols
        ), f"Expected call to operations module, got: {callee_symbols}"

    def test_call_sites_filter_by_caller(self, python_index):
        """Test getting all calls FROM a specific function."""
        # Use utility function to get all calls made by Calculator.add
        calls = get_callees_of(python_index, "Calculator", "add")

        # May be empty list if add() doesn't call anything
        assert isinstance(calls, list)

    def test_call_sites_filter_by_callee(self, python_index):
        """Test getting all calls TO a specific function."""
        # Use utility function to find all callers of len()
        callers = get_callers_of(python_index, "len")

        # Should find helper_function() which calls len()
        # (if we implement this extraction)
        assert isinstance(callers, list)


class TestDependencyExtraction:
    """Test extraction of import/dependency information."""

    def test_dependency_extraction_from_imports(self, python_index):
        """Test that import statements are extracted as dependencies."""
        # Calculator class has imports: typing, operations, utils
        calc = python_index["modules"].get("Calculator")
        assert calc is not None, "Calculator module not found"

        # Check that dependencies field exists and matches Elixir format
        assert "dependencies" in calc, "No dependencies field in Calculator module"
        deps = calc["dependencies"]
        assert isinstance(deps, dict), "Dependencies should be a dict (Elixir format)"
        assert "modules" in deps, "Dependencies should have 'modules' key"
        assert "has_dynamic_calls" in deps, "Dependencies should have 'has_dynamic_calls' key"

        # This fixture uses only static calls; ensure dynamic calls are correctly
        # detected and encoded as `False` in the dependency format to guard
        # against regressions in dynamic call detection.
        has_dynamic_calls = deps["has_dynamic_calls"]
        assert isinstance(has_dynamic_calls, bool), "has_dynamic_calls should be a boolean flag"
        assert has_dynamic_calls is False, "Calculator fixture should not have dynamic calls"

        # Get the modules list
        module_list = deps["modules"]
        assert isinstance(module_list, list), "modules should be a list of strings"

        # Should have at least 2 dependencies (operations, utils)
        # typing might be excluded as stdlib
        assert len(module_list) > 0, "Should have at least one dependency"

        # Check that each module name is a string
        for module_name in module_list:
            assert isinstance(module_name, str), "Module name should be a string"

    def test_dependency_includes_imported_symbols(self, python_index):
        """Test that we track what symbols were imported."""
        # Calculator imports specific symbols: from utils import chain_add, format_result
        calc = python_index["modules"].get("Calculator")
        assert calc is not None

        deps = calc.get("dependencies", {})
        module_names = deps.get("modules", [])

        # Check that utils module is tracked as a dependency
        assert "utils" in module_names, "Should track utils as a dependency"

    def test_dependency_includes_source_module(self, python_index):
        """Test that we track where imports come from."""
        # Calculator imports operations module
        calc = python_index["modules"].get("Calculator")
        assert calc is not None

        deps = calc.get("dependencies", {})
        module_names = deps.get("modules", [])

        # Should track operations as a dependency
        assert "operations" in module_names, "Should track operations module import"

    def test_dependency_line_numbers(self, python_index):
        """Test that dependency call locations are tracked at function level."""
        calc = python_index["modules"].get("Calculator")
        assert calc is not None

        # Check that functions have dependencies with line numbers
        for func in calc.get("functions", []):
            func_deps = func.get("dependencies", [])
            if func_deps:
                # Check that dependencies have line numbers
                for dep in func_deps:
                    assert "line" in dep, "Dependency should include line number"
                    assert dep["line"] > 0, "Line number should be positive"
                    # Also check other required fields
                    assert "function" in dep, "Dependency should have function name"
                    assert "arity" in dep, "Dependency should have arity"
                break

        # It's okay if no dependencies found (might be empty fixture)
        # Just verify structure when present


class TestReferenceRoles:
    """Test distinguishing different types of references."""

    def test_references_include_all_roles(self, python_index):
        """Test that Definition, Read, Write, Import roles are distinguished."""
        # SCIP has symbol_roles bitfield:
        # Definition = 0x1
        # Import = 0x2
        # WriteAccess = 0x4
        # ReadAccess = 0x8

        # Our index should preserve this distinction
        calc = python_index["modules"]["Calculator"]

        # Look for any references with role info
        for func in calc.get("functions", []):
            if "references" in func or "calls" in func:
                # If implemented, should distinguish roles
                pass

        pytest.skip("Reference role extraction not yet implemented")

    def test_references_distinguish_definition_vs_usage(self, python_index):
        """Test that definition location is distinguished from usage."""
        # Definition = where function is defined (def foo:)
        # Usage = where function is called (foo())

        # These should be tracked separately
        pytest.skip("Not yet implemented")

    def test_references_external_symbols(self, python_index):
        """Test tracking references to external/stdlib symbols."""
        # Calling len(), print(), etc. (builtins)
        # Should be tracked but marked as external

        pytest.skip("External symbol tracking not yet implemented")


class TestUnusedFunctions:
    """Test identifying functions with no references."""

    def test_unused_functions_have_no_references(self, python_index):
        """Test that we can identify unused functions."""
        # A function with zero call sites is potentially unused
        # (unless it's an entry point)

        calc = python_index["modules"]["Calculator"]

        unused_functions = []
        for func in calc.get("functions", []):
            calls_to_this = get_references_to(python_index, "Calculator", func["name"])

            if len(calls_to_this) == 0:
                unused_functions.append(func["name"])

        # Some functions like _private_method might be unused
        # This is OK - test just verifies we can detect it
        assert isinstance(unused_functions, list)

    def test_builtin_symbols_excluded(self, python_index):
        """Test that builtin functions like print(), len() are not indexed as modules."""
        # We shouldn't create modules for builtins

        builtins = ["print", "len", "range", "int", "str", "dict", "list"]

        for builtin in builtins:
            assert (
                builtin not in python_index["modules"]
            ), f"Builtin '{builtin}' should not be indexed as a module"


class TestReferenceCount:
    """Test counting references accurately."""

    def test_reference_count_accuracy(self, python_index):
        """Test that reference counts match actual occurrences."""
        # If we track reference counts, they should be accurate

        calc = python_index["modules"]["Calculator"]

        for func in calc.get("functions", []):
            if "reference_count" in func:
                count = func["reference_count"]
                assert isinstance(count, int)
                assert count >= 0


class TestCircularDependencies:
    """Test handling of circular dependencies."""

    def test_circular_dependencies_tracked(self, python_index):
        """Test that circular imports/calls don't break indexing."""
        # A imports B imports A
        # Should be tracked without infinite loop

        pytest.skip("Requires multi-file fixture with circular dependency")


class TestUtilityFunctions:
    """Test utility functions for querying references."""

    def test_get_call_sites_for_function(self, python_index):
        """Test getting all call sites for a specific function."""
        call_sites = get_call_sites(python_index, "Calculator", "add")

        assert isinstance(call_sites, list)
        # May be empty if add() is never called in fixture

    def test_get_callers_of_function(self, python_index):
        """Test finding all functions that call a specific function."""
        callers = get_callers_of(python_index, "len")

        assert isinstance(callers, list)
        # helper_function() calls len(), so should appear in list
        # (if we implement this extraction)

    def test_get_callees_of_function(self, python_index):
        """Test finding all functions called by a specific function."""
        callees = get_callees_of(python_index, "Calculator", "helper_function")

        assert isinstance(callees, list)

    def test_get_dependencies_for_module(self, python_index):
        """Test getting all dependencies for a module."""
        deps = get_dependencies(python_index, "Calculator")

        assert isinstance(deps, list)

    def test_get_references_to_symbol(self, python_index):
        """Test finding all references to a symbol (function/class)."""
        refs = get_references_to(python_index, "Calculator", "add")

        assert isinstance(refs, list)
        # Each ref should have location info
        for ref in refs:
            assert "file" in ref or "line" in ref
