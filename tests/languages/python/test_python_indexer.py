"""Comprehensive tests for Python SCIP indexer."""

import json
import pytest
import subprocess
from unittest.mock import patch, Mock

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

    @patch.object(SCIPPythonInstaller, "is_npm_available")
    @patch.object(SCIPPythonInstaller, "is_scip_python_installed")
    def test_ensure_scip_python_not_installed(self, mock_installed, mock_npm, indexer):
        """Should raise error when scip-python is not installed and npm unavailable."""
        mock_installed.return_value = False
        mock_npm.return_value = False  # npm not available, can't auto-install

        with pytest.raises(RuntimeError) as exc_info:
            indexer._ensure_scip_python_installed()

        assert "scip-python is required" in str(exc_info.value)
        assert "npm is required" in str(exc_info.value)

    @patch.object(SCIPPythonInstaller, "install_locally")
    @patch.object(SCIPPythonInstaller, "is_npm_available")
    @patch.object(SCIPPythonInstaller, "is_scip_python_installed")
    def test_ensure_scip_python_auto_installs(
        self, mock_installed, mock_npm, mock_install, indexer
    ):
        """Should auto-install scip-python locally when npm is available."""
        mock_installed.return_value = False
        mock_npm.return_value = True
        mock_install.return_value = True  # Install succeeds

        # Should not raise - auto-install succeeds
        indexer._ensure_scip_python_installed()

        mock_install.assert_called_once()

    @patch.object(SCIPPythonInstaller, "install_locally")
    @patch.object(SCIPPythonInstaller, "is_npm_available")
    @patch.object(SCIPPythonInstaller, "is_scip_python_installed")
    def test_ensure_scip_python_auto_install_fails(
        self, mock_installed, mock_npm, mock_install, indexer
    ):
        """Should raise error when auto-install fails."""
        mock_installed.return_value = False
        mock_npm.return_value = True
        mock_install.return_value = False  # Install fails

        with pytest.raises(RuntimeError) as exc_info:
            indexer._ensure_scip_python_installed()

        assert "scip-python is required" in str(exc_info.value)

    @patch.object(SCIPPythonInstaller, "is_local_install")
    @patch.object(SCIPPythonInstaller, "get_scip_python_path")
    @patch.object(SCIPPythonInstaller, "is_scip_python_installed")
    @patch.object(SCIPPythonInstaller, "get_scip_python_version")
    def test_ensure_scip_python_local_log_message(
        self, mock_version, mock_installed, mock_path, mock_is_local, verbose_indexer, capsys
    ):
        """Should show (local) in log message when using local installation."""
        mock_installed.return_value = True
        mock_version.return_value = "0.3.15"
        mock_path.return_value = str(SCIPPythonInstaller.LOCAL_BIN_DIR / "scip-python")
        mock_is_local.return_value = True

        verbose_indexer._ensure_scip_python_installed()

        captured = capsys.readouterr()
        assert "Using scip-python 0.3.15 (local)" in captured.out

    @patch.object(SCIPPythonInstaller, "get_scip_python_path")
    def test_run_scip_python_raises_when_path_is_none(self, mock_path, indexer, tmp_path):
        """Should raise RuntimeError when scip-python path is not available."""
        mock_path.return_value = None

        with pytest.raises(RuntimeError) as exc_info:
            indexer._run_scip_python(tmp_path)

        assert "call _ensure_scip_python_installed() first" in str(exc_info.value)

    def test_run_scip_python_success(self, indexer, tmp_path):
        """Should successfully run scip-python using resolved path from installer."""
        # Create a mock .scip file
        mock_scip_content = scip_pb2.Index()
        mock_scip_content.metadata.version = 0  # ProtocolVersion enum

        fake_scip_python_path = "/fake/bin/scip-python"

        with patch.object(
            SCIPPythonInstaller, "get_scip_python_path", return_value=fake_scip_python_path
        ):
            with patch("cicada.languages.python.indexer.subprocess.run") as mock_run:
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

                    # Verify the resolved scip-python path is used as the command
                    mock_run.assert_called_once()
                    called_cmd = mock_run.call_args[0][0]
                    assert called_cmd[0] == fake_scip_python_path

                    # Verify NamedTemporaryFile usage
                    mock_temp.assert_called_once()
                    call_kwargs = mock_temp.call_args[1]
                    assert "dir" not in call_kwargs

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

    def test_run_scip_python_keyboard_interrupt_cleanup(self, indexer, tmp_path):
        """Should cleanup temp file on KeyboardInterrupt and re-raise."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = KeyboardInterrupt()

            with patch("tempfile.NamedTemporaryFile") as mock_temp:
                scip_file_path = tmp_path / "test.scip"
                mock_temp.return_value.__enter__.return_value.name = str(scip_file_path)

                # Create file
                scip_file_path.touch()

                with pytest.raises(KeyboardInterrupt):
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
        scip_index.documents.add()

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


class TestPythonIndexerHelperMethods:
    """Test Python indexer helper methods."""

    @pytest.fixture
    def indexer(self):
        """Create a PythonSCIPIndexer instance."""
        return PythonSCIPIndexer(verbose=False)

    @pytest.fixture
    def verbose_indexer(self):
        """Create a verbose indexer."""
        return PythonSCIPIndexer(verbose=True)

    # Tests for _find_python_files

    def test_find_python_files_basic(self, indexer, tmp_path):
        """Should find Python files in repository."""
        repo = tmp_path / "repo"
        repo.mkdir()

        (repo / "file1.py").touch()
        (repo / "file2.py").touch()
        subdir = repo / "subdir"
        subdir.mkdir()
        (subdir / "file3.py").touch()

        files = list(indexer._find_python_files(repo))
        assert len(files) == 3

    def test_find_python_files_excludes_pycache(self, indexer, tmp_path):
        """Should exclude __pycache__ directories."""
        repo = tmp_path / "repo"
        repo.mkdir()

        (repo / "main.py").touch()
        pycache = repo / "__pycache__"
        pycache.mkdir()
        (pycache / "cached.py").touch()

        files = list(indexer._find_python_files(repo))
        assert len(files) == 1
        assert files[0].name == "main.py"

    def test_find_python_files_excludes_venv(self, indexer, tmp_path):
        """Should exclude .venv and venv directories."""
        repo = tmp_path / "repo"
        repo.mkdir()

        (repo / "main.py").touch()
        venv1 = repo / ".venv"
        venv1.mkdir()
        (venv1 / "lib.py").touch()
        venv2 = repo / "venv"
        venv2.mkdir()
        (venv2 / "lib.py").touch()

        files = list(indexer._find_python_files(repo))
        assert len(files) == 1
        assert files[0].name == "main.py"

    def test_find_python_files_nested_structure(self, indexer, tmp_path):
        """Should handle deeply nested directory structures."""
        repo = tmp_path / "repo"
        repo.mkdir()

        (repo / "root.py").touch()
        deep = repo / "a" / "b" / "c" / "d"
        deep.mkdir(parents=True)
        (deep / "deep.py").touch()

        files = list(indexer._find_python_files(repo))
        assert len(files) == 2
        file_names = [f.name for f in files]
        assert "root.py" in file_names
        assert "deep.py" in file_names

    def test_find_python_files_empty_directory(self, indexer, tmp_path):
        """Should return empty list for empty directory."""
        repo = tmp_path / "repo"
        repo.mkdir()

        files = list(indexer._find_python_files(repo))
        assert files == []

    # Tests for _extract_string_keywords

    def test_extract_string_keywords_success(self, verbose_indexer, tmp_path, capsys):
        """Should extract string keywords from Python files."""
        from unittest.mock import MagicMock

        repo = tmp_path / "repo"
        repo.mkdir()
        py_file = repo / "test.py"
        py_file.write_text('x = "SELECT * FROM users"')

        index = {
            "modules": {
                "TestModule": {
                    "file": "test.py",
                    "functions": [],
                }
            }
        }

        keyword_extractor = MagicMock()
        keyword_extractor.extract_keywords.return_value = {
            "top_keywords": [("select", 0.9), ("users", 0.8)]
        }

        keyword_expander = MagicMock()
        # Return new dict format with words and simple keys
        keyword_expander.expand_keywords.return_value = {
            "words": [{"word": "database", "score": 0.7}],
            "simple": ["database"],
        }

        verbose_indexer._extract_string_keywords(index, repo, keyword_extractor, keyword_expander)

        captured = capsys.readouterr()
        assert "Extracting string keywords" in captured.out

        module = index["modules"]["TestModule"]
        assert "string_sources" in module
        assert "string_keywords" in module
        # Check boost is applied (1.3x)
        assert module["string_keywords"]["select"] == pytest.approx(0.9 * 1.3)
        assert module["string_keywords"]["users"] == pytest.approx(0.8 * 1.3)

    def test_extract_string_keywords_file_not_found(self, indexer, tmp_path):
        """Should handle missing files gracefully."""
        from unittest.mock import MagicMock

        repo = tmp_path / "repo"
        repo.mkdir()

        index = {
            "modules": {
                "TestModule": {
                    "file": "nonexistent.py",
                    "functions": [],
                }
            }
        }

        keyword_extractor = MagicMock()
        keyword_expander = MagicMock()

        # Should not raise an error
        indexer._extract_string_keywords(index, repo, keyword_extractor, keyword_expander)

        # String keywords should not be added
        module = index["modules"]["TestModule"]
        assert "string_keywords" not in module

    def test_extract_string_keywords_empty_results(self, indexer, tmp_path):
        """Should handle files with no extractable strings."""
        from unittest.mock import MagicMock

        repo = tmp_path / "repo"
        repo.mkdir()
        py_file = repo / "test.py"
        py_file.write_text("x = 42")  # No strings

        index = {
            "modules": {
                "TestModule": {
                    "file": "test.py",
                    "functions": [],
                }
            }
        }

        keyword_extractor = MagicMock()
        keyword_expander = MagicMock()

        indexer._extract_string_keywords(index, repo, keyword_extractor, keyword_expander)

        module = index["modules"]["TestModule"]
        assert "string_keywords" not in module

    def test_extract_string_keywords_parse_error(self, verbose_indexer, tmp_path, capsys):
        """Should handle syntax errors in Python files."""
        from unittest.mock import MagicMock

        repo = tmp_path / "repo"
        repo.mkdir()
        py_file = repo / "test.py"
        py_file.write_text("def broken(")  # Syntax error

        index = {
            "modules": {
                "TestModule": {
                    "file": "test.py",
                    "functions": [],
                }
            }
        }

        keyword_extractor = MagicMock()
        keyword_expander = MagicMock()

        verbose_indexer._extract_string_keywords(index, repo, keyword_extractor, keyword_expander)

        # Should have warning in output
        captured = capsys.readouterr()
        # String extraction returns empty list for syntax errors, so no warning expected
        # but no string_keywords should be added
        module = index["modules"]["TestModule"]
        assert "string_keywords" not in module

    # Tests for _compute_timestamps

    def test_compute_timestamps_success(self, verbose_indexer, tmp_path, capsys):
        """Should compute timestamps for functions."""
        from unittest.mock import MagicMock

        repo = tmp_path / "repo"
        repo.mkdir()

        index = {
            "modules": {
                "TestModule": {
                    "file": "test.py",
                    "functions": [{"name": "test_func", "line": 5}],
                }
            }
        }

        with patch("cicada.languages.python.indexer.GitHelper") as mock_git_helper_class:
            mock_git_helper = MagicMock()
            mock_git_helper.get_functions_evolution_batch.return_value = {
                "test_func": {
                    "created_at": {
                        "date": "2024-01-01T00:00:00+00:00",
                        "sha": "abc123",
                        "author": "Test Author",
                        "message": "Initial commit",
                    },
                    "last_modified": {
                        "date": "2024-01-10T00:00:00+00:00",
                        "sha": "def456",
                        "author": "Test Author",
                        "message": "Update function",
                    },
                    "total_modifications": 5,
                    "modification_frequency": 0.5,
                }
            }
            mock_git_helper_class.return_value = mock_git_helper

            verbose_indexer._compute_timestamps(index, repo)

            captured = capsys.readouterr()
            assert "Computing git timestamps" in captured.out

            func = index["modules"]["TestModule"]["functions"][0]
            # Now individual fields are extracted instead of timestamps dict
            assert "created_at" in func
            assert func["created_at"] == "2024-01-01T00:00:00+00:00"
            assert "last_modified_at" in func
            assert func["last_modified_at"] == "2024-01-10T00:00:00+00:00"
            assert "last_modified_sha" in func
            assert func["last_modified_sha"] == "def456"
            assert "modification_count" in func
            assert func["modification_count"] == 5
            assert "modification_frequency" in func
            assert func["modification_frequency"] == 0.5

    def test_compute_timestamps_git_helper_failure(self, verbose_indexer, tmp_path, capsys):
        """Should handle git helper initialization failure."""
        repo = tmp_path / "repo"
        repo.mkdir()

        index = {
            "modules": {
                "TestModule": {
                    "file": "test.py",
                    "functions": [{"name": "test_func", "line": 5}],
                }
            }
        }

        with patch("cicada.languages.python.indexer.GitHelper") as mock_git_helper_class:
            mock_git_helper_class.side_effect = Exception("Not a git repo")

            verbose_indexer._compute_timestamps(index, repo)

            captured = capsys.readouterr()
            assert "Could not initialize git helper" in captured.out

            # Functions should not have timestamps
            func = index["modules"]["TestModule"]["functions"][0]
            assert "timestamps" not in func

    def test_compute_timestamps_no_functions(self, indexer, tmp_path):
        """Should handle index with no functions."""
        from unittest.mock import MagicMock

        repo = tmp_path / "repo"
        repo.mkdir()

        index = {
            "modules": {
                "TestModule": {
                    "file": "test.py",
                    "functions": [],
                }
            }
        }

        with patch("cicada.languages.python.indexer.GitHelper") as mock_git_helper_class:
            mock_git_helper = MagicMock()
            mock_git_helper_class.return_value = mock_git_helper

            indexer._compute_timestamps(index, repo)

            # Should return early, git helper should not be called
            mock_git_helper.get_functions_evolution_batch.assert_not_called()

    def test_compute_timestamps_batch_processing(self, indexer, tmp_path):
        """Should batch process functions by file."""
        from unittest.mock import MagicMock

        repo = tmp_path / "repo"
        repo.mkdir()

        index = {
            "modules": {
                "Module1": {
                    "file": "file1.py",
                    "functions": [
                        {"name": "func1", "line": 5},
                        {"name": "func2", "line": 10},
                    ],
                },
                "Module2": {
                    "file": "file2.py",
                    "functions": [
                        {"name": "func3", "line": 3},
                    ],
                },
            }
        }

        with patch("cicada.languages.python.indexer.GitHelper") as mock_git_helper_class:
            mock_git_helper = MagicMock()
            mock_git_helper.get_functions_evolution_batch.return_value = {}
            mock_git_helper_class.return_value = mock_git_helper

            indexer._compute_timestamps(index, repo)

            # Should be called once per file
            assert mock_git_helper.get_functions_evolution_batch.call_count == 2

    # Tests for _extract_cochange

    def test_extract_cochange_success(self, verbose_indexer, tmp_path, capsys):
        """Should extract co-change relationships."""
        from unittest.mock import MagicMock

        repo = tmp_path / "repo"
        repo.mkdir()

        index = {
            "modules": {
                "ModuleA": {"file": "a.py", "functions": []},
                "ModuleB": {"file": "b.py", "functions": []},
            }
        }

        with patch("cicada.languages.python.indexer.CoChangeAnalyzer") as mock_analyzer_class:
            mock_analyzer = MagicMock()
            mock_analyzer.analyze_repository.return_value = {
                "metadata": {"file_pairs": 1, "function_pairs": 0, "commit_count": 10},
                "file_pairs": {},
            }
            mock_analyzer_class.return_value = mock_analyzer
            mock_analyzer_class.find_cochange_pairs = MagicMock(return_value=[])

            verbose_indexer._extract_cochange(index, repo)

            captured = capsys.readouterr()
            assert "Analyzing co-change patterns" in captured.out
            assert "cochange_metadata" in index

    def test_extract_cochange_analyzer_failure(self, verbose_indexer, tmp_path, capsys):
        """Should handle analyzer failures gracefully."""
        repo = tmp_path / "repo"
        repo.mkdir()

        index = {"modules": {}}

        with patch("cicada.languages.python.indexer.CoChangeAnalyzer") as mock_analyzer_class:
            mock_analyzer_class.side_effect = Exception("Git error")

            verbose_indexer._extract_cochange(index, repo)

            captured = capsys.readouterr()
            assert "Failed to analyze co-changes" in captured.out
            assert "cochange_metadata" not in index

    def test_extract_cochange_file_mapping(self, indexer, tmp_path):
        """Should correctly map files to modules."""
        from unittest.mock import MagicMock

        repo = tmp_path / "repo"
        repo.mkdir()

        index = {
            "modules": {
                "ModuleA": {"file": "a.py", "functions": []},
                "ModuleB": {"file": "b.py", "functions": []},
            }
        }

        with patch("cicada.languages.python.indexer.CoChangeAnalyzer") as mock_analyzer_class:
            mock_analyzer = MagicMock()
            mock_analyzer.analyze_repository.return_value = {
                "metadata": {"file_pairs": 1, "function_pairs": 0, "commit_count": 5},
                "file_pairs": {},
            }
            mock_analyzer_class.return_value = mock_analyzer

            # Mock find_cochange_pairs to return related files
            def find_cochange_pairs_side_effect(file, _):
                if file == "a.py":
                    return [("b.py", 5)]
                return []

            mock_analyzer_class.find_cochange_pairs = MagicMock(
                side_effect=find_cochange_pairs_side_effect
            )

            indexer._extract_cochange(index, repo)

            # ModuleA should have cochange_files pointing to b.py
            assert "cochange_files" in index["modules"]["ModuleA"]
            cochange = index["modules"]["ModuleA"]["cochange_files"][0]
            assert cochange["file"] == "b.py"
            assert cochange["module"] == "ModuleB"
            assert cochange["count"] == 5

    def test_extract_cochange_limits_top_10(self, indexer, tmp_path):
        """Should limit co-change results to top 10."""
        from unittest.mock import MagicMock

        repo = tmp_path / "repo"
        repo.mkdir()

        index = {
            "modules": {
                "ModuleA": {"file": "a.py", "functions": []},
            }
        }

        with patch("cicada.languages.python.indexer.CoChangeAnalyzer") as mock_analyzer_class:
            mock_analyzer = MagicMock()
            mock_analyzer.analyze_repository.return_value = {
                "metadata": {"file_pairs": 15, "function_pairs": 0, "commit_count": 10},
                "file_pairs": {},
            }
            mock_analyzer_class.return_value = mock_analyzer

            # Return 15 co-change pairs
            pairs = [(f"file{i}.py", 100 - i) for i in range(15)]
            mock_analyzer_class.find_cochange_pairs = MagicMock(return_value=pairs)

            indexer._extract_cochange(index, repo)

            # Should limit to 10
            assert len(index["modules"]["ModuleA"]["cochange_files"]) == 10

    # Tests for incremental indexing

    def test_incremental_index_detects_new_files(self, indexer, tmp_path):
        """Should detect new files and trigger reindexing."""
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "new.py").touch()

        output = tmp_path / "index.json"

        scip_index = scip_pb2.Index()
        doc = scip_index.documents.add()
        doc.relative_path = "new.py"

        with patch.object(indexer, "_ensure_scip_python_installed"):
            with patch.object(indexer, "_run_scip_python") as mock_run:
                scip_file = tmp_path / "temp.scip"
                with open(scip_file, "wb") as f:
                    f.write(scip_index.SerializeToString())
                mock_run.return_value = scip_file

                try:
                    result = indexer.incremental_index_repository(
                        repo_path=str(repo),
                        output_path=str(output),
                        force_full=False,
                        verbose=False,
                    )

                    assert result["success"] is True
                    assert "skipped" not in result
                finally:
                    if scip_file.exists():
                        scip_file.unlink()

    def test_incremental_index_skips_when_up_to_date(self, verbose_indexer, tmp_path, capsys):
        """Should skip reindexing when no changes detected."""
        from cicada.utils.storage import get_hashes_path
        from cicada.utils.hash_utils import save_file_hashes
        from pathlib import Path

        repo = tmp_path / "repo"
        repo.mkdir()

        # Create test file
        py_file = repo / "test.py"
        py_file.write_text("x = 42")

        output = tmp_path / "index.json"

        # Create initial index
        initial_index = {
            "modules": {"test": {"file": "test.py"}},
            "metadata": {"total_functions": 0},
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w") as f:
            json.dump(initial_index, f)

        # Mock the file finding and hash comparison to simulate no changes
        with patch.object(verbose_indexer, "_find_python_files", return_value=[py_file]):
            with patch(
                "cicada.languages.python.indexer.detect_file_changes", return_value=([], [], [])
            ):
                result = verbose_indexer.incremental_index_repository(
                    repo_path=str(repo),
                    output_path=str(output),
                    force_full=False,
                    verbose=True,
                )

                captured = capsys.readouterr()
                assert "No changes detected" in captured.out
                assert result["skipped"] is True
                assert result["success"] is True

    def test_incremental_index_force_full_reindex(self, indexer, tmp_path):
        """Should force full reindex when force_full=True."""
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "test.py").touch()

        output = tmp_path / "index.json"

        # Create existing index
        initial_index = {"modules": {}, "metadata": {}}
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w") as f:
            json.dump(initial_index, f)

        scip_index = scip_pb2.Index()
        scip_index.documents.add()

        with patch.object(indexer, "_ensure_scip_python_installed"):
            with patch.object(indexer, "_run_scip_python") as mock_run:
                scip_file = tmp_path / "temp.scip"
                with open(scip_file, "wb") as f:
                    f.write(scip_index.SerializeToString())
                mock_run.return_value = scip_file

                try:
                    result = indexer.incremental_index_repository(
                        repo_path=str(repo),
                        output_path=str(output),
                        force_full=True,  # Force reindex
                        verbose=False,
                    )

                    # Should reindex even if no changes
                    assert result["success"] is True
                    assert "skipped" not in result
                    mock_run.assert_called_once()
                finally:
                    if scip_file.exists():
                        scip_file.unlink()


class TestExtractDocstringKeywords:
    """Tests for _extract_docstring_keywords method."""

    @pytest.fixture
    def indexer(self):
        return PythonSCIPIndexer(verbose=False)

    @pytest.fixture
    def verbose_indexer(self):
        return PythonSCIPIndexer(verbose=True)

    def test_extract_keywords_from_module_and_functions(self, indexer):
        """Should extract keywords from both module and function docstrings."""
        from unittest.mock import MagicMock

        index = {
            "modules": {
                "TestModule": {
                    "moduledoc": "This module handles user authentication.",
                    "functions": [
                        {"name": "process_data", "doc": "Process incoming data from API."},
                    ],
                }
            }
        }

        keyword_extractor = MagicMock()
        keyword_extractor.extract_keywords.return_value = {
            "top_keywords": [("authentication", 0.9), ("user", 0.8)]
        }

        keyword_expander = MagicMock()
        keyword_expander.expand_keywords.return_value = {
            "words": [{"word": "login", "score": 0.7}],
            "simple": ["login"],
        }

        indexer._extract_docstring_keywords(index, keyword_extractor, keyword_expander)

        module = index["modules"]["TestModule"]
        assert "keywords" in module
        assert module["keywords"]["authentication"] == 0.9
        func = module["functions"][0]
        assert "keywords" in func

    def test_handles_invalid_module_data(self, verbose_indexer, capsys):
        """Should handle non-dict modules and module_data gracefully."""
        from unittest.mock import MagicMock

        # Test non-dict modules
        index = {"modules": "not a dict"}
        keyword_extractor = MagicMock()
        verbose_indexer._extract_docstring_keywords(index, keyword_extractor, None)
        captured = capsys.readouterr()
        assert "modules is not a dict" in captured.out

        # Test non-dict module_data
        index = {"modules": {"BadModule": "not a dict"}}
        verbose_indexer._extract_docstring_keywords(index, keyword_extractor, None)
        captured = capsys.readouterr()
        assert "not a dict" in captured.out

    def test_handles_extraction_errors_and_progress(self, verbose_indexer, capsys):
        """Should handle extraction errors and log progress."""
        from unittest.mock import MagicMock

        # Create 55 modules to trigger progress logging
        modules = {f"Module{i}": {"moduledoc": f"Module {i}.", "functions": []} for i in range(55)}
        index = {"modules": modules}

        keyword_extractor = MagicMock()
        keyword_extractor.extract_keywords.side_effect = Exception("Extraction failed")

        verbose_indexer._extract_docstring_keywords(index, keyword_extractor, None)

        captured = capsys.readouterr()
        assert "Failed to extract keywords" in captured.out
        assert "Processed 50/55 modules" in captured.out

    def test_works_without_expander_and_with_higher_score(self, indexer):
        """Should work without expander and update score when expander returns higher."""
        from unittest.mock import MagicMock

        index = {"modules": {"TestModule": {"moduledoc": "Test module.", "functions": []}}}
        keyword_extractor = MagicMock()
        keyword_extractor.extract_keywords.return_value = {"top_keywords": [("test", 0.5)]}

        # Without expander
        indexer._extract_docstring_keywords(index, keyword_extractor, None)
        assert index["modules"]["TestModule"]["keywords"]["test"] == 0.5

        # With expander returning higher score
        keyword_expander = MagicMock()
        keyword_expander.expand_keywords.return_value = {
            "words": [{"word": "test", "score": 0.9}],
            "simple": ["test"],
        }
        indexer._extract_docstring_keywords(index, keyword_extractor, keyword_expander)
        assert index["modules"]["TestModule"]["keywords"]["test"] == 0.9


class TestExpandAndUpdateKeywords:
    """Tests for _expand_and_update_keywords helper method."""

    @pytest.fixture
    def indexer(self):
        return PythonSCIPIndexer(verbose=False)

    def test_returns_original_when_no_expander(self, indexer):
        """Should return original keywords when expander is None."""
        keywords = {"test": 0.5, "hello": 0.3}
        result = indexer._expand_and_update_keywords(keywords, None)
        assert result == keywords
        assert result is keywords  # Returns same object when no expansion

    def test_returns_original_when_empty_keywords(self, indexer):
        """Should return empty dict when keywords is empty."""
        from unittest.mock import MagicMock

        expander = MagicMock()
        result = indexer._expand_and_update_keywords({}, expander)
        assert result == {}
        expander.expand_keywords.assert_not_called()

    def test_adds_expanded_keywords(self, indexer):
        """Should add new keywords from expansion."""
        from unittest.mock import MagicMock

        keywords = {"test": 0.5}
        expander = MagicMock()
        expander.expand_keywords.return_value = {
            "words": [{"word": "testing", "score": 0.4}, {"word": "exam", "score": 0.3}],
            "simple": ["testing", "exam"],
        }

        result = indexer._expand_and_update_keywords(keywords, expander)

        assert result["test"] == 0.5  # Original preserved
        assert result["testing"] == 0.4  # New keyword added
        assert result["exam"] == 0.3  # New keyword added

    def test_updates_score_when_higher(self, indexer):
        """Should update score when expansion returns higher score."""
        from unittest.mock import MagicMock

        keywords = {"test": 0.5}
        expander = MagicMock()
        expander.expand_keywords.return_value = {
            "words": [{"word": "test", "score": 0.9}],
            "simple": ["test"],
        }

        result = indexer._expand_and_update_keywords(keywords, expander)
        assert result["test"] == 0.9  # Higher score wins

    def test_keeps_original_score_when_higher(self, indexer):
        """Should keep original score when it's higher than expansion."""
        from unittest.mock import MagicMock

        keywords = {"test": 0.9}
        expander = MagicMock()
        expander.expand_keywords.return_value = {
            "words": [{"word": "test", "score": 0.5}],
            "simple": ["test"],
        }

        result = indexer._expand_and_update_keywords(keywords, expander)
        assert result["test"] == 0.9  # Original higher score preserved


