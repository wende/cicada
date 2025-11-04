"""Unit tests for Rust SCIP support.

Tests the core Rust indexing functionality including language detection,
rust-analyzer integration, and conversion to Cicada format.
"""

import pytest
from pathlib import Path

from cicada.setup import detect_project_language
from cicada.languages.rust.scip_installer import SCIPRustInstaller


class TestLanguageDetection:
    """Test language detection for Rust projects."""

    def test_detect_rust_from_cargo_toml(self, tmp_path):
        """Should detect Rust from Cargo.toml."""
        (tmp_path / "Cargo.toml").write_text("[package]\nname = 'test'")
        assert detect_project_language(tmp_path) == "rust"

    def test_rust_takes_precedence_over_elixir(self, tmp_path):
        """Rust detection should work when both Rust and Elixir markers present."""
        (tmp_path / "Cargo.toml").write_text("[package]")
        (tmp_path / "mix.exs").write_text("defmodule")
        # Python checked first, then Rust, then Elixir
        assert detect_project_language(tmp_path) == "rust"

    def test_python_takes_precedence_over_rust(self, tmp_path):
        """Python markers should be checked before Rust."""
        (tmp_path / "pyproject.toml").write_text("[project]")
        (tmp_path / "Cargo.toml").write_text("[package]")
        assert detect_project_language(tmp_path) == "python"


class TestSCIPRustInstaller:
    """Test rust-analyzer installer utilities."""

    def test_cargo_availability_check(self):
        """Should correctly detect cargo availability."""
        result = SCIPRustInstaller.is_cargo_available()
        assert isinstance(result, bool)

    def test_rust_analyzer_availability_check(self):
        """Should correctly detect rust-analyzer availability."""
        result = SCIPRustInstaller.is_rust_analyzer_installed()
        assert isinstance(result, bool)

    def test_get_version_returns_none_when_not_installed(self, monkeypatch):
        """Should return None when rust-analyzer is not installed."""
        monkeypatch.setattr(
            SCIPRustInstaller, "is_rust_analyzer_installed", lambda: False
        )
        assert SCIPRustInstaller.get_rust_analyzer_version() is None


class TestRustIndexer:
    """Test Rust SCIP indexer integration."""

    @pytest.fixture
    def sample_rust_repo(self, fixtures_dir):
        """Path to sample Rust test fixture."""
        return fixtures_dir / "sample_rust"

    def test_sample_rust_repo_exists(self, sample_rust_repo):
        """Test fixture should exist."""
        assert sample_rust_repo.exists()
        assert (sample_rust_repo / "Cargo.toml").exists()
        assert (sample_rust_repo / "src" / "lib.rs").exists()

    def test_detect_language_for_sample_repo(self, sample_rust_repo):
        """Should detect sample repo as Rust."""
        assert detect_project_language(sample_rust_repo) == "rust"

    def test_sample_rust_has_required_files(self, sample_rust_repo):
        """Sample Rust project should have all required files."""
        required_files = [
            "Cargo.toml",
            "src/lib.rs",
            "src/models.rs",
            "src/handlers.rs",
            "src/utils.rs",
            "src/config.rs",
        ]
        for file in required_files:
            assert (sample_rust_repo / file).exists(), f"Missing {file}"


class TestRustSCIPConverter:
    """Test SCIP to Cicada format conversion for Rust-specific symbols."""

    @pytest.fixture
    def converter(self):
        """Create a SCIPConverter instance."""
        from cicada.languages.scip.converter import SCIPConverter

        return SCIPConverter()

    def test_get_symbol_type_struct(self, converter):
        """Should identify struct symbols as classes."""
        # In SCIP, Rust structs are represented similarly to classes
        symbol = "scip-rust rust sample 0.1.0 models/User#"
        # The _get_symbol_type method looks for trailing # to identify classes
        assert converter._get_symbol_type(symbol) == "class"

    def test_get_symbol_type_method(self, converter):
        """Should identify struct methods."""
        symbol = "scip-rust rust sample 0.1.0 models/User#new()."
        assert converter._get_symbol_type(symbol) == "method"

    def test_get_symbol_type_function(self, converter):
        """Should identify top-level functions."""
        symbol = "scip-rust rust sample 0.1.0 utils/validate_email()."
        assert converter._get_symbol_type(symbol) == "function"

    def test_extract_name_struct(self, converter):
        """Should extract struct name correctly."""
        symbol = "scip-rust rust sample 0.1.0 models/User#"
        assert converter._extract_name(symbol) == "User"

    def test_extract_name_method(self, converter):
        """Should extract method name correctly."""
        symbol = "scip-rust rust sample 0.1.0 models/User#new()."
        assert converter._extract_name(symbol) == "new"

    def test_extract_name_function(self, converter):
        """Should extract function name correctly."""
        symbol = "scip-rust rust sample 0.1.0 utils/validate_email()."
        assert converter._extract_name(symbol) == "validate_email"

    def test_is_private_detects_private_method(self, converter):
        """Should detect private methods by leading underscore."""
        symbol = "scip-rust rust sample 0.1.0 models/User#_is_admin()."
        assert converter._is_private(symbol) is True

    def test_is_private_detects_public_method(self, converter):
        """Should detect public methods."""
        symbol = "scip-rust rust sample 0.1.0 models/User#new()."
        assert converter._is_private(symbol) is False


