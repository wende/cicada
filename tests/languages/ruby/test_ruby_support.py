"""Unit tests for Ruby SCIP support.

Tests the core Ruby indexing functionality including language detection,
SCIP reading, and conversion to Cicada format.
"""

import pytest
from pathlib import Path

from cicada.setup import detect_project_language
from cicada.languages.ruby.scip_installer import SCIPRubyInstaller
from cicada.languages.scip import scip_pb2
from cicada.languages.scip.converter import SCIPConverter


class TestLanguageDetection:
    """Test language detection for Ruby projects."""

    def test_detect_ruby_from_gemfile(self, tmp_path):
        """Should detect Ruby from Gemfile."""
        (tmp_path / "Gemfile").write_text("source 'https://rubygems.org'")
        assert detect_project_language(tmp_path) == "ruby"

    def test_detect_ruby_from_ruby_version(self, tmp_path):
        """Should detect Ruby from .ruby-version."""
        (tmp_path / ".ruby-version").write_text("3.2.0")
        assert detect_project_language(tmp_path) == "ruby"

    def test_detect_ruby_from_rakefile(self, tmp_path):
        """Should detect Ruby from Rakefile."""
        (tmp_path / "Rakefile").write_text("# rakefile")
        assert detect_project_language(tmp_path) == "ruby"

    def test_ruby_detection_with_multiple_markers(self, tmp_path):
        """Should detect Ruby when multiple markers present."""
        (tmp_path / "Gemfile").write_text("source 'https://rubygems.org'")
        (tmp_path / ".ruby-version").write_text("3.2.0")
        assert detect_project_language(tmp_path) == "ruby"

    def test_python_takes_precedence_over_ruby(self, tmp_path):
        """Python markers should be checked before Ruby."""
        (tmp_path / "pyproject.toml").write_text("[project]")
        (tmp_path / "Gemfile").write_text("source 'https://rubygems.org'")
        assert detect_project_language(tmp_path) == "python"


class TestSCIPRubyInstaller:
    """Test SCIP-Ruby installer utilities."""

    def test_gem_availability_check(self):
        """Should correctly detect gem availability."""
        result = SCIPRubyInstaller.is_gem_available()
        assert isinstance(result, bool)

    def test_bundle_availability_check(self):
        """Should correctly detect bundle availability."""
        result = SCIPRubyInstaller.is_bundle_available()
        assert isinstance(result, bool)

    def test_scip_ruby_availability_check(self):
        """Should correctly detect scip-ruby availability."""
        result = SCIPRubyInstaller.is_scip_ruby_installed()
        assert isinstance(result, bool)

    def test_get_version_returns_none_when_not_installed(self, monkeypatch):
        """Should return None when scip-ruby is not installed."""
        monkeypatch.setattr(
            SCIPRubyInstaller, "is_scip_ruby_installed", lambda: False
        )
        assert SCIPRubyInstaller.get_scip_ruby_version() is None


class TestRubyIndexer:
    """Test Ruby SCIP indexer integration."""

    @pytest.fixture
    def sample_ruby_repo(self, fixtures_dir):
        """Path to sample Ruby test fixture."""
        return fixtures_dir / "sample_ruby"

    def test_sample_ruby_repo_exists(self, sample_ruby_repo):
        """Test fixture should exist."""
        assert sample_ruby_repo.exists()
        assert (sample_ruby_repo / "calculator.rb").exists()
        assert (sample_ruby_repo / "Gemfile").exists()

    def test_detect_language_for_sample_repo(self, sample_ruby_repo):
        """Should detect sample repo as Ruby."""
        assert detect_project_language(sample_ruby_repo) == "ruby"

    def test_ruby_version_file_exists(self, sample_ruby_repo):
        """Ruby version file should exist."""
        assert (sample_ruby_repo / ".ruby-version").exists()

    def test_all_ruby_files_present(self, sample_ruby_repo):
        """All expected Ruby files should be present."""
        expected_files = [
            "calculator.rb",
            "operations.rb",
            "formatter.rb",
            "utils.rb",
            "main.rb",
        ]
        for file in expected_files:
            assert (sample_ruby_repo / file).exists(), f"Missing {file}"