class TestExtractKeywordsFromText:
    """Tests for _extract_keywords_from_text helper method."""

    @pytest.fixture
    def indexer(self):
        return PythonSCIPIndexer(verbose=False)

    def test_returns_none_for_empty_text(self, indexer):
        """Should return None when text is empty."""
        from unittest.mock import MagicMock

        extractor = MagicMock()
        result = indexer._extract_keywords_from_text("", extractor, None)
        assert result is None
        extractor.extract_keywords.assert_not_called()

    def test_returns_none_for_no_keywords(self, indexer):
        """Should return None when extractor returns no keywords."""
        from unittest.mock import MagicMock

        extractor = MagicMock()
        extractor.extract_keywords.return_value = {"top_keywords": []}

        result = indexer._extract_keywords_from_text("some text", extractor, None)
        assert result is None

    def test_extracts_and_returns_keywords(self, indexer):
        """Should extract keywords and return as dict."""
        from unittest.mock import MagicMock

        extractor = MagicMock()
        extractor.extract_keywords.return_value = {"top_keywords": [("auth", 0.8), ("login", 0.6)]}

        result = indexer._extract_keywords_from_text("authentication login", extractor, None)

        assert result == {"auth": 0.8, "login": 0.6}
        extractor.extract_keywords.assert_called_once_with("authentication login", top_n=10)

    def test_respects_top_n_parameter(self, indexer):
        """Should pass top_n to extractor."""
        from unittest.mock import MagicMock

        extractor = MagicMock()
        extractor.extract_keywords.return_value = {"top_keywords": [("test", 0.5)]}

        indexer._extract_keywords_from_text("text", extractor, None, top_n=5)

        extractor.extract_keywords.assert_called_once_with("text", top_n=5)

    def test_expands_keywords_when_expander_provided(self, indexer):
        """Should expand keywords when expander is provided."""
        from unittest.mock import MagicMock

        extractor = MagicMock()
        extractor.extract_keywords.return_value = {"top_keywords": [("auth", 0.8)]}

        expander = MagicMock()
        expander.expand_keywords.return_value = {
            "words": [{"word": "auth", "score": 0.8}, {"word": "authentication", "score": 0.7}],
            "simple": ["auth", "authentication"],
        }

        result = indexer._extract_keywords_from_text("auth text", extractor, expander)

        assert "auth" in result
        assert "authentication" in result


