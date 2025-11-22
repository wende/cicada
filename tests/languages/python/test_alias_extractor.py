"""Tests for Python alias extraction."""

from cicada.languages.python.alias_extractor import PythonAliasExtractor


class TestPythonAliasExtractor:
    """Test the Python alias extractor."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = PythonAliasExtractor()

    def test_module_alias_extraction(self):
        """Test extraction of module aliases (import X as Y)."""
        source = """
import operations
import operations as ops
import utils as util
"""
        aliases = self.extractor.extract_aliases_from_source(source)

        assert "ops" in aliases
        assert aliases["ops"] == "operations"
        assert "util" in aliases
        assert aliases["util"] == "utils"
        # "operations" without alias should not be in the dict
        assert "operations" not in aliases

    def test_symbol_alias_extraction(self):
        """Test extraction of symbol aliases (from X import Y as Z)."""
        source = """
from utils import average as avg
from calculator import Calculator as Calc
from operations import add as sum_func
"""
        aliases = self.extractor.extract_aliases_from_source(source)

        assert "avg" in aliases
        assert aliases["avg"] == "utils"
        assert "Calc" in aliases
        assert aliases["Calc"] == "calculator"
        assert "sum_func" in aliases
        assert aliases["sum_func"] == "operations"

    def test_direct_imports_tracked(self):
        """Test that direct imports without alias are also tracked."""
        source = """
from utils import chain_add
from calculator import Calculator
"""
        aliases = self.extractor.extract_aliases_from_source(source)

        # Direct imports are tracked as implicit aliases
        assert "chain_add" in aliases
        assert aliases["chain_add"] == "utils"
        assert "Calculator" in aliases
        assert aliases["Calculator"] == "calculator"

    def test_mixed_imports(self):
        """Test mixed import patterns in one file."""
        source = """
import operations
import operations as ops
from utils import chain_add
from utils import average as avg
from calculator import Calculator as Calc
"""
        aliases = self.extractor.extract_aliases_from_source(source)

        # Module alias
        assert "ops" in aliases
        assert aliases["ops"] == "operations"

        # Direct symbol imports
        assert "chain_add" in aliases
        assert aliases["chain_add"] == "utils"

        # Symbol with alias
        assert "avg" in aliases
        assert aliases["avg"] == "utils"

        # Class with alias
        assert "Calc" in aliases
        assert aliases["Calc"] == "calculator"

    def test_star_imports_ignored(self):
        """Test that star imports are not tracked."""
        source = """
from utils import *
"""
        aliases = self.extractor.extract_aliases_from_source(source)

        # Star imports should not create an alias entry
        assert "*" not in aliases
        # Should return empty dict for star imports
        assert len(aliases) == 0

    def test_syntax_error_returns_empty(self):
        """Test that syntax errors return empty dict."""
        source = """
import operations as
from utils import
"""
        aliases = self.extractor.extract_aliases_from_source(source)

        assert aliases == {}

    def test_empty_source(self):
        """Test extraction from empty source."""
        aliases = self.extractor.extract_aliases_from_source("")

        assert aliases == {}

    def test_no_imports(self):
        """Test file with no imports."""
        source = """
def add(x, y):
    return x + y

class Calculator:
    def multiply(self, x, y):
        return x * y
"""
        aliases = self.extractor.extract_aliases_from_source(source)

        assert aliases == {}

    def test_relative_imports(self):
        """Test relative imports."""
        source = """
from . import operations
from .. import utils
from .submodule import helper as hlp
"""
        aliases = self.extractor.extract_aliases_from_source(source)

        # Relative imports without explicit module name are skipped
        # Only explicit aliases are tracked
        assert "hlp" in aliases
        # Note: relative imports like "from . import X" don't have module name
        # so they won't appear in our alias tracking

    def test_multiple_symbol_imports(self):
        """Test multiple symbols from same module."""
        source = """
from operations import add, subtract, multiply
from utils import (
    chain_add as sum_list,
    average,
    format_result
)
"""
        aliases = self.extractor.extract_aliases_from_source(source)

        # Direct imports
        assert "add" in aliases
        assert aliases["add"] == "operations"
        assert "subtract" in aliases
        assert aliases["subtract"] == "operations"
        assert "multiply" in aliases
        assert aliases["multiply"] == "operations"

        # Mixed with alias
        assert "sum_list" in aliases
        assert aliases["sum_list"] == "utils"
        assert "average" in aliases
        assert aliases["average"] == "utils"
        assert "format_result" in aliases
        assert aliases["format_result"] == "utils"

    def test_get_module_for_alias(self):
        """Test resolving alias to module name."""
        aliases = {"ops": "operations", "avg": "utils"}

        assert self.extractor.get_module_for_alias("ops", aliases) == "operations"
        assert self.extractor.get_module_for_alias("avg", aliases) == "utils"
        assert self.extractor.get_module_for_alias("unknown", aliases) is None

    def test_real_file_extraction(self, tmp_path):
        """Test extraction from a real file."""
        test_file = tmp_path / "test_module.py"
        test_file.write_text(
            """
import operations as ops
from utils import average as avg
from calculator import Calculator

def test_function():
    result = ops.add(1, 2)
    avg_val = avg([1, 2, 3])
    calc = Calculator()
    return result
"""
        )

        aliases = self.extractor.extract_aliases(test_file)

        assert "ops" in aliases
        assert aliases["ops"] == "operations"
        assert "avg" in aliases
        assert aliases["avg"] == "utils"
        assert "Calculator" in aliases
        assert aliases["Calculator"] == "calculator"

    def test_file_not_found(self):
        """Test extraction from non-existent file returns empty dict."""
        aliases = self.extractor.extract_aliases("/nonexistent/file.py")

        assert aliases == {}

    def test_unicode_handling(self, tmp_path):
        """Test handling of unicode in source files."""
        test_file = tmp_path / "unicode_test.py"
        test_file.write_text(
            """
# -*- coding: utf-8 -*-
import operations as ops  # Операции

def тест():  # Cyrillic function name
    return ops.add(1, 2)
""",
            encoding="utf-8",
        )

        aliases = self.extractor.extract_aliases(test_file)

        assert "ops" in aliases
        assert aliases["ops"] == "operations"