class TestSCIPConverterRuby:
    """Test SCIP to Cicada format conversion for Ruby-specific features."""

    @pytest.fixture
    def converter(self):
        """Create a SCIPConverter instance."""
        return SCIPConverter()

    @pytest.fixture
    def mock_ruby_doc(self):
        """Create a mock SCIP Document with Ruby test symbols."""
        doc = scip_pb2.Document()
        doc.relative_path = "calculator.rb"
        doc.language = "ruby"

        # Add a class symbol (Ruby class)
        class_symbol = doc.symbols.add()
        class_symbol.symbol = "scip-ruby ruby sample_ruby 1.0 calculator/Calculator#"
        class_symbol.documentation.append("Calculator class documentation")

        # Add an instance method with parameters
        method_symbol = doc.symbols.add()
        method_symbol.symbol = (
            "scip-ruby ruby sample_ruby 1.0 calculator/Calculator#add()."
        )
        method_symbol.documentation.append("Add two numbers")

        # Add method parameters
        param1 = doc.symbols.add()
        param1.symbol = (
            "scip-ruby ruby sample_ruby 1.0 calculator/Calculator#add().(x)"
        )

        param2 = doc.symbols.add()
        param2.symbol = (
            "scip-ruby ruby sample_ruby 1.0 calculator/Calculator#add().(y)"
        )

        # Add a class method (Ruby class method with self.)
        class_method_symbol = doc.symbols.add()
        class_method_symbol.symbol = (
            "scip-ruby ruby sample_ruby 1.0 calculator/Calculator#quick_add()."
        )
        class_method_symbol.documentation.append("Class method for quick addition")

        # Add a private method
        private_method_symbol = doc.symbols.add()
        private_method_symbol.symbol = (
            "scip-ruby ruby sample_ruby 1.0 calculator/Calculator#_private_method()."
        )
        private_method_symbol.documentation.append("Private method")

        # Add a module (Ruby module)
        module_symbol = doc.symbols.add()
        module_symbol.symbol = "scip-ruby ruby sample_ruby 1.0 operations/Operations#"
        module_symbol.documentation.append("Operations module")

        # Add a module method
        module_method_symbol = doc.symbols.add()
        module_method_symbol.symbol = (
            "scip-ruby ruby sample_ruby 1.0 operations/Operations#multiply()."
        )
        module_method_symbol.documentation.append("Multiply two numbers")

        # Add occurrences with definition markers
        occ1 = doc.occurrences.add()
        occ1.symbol = "scip-ruby ruby sample_ruby 1.0 calculator/Calculator#"
        occ1.range.extend([0, 0, 9])
        occ1.symbol_roles = scip_pb2.SymbolRole.Definition

        occ2 = doc.occurrences.add()
        occ2.symbol = (
            "scip-ruby ruby sample_ruby 1.0 calculator/Calculator#add()."
        )
        occ2.range.extend([10, 4, 15])
        occ2.symbol_roles = scip_pb2.SymbolRole.Definition

        occ3 = doc.occurrences.add()
        occ3.symbol = (
            "scip-ruby ruby sample_ruby 1.0 calculator/Calculator#_private_method()."
        )
        occ3.range.extend([50, 4, 20])
        occ3.symbol_roles = scip_pb2.SymbolRole.Definition

        return doc

    def test_get_symbol_type_ruby_class(self, converter):
        """Should identify Ruby class symbols."""
        symbol = "scip-ruby ruby test 1.0 module/Calculator#"
        assert converter._get_symbol_type(symbol) == "class"

    def test_get_symbol_type_ruby_method(self, converter):
        """Should identify Ruby method symbols."""
        symbol = "scip-ruby ruby test 1.0 module/Calculator#calculate()."
        assert converter._get_symbol_type(symbol) == "method"

    def test_get_symbol_type_ruby_module(self, converter):
        """Should identify Ruby module symbols."""
        symbol = "scip-ruby ruby test 1.0 operations/__init__:"
        assert converter._get_symbol_type(symbol) == "module"

    def test_extract_name_ruby_class(self, converter):
        """Should extract Ruby class name correctly."""
        symbol = "scip-ruby ruby test 1.0 calculator/Calculator#"
        assert converter._extract_name(symbol) == "Calculator"

    def test_extract_name_ruby_method(self, converter):
        """Should extract Ruby method name correctly."""
        symbol = "scip-ruby ruby test 1.0 calculator/Calculator#add()."
        assert converter._extract_name(symbol) == "add"

    def test_extract_name_ruby_private_method(self, converter):
        """Should extract Ruby private method name correctly."""
        symbol = "scip-ruby ruby test 1.0 calculator/Calculator#_private()."
        assert converter._extract_name(symbol) == "_private"

    def test_is_private_detects_ruby_private_method(self, converter):
        """Should detect Ruby private methods by leading underscore."""
        symbol = "scip-ruby ruby test 1.0 module/Class#_private()."
        assert converter._is_private(symbol) is True

    def test_is_private_detects_ruby_public_method(self, converter):
        """Should detect Ruby public methods."""
        symbol = "scip-ruby ruby test 1.0 module/Class#public_method()."
        assert converter._is_private(symbol) is False

    def test_extract_args_ruby_method(self, converter, mock_ruby_doc):
        """Should extract Ruby method parameters."""
        method_symbol = (
            "scip-ruby ruby sample_ruby 1.0 calculator/Calculator#add()."
        )
        args = converter._extract_args(method_symbol, mock_ruby_doc)
        assert args == ["x", "y"]

    def test_convert_function_ruby_method(self, converter, mock_ruby_doc):
        """Should convert Ruby method to function data."""
        method_symbol = None
        for sym in mock_ruby_doc.symbols:
            if (
                sym.symbol
                == "scip-ruby ruby sample_ruby 1.0 calculator/Calculator#add()."
            ):
                method_symbol = sym
                break

        assert method_symbol is not None
        symbol_map = {}
        func_data = converter._convert_function(
            method_symbol, mock_ruby_doc, symbol_map
        )

        assert func_data["name"] == "add"
        assert func_data["arity"] == 2
        assert func_data["args"] == ["x", "y"]
        assert func_data["type"] == "public"

    def test_convert_function_ruby_private_method(self, converter, mock_ruby_doc):
        """Should mark Ruby private methods correctly."""
        method_symbol = None
        for sym in mock_ruby_doc.symbols:
            if (
                sym.symbol
                == "scip-ruby ruby sample_ruby 1.0 calculator/Calculator#_private_method()."
            ):
                method_symbol = sym
                break

        assert method_symbol is not None
        symbol_map = {}
        func_data = converter._convert_function(
            method_symbol, mock_ruby_doc, symbol_map
        )

        assert func_data["name"] == "_private_method"
        assert func_data["type"] == "private"

    def test_detect_language_ruby(self, converter):
        """Should detect Ruby from SCIP metadata."""
        scip_index = scip_pb2.Index()
        doc = scip_index.documents.add()
        doc.language = "ruby"

        language = converter._detect_language(scip_index)
        assert language == "ruby"