class TestExtractModuleKeywords:
    """Tests for _extract_module_keywords helper method."""

    @pytest.fixture
    def indexer(self):
        return PythonSCIPIndexer(verbose=False)

    def test_extracts_module_level_keywords(self, indexer):
        """Should extract keywords from moduledoc and function docs combined."""
        from unittest.mock import MagicMock

        extractor = MagicMock()
        extractor.extract_keywords.return_value = {"top_keywords": [("user", 0.9), ("auth", 0.7)]}

        module_data = {
            "moduledoc": "User authentication module",
            "functions": [{"name": "login", "doc": "Login function"}],
        }

        indexer._extract_module_keywords(module_data, extractor, None)

        assert "keywords" in module_data
        assert module_data["keywords"] == {"user": 0.9, "auth": 0.7}

    def test_extracts_function_level_keywords(self, indexer):
        """Should extract keywords for each function with docs."""
        from unittest.mock import MagicMock

        extractor = MagicMock()
        extractor.extract_keywords.side_effect = [
            {"top_keywords": [("module", 0.8)]},  # Module-level
            {"top_keywords": [("login", 0.9)]},  # Function 1
            {"top_keywords": []},  # Function 2 - no keywords
        ]

        module_data = {
            "moduledoc": "Module doc",
            "functions": [
                {"name": "func1", "doc": "Login function"},
                {"name": "func2", "doc": "Another function"},
            ],
        }

        indexer._extract_module_keywords(module_data, extractor, None)

        assert module_data["functions"][0].get("keywords") == {"login": 0.9}
        assert "keywords" not in module_data["functions"][1]  # No keywords extracted

    def test_skips_functions_without_docs(self, indexer):
        """Should skip functions without documentation."""
        from unittest.mock import MagicMock

        extractor = MagicMock()
        extractor.extract_keywords.return_value = {"top_keywords": [("test", 0.5)]}

        module_data = {
            "moduledoc": "Module doc",
            "functions": [
                {"name": "func1", "doc": ""},  # Empty doc
                {"name": "func2"},  # No doc key
            ],
        }

        indexer._extract_module_keywords(module_data, extractor, None)

        # Only module-level extraction should happen
        assert extractor.extract_keywords.call_count == 1


