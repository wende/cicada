"""Tests for Rust SCIP indexer."""

import json
import pytest
import subprocess
from unittest.mock import patch, Mock

from cicada.languages.rust.indexer import RustSCIPIndexer
from cicada.languages.scip import scip_pb2


class TestRustSCIPIndexer:
    """Test Rust SCIP indexer functionality."""

    @pytest.fixture
    def indexer(self):
        """Create a RustSCIPIndexer instance."""
        return RustSCIPIndexer(verbose=False)

    @pytest.fixture
    def verbose_indexer(self):
        """Create a verbose indexer."""
        return RustSCIPIndexer(verbose=True)

    def test_get_language_name(self, indexer):
        """Should return 'rust' as language name."""
        assert indexer.get_language_name() == "rust"

    def test_get_file_extensions(self, indexer):
        """Should return .rs extension."""
        extensions = indexer.get_file_extensions()
        assert extensions == [".rs"]

    def test_get_excluded_dirs(self, indexer):
        """Should return list of excluded directories."""
        excluded = indexer.get_excluded_dirs()

        assert "target" in excluded
        assert ".git" in excluded
        assert "vendor" in excluded

    def test_is_rust_analyzer_installed_when_present(self, indexer):
        """Should return True when rust-analyzer is in PATH."""
        with patch("shutil.which", return_value="/usr/bin/rust-analyzer"):
            assert indexer._is_rust_analyzer_installed() is True

    def test_is_rust_analyzer_installed_when_missing(self, indexer):
        """Should return False when rust-analyzer is not in PATH."""
        with patch("shutil.which", return_value=None):
            assert indexer._is_rust_analyzer_installed() is False

    def test_get_rust_analyzer_path_from_which(self, indexer):
        """Should return path from shutil.which."""
        with patch("shutil.which", return_value="/usr/local/bin/rust-analyzer"):
            assert indexer._get_rust_analyzer_path() == "/usr/local/bin/rust-analyzer"

    def test_get_rust_analyzer_path_returns_none_when_missing(self, indexer):
        """Should return None when rust-analyzer not found."""
        with patch("shutil.which", return_value=None):
            assert indexer._get_rust_analyzer_path() is None

    def test_ensure_rust_analyzer_raises_when_not_installed(self, indexer):
        """Should raise RuntimeError when rust-analyzer is not installed and auto-install fails."""
        with patch.object(indexer, "_is_rust_analyzer_installed", return_value=False):
            with patch(
                "cicada.languages.scip.installer.SCIPToolInstaller.try_install",
                return_value=None,
            ):
                with pytest.raises(RuntimeError) as exc_info:
                    indexer._ensure_rust_analyzer_installed()

                assert "rust-analyzer is required" in str(exc_info.value)
                assert "rustup component add rust-analyzer" in str(exc_info.value)

    def test_ensure_rust_analyzer_passes_when_installed(self, indexer):
        """Should not raise when rust-analyzer is installed."""
        with patch.object(indexer, "_is_rust_analyzer_installed", return_value=True):
            # Should not raise
            indexer._ensure_rust_analyzer_installed()

    def test_ensure_rust_analyzer_verbose_output(self, verbose_indexer, capsys):
        """Should print version info when verbose."""
        with patch.object(verbose_indexer, "_is_rust_analyzer_installed", return_value=True):
            with patch.object(verbose_indexer, "_get_rust_analyzer_version", return_value="1.0.0"):
                verbose_indexer._ensure_rust_analyzer_installed()

                captured = capsys.readouterr()
                assert "rust-analyzer 1.0.0" in captured.out

    def test_run_rust_analyzer_scip_success(self, indexer, tmp_path):
        """Should successfully run rust-analyzer scip command."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        (repo_path / "Cargo.toml").write_text('[package]\nname = "test"')

        # Create mock SCIP output
        mock_scip_content = scip_pb2.Index()
        mock_scip_content.metadata.version = 0

        with patch.object(
            indexer, "_get_rust_analyzer_path", return_value="/usr/bin/rust-analyzer"
        ):
            with patch("subprocess.run") as mock_run:
                mock_result = Mock()
                mock_result.returncode = 0
                mock_result.stderr = ""
                mock_run.return_value = mock_result

                with patch("tempfile.NamedTemporaryFile") as mock_temp:
                    scip_file_path = tmp_path / "test.scip"
                    mock_temp.return_value.__enter__.return_value.name = str(scip_file_path)

                    # Create the file to simulate rust-analyzer output
                    with open(scip_file_path, "wb") as f:
                        f.write(mock_scip_content.SerializeToString())

                    result_path = indexer._run_rust_analyzer_scip(repo_path)

                    assert result_path == scip_file_path
                    assert result_path.exists()

                    # Verify rust-analyzer was called with correct args
                    mock_run.assert_called_once()
                    called_cmd = mock_run.call_args[0][0]
                    assert called_cmd[0] == "/usr/bin/rust-analyzer"
                    assert "scip" in called_cmd
                    assert str(repo_path) in called_cmd

    def test_run_rust_analyzer_scip_raises_when_path_none(self, indexer, tmp_path):
        """Should raise RuntimeError when rust-analyzer path is None."""
        with patch.object(indexer, "_get_rust_analyzer_path", return_value=None):
            with pytest.raises(RuntimeError) as exc_info:
                indexer._run_rust_analyzer_scip(tmp_path)

            assert "rust-analyzer not found" in str(exc_info.value)

    def test_run_rust_analyzer_scip_command_failure(self, indexer, tmp_path):
        """Should raise error when rust-analyzer command fails."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        with patch.object(
            indexer, "_get_rust_analyzer_path", return_value="/usr/bin/rust-analyzer"
        ):
            with patch("subprocess.run") as mock_run:
                mock_result = Mock()
                mock_result.returncode = 1
                mock_result.stderr = "rust-analyzer error: failed to index"
                mock_run.return_value = mock_result

                with patch("tempfile.NamedTemporaryFile") as mock_temp:
                    scip_file_path = tmp_path / "test.scip"
                    mock_temp.return_value.__enter__.return_value.name = str(scip_file_path)

                    with pytest.raises(RuntimeError) as exc_info:
                        indexer._run_rust_analyzer_scip(repo_path)

                    assert "rust-analyzer scip failed" in str(exc_info.value).lower()

    def test_run_rust_analyzer_scip_timeout(self, indexer, tmp_path):
        """Should handle timeout gracefully."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        with patch.object(
            indexer, "_get_rust_analyzer_path", return_value="/usr/bin/rust-analyzer"
        ):
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = subprocess.TimeoutExpired("rust-analyzer", 600)

                with patch("tempfile.NamedTemporaryFile") as mock_temp:
                    scip_file_path = tmp_path / "test.scip"
                    mock_temp.return_value.__enter__.return_value.name = str(scip_file_path)
                    scip_file_path.touch()

                    with pytest.raises(RuntimeError) as exc_info:
                        indexer._run_rust_analyzer_scip(repo_path)

                    assert "timed out" in str(exc_info.value)

    def test_find_rust_files_basic(self, indexer, tmp_path):
        """Should find Rust files in repository."""
        repo = tmp_path / "repo"
        repo.mkdir()

        (repo / "lib.rs").touch()
        (repo / "main.rs").touch()
        src_dir = repo / "src"
        src_dir.mkdir()
        (src_dir / "module.rs").touch()

        files = list(indexer._find_source_files(repo))
        assert len(files) == 3

    def test_find_rust_files_excludes_target(self, indexer, tmp_path):
        """Should exclude target directory."""
        repo = tmp_path / "repo"
        repo.mkdir()

        (repo / "main.rs").touch()
        target = repo / "target"
        target.mkdir()
        (target / "debug.rs").touch()

        files = list(indexer._find_source_files(repo))
        assert len(files) == 1
        assert files[0].name == "main.rs"

    def test_find_rust_files_excludes_vendor(self, indexer, tmp_path):
        """Should exclude vendor directory."""
        repo = tmp_path / "repo"
        repo.mkdir()

        (repo / "main.rs").touch()
        vendor = repo / "vendor"
        vendor.mkdir()
        (vendor / "lib.rs").touch()

        files = list(indexer._find_source_files(repo))
        assert len(files) == 1
        assert files[0].name == "main.rs"

    def test_index_repository_full_flow(self, indexer, tmp_path):
        """Should successfully index a repository (mocked flow)."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        (repo_path / "Cargo.toml").write_text('[package]\nname = "test"')
        output_path = tmp_path / "output" / "index.json"

        # Create mock SCIP index
        scip_index = scip_pb2.Index()
        scip_index.metadata.version = 0
        doc = scip_index.documents.add()
        doc.relative_path = "src/lib.rs"

        symbol = doc.symbols.add()
        symbol.symbol = "rust-analyzer cargo test 0.1.0 test/Calculator#"

        with patch.object(indexer, "_ensure_rust_analyzer_installed"):
            with patch.object(indexer, "_run_rust_analyzer_scip") as mock_run_scip:
                scip_file = tmp_path / "temp.scip"
                with open(scip_file, "wb") as f:
                    f.write(scip_index.SerializeToString())

                mock_run_scip.return_value = scip_file

                try:
                    result = indexer.index_repository(repo_path, output_path)

                    assert result["success"] is True
                    assert result["modules_count"] >= 0
                    assert result["files_indexed"] == 1
                    assert len(result["errors"]) == 0
                    assert output_path.exists()
                finally:
                    if scip_file.exists():
                        scip_file.unlink()

    def test_index_repository_scip_read_failure(self, indexer, tmp_path):
        """Should handle SCIP reading failures gracefully."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        (repo_path / "Cargo.toml").write_text('[package]\nname = "test"')
        output_path = tmp_path / "output" / "index.json"

        with patch.object(indexer, "_ensure_rust_analyzer_installed"):
            with patch.object(indexer, "_run_rust_analyzer_scip") as mock_run_scip:
                # Create corrupt SCIP file
                scip_file = tmp_path / "corrupt.scip"
                scip_file.write_bytes(b"corrupt data")
                mock_run_scip.return_value = scip_file

                try:
                    result = indexer.index_repository(repo_path, output_path)

                    assert result["success"] is False
                    assert result["modules_count"] == 0
                    assert len(result["errors"]) > 0
                finally:
                    if scip_file.exists():
                        scip_file.unlink()

    def test_index_repository_cleanup_on_success(self, indexer, tmp_path):
        """Should cleanup temporary SCIP file after successful indexing."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        (repo_path / "Cargo.toml").write_text('[package]\nname = "test"')
        output_path = tmp_path / "output" / "index.json"

        scip_index = scip_pb2.Index()
        doc = scip_index.documents.add()
        doc.relative_path = "src/lib.rs"

        with patch.object(indexer, "_ensure_rust_analyzer_installed"):
            with patch.object(indexer, "_run_rust_analyzer_scip") as mock_run_scip:
                scip_file = tmp_path / "temp.scip"
                with open(scip_file, "wb") as f:
                    f.write(scip_index.SerializeToString())

                mock_run_scip.return_value = scip_file

                indexer.index_repository(repo_path, output_path)

                # Temp file should be cleaned up
                assert not scip_file.exists()

    def test_verbose_output(self, verbose_indexer, tmp_path, capsys):
        """Should print verbose output when enabled."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        (repo_path / "Cargo.toml").write_text('[package]\nname = "test"')
        output_path = tmp_path / "output" / "index.json"

        scip_index = scip_pb2.Index()
        scip_index.documents.add()

        with patch.object(verbose_indexer, "_ensure_rust_analyzer_installed"):
            with patch.object(verbose_indexer, "_run_rust_analyzer_scip") as mock_run_scip:
                scip_file = tmp_path / "temp.scip"
                with open(scip_file, "wb") as f:
                    f.write(scip_index.SerializeToString())
                mock_run_scip.return_value = scip_file

                try:
                    verbose_indexer.index_repository(repo_path, output_path, verbose=True)

                    captured = capsys.readouterr()
                    assert "rust" in captured.out.lower()
                    assert "Index saved to" in captured.out
                finally:
                    if scip_file.exists():
                        scip_file.unlink()


class TestRustIndexerHelperMethods:
    """Test Rust indexer helper methods."""

    @pytest.fixture
    def indexer(self):
        """Create a RustSCIPIndexer instance."""
        return RustSCIPIndexer(verbose=False)

    def test_find_source_files_nested_structure(self, indexer, tmp_path):
        """Should handle deeply nested directory structures."""
        repo = tmp_path / "repo"
        repo.mkdir()

        (repo / "lib.rs").touch()
        deep = repo / "src" / "a" / "b" / "c"
        deep.mkdir(parents=True)
        (deep / "deep.rs").touch()

        files = list(indexer._find_source_files(repo))
        assert len(files) == 2
        file_names = [f.name for f in files]
        assert "lib.rs" in file_names
        assert "deep.rs" in file_names

    def test_find_source_files_empty_directory(self, indexer, tmp_path):
        """Should return empty list for empty directory."""
        repo = tmp_path / "repo"
        repo.mkdir()

        files = list(indexer._find_source_files(repo))
        assert files == []

    def test_save_index(self, indexer, tmp_path):
        """Should save index to JSON file."""
        output_path = tmp_path / "subdir" / "index.json"
        index_data = {
            "modules": {"Calculator": {"file": "src/lib.rs", "functions": []}},
            "metadata": {"total_modules": 1},
        }

        indexer._save_index(index_data, output_path)

        assert output_path.exists()
        with open(output_path) as f:
            saved_data = json.load(f)

        assert saved_data == index_data

    def test_save_index_creates_parent_dirs(self, indexer, tmp_path):
        """Should create parent directories if they don't exist."""
        output_path = tmp_path / "a" / "b" / "c" / "index.json"
        index_data = {"modules": {}, "metadata": {}}

        indexer._save_index(index_data, output_path)

        assert output_path.exists()
        assert output_path.parent.exists()


class TestRustLanguageRegistration:
    """Test Rust language registration."""

    def test_rust_is_registered(self):
        """Rust should be registered in the language registry."""
        from cicada.languages import LanguageRegistry

        assert LanguageRegistry.is_language_supported("rust")

    def test_rust_indexer_can_be_retrieved(self):
        """Should be able to get Rust indexer from registry."""
        from cicada.languages import LanguageRegistry

        indexer = LanguageRegistry.get_indexer("rust")
        assert indexer.get_language_name() == "rust"

    def test_rust_config_exists(self):
        """Rust config should be available."""
        from cicada.languages import LanguageRegistry

        config = LanguageRegistry.get_config("rust")
        assert config is not None
        assert config.language == "rust"
        assert ".rs" in config.file_extensions
        assert "target" in config.excluded_dirs

    def test_detect_rust_project_language(self, tmp_path):
        """Should detect Rust project from Cargo.toml."""
        from cicada.setup import detect_project_language

        (tmp_path / "Cargo.toml").write_text('[package]\nname = "test"')
        assert detect_project_language(tmp_path) == "rust"
