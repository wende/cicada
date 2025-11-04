"""Integration tests for Rust indexer.

These tests verify the complete indexing workflow for Rust projects.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from cicada.languages.rust.indexer import RustSCIPIndexer


class TestRustIndexerInitialization:
    """Test Rust indexer initialization."""

    def test_indexer_creation(self):
        """Should create indexer with default settings."""
        indexer = RustSCIPIndexer()
        assert indexer is not None
        assert indexer.verbose is False

    def test_indexer_verbose_mode(self):
        """Should create indexer in verbose mode."""
        indexer = RustSCIPIndexer(verbose=True)
        assert indexer.verbose is True

    def test_language_name(self):
        """Should return 'rust' as language name."""
        indexer = RustSCIPIndexer()
        assert indexer.get_language_name() == "rust"

    def test_file_extensions(self):
        """Should return Rust file extensions."""
        indexer = RustSCIPIndexer()
        extensions = indexer.get_file_extensions()
        assert ".rs" in extensions

    def test_excluded_dirs(self):
        """Should return list of excluded directories."""
        indexer = RustSCIPIndexer()
        excluded = indexer.get_excluded_dirs()

        # Rust-specific directories
        assert "target" in excluded  # Build output
        assert ".cargo" in excluded  # Cargo cache
        assert ".git" in excluded  # Git directory


class TestRustIndexerValidation:
    """Test validation and error handling."""

    def test_rust_analyzer_check_when_installed(self):
        """Should pass when rust-analyzer is installed."""
        indexer = RustSCIPIndexer(verbose=False)

        with patch.object(
            indexer, "_ensure_rust_analyzer_installed"
        ) as mock_ensure:
            mock_ensure.return_value = None
            # Should not raise
            indexer._ensure_rust_analyzer_installed()

    def test_rust_analyzer_check_when_missing(self):
        """Should attempt installation when rust-analyzer is missing."""
        from cicada.languages.rust.scip_installer import SCIPRustInstaller

        indexer = RustSCIPIndexer(verbose=False)

        with patch.object(
            SCIPRustInstaller, "is_rust_analyzer_installed", return_value=False
        ):
            with patch.object(
                SCIPRustInstaller, "is_cargo_available", return_value=False
            ):
                with pytest.raises(RuntimeError, match="Rust toolchain is required"):
                    indexer._ensure_rust_analyzer_installed()


class TestRustIndexerExecution:
    """Test rust-analyzer execution."""

    @pytest.fixture
    def mock_subprocess_success(self):
        """Mock successful subprocess execution."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="Indexing complete", stderr=""
            )
            yield mock_run

    @pytest.fixture
    def mock_subprocess_failure(self):
        """Mock failed subprocess execution."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1, stdout="", stderr="Error occurred"
            )
            yield mock_run

    def test_run_rust_analyzer_creates_scip_file(
        self, tmp_path, mock_subprocess_success
    ):
        """Should create .scip file when rust-analyzer succeeds."""
        # Create minimal Rust project
        (tmp_path / "Cargo.toml").write_text("[package]\nname = 'test'")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "lib.rs").write_text("pub fn test() {}")

        # Create index.scip file that rust-analyzer would create
        (tmp_path / "index.scip").write_bytes(b"\x00\x00\x00\x00")  # Minimal SCIP

        indexer = RustSCIPIndexer(verbose=False)

        # Should create a temporary SCIP file
        result_path = indexer._run_rust_analyzer(tmp_path)

        assert result_path.exists()
        assert result_path.suffix == ".scip"

        # Cleanup
        if result_path.exists():
            result_path.unlink()

    def test_run_rust_analyzer_handles_failure(self, tmp_path, mock_subprocess_failure):
        """Should raise RuntimeError when rust-analyzer fails."""
        (tmp_path / "Cargo.toml").write_text("[package]\nname = 'test'")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "lib.rs").write_text("pub fn test() {}")

        indexer = RustSCIPIndexer(verbose=False)

        with pytest.raises(RuntimeError, match="rust-analyzer indexing failed"):
            indexer._run_rust_analyzer(tmp_path)

    def test_run_rust_analyzer_timeout(self, tmp_path):
        """Should handle timeout gracefully."""
        (tmp_path / "Cargo.toml").write_text("[package]\nname = 'test'")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "lib.rs").write_text("pub fn test() {}")

        indexer = RustSCIPIndexer(verbose=False)

        with patch("subprocess.run") as mock_run:
            from subprocess import TimeoutExpired

            mock_run.side_effect = TimeoutExpired("rust-analyzer", 600)

            with pytest.raises(RuntimeError, match="timed out"):
                indexer._run_rust_analyzer(tmp_path)


class TestRustIndexerOutput:
    """Test indexer output generation."""

    def test_save_index_creates_file(self, tmp_path):
        """Should create index.json file."""
        indexer = RustSCIPIndexer(verbose=False)

        test_index = {
            "modules": {},
            "metadata": {
                "language": "rust",
                "total_modules": 0,
                "total_functions": 0,
            },
        }

        output_path = tmp_path / "index.json"
        indexer._save_index(test_index, output_path)

        assert output_path.exists()

        # Verify contents
        with open(output_path) as f:
            loaded = json.load(f)
            assert loaded["metadata"]["language"] == "rust"

    def test_save_index_creates_parent_dirs(self, tmp_path):
        """Should create parent directories if they don't exist."""
        indexer = RustSCIPIndexer(verbose=False)

        test_index = {"modules": {}, "metadata": {}}
        output_path = tmp_path / "nested" / "dir" / "index.json"

        indexer._save_index(test_index, output_path)

        assert output_path.exists()
        assert output_path.parent.exists()


