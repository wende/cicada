"""Unit tests for Python SCIP support.

Tests the core Python indexing functionality including language detection,
SCIP reading, and conversion to Cicada format.
"""

import pytest

from cicada.setup import detect_project_language
from cicada.languages.python.scip_installer import SCIPPythonInstaller
from cicada.languages.scip import scip_pb2
from cicada.languages.scip.converter import SCIPConverter


class TestLanguageDetection:
    """Test language detection for Python and Elixir projects."""

    def test_detect_python_from_pyproject_toml(self, tmp_path):
        """Should detect Python from pyproject.toml."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'")
        assert detect_project_language(tmp_path) == "python"

    def test_detect_python_from_setup_py(self, tmp_path):
        """Should detect Python from setup.py."""
        (tmp_path / "setup.py").write_text("# setup")
        assert detect_project_language(tmp_path) == "python"

    def test_detect_python_from_requirements_txt(self, tmp_path):
        """Should detect Python from requirements.txt."""
        (tmp_path / "requirements.txt").write_text("requests")
        assert detect_project_language(tmp_path) == "python"

    def test_detect_elixir_from_mix_exs(self, tmp_path):
        """Should detect Elixir from mix.exs."""
        (tmp_path / "mix.exs").write_text("defmodule")
        assert detect_project_language(tmp_path) == "elixir"

    def test_detect_fails_for_unknown_project(self, tmp_path):
        """Should raise ValueError for unrecognized projects."""
        with pytest.raises(ValueError, match="Could not detect project language"):
            detect_project_language(tmp_path)

    def test_python_takes_precedence_over_elixir(self, tmp_path):
        """Python markers should be checked before Elixir."""
        (tmp_path / "pyproject.toml").write_text("[project]")
        (tmp_path / "mix.exs").write_text("defmodule")
        assert detect_project_language(tmp_path) == "python"


class TestSCIPPythonInstaller:
    """Test SCIP-Python installer utilities."""

    def test_npm_availability_check(self):
        """Should correctly detect npm availability."""
        # This will return True or False depending on system
        result = SCIPPythonInstaller.is_npm_available()
        assert isinstance(result, bool)

    def test_scip_python_availability_check(self):
        """Should correctly detect scip-python availability."""
        # This will return True or False depending on system
        result = SCIPPythonInstaller.is_scip_python_installed()
        assert isinstance(result, bool)

    def test_get_version_returns_none_when_not_installed(self, monkeypatch):
        """Should return None when scip-python is not installed."""
        # Mock get_scip_python_path to return None (not installed)
        monkeypatch.setattr(SCIPPythonInstaller, "get_scip_python_path", lambda: None)
        assert SCIPPythonInstaller.get_scip_python_version() is None


class TestPythonIndexer:
    """Test Python SCIP indexer integration."""

    @pytest.fixture
    def sample_python_repo(self, fixtures_dir):
        """Path to sample Python test fixture."""
        return fixtures_dir / "sample_python"

    def test_sample_python_repo_exists(self, sample_python_repo):
        """Test fixture should exist."""
        assert sample_python_repo.exists()
        assert (sample_python_repo / "calculator.py").exists()
        assert (sample_python_repo / "pyproject.toml").exists()

    def test_detect_language_for_sample_repo(self, sample_python_repo):
        """Should detect sample repo as Python."""
        assert detect_project_language(sample_python_repo) == "python"

    # Note: Full indexing tests require scip-python to be installed
    # These are covered in manual testing (Phase 4.3)


class TestSCIPConverter:
    """Test SCIP to Cicada format conversion."""

    @pytest.fixture
    def converter(self):
        """Create a SCIPConverter instance."""
        return SCIPConverter()

    @pytest.fixture
    def mock_doc(self):
        """Create a mock SCIP Document with test symbols."""
        doc = scip_pb2.Document()
        doc.relative_path = "test.py"
        doc.language = "python"

        # Add a class symbol
        class_symbol = doc.symbols.add()
        class_symbol.symbol = "scip-python python test 1.0 test/TestClass#"
        class_symbol.documentation.append("Test class documentation")

        # Add a method with parameters
        method_symbol = doc.symbols.add()
        method_symbol.symbol = "scip-python python test 1.0 test/TestClass#test_method()."
        method_symbol.documentation.append("Test method documentation")

        # Add method parameters
        param1 = doc.symbols.add()
        param1.symbol = "scip-python python test 1.0 test/TestClass#test_method().(self)"

        param2 = doc.symbols.add()
        param2.symbol = "scip-python python test 1.0 test/TestClass#test_method().(arg1)"

        param3 = doc.symbols.add()
        param3.symbol = "scip-python python test 1.0 test/TestClass#test_method().(arg2)"

        # Add a function with no parameters
        func_symbol = doc.symbols.add()
        func_symbol.symbol = "scip-python python test 1.0 test/no_params()."
        func_symbol.documentation.append("Function with no parameters")

        # Add a function with one parameter
        func2_symbol = doc.symbols.add()
        func2_symbol.symbol = "scip-python python test 1.0 test/with_param()."

        func2_param = doc.symbols.add()
        func2_param.symbol = "scip-python python test 1.0 test/with_param().(data)"

        # Add occurrences with definition markers
        occ1 = doc.occurrences.add()
        occ1.symbol = "scip-python python test 1.0 test/TestClass#"
        occ1.range.extend([0, 0, 9])
        occ1.symbol_roles = scip_pb2.SymbolRole.Definition

        occ2 = doc.occurrences.add()
        occ2.symbol = "scip-python python test 1.0 test/TestClass#test_method()."
        occ2.range.extend([4, 4, 15])  # 0-indexed: line 4 -> 1-indexed: line 5
        occ2.symbol_roles = scip_pb2.SymbolRole.Definition

        occ3 = doc.occurrences.add()
        occ3.symbol = "scip-python python test 1.0 test/no_params()."
        occ3.range.extend([10, 0, 9])
        occ3.symbol_roles = scip_pb2.SymbolRole.Definition

        occ4 = doc.occurrences.add()
        occ4.symbol = "scip-python python test 1.0 test/with_param()."
        occ4.range.extend([15, 0, 10])
        occ4.symbol_roles = scip_pb2.SymbolRole.Definition

        return doc

    def test_get_symbol_type_class(self, converter):
        """Should identify class symbols."""
        symbol = "scip-python python test 1.0 module/MyClass#"
        assert converter._get_symbol_type(symbol) == "class"

    def test_get_symbol_type_method(self, converter):
        """Should identify method symbols."""
        symbol = "scip-python python test 1.0 module/MyClass#method()."
        assert converter._get_symbol_type(symbol) == "method"

    def test_get_symbol_type_function(self, converter):
        """Should identify function symbols."""
        symbol = "scip-python python test 1.0 module/my_function()."
        assert converter._get_symbol_type(symbol) == "function"

    def test_get_symbol_type_parameter(self, converter):
        """Should identify parameter symbols."""
        symbol = "scip-python python test 1.0 module/func().(param)"
        assert converter._get_symbol_type(symbol) == "parameter"

    def test_get_symbol_type_module(self, converter):
        """Should identify module symbols."""
        symbol = "scip-python python test 1.0 module/__init__:"
        assert converter._get_symbol_type(symbol) == "module"

    def test_extract_name_class(self, converter):
        """Should extract class name correctly."""
        symbol = "scip-python python test 1.0 module/Calculator#"
        assert converter._extract_name(symbol) == "Calculator"

    def test_extract_name_method(self, converter):
        """Should extract method name correctly."""
        symbol = "scip-python python test 1.0 module/Class#add()."
        assert converter._extract_name(symbol) == "add"

    def test_extract_name_function(self, converter):
        """Should extract function name correctly."""
        symbol = "scip-python python test 1.0 module/helper_function()."
        assert converter._extract_name(symbol) == "helper_function"

    def test_extract_name_private_method(self, converter):
        """Should extract private method name correctly."""
        symbol = "scip-python python test 1.0 module/Class#_private()."
        assert converter._extract_name(symbol) == "_private"

    def test_is_private_detects_private_method(self, converter):
        """Should detect private methods by leading underscore."""
        symbol = "scip-python python test 1.0 module/Class#_private()."
        assert converter._is_private(symbol) is True

    def test_is_private_detects_public_method(self, converter):
        """Should detect public methods."""
        symbol = "scip-python python test 1.0 module/Class#public()."
        assert converter._is_private(symbol) is False

    def test_is_private_ignores_dunder_methods(self, converter):
        """Should not treat __dunder__ methods as private."""
        symbol = "scip-python python test 1.0 module/Class#__init__()."
        assert converter._is_private(symbol) is False

    def test_extract_args_with_multiple_params(self, converter, mock_doc):
        """Should extract all parameters in order."""
        func_symbol = "scip-python python test 1.0 test/TestClass#test_method()."
        args = converter._extract_args(func_symbol, mock_doc)
        assert args == ["self", "arg1", "arg2"]

    def test_extract_args_with_no_params(self, converter, mock_doc):
        """Should return empty list for parameterless functions."""
        func_symbol = "scip-python python test 1.0 test/no_params()."
        args = converter._extract_args(func_symbol, mock_doc)
        assert args == []

    def test_extract_args_with_single_param(self, converter, mock_doc):
        """Should extract single parameter."""
        func_symbol = "scip-python python test 1.0 test/with_param()."
        args = converter._extract_args(func_symbol, mock_doc)
        assert args == ["data"]

    def test_convert_function_has_correct_arity(self, converter, mock_doc):
        """Should calculate arity correctly from extracted args."""
        # Get the method symbol
        method_symbol = None
        for sym in mock_doc.symbols:
            if sym.symbol == "scip-python python test 1.0 test/TestClass#test_method().":
                method_symbol = sym
                break

        assert method_symbol is not None
        symbol_map = {}
        func_data = converter._convert_function(method_symbol, mock_doc, symbol_map)

        assert func_data["name"] == "test_method"
        assert func_data["arity"] == 3
        assert func_data["args"] == ["self", "arg1", "arg2"]

    def test_convert_function_with_no_args(self, converter, mock_doc):
        """Should handle functions with no parameters."""
        # Get the no-param function symbol
        func_symbol = None
        for sym in mock_doc.symbols:
            if sym.symbol == "scip-python python test 1.0 test/no_params().":
                func_symbol = sym
                break

        assert func_symbol is not None
        symbol_map = {}
        func_data = converter._convert_function(func_symbol, mock_doc, symbol_map)

        assert func_data["name"] == "no_params"
        assert func_data["arity"] == 0
        assert func_data["args"] == []

    def test_get_definition_line(self, converter, mock_doc):
        """Should extract correct line number from occurrences."""
        symbol = "scip-python python test 1.0 test/TestClass#test_method()."
        line = converter._get_definition_line(symbol, mock_doc)
        assert line == 5

    def test_get_definition_line_fallback(self, converter, mock_doc):
        """Should return 1 if no definition occurrence found."""
        symbol = "scip-python python test 1.0 test/NonExistent#method()."
        line = converter._get_definition_line(symbol, mock_doc)
        assert line == 1
