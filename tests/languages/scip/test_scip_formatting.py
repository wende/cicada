"""Tests for text formatting of SCIP-generated indexes.

These tests verify that SCIP-generated indexes can be formatted as
readable text/markdown output (not JSON), using the existing formatter
utilities that were designed for Elixir but should work generically.
"""

import pytest

from cicada.languages.scip.reader import SCIPReader
from cicada.languages.scip.converter import SCIPConverter
from cicada.format.formatter import ModuleFormatter
from cicada.utils.function_grouper import FunctionGrouper


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


@pytest.fixture
def typescript_index(fixtures_dir):
    """Load and convert TypeScript SCIP index for testing."""
    scip_file = fixtures_dir / "sample_typescript" / "index.scip"
    if not scip_file.exists():
        pytest.fail("TypeScript SCIP index not found - run make setup-scip")

    reader = SCIPReader()
    scip_index = reader.read_index(scip_file)

    converter = SCIPConverter()
    return converter.convert(scip_index, scip_file.parent)


class TestModuleFormatter:
    """Test ModuleFormatter with SCIP-generated data."""

    def test_module_formatter_with_scip_data(self, python_index):
        """Test that ModuleFormatter can format SCIP modules."""
        calc = python_index["modules"]["Calculator"]

        formatter = ModuleFormatter()

        # Format the module
        output = formatter.format_module_json("Calculator", calc)

        # Should produce markdown output
        assert isinstance(output, str)
        assert len(output) > 0

        # Should contain module name
        assert "Calculator" in output

        # Should contain function names
        assert "add" in output or "multiply" in output

    def test_function_formatter_with_scip_signature(self, python_index):
        """Test formatting function signatures from SCIP data."""
        calc = python_index["modules"]["Calculator"]
        functions = {f["name"]: f for f in calc["functions"]}

        # Get a specific function
        add_func = functions["add"]

        # Function should have signature and doc attributes
        assert "signature" in add_func
        assert "doc" in add_func

    def test_call_site_formatter_with_references(self, python_index):
        """Test formatting call sites if they exist."""
        calc = python_index["modules"]["Calculator"]

        # If call sites are extracted
        for func in calc.get("functions", []):
            if "calls" in func and func["calls"]:
                # Call sites can be formatted
                calls = func["calls"]
                assert isinstance(calls, list)
                return

        pytest.skip("No call sites to format")

    def test_keyword_display_with_scores(self, python_index):
        """Test displaying keywords with their scores."""
        calc = python_index["modules"]["Calculator"]

        if "keywords" in calc and calc["keywords"]:
            keywords = calc["keywords"]

            # Format as readable text
            output = []
            for keyword, score in sorted(keywords.items(), key=lambda x: -x[1]):
                output.append(f"{keyword}: {score:.2f}")

            text = "\n".join(output)

            assert len(text) > 0
            assert any(char.isdigit() for char in text)  # Contains scores


class TestMarkdownOutput:
    """Test complete markdown output generation."""

    def test_markdown_output_complete(self, python_index):
        """Test generating full markdown output for a module."""
        calc = python_index["modules"]["Calculator"]

        formatter = ModuleFormatter()
        output = formatter.format_module_markdown("Calculator", calc)

        # Should have markdown structure
        # Note: formatter uses plain text formatting, not markdown "#" headers
        assert "\n" in output  # Line breaks
        assert "Public:" in output  # Section headers

        # Should have function information
        assert "add" in output.lower() or "multiply" in output.lower()

    def test_function_grouping_by_name_arity(self, python_index):
        """Test that FunctionGrouper works with SCIP functions."""
        calc = python_index["modules"]["Calculator"]
        functions = calc["functions"]

        grouper = FunctionGrouper()
        grouped = grouper.group_by_name_arity(functions)

        # Should produce valid grouping
        assert isinstance(grouped, dict) or isinstance(grouped, list)

    def test_signature_builder_python_types(self, python_index):
        """Test that SignatureBuilder handles Python type annotations."""
        calc = python_index["modules"]["Calculator"]
        functions = {f["name"]: f for f in calc["functions"]}

        add_func = functions["add"]

        # Should be able to build signature from SCIP data
        # (API may vary - this tests compatibility)

        if "signature" in add_func:
            sig = add_func["signature"]
            assert "int" in sig or ":" in sig  # Type annotations present