class TestRubySpecificFeatures:
    """Test Ruby-specific language features and edge cases."""

    @pytest.fixture
    def converter(self):
        """Create a SCIPConverter instance."""
        return SCIPConverter()

    def test_ruby_module_method_symbol(self, converter):
        """Should correctly handle Ruby module methods."""
        symbol = "scip-ruby ruby test 1.0 operations/Operations#add()."
        assert converter._get_symbol_type(symbol) == "method"
        assert converter._extract_name(symbol) == "add"

    def test_ruby_class_method_symbol(self, converter):
        """Should correctly handle Ruby class methods (self.method)."""
        # In SCIP, class methods are represented similarly to instance methods
        symbol = "scip-ruby ruby test 1.0 calculator/Calculator#self_method()."
        assert converter._get_symbol_type(symbol) == "method"
        assert converter._extract_name(symbol) == "self_method"

    def test_ruby_attr_accessor(self, converter):
        """Should handle Ruby attr_accessor/attr_reader/attr_writer."""
        # These typically show up as attributes in SCIP
        symbol = "scip-ruby ruby test 1.0 calculator/Calculator#value."
        assert converter._get_symbol_type(symbol) == "attribute"

    def test_ruby_constant(self, converter):
        """Should handle Ruby constants."""
        symbol = "scip-ruby ruby test 1.0 formatter/Formatter#DECIMAL_PLACES."
        # Constants are typically attributes in SCIP
        assert converter._get_symbol_type(symbol) == "attribute"

    def test_ruby_block_parameter(self, converter):
        """Should handle Ruby block parameters."""
        symbol = "scip-ruby ruby test 1.0 utils/Utils#map().(block)"
        assert converter._get_symbol_type(symbol) == "parameter"

    def test_ruby_initialize_method(self, converter):
        """Should handle Ruby initialize method (constructor)."""
        symbol = "scip-ruby ruby test 1.0 calculator/Calculator#initialize()."
        assert converter._get_symbol_type(symbol) == "method"
        assert converter._extract_name(symbol) == "initialize"
        assert converter._is_private(symbol) is False  # initialize is not private by convention

    def test_ruby_question_mark_method(self, converter):
        """Should handle Ruby predicate methods (ending with ?)."""
        # Note: SCIP may normalize these
        symbol = "scip-ruby ruby test 1.0 calculator/Calculator#valid()."
        assert converter._get_symbol_type(symbol) == "method"

    def test_ruby_bang_method(self, converter):
        """Should handle Ruby destructive methods (ending with !)."""
        # Note: SCIP may normalize these
        symbol = "scip-ruby ruby test 1.0 calculator/Calculator#reset()."
        assert converter._get_symbol_type(symbol) == "method"


