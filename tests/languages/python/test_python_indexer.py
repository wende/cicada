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
        keyword_expander.expand_keywords.return_value = {"database": 0.7}

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