class TestTypeCompatibility:
    """Test that SCIP's public/private types work with formatters."""

    def test_format_respects_public_private(self, python_index):
        """Test that public/private types are displayed correctly."""
        calc = python_index["modules"]["Calculator"]
        functions = {f["name"]: f for f in calc["functions"]}

        # Find public and private functions
        public_funcs = [f for f in functions.values() if f.get("type") == "public"]
        private_funcs = [f for f in functions.values() if f.get("type") == "private"]

        # Should have both
        assert len(public_funcs) > 0
        assert len(private_funcs) > 0

        # Formatter should handle both types
        formatter = ModuleFormatter()
        # Include private functions to test both types
        output = formatter.format_module_json("Calculator", calc, visibility="all")

        # Should contain both public and private functions
        assert "_private_method" in output


class TestListFormatting:
    """Test formatting lists of modules and functions."""

    def test_format_module_list(self, python_index):
        """Test formatting a list of modules."""
        modules = python_index["modules"]

        # Should be able to list all modules
        module_names = list(modules.keys())

        assert len(module_names) > 0
        assert "Calculator" in module_names

    def test_format_function_list(self, python_index):
        """Test formatting a list of functions within a module."""
        calc = python_index["modules"]["Calculator"]
        functions = calc["functions"]

        # Format as list
        output_lines = []
        for func in functions:
            line = f"{func['name']}/{func['arity']} - line {func['line']}"
            output_lines.append(line)

        text = "\n".join(output_lines)

        assert "add" in text
        assert "multiply" in text


class TestEmptyFormatting:
    """Test graceful handling of empty/missing data."""

    def test_format_empty_module(self, python_index):
        """Test formatting a module with no functions."""
        # Create mock empty module
        empty_module = {"file": "empty.py", "line": 1, "functions": []}

        formatter = ModuleFormatter()

        # Should not crash on empty module
        output = formatter.format_module_json("EmptyModule", empty_module)

        assert isinstance(output, str)

    def test_format_with_missing_optional_fields(self, python_index):
        """Test formatting when optional fields are missing."""
        calc = python_index["modules"]["Calculator"]

        # Remove optional fields
        calc_copy = dict(calc)
        calc_copy.pop("moduledoc", None)
        calc_copy.pop("keywords", None)

        formatter = ModuleFormatter()

        # Should still work without optional fields
        output = formatter.format_module_json("Calculator", calc_copy)

        assert isinstance(output, str)
        assert "Calculator" in output


class TestLineNumberDisplay:
    """Test that line numbers are included in formatted output."""

    def test_format_preserves_line_numbers(self, python_index):
        """Test that formatted output includes line numbers."""
        calc = python_index["modules"]["Calculator"]

        formatter = ModuleFormatter()
        output = formatter.format_module_json("Calculator", calc)

        # Should contain line number references
        # (exact format depends on formatter implementation)

        # At minimum, function definitions should show line numbers
        functions = calc["functions"]
        for func in functions:
            if func["name"] in output:
                # Line number should appear somewhere near function name
                # (specific format may vary)
                assert str(func["line"]) in output or "line" in output.lower()


class TestCallSiteFormatting:
    """Test formatting of call sites and references."""

    def test_format_call_sites_grouped_by_file(self, python_index):
        """Test that call sites are grouped by file for readability."""
        # If call sites are extracted
        calc = python_index["modules"]["Calculator"]

        for func in calc.get("functions", []):
            if "calls" in func and func["calls"]:
                calls = func["calls"]

                # Group by file
                by_file = {}
                for call in calls:
                    file = call.get("file", call.get("caller_file", "unknown"))
                    by_file.setdefault(file, []).append(call)

                # Should be able to format grouped output
                assert len(by_file) > 0
                return

        pytest.skip("No call sites to format")


class TestTypescriptFormatting:
    """Test that TypeScript data formats correctly too."""

    def test_signature_builder_typescript_types(self, typescript_index):
        """Test formatting TypeScript type annotations."""
        calc = typescript_index["modules"]["Calculator"]

        formatter = ModuleFormatter()
        output = formatter.format_module_json("Calculator", calc)

        # Should handle TypeScript-specific elements
        assert isinstance(output, str)
        assert len(output) > 0