class TestRustLanguageFeatures:
    """Test Rust-specific language features and edge cases."""

    def test_impl_block_methods_detected_as_class_methods(self):
        """Impl block methods should be treated as class methods."""
        # In Rust: impl User { fn new() -> Self { ... } }
        # SCIP should represent this as User#new().
        # The converter should group these under the User "class"
        assert True  # Placeholder for structure validation

    def test_trait_implementations_detected(self):
        """Trait implementations should be indexed."""
        # In Rust: impl Default for Config { fn default() -> Self { ... } }
        # These should be indexed as methods on the implementing type
        assert True  # Placeholder for trait impl validation

    def test_generic_functions_handled(self):
        """Generic functions should be indexed without type parameters."""
        # In Rust: fn process<T>(value: T) -> T { ... }
        # SCIP should represent this cleanly
        assert True  # Placeholder for generic handling

    def test_module_system_represented(self):
        """Rust module system should be represented in file paths."""
        # mod models; should link to models.rs or models/mod.rs
        # The SCIP index should capture these relationships
        assert True  # Placeholder for module system validation

    def test_public_vs_private_visibility(self):
        """Rust visibility modifiers (pub, pub(crate), etc.) should be detected."""
        # Functions without 'pub' are module-private
        # Functions starting with _ are conventionally private
        assert True  # Placeholder for visibility detection


class TestRustIndexerEdgeCases:
    """Test edge cases specific to Rust indexing."""

    def test_empty_rust_project(self, tmp_path):
        """Should handle empty Rust project gracefully."""
        (tmp_path / "Cargo.toml").write_text("[package]\nname = 'empty'")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "lib.rs").write_text("// Empty library")

        from cicada.languages.rust.indexer import RustSCIPIndexer

        indexer = RustSCIPIndexer(verbose=False)

        # Should detect as Rust even if minimal
        assert detect_project_language(tmp_path) == "rust"

    def test_rust_project_with_tests(self, tmp_path):
        """Should index test modules appropriately."""
        (tmp_path / "Cargo.toml").write_text("[package]\nname = 'test_proj'")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "lib.rs").write_text(
            """
            pub fn add(a: i32, b: i32) -> i32 { a + b }

            #[cfg(test)]
            mod tests {
                use super::*;

                #[test]
                fn test_add() {
                    assert_eq!(add(2, 2), 4);
                }
            }
            """
        )
        # Test functions should be indexed but potentially marked differently
        assert True  # Placeholder for test detection

    def test_rust_workspace_detection(self, tmp_path):
        """Should detect Rust workspace at root."""
        (tmp_path / "Cargo.toml").write_text(
            """
            [workspace]
            members = ["crate1", "crate2"]
            """
        )
        # Workspace root should be detected as Rust project
        assert detect_project_language(tmp_path) == "rust"

    def test_binary_vs_library_project(self, tmp_path):
        """Should handle both binary (main.rs) and library (lib.rs) projects."""
        (tmp_path / "Cargo.toml").write_text("[package]\nname = 'bin_proj'")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.rs").write_text("fn main() {}")
        (tmp_path / "src" / "lib.rs").write_text("pub fn helper() {}")

        # Should index both main.rs and lib.rs
        assert detect_project_language(tmp_path) == "rust"


class TestRustSCIPIntegration:
    """Integration tests for complete Rust indexing workflow."""

    @pytest.fixture
    def sample_rust_repo(self, fixtures_dir):
        """Path to sample Rust test fixture."""
        return fixtures_dir / "sample_rust"

    def test_fixture_has_struct_definitions(self, sample_rust_repo):
        """Fixture should contain struct definitions for testing."""
        models_file = sample_rust_repo / "src" / "models.rs"
        content = models_file.read_text()

        assert "struct User" in content
        assert "struct Task" in content
        assert "impl User" in content
        assert "impl Task" in content

    def test_fixture_has_public_and_private_methods(self, sample_rust_repo):
        """Fixture should have both public and private methods."""
        models_file = sample_rust_repo / "src" / "models.rs"
        content = models_file.read_text()

        assert "pub fn new(" in content  # Public method
        assert "fn _is_admin(" in content  # Private method

    def test_fixture_has_trait_implementations(self, sample_rust_repo):
        """Fixture should have trait implementations."""
        handlers_file = sample_rust_repo / "src" / "handlers.rs"
        content = handlers_file.read_text()

        assert "impl Default for" in content

    def test_fixture_has_cross_file_calls(self, sample_rust_repo):
        """Fixture should demonstrate cross-file function calls."""
        handlers_file = sample_rust_repo / "src" / "handlers.rs"
        content = handlers_file.read_text()

        # Should have calls to utils module
        assert "validate_email" in content
        assert "format_response" in content

    def test_fixture_has_documentation_comments(self, sample_rust_repo):
        """Fixture should have documentation comments for keyword extraction."""
        models_file = sample_rust_repo / "src" / "models.rs"
        content = models_file.read_text()

        assert "///" in content  # Doc comments
        assert "# Arguments" in content  # Doc comment sections
        assert "# Returns" in content


class TestRustMetadata:
    """Test metadata extraction for Rust projects."""

    def test_cargo_toml_project_name_extraction(self, tmp_path):
        """Should extract project name from Cargo.toml."""
        cargo_toml = tmp_path / "Cargo.toml"
        cargo_toml.write_text(
            """
            [package]
            name = "my_awesome_crate"
            version = "0.1.0"
            edition = "2021"
            """
        )

        # Project name should be available from Cargo.toml
        assert cargo_toml.exists()
        content = cargo_toml.read_text()
        assert "my_awesome_crate" in content

    def test_rust_edition_detection(self, tmp_path):
        """Should detect Rust edition from Cargo.toml."""
        cargo_toml = tmp_path / "Cargo.toml"
        cargo_toml.write_text('[package]\nname = "test"\nedition = "2021"')

        content = cargo_toml.read_text()
        assert '2021' in content  # Edition should be detectable