class TestIndexRepositoryErrorPaths:
    """Tests for error handling in incremental_index_repository."""

    @pytest.fixture
    def verbose_indexer(self):
        return PythonSCIPIndexer(verbose=True)

    def _create_scip_file(self, tmp_path):
        """Helper to create a valid SCIP file."""
        scip_index = scip_pb2.Index()
        scip_index.documents.add()
        scip_file = tmp_path / "temp.scip"
        with open(scip_file, "wb") as f:
            f.write(scip_index.SerializeToString())
        return scip_file

    @pytest.mark.parametrize(
        "method_to_mock,error_msg,index_kwargs",
        [
            (
                "_extract_docstring_keywords",
                "Docstring keyword extraction failed",
                {"extract_keywords": True},
            ),
            (
                "_extract_string_keywords",
                "String keyword extraction failed",
                {"extract_string_keywords": True},
            ),
            ("_compute_timestamps", "Timestamp computation failed", {"compute_timestamps": True}),
            ("_extract_cochange", "Co-change analysis failed", {"extract_cochange": True}),
        ],
    )
    def test_extraction_failures_are_graceful(
        self, verbose_indexer, tmp_path, capsys, method_to_mock, error_msg, index_kwargs
    ):
        """Should handle extraction failures gracefully without failing overall."""
        repo = tmp_path / "repo"
        repo.mkdir()
        output = tmp_path / "index.json"
        scip_file = self._create_scip_file(tmp_path)

        with patch.object(verbose_indexer, "_ensure_scip_python_installed"):
            with patch.object(verbose_indexer, "_run_scip_python", return_value=scip_file):
                with patch.object(verbose_indexer, method_to_mock) as mock_method:
                    mock_method.side_effect = Exception(error_msg)
                    with patch(
                        "cicada.languages.python.indexer.read_keyword_extraction_config",
                        return_value=("regular", "lemminflect"),
                    ):
                        with patch("cicada.extractors.keyword.RegularKeywordExtractor"):
                            with patch("cicada.keyword_expander.KeywordExpander"):
                                result = verbose_indexer.incremental_index_repository(
                                    repo_path=str(repo),
                                    output_path=str(output),
                                    verbose=True,
                                    **index_kwargs,
                                )

        captured = capsys.readouterr()
        assert error_msg in captured.out
        assert result["success"] is True
        if scip_file.exists():
            scip_file.unlink()

    def test_scip_conversion_and_save_failures(self, verbose_indexer, tmp_path, capsys):
        """Should handle SCIP conversion and save failures."""
        repo = tmp_path / "repo"
        repo.mkdir()
        output = tmp_path / "index.json"
        scip_file = self._create_scip_file(tmp_path)

        with patch.object(verbose_indexer, "_ensure_scip_python_installed"):
            with patch.object(verbose_indexer, "_run_scip_python", return_value=scip_file):
                # Test conversion failure
                with patch("cicada.languages.python.indexer.SCIPConverter") as mock_converter:
                    mock_converter.return_value.convert.side_effect = Exception("Conversion failed")
                    result = verbose_indexer.index_repository(repo, output, verbose=True)
                    assert result["success"] is False
                    assert "Failed to convert SCIP" in result["errors"][0]

        # Test save failure
        scip_file = self._create_scip_file(tmp_path)
        with patch.object(verbose_indexer, "_ensure_scip_python_installed"):
            with patch.object(verbose_indexer, "_run_scip_python", return_value=scip_file):
                with patch.object(verbose_indexer, "_save_index") as mock_save:
                    mock_save.side_effect = Exception("Save failed")
                    result = verbose_indexer.index_repository(repo, output, verbose=True)
                    assert result["success"] is False
                    assert "Failed to save index" in result["errors"][0]

    def test_keyword_extractor_init_and_hash_save_failures(self, verbose_indexer, tmp_path, capsys):
        """Should handle keyword extractor init and hash save failures gracefully."""
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "test.py").touch()
        output = tmp_path / "index.json"
        scip_file = self._create_scip_file(tmp_path)

        with patch.object(verbose_indexer, "_ensure_scip_python_installed"):
            with patch.object(verbose_indexer, "_run_scip_python", return_value=scip_file):
                # Test keyword extractor init failure
                with patch(
                    "cicada.languages.python.indexer.read_keyword_extraction_config"
                ) as mock_config:
                    mock_config.side_effect = Exception("Config error")
                    result = verbose_indexer.incremental_index_repository(
                        repo_path=str(repo),
                        output_path=str(output),
                        extract_keywords=True,
                        verbose=True,
                    )
                    captured = capsys.readouterr()
                    assert "Keyword extractor initialization failed" in captured.out
                    assert result["success"] is True

        # Test hash save failure
        scip_file = self._create_scip_file(tmp_path)
        with patch.object(verbose_indexer, "_ensure_scip_python_installed"):
            with patch.object(verbose_indexer, "_run_scip_python", return_value=scip_file):
                with patch("cicada.languages.python.indexer.save_file_hashes") as mock_save:
                    mock_save.side_effect = Exception("Hash save failed")
                    result = verbose_indexer.index_repository(repo, output, verbose=True)
                    captured = capsys.readouterr()
                    assert "Failed to save file hashes" in captured.out
                    assert result["success"] is True

    def test_bert_extractor_and_change_detection_logging(self, tmp_path, capsys):
        """Should use BERT extractor when configured and log change detection."""
        indexer = PythonSCIPIndexer(verbose=False)
        verbose_indexer = PythonSCIPIndexer(verbose=True)
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "new.py").touch()
        output = tmp_path / "index.json"

        scip_index = scip_pb2.Index()
        scip_index.documents.add()
        scip_file = tmp_path / "temp.scip"
        with open(scip_file, "wb") as f:
            f.write(scip_index.SerializeToString())

        # Test BERT extractor
        with patch.object(indexer, "_ensure_scip_python_installed"):
            with patch.object(indexer, "_run_scip_python", return_value=scip_file):
                with patch(
                    "cicada.languages.python.indexer.read_keyword_extraction_config",
                    return_value=("bert", "fasttext"),
                ):
                    with patch("cicada.extractors.keybert.KeyBERTExtractor") as mock_bert:
                        with patch("cicada.keyword_expander.KeywordExpander"):
                            indexer.incremental_index_repository(
                                repo_path=str(repo),
                                output_path=str(output),
                                extract_keywords=True,
                                verbose=False,
                            )
                            mock_bert.assert_called_once()

        # Test change detection logging
        scip_file = tmp_path / "temp2.scip"
        with open(scip_file, "wb") as f:
            f.write(scip_index.SerializeToString())
        with patch.object(verbose_indexer, "_ensure_scip_python_installed"):
            with patch.object(verbose_indexer, "_run_scip_python", return_value=scip_file):
                with patch(
                    "cicada.languages.python.indexer.detect_file_changes",
                    return_value=(["new.py"], ["modified.py"], ["deleted.py"]),
                ):
                    verbose_indexer.index_repository(repo, output, verbose=True)
                    captured = capsys.readouterr()
                    assert "Changes detected: 1 new, 1 modified, 1 deleted" in captured.out


