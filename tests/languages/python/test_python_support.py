"""Unit tests for Python SCIP support.

Tests the core Python indexing functionality including language detection,
SCIP reading, and conversion to Cicada format.
"""

import pytest

from cicada.setup import detect_project_language
from cicada.languages.python.scip_installer import SCIPPythonInstaller
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

    # Note: Tests for _extract_args, _convert_function, and _get_definition_line
    # were removed as these methods have been refactored in the SCIP converter.
    # The new implementation is tested in test_scip_converter.py