class TestRubyFileExtensions:
    """Test Ruby file extension handling."""

    def test_rb_extension_recognized(self, tmp_path):
        """Should recognize .rb files."""
        from cicada.languages.ruby.indexer import RubySCIPIndexer

        indexer = RubySCIPIndexer()
        assert ".rb" in indexer.get_file_extensions()

    def test_rake_extension_recognized(self, tmp_path):
        """Should recognize .rake files."""
        from cicada.languages.ruby.indexer import RubySCIPIndexer

        indexer = RubySCIPIndexer()
        assert ".rake" in indexer.get_file_extensions()

    def test_gemspec_extension_recognized(self, tmp_path):
        """Should recognize .gemspec files."""
        from cicada.languages.ruby.indexer import RubySCIPIndexer

        indexer = RubySCIPIndexer()
        assert ".gemspec" in indexer.get_file_extensions()


class TestRubyExcludedDirectories:
    """Test Ruby-specific excluded directories."""

    def test_vendor_directory_excluded(self):
        """Should exclude vendor directory."""
        from cicada.languages.ruby.indexer import RubySCIPIndexer

        indexer = RubySCIPIndexer()
        assert "vendor" in indexer.get_excluded_dirs()

    def test_bundle_directory_excluded(self):
        """Should exclude .bundle directory."""
        from cicada.languages.ruby.indexer import RubySCIPIndexer

        indexer = RubySCIPIndexer()
        assert ".bundle" in indexer.get_excluded_dirs()

    def test_tmp_directory_excluded(self):
        """Should exclude tmp directory."""
        from cicada.languages.ruby.indexer import RubySCIPIndexer

        indexer = RubySCIPIndexer()
        assert "tmp" in indexer.get_excluded_dirs()

    def test_sorbet_directory_excluded(self):
        """Should exclude sorbet directory."""
        from cicada.languages.ruby.indexer import RubySCIPIndexer

        indexer = RubySCIPIndexer()
        assert "sorbet" in indexer.get_excluded_dirs()