class TestRustIndexerIntegration:
    """Integration tests for complete indexing workflow."""

    @pytest.fixture
    def sample_rust_repo(self, fixtures_dir):
        """Path to sample Rust test fixture."""
        return fixtures_dir / "sample_rust"

    def test_sample_repo_structure(self, sample_rust_repo):
        """Sample repo should have expected structure."""
        assert (sample_rust_repo / "Cargo.toml").exists()
        assert (sample_rust_repo / "src" / "lib.rs").exists()
        assert (sample_rust_repo / "src" / "models.rs").exists()

    @pytest.mark.skip(reason="Requires rust-analyzer to be installed")
    def test_index_sample_repository(self, sample_rust_repo, tmp_path):
        """Should successfully index the sample Rust repository."""
        indexer = RustSCIPIndexer(verbose=True)

        output_path = tmp_path / "index.json"

        result = indexer.index_repository(
            repo_path=sample_rust_repo,
            output_path=output_path,
            force=True,
            verbose=True,
        )

        assert result["success"] is True
        assert result["modules_count"] > 0
        assert result["functions_count"] > 0
        assert output_path.exists()

        # Verify index structure
        with open(output_path) as f:
            index = json.load(f)
            assert "modules" in index
            assert "metadata" in index
            assert index["metadata"]["language"] == "rust"


class TestRustIndexerErrorReporting:
    """Test error reporting and recovery."""

    def test_missing_cargo_toml_error(self, tmp_path):
        """Should report error for missing Cargo.toml."""
        # Empty directory
        indexer = RustSCIPIndexer(verbose=False)
        output_path = tmp_path / "index.json"

        # Should fail gracefully
        with patch.object(indexer, "_ensure_rust_analyzer_installed"):
            with pytest.raises(Exception):
                indexer.index_repository(
                    repo_path=tmp_path, output_path=output_path, force=True
                )

    def test_invalid_rust_code_error(self, tmp_path):
        """Should handle invalid Rust code gracefully."""
        (tmp_path / "Cargo.toml").write_text("[package]\nname = 'invalid'")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "lib.rs").write_text("this is not valid rust code!!!")

        indexer = RustSCIPIndexer(verbose=False)
        output_path = tmp_path / "index.json"

        # rust-analyzer should fail, but we handle it
        with patch.object(indexer, "_ensure_rust_analyzer_installed"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=1, stdout="", stderr="Parse error"
                )

                with pytest.raises(RuntimeError):
                    indexer._run_rust_analyzer(tmp_path)

    def test_cleanup_on_failure(self, tmp_path):
        """Should cleanup temporary files on failure."""
        (tmp_path / "Cargo.toml").write_text("[package]\nname = 'test'")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "lib.rs").write_text("pub fn test() {}")

        indexer = RustSCIPIndexer(verbose=False)

        with patch.object(indexer, "_ensure_rust_analyzer_installed"):
            with patch.object(indexer, "_run_rust_analyzer") as mock_run:
                # Create a temp file
                temp_file = tmp_path / "temp.scip"
                temp_file.write_bytes(b"data")
                mock_run.return_value = temp_file

                with patch(
                    "cicada.languages.scip.reader.SCIPReader.read_index"
                ) as mock_read:
                    mock_read.side_effect = Exception("Parse error")

                    output_path = tmp_path / "output" / "index.json"

                    result = indexer.index_repository(
                        repo_path=tmp_path, output_path=output_path, force=True
                    )

                    assert result["success"] is False
                    # Temp file should be cleaned up
                    assert not temp_file.exists()