class TestHelperMethodEdgeCases:
    """Tests for edge cases in helper methods."""

    @pytest.fixture
    def indexer(self):
        return PythonSCIPIndexer(verbose=False)

    @pytest.fixture
    def verbose_indexer(self):
        return PythonSCIPIndexer(verbose=True)

    def test_compute_timestamps_edge_cases(self, indexer, verbose_indexer, tmp_path, capsys):
        """Should handle various timestamp computation edge cases."""
        from unittest.mock import MagicMock

        repo = tmp_path / "repo"
        repo.mkdir()

        # Test missing file path
        index = {"modules": {"TestModule": {"functions": [{"name": "func", "line": 5}]}}}
        with patch("cicada.languages.python.indexer.GitHelper") as mock_git:
            mock_git.return_value = MagicMock()
            indexer._compute_timestamps(index, repo)
            mock_git.return_value.get_functions_evolution_batch.assert_not_called()

        # Test batch query failure
        index = {
            "modules": {
                "TestModule": {"file": "test.py", "functions": [{"name": "func", "line": 5}]}
            }
        }
        with patch("cicada.languages.python.indexer.GitHelper") as mock_git:
            mock_git.return_value.get_functions_evolution_batch.side_effect = Exception("Git error")
            verbose_indexer._compute_timestamps(index, repo)
            captured = capsys.readouterr()
            assert "Failed to compute timestamps" in captured.out

        # Test partial evolution data
        with patch("cicada.languages.python.indexer.GitHelper") as mock_git:
            mock_git.return_value.get_functions_evolution_batch.return_value = {
                "func": {"created_at": {"date": "2024-01-01"}}
            }
            indexer._compute_timestamps(index, repo)
            func = index["modules"]["TestModule"]["functions"][0]
            assert "created_at" in func
            assert "last_modified_at" not in func

    def test_extract_string_keywords_edge_cases(self, indexer, tmp_path):
        """Should handle various string keyword extraction edge cases."""
        from unittest.mock import MagicMock

        repo = tmp_path / "repo"
        repo.mkdir()
        keyword_extractor = MagicMock()
        keyword_expander = MagicMock()

        # Test missing file path
        index = {"modules": {"TestModule": {"functions": []}}}
        indexer._extract_string_keywords(index, repo, keyword_extractor, keyword_expander)
        keyword_extractor.extract_keywords.assert_not_called()

        # Test empty string text
        (repo / "test.py").write_text('x = ""')
        index = {"modules": {"TestModule": {"file": "test.py", "functions": []}}}
        indexer._extract_string_keywords(index, repo, keyword_extractor, keyword_expander)
        keyword_extractor.extract_keywords.assert_not_called()

    def test_extract_cochange_missing_file_path(self, indexer, tmp_path):
        """Should skip modules without file path in co-change analysis."""
        from unittest.mock import MagicMock

        repo = tmp_path / "repo"
        repo.mkdir()
        index = {"modules": {"TestModule": {"functions": []}}}

        with patch("cicada.languages.python.indexer.CoChangeAnalyzer") as mock_analyzer:
            mock_analyzer.return_value.analyze_repository.return_value = {
                "metadata": {"file_pairs": 0, "function_pairs": 0, "commit_count": 0},
                "file_pairs": {},
            }
            mock_analyzer.find_cochange_pairs = MagicMock(return_value=[])
            indexer._extract_cochange(index, repo)
            assert "cochange_files" not in index["modules"]["TestModule"]

    def test_run_scip_python_verbose_messages(self, verbose_indexer, tmp_path, capsys):
        """Should print verbose messages during SCIP execution."""
        repo = tmp_path / "repo"
        repo.mkdir()

        mock_scip_content = scip_pb2.Index()
        scip_file_path = tmp_path / "test.scip"
        with open(scip_file_path, "wb") as f:
            f.write(mock_scip_content.SerializeToString())

        with patch.object(SCIPPythonInstaller, "get_scip_python_path", return_value="/fake/scip"):
            with patch("cicada.languages.python.indexer.subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0)
                with patch("tempfile.NamedTemporaryFile") as mock_temp:
                    mock_temp.return_value.__enter__.return_value.name = str(scip_file_path)
                    verbose_indexer._run_scip_python(repo)
                    captured = capsys.readouterr()
                    assert "Running SCIP" in captured.out
                    assert "Created temporary pyrightconfig.json" in captured.out


class TestPythonIndexerIntegration:
    """Integration tests for Python indexer with all features."""

    @pytest.fixture
    def indexer(self):
        """Create a PythonSCIPIndexer instance."""
        return PythonSCIPIndexer(verbose=False)

    def test_index_with_all_features_enabled(self, indexer, tmp_path):
        """Should index with all features enabled."""
        from unittest.mock import MagicMock

        repo = tmp_path / "repo"
        repo.mkdir()
        py_file = repo / "test.py"
        py_file.write_text('def test():\n    return "SELECT * FROM users"')

        output = tmp_path / "index.json"

        scip_index = scip_pb2.Index()
        doc = scip_index.documents.add()
        doc.relative_path = "test.py"

        with patch.object(indexer, "_ensure_scip_python_installed"):
            with patch.object(indexer, "_run_scip_python") as mock_run:
                scip_file = tmp_path / "temp.scip"
                with open(scip_file, "wb") as f:
                    f.write(scip_index.SerializeToString())
                mock_run.return_value = scip_file

                # Mock all feature extractors
                with patch.object(indexer, "_extract_string_keywords") as mock_strings:
                    with patch.object(indexer, "_compute_timestamps") as mock_timestamps:
                        with patch.object(indexer, "_extract_cochange") as mock_cochange:
                            try:
                                result = indexer.incremental_index_repository(
                                    repo_path=str(repo),
                                    output_path=str(output),
                                    extract_keywords=True,
                                    extract_string_keywords=True,
                                    compute_timestamps=True,
                                    extract_cochange=True,
                                    verbose=False,
                                )

                                assert result["success"] is True
                                mock_strings.assert_called_once()
                                mock_timestamps.assert_called_once()
                                mock_cochange.assert_called_once()
                            finally:
                                if scip_file.exists():
                                    scip_file.unlink()


class TestInterruptibleEnrichmentPhases:
    """Test graceful interruption handling during enrichment phases."""

    @pytest.fixture
    def indexer(self):
        """Create a PythonSCIPIndexer instance."""
        return PythonSCIPIndexer(verbose=False)

    @pytest.fixture
    def verbose_indexer(self):
        """Create a verbose indexer."""
        return PythonSCIPIndexer(verbose=True)

    def test_extract_string_keywords_interrupt_saves_partial(self, indexer, tmp_path):
        """Should save partial progress when KeyboardInterrupt during string keyword extraction."""
        # Create test modules
        index = {
            "modules": {
                "module1": {"file": "file1.py"},
                "module2": {"file": "file2.py"},
                "module3": {"file": "file3.py"},
            }
        }

        # Create test files
        for i in range(1, 4):
            (tmp_path / f"file{i}.py").write_text(f"var{i} = 'test string {i}'")

        # Mock keyword extractor that raises KeyboardInterrupt on second call
        call_count = [0]

        def mock_extract(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                raise KeyboardInterrupt()
            return {"top_keywords": [("test", 0.9)]}

        mock_extractor = Mock()
        mock_extractor.extract_keywords = mock_extract

        # Run extraction
        processed = indexer._extract_string_keywords(index, tmp_path, mock_extractor, None)

        # Should have processed at least 1 module before interrupt
        assert processed >= 1
        assert indexer._interrupted is True

    def test_extract_string_keywords_checks_interrupted_flag(self, indexer, tmp_path):
        """Should stop early if _interrupted flag is already set."""
        index = {
            "modules": {
                "module1": {"file": "file1.py"},
                "module2": {"file": "file2.py"},
            }
        }

        # Set interrupted flag before starting
        indexer._interrupted = True

        mock_extractor = Mock()
        mock_extractor.extract_keywords = Mock(return_value={"top_keywords": []})

        processed = indexer._extract_string_keywords(index, tmp_path, mock_extractor, None)

        # Should stop immediately without processing any modules
        assert processed == 0
        mock_extractor.extract_keywords.assert_not_called()

    def test_enrichment_interrupt_saves_index(self, indexer, tmp_path):
        """Should save index even when enrichment phase is interrupted."""
        repo = tmp_path / "repo"
        repo.mkdir()
        output = tmp_path / "index.json"

        scip_index = scip_pb2.Index()
        doc = scip_index.documents.add()
        doc.relative_path = "test.py"

        with patch.object(indexer, "_ensure_scip_python_installed"):
            with patch.object(indexer, "_run_scip_python") as mock_run:
                scip_file = tmp_path / "temp.scip"
                with open(scip_file, "wb") as f:
                    f.write(scip_index.SerializeToString())
                mock_run.return_value = scip_file

                # Mock string extraction to raise KeyboardInterrupt
                with patch.object(
                    indexer, "_extract_string_keywords", side_effect=KeyboardInterrupt
                ):
                    try:
                        result = indexer.incremental_index_repository(
                            repo_path=str(repo),
                            output_path=str(output),
                            extract_string_keywords=True,
                            compute_timestamps=True,
                            verbose=False,
                        )

                        # Should still succeed and save
                        assert result["success"] is True
                        assert result["interrupted"] is True
                        assert "string keywords (partial)" in result["skipped_phases"]
                        assert "timestamp computation" in result["skipped_phases"]
                        assert output.exists()
                    finally:
                        if scip_file.exists():
                            scip_file.unlink()

    def test_enrichment_interrupt_skips_remaining_phases(self, indexer, tmp_path):
        """Should skip remaining enrichment phases after interruption."""
        repo = tmp_path / "repo"
        repo.mkdir()
        output = tmp_path / "index.json"

        scip_index = scip_pb2.Index()
        doc = scip_index.documents.add()
        doc.relative_path = "test.py"

        with patch.object(indexer, "_ensure_scip_python_installed"):
            with patch.object(indexer, "_run_scip_python") as mock_run:
                scip_file = tmp_path / "temp.scip"
                with open(scip_file, "wb") as f:
                    f.write(scip_index.SerializeToString())
                mock_run.return_value = scip_file

                with patch.object(
                    indexer, "_extract_string_keywords", side_effect=KeyboardInterrupt
                ):
                    with patch.object(indexer, "_compute_timestamps") as mock_ts:
                        with patch.object(indexer, "_extract_cochange") as mock_cc:
                            try:
                                result = indexer.incremental_index_repository(
                                    repo_path=str(repo),
                                    output_path=str(output),
                                    extract_string_keywords=True,
                                    compute_timestamps=True,
                                    extract_cochange=True,
                                    verbose=False,
                                )

                                # Timestamps and cochange should NOT be called
                                mock_ts.assert_not_called()
                                mock_cc.assert_not_called()
                                assert result["interrupted"] is True
                            finally:
                                if scip_file.exists():
                                    scip_file.unlink()

    def test_interrupted_flag_reset_on_new_run(self, indexer, tmp_path):
        """Should reset _interrupted flag when starting new indexing run."""
        # Set interrupted flag
        indexer._interrupted = True

        repo = tmp_path / "repo"
        repo.mkdir()
        output = tmp_path / "index.json"

        scip_index = scip_pb2.Index()
        doc = scip_index.documents.add()
        doc.relative_path = "test.py"

        with patch.object(indexer, "_ensure_scip_python_installed"):
            with patch.object(indexer, "_run_scip_python") as mock_run:
                scip_file = tmp_path / "temp.scip"
                with open(scip_file, "wb") as f:
                    f.write(scip_index.SerializeToString())
                mock_run.return_value = scip_file

                try:
                    result = indexer.incremental_index_repository(
                        repo_path=str(repo),
                        output_path=str(output),
                        verbose=False,
                    )

                    # Flag should have been reset at start
                    assert result["success"] is True
                    assert result.get("interrupted", False) is False
                finally:
                    if scip_file.exists():
                        scip_file.unlink()

    def test_verbose_output_on_interrupt(self, verbose_indexer, tmp_path, capsys):
        """Should print informative messages when interrupted."""
        repo = tmp_path / "repo"
        repo.mkdir()
        output = tmp_path / "index.json"

        scip_index = scip_pb2.Index()
        doc = scip_index.documents.add()
        doc.relative_path = "test.py"

        with patch.object(verbose_indexer, "_ensure_scip_python_installed"):
            with patch.object(verbose_indexer, "_run_scip_python") as mock_run:
                scip_file = tmp_path / "temp.scip"
                with open(scip_file, "wb") as f:
                    f.write(scip_index.SerializeToString())
                mock_run.return_value = scip_file

                with patch.object(
                    verbose_indexer, "_compute_timestamps", side_effect=KeyboardInterrupt
                ):
                    try:
                        verbose_indexer.incremental_index_repository(
                            repo_path=str(repo),
                            output_path=str(output),
                            compute_timestamps=True,
                            verbose=True,
                        )

                        captured = capsys.readouterr()
                        assert "Interrupted during timestamp computation" in captured.out
                        assert "Partial index saved" in captured.out
                        assert "Skipped phases" in captured.out
                    finally:
                        if scip_file.exists():
                            scip_file.unlink()

    def test_run_interruptible_phase_handles_exception(self, indexer):
        """Test that _run_interruptible_phase handles generic exceptions."""
        skipped_phases = []

        def failing_phase():
            raise ValueError("Test error")

        # Should return False but not set _interrupted
        result = indexer._run_interruptible_phase(
            "test phase",
            failing_phase,
            skipped_phases,
        )

        assert result is False
        assert indexer._interrupted is False
        assert skipped_phases == []

    def test_run_interruptible_phase_handles_exception_verbose(self, indexer, capsys):
        """Test exception handling in verbose mode."""
        indexer.verbose = True
        skipped_phases = []

        def failing_phase():
            raise RuntimeError("Something went wrong")

        result = indexer._run_interruptible_phase(
            "timestamp computation",
            failing_phase,
            skipped_phases,
        )

        assert result is False
        captured = capsys.readouterr()
        assert "Warning: Timestamp computation failed: Something went wrong" in captured.out
