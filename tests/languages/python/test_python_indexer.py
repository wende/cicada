"""Comprehensive tests for Python SCIP indexer."""

import json
import pytest
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock

from cicada.languages.python.indexer import PythonSCIPIndexer
from cicada.languages.python.scip_installer import SCIPPythonInstaller
from cicada.languages.scip import scip_pb2


class TestPythonSCIPIndexer:
    """Test Python SCIP indexer functionality."""

    @pytest.fixture
    def indexer(self):
        """Create a PythonSCIPIndexer instance."""
        return PythonSCIPIndexer(verbose=False)

    @pytest.fixture
    def verbose_indexer(self):
        """Create a verbose indexer."""
        return PythonSCIPIndexer(verbose=True)

    def test_get_language_name(self, indexer):
        """Should return 'python' as language name."""
        assert indexer.get_language_name() == "python"

    def test_get_file_extensions(self, indexer):
        """Should return .py extension."""
        extensions = indexer.get_file_extensions()
        assert extensions == [".py"]

    def test_get_excluded_dirs(self, indexer):
        """Should return list of excluded directories."""
        excluded = indexer.get_excluded_dirs()

        assert "__pycache__" in excluded
        assert ".venv" in excluded
        assert "venv" in excluded
        assert "node_modules" in excluded
        assert ".git" in excluded

    @patch.object(SCIPPythonInstaller, "is_scip_python_installed")
    @patch.object(SCIPPythonInstaller, "get_scip_python_version")
    def test_ensure_scip_python_already_installed(
        self, mock_version, mock_installed, verbose_indexer, capsys
    ):
        """Should use existing scip-python installation."""
        mock_installed.return_value = True
        mock_version.return_value = "0.3.15"

        verbose_indexer._ensure_scip_python_installed()

        captured = capsys.readouterr()
        assert "Using scip-python 0.3.15" in captured.out

    @patch.object(SCIPPythonInstaller, "is_scip_python_installed")
    @patch.object(SCIPPythonInstaller, "is_npm_available")
    def test_ensure_scip_python_npm_not_available(self, mock_npm, mock_installed, indexer):
        """Should raise error when npm is not available."""
        mock_installed.return_value = False
        mock_npm.return_value = False

        with pytest.raises(RuntimeError) as exc_info:
            indexer._ensure_scip_python_installed()

        assert "npm is required" in str(exc_info.value)
        assert "https://nodejs.org" in str(exc_info.value)

    @patch.object(SCIPPythonInstaller, "is_scip_python_installed")
    @patch.object(SCIPPythonInstaller, "is_npm_available")
    @patch.object(SCIPPythonInstaller, "install_scip_python")
    def test_ensure_scip_python_auto_install_success(
        self, mock_install, mock_npm, mock_installed, indexer, capsys
    ):
        """Should auto-install scip-python when npm is available."""
        mock_installed.return_value = False
        mock_npm.return_value = True
        mock_install.return_value = True

        indexer._ensure_scip_python_installed()

        mock_install.assert_called_once()
        captured = capsys.readouterr()
        assert "Installing scip-python" in captured.out
        assert "installed successfully" in captured.out

    @patch.object(SCIPPythonInstaller, "is_scip_python_installed")
    @patch.object(SCIPPythonInstaller, "is_npm_available")
    @patch.object(SCIPPythonInstaller, "install_scip_python")
    def test_ensure_scip_python_auto_install_failure(
        self, mock_install, mock_npm, mock_installed, indexer
    ):
        """Should raise error when auto-install fails."""
        mock_installed.return_value = False
        mock_npm.return_value = True
        mock_install.return_value = False

        with pytest.raises(RuntimeError) as exc_info:
            indexer._ensure_scip_python_installed()

        assert "Failed to install scip-python" in str(exc_info.value)
        assert "Try installing manually" in str(exc_info.value)

    def test_run_scip_python_success(self, indexer, tmp_path):
        """Should successfully run scip-python and return .scip file path."""
        # Create a mock .scip file
        mock_scip_content = scip_pb2.Index()
        mock_scip_content.metadata.version = 0  # ProtocolVersion enum

        with patch("subprocess.run") as mock_run:
            # Mock successful subprocess run
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            # Mock the scip file creation
            with patch("tempfile.NamedTemporaryFile") as mock_temp:
                scip_file_path = tmp_path / "test.scip"
                mock_temp.return_value.__enter__.return_value.name = str(scip_file_path)

                # Create the file to simulate scip-python output
                with open(scip_file_path, "wb") as f:
                    f.write(mock_scip_content.SerializeToString())

                result_path = indexer._run_scip_python(tmp_path)

                assert result_path == scip_file_path
                assert result_path.exists()

    def test_run_scip_python_command_failure(self, indexer, tmp_path):
        """Should raise error when scip-python command fails."""
        with patch("subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stderr = "scip-python error: failed to index"
            mock_run.return_value = mock_result

            with patch("tempfile.NamedTemporaryFile") as mock_temp:
                scip_file_path = tmp_path / "test.scip"
                mock_temp.return_value.__enter__.return_value.name = str(scip_file_path)

                with pytest.raises(RuntimeError) as exc_info:
                    indexer._run_scip_python(tmp_path)

                assert "scip-python indexing failed" in str(exc_info.value)
                assert "failed to index" in str(exc_info.value)

    def test_run_scip_python_file_not_generated(self, indexer, tmp_path):
        """Should raise error when scip-python doesn't generate output file."""
        with patch("subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            with patch("tempfile.NamedTemporaryFile") as mock_temp:
                scip_file_path = tmp_path / "nonexistent.scip"
                mock_temp.return_value.__enter__.return_value.name = str(scip_file_path)
                # Don't create the file

                with pytest.raises(RuntimeError) as exc_info:
                    indexer._run_scip_python(tmp_path)

                assert "did not generate" in str(exc_info.value)

    def test_run_scip_python_timeout(self, indexer, tmp_path):
        """Should handle timeout gracefully."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("scip-python", 600)

            with patch("tempfile.NamedTemporaryFile") as mock_temp:
                scip_file_path = tmp_path / "test.scip"
                mock_temp.return_value.__enter__.return_value.name = str(scip_file_path)

                # Create file to test cleanup
                scip_file_path.touch()

                with pytest.raises(RuntimeError) as exc_info:
                    indexer._run_scip_python(tmp_path)

                assert "timed out" in str(exc_info.value)
                assert "10 minutes" in str(exc_info.value)

    def test_run_scip_python_exception_cleanup(self, indexer, tmp_path):
        """Should cleanup temp file on exception."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = Exception("Unexpected error")

            with patch("tempfile.NamedTemporaryFile") as mock_temp:
                scip_file_path = tmp_path / "test.scip"
                mock_temp.return_value.__enter__.return_value.name = str(scip_file_path)

                # Create file
                scip_file_path.touch()

                with pytest.raises(Exception):
                    indexer._run_scip_python(tmp_path)

                # File should be cleaned up
                assert not scip_file_path.exists()

    def test_save_index(self, indexer, tmp_path):
        """Should save index to JSON file."""
        output_path = tmp_path / "subdir" / "index.json"
        index_data = {
            "modules": {"TestModule": {"file": "test.py", "functions": []}},
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

    def test_index_repository_full_flow(self, indexer, tmp_path):
        """Should successfully index a repository (mocked flow)."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        output_path = tmp_path / "output" / "index.json"

        # Create mock SCIP index
        scip_index = scip_pb2.Index()
        scip_index.metadata.version = 0  # ProtocolVersion enum
        doc = scip_index.documents.add()
        doc.relative_path = "test.py"

        symbol = doc.symbols.add()
        symbol.symbol = "scip-python python test 1.0 test/TestClass#"

        # Mock all the steps
        with patch.object(indexer, "_ensure_scip_python_installed"):
            with patch.object(indexer, "_run_scip_python") as mock_run_scip:
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
        output_path = tmp_path / "output" / "index.json"

        with patch.object(indexer, "_ensure_scip_python_installed"):
            with patch.object(indexer, "_run_scip_python") as mock_run_scip:
                # Create corrupt SCIP file
                scip_file = tmp_path / "corrupt.scip"
                scip_file.write_bytes(b"corrupt data")
                mock_run_scip.return_value = scip_file

                try:
                    result = indexer.index_repository(repo_path, output_path)

                    assert result["success"] is False
                    assert result["modules_count"] == 0
                    assert len(result["errors"]) > 0
                    assert "Failed to process SCIP index" in result["errors"][0]
                finally:
                    if scip_file.exists():
                        scip_file.unlink()

    def test_index_repository_cleanup_on_success(self, indexer, tmp_path):
        """Should cleanup temporary SCIP file after successful indexing."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        output_path = tmp_path / "output" / "index.json"

        scip_index = scip_pb2.Index()
        doc = scip_index.documents.add()
        doc.relative_path = "test.py"

        with patch.object(indexer, "_ensure_scip_python_installed"):
            with patch.object(indexer, "_run_scip_python") as mock_run_scip:
                scip_file = tmp_path / "temp.scip"
                with open(scip_file, "wb") as f:
                    f.write(scip_index.SerializeToString())

                mock_run_scip.return_value = scip_file

                indexer.index_repository(repo_path, output_path)

                # Temp file should be cleaned up
                assert not scip_file.exists()

    def test_index_repository_cleanup_on_error(self, indexer, tmp_path):
        """Should cleanup temporary SCIP file even on error."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        output_path = tmp_path / "output" / "index.json"

        with patch.object(indexer, "_ensure_scip_python_installed"):
            with patch.object(indexer, "_run_scip_python") as mock_run_scip:
                scip_file = tmp_path / "temp.scip"
                scip_file.write_bytes(b"corrupt")
                mock_run_scip.return_value = scip_file

                indexer.index_repository(repo_path, output_path)

                # Temp file should be cleaned up even on error
                assert not scip_file.exists()

    def test_verbose_output(self, verbose_indexer, tmp_path, capsys):
        """Should print verbose output when enabled."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        output_path = tmp_path / "output" / "index.json"

        scip_index = scip_pb2.Index()
        doc = scip_index.documents.add()

        with patch.object(verbose_indexer, "_ensure_scip_python_installed"):
            with patch.object(verbose_indexer, "_run_scip_python") as mock_run_scip:
                scip_file = tmp_path / "temp.scip"
                with open(scip_file, "wb") as f:
                    f.write(scip_index.SerializeToString())
                mock_run_scip.return_value = scip_file

                try:
                    verbose_indexer.index_repository(repo_path, output_path, verbose=True)

                    captured = capsys.readouterr()
                    assert "Indexing Python repository" in captured.out
                    assert "SCIP index" in captured.out
                    assert "Index saved to" in captured.out
                    assert "Cleaned up temporary file" in captured.out
                finally:
                    if scip_file.exists():
                        scip_file.unlink()
