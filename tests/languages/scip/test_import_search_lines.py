"""Tests for configurable import_search_lines parameter.

These tests verify that the import line limit can be configured
to handle files with large docstrings, copyright headers, etc.
"""

import pytest
from unittest.mock import Mock

from cicada.languages.scip import scip_pb2
from cicada.languages.scip.converter import SCIPConverter


class TestImportSearchLinesConfiguration:
    """Test that import_search_lines is configurable and works correctly."""

    def test_default_import_search_lines_is_50(self):
        """Test that default import_search_lines is 50."""
        converter = SCIPConverter()
        assert converter.import_search_lines == 50

    def test_custom_import_search_lines(self):
        """Test that import_search_lines can be customized."""
        converter = SCIPConverter(import_search_lines=100)
        assert converter.import_search_lines == 100

    def test_import_detection_respects_line_limit(self):
        """Test that imports beyond the limit are not detected."""
        # Create a mock SCIP document with an import at line 60
        doc = scip_pb2.Document()
        doc.relative_path = "test.py"

        # Create an occurrence representing an import at line 60
        occurrence = doc.occurrences.add()
        occurrence.symbol = "scip-python python pkg v1 mymodule:"
        occurrence.symbol_roles = scip_pb2.SymbolRole.ReadAccess
        occurrence.range.extend([59, 0, 59, 10])  # Line 60 (0-indexed)

        # Test with default limit (50) - should NOT detect import
        converter_default = SCIPConverter(import_search_lines=50)
        dependencies = converter_default._extract_dependencies(doc)
        assert len(dependencies) == 0, "Import at line 60 should be ignored with limit 50"

        # Test with higher limit (100) - SHOULD detect import
        converter_high = SCIPConverter(import_search_lines=100)
        dependencies = converter_high._extract_dependencies(doc)
        assert len(dependencies) == 1, "Import at line 60 should be detected with limit 100"
        assert dependencies[0]["module"] == "mymodule"

    def test_import_within_limit_is_detected(self):
        """Test that imports within the limit are always detected."""
        # Create a mock SCIP document with an import at line 10
        doc = scip_pb2.Document()
        doc.relative_path = "test.py"

        occurrence = doc.occurrences.add()
        occurrence.symbol = "scip-python python pkg v1 mymodule:"
        occurrence.symbol_roles = scip_pb2.SymbolRole.ReadAccess
        occurrence.range.extend([9, 0, 9, 10])  # Line 10 (0-indexed)

        # Should be detected with both default and custom limits
        for limit in [15, 50, 100]:
            converter = SCIPConverter(import_search_lines=limit)
            dependencies = converter._extract_dependencies(doc)
            assert (
                len(dependencies) == 1
            ), f"Import at line 10 should be detected with limit {limit}"

    def test_multiple_imports_some_beyond_limit(self):
        """Test that only imports within limit are detected."""
        doc = scip_pb2.Document()
        doc.relative_path = "test.py"

        # Import at line 10 (within limit)
        occ1 = doc.occurrences.add()
        occ1.symbol = "scip-python python pkg v1 module1:"
        occ1.symbol_roles = scip_pb2.SymbolRole.ReadAccess
        occ1.range.extend([9, 0, 9, 10])

        # Import at line 40 (within default limit of 50)
        occ2 = doc.occurrences.add()
        occ2.symbol = "scip-python python pkg v1 module2:"
        occ2.symbol_roles = scip_pb2.SymbolRole.ReadAccess
        occ2.range.extend([39, 0, 39, 10])

        # Import at line 60 (beyond default limit of 50)
        occ3 = doc.occurrences.add()
        occ3.symbol = "scip-python python pkg v1 module3:"
        occ3.symbol_roles = scip_pb2.SymbolRole.ReadAccess
        occ3.range.extend([59, 0, 59, 10])

        # With default limit (50)
        converter_default = SCIPConverter(import_search_lines=50)
        deps = converter_default._extract_dependencies(doc)
        assert len(deps) == 2, "Should detect 2 imports within line 50"
        module_names = {d["module"] for d in deps}
        assert module_names == {"module1", "module2"}

        # With higher limit (100)
        converter_high = SCIPConverter(import_search_lines=100)
        deps = converter_high._extract_dependencies(doc)
        assert len(deps) == 3, "Should detect all 3 imports with limit 100"
        module_names = {d["module"] for d in deps}
        assert module_names == {"module1", "module2", "module3"}

    def test_backward_compatibility(self):
        """Test that existing code without import_search_lines still works."""
        # Should work with no parameters (uses default)
        converter = SCIPConverter()
        assert converter.import_search_lines == 50

        # Should work with other parameters
        converter = SCIPConverter(verbose=True, extract_references=False)
        assert converter.import_search_lines == 50
