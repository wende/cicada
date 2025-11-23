"""Tests for GenericSCIPIndexer base class."""

import subprocess
from pathlib import Path

import pytest

from cicada.languages.scip.indexer import GenericSCIPIndexer


class TestGenericSCIPIndexer:
    """Test GenericSCIPIndexer base class functionality."""

    @pytest.fixture
    def mock_indexer(self):
        """Create a mock subclass of GenericSCIPIndexer for testing."""

        class MockSCIPIndexer(GenericSCIPIndexer):
            """Mock implementation for testing."""

            def get_language_name(self) -> str:
                return "mock"

            def get_file_extensions(self) -> list[str]:
                return [".mock", ".test"]

            def get_excluded_dirs(self) -> list[str]:
                return ["excluded", ".git", "node_modules"]

            def _run_scip_indexer(self, repo_path: Path) -> Path:
                # Return a mock path
                return repo_path / "index.scip"

        return MockSCIPIndexer(verbose=False)

    @pytest.fixture
    def test_repo(self, tmp_path):
        """Create a test repository with various files."""
        # Create directory structure
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "subdir").mkdir()
        (tmp_path / "excluded").mkdir()
        (tmp_path / ".git").mkdir()
        (tmp_path / "node_modules").mkdir()

        # Create source files
        (tmp_path / "file1.mock").write_text("mock content")
        (tmp_path / "file2.test").write_text("test content")
        (tmp_path / "src" / "file3.mock").write_text("mock content")
        (tmp_path / "src" / "subdir" / "file4.test").write_text("test content")

        # Create files in excluded directories
        (tmp_path / "excluded" / "excluded.mock").write_text("should be excluded")
        (tmp_path / ".git" / "config.mock").write_text("should be excluded")
        (tmp_path / "node_modules" / "package.mock").write_text("should be excluded")

        # Create non-source files
        (tmp_path / "README.md").write_text("readme")
        (tmp_path / "src" / "data.json").write_text("{}")

        return tmp_path

    def test_find_source_files_basic(self, mock_indexer, test_repo):
        """Should find all source files with matching extensions."""
        files = mock_indexer._find_source_files(test_repo)
        file_names = [f.name for f in files]

        # Should find .mock and .test files
        assert "file1.mock" in file_names
        assert "file2.test" in file_names
        assert "file3.mock" in file_names
        assert "file4.test" in file_names

        # Should have exactly 4 files
        assert len(files) == 4

    def test_find_source_files_excludes_directories(self, mock_indexer, test_repo):
        """Should exclude files from excluded directories."""
        files = mock_indexer._find_source_files(test_repo)
        file_paths = [str(f) for f in files]

        # Should NOT find files in excluded directories
        assert all("excluded" not in path for path in file_paths)
        assert all(".git" not in path for path in file_paths)
        assert all("node_modules" not in path for path in file_paths)

    def test_find_source_files_only_matching_extensions(self, mock_indexer, test_repo):
        """Should only return files with specified extensions."""
        files = mock_indexer._find_source_files(test_repo)
        file_names = [f.name for f in files]

        # Should NOT find non-source files
        assert "README.md" not in file_names
        assert "data.json" not in file_names

        # All found files should have valid extensions
        valid_extensions = mock_indexer.get_file_extensions()
        for f in files:
            assert any(f.suffix == ext for ext in valid_extensions)

    def test_find_source_files_recursive(self, mock_indexer, test_repo):
        """Should recursively find files in subdirectories."""
        files = mock_indexer._find_source_files(test_repo)
        file_paths = [str(f.relative_to(test_repo)) for f in files]

        # Should find files in nested directories
        assert any("src/file3.mock" in path for path in file_paths)
        assert any("src/subdir/file4.test" in path for path in file_paths)

    def test_find_source_files_returns_path_objects(self, mock_indexer, test_repo):
        """Should return Path objects, not strings."""
        files = mock_indexer._find_source_files(test_repo)

        assert all(isinstance(f, Path) for f in files)

    def test_find_source_files_empty_directory(self, mock_indexer, tmp_path):
        """Should return empty list for directory with no source files."""
        files = mock_indexer._find_source_files(tmp_path)
        assert files == []

    def test_find_source_files_with_multiple_extensions(self, tmp_path):
        """Should find files matching any of the specified extensions."""

        class MultiExtIndexer(GenericSCIPIndexer):
            def get_language_name(self) -> str:
                return "multi"

            def get_file_extensions(self) -> list[str]:
                return [".py", ".pyx", ".pyi"]

            def get_excluded_dirs(self) -> list[str]:
                return []

            def _run_scip_indexer(self, repo_path: Path) -> Path:
                return repo_path / "index.scip"

        indexer = MultiExtIndexer(verbose=False)

        # Create files with different extensions
        (tmp_path / "file1.py").write_text("python")
        (tmp_path / "file2.pyx").write_text("cython")
        (tmp_path / "file3.pyi").write_text("stub")
        (tmp_path / "file4.txt").write_text("text")

        files = indexer._find_source_files(tmp_path)
        file_names = [f.name for f in files]

        assert "file1.py" in file_names
        assert "file2.pyx" in file_names
        assert "file3.pyi" in file_names
        assert "file4.txt" not in file_names
        assert len(files) == 3

    def test_find_source_files_nested_excluded_directories(self, mock_indexer, tmp_path):
        """Should exclude nested excluded directories."""
        # Create nested structure with excluded dirs at various levels
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "node_modules").mkdir()
        (tmp_path / "src" / "valid").mkdir()

        (tmp_path / "file.mock").write_text("content")
        (tmp_path / "src" / "valid.mock").write_text("content")
        (tmp_path / "src" / "node_modules" / "excluded.mock").write_text("content")

        files = mock_indexer._find_source_files(tmp_path)
        file_names = [f.name for f in files]

        # Should find root and src/valid files
        assert "file.mock" in file_names
        assert "valid.mock" in file_names

        # Should NOT find files in nested excluded dir
        assert "excluded.mock" not in file_names
        assert len(files) == 2

    def test_find_source_files_case_sensitive_extensions(self, mock_indexer, tmp_path):
        """Should match extensions case-sensitively."""
        # Create files with different case extensions
        (tmp_path / "lower.mock").write_text("content")
        (tmp_path / "upper.MOCK").write_text("content")

        files = mock_indexer._find_source_files(tmp_path)
        file_names = [f.name for f in files]

        # Should only match exact case (extensions specified as lowercase)
        assert "lower.mock" in file_names
        assert "upper.MOCK" not in file_names

    def test_abstract_methods_must_be_implemented(self):
        """Should require subclasses to implement abstract methods."""
        # Try to instantiate without implementing abstract methods
        with pytest.raises(TypeError) as exc_info:

            class IncompleteIndexer(GenericSCIPIndexer):
                pass

            IncompleteIndexer()

        # Error should mention abstract methods
        error_msg = str(exc_info.value)
        assert "abstract" in error_msg.lower()

    def test_initialization_sets_verbose(self):
        """Should correctly set verbose flag during initialization."""

        class TestIndexer(GenericSCIPIndexer):
            def get_language_name(self) -> str:
                return "test"

            def get_file_extensions(self) -> list[str]:
                return [".test"]

            def get_excluded_dirs(self) -> list[str]:
                return []

            def _run_scip_indexer(self, repo_path: Path) -> Path:
                return repo_path / "index.scip"

        # Test default (False)
        indexer = TestIndexer()
        assert indexer.verbose is False

        # Test explicit True
        verbose_indexer = TestIndexer(verbose=True)
        assert verbose_indexer.verbose is True

    def test_run_scip_command_success_returns_path_and_prints_verbose(
        self, tmp_path, capsys, monkeypatch
    ):
        """_run_scip_command should return path and emit verbose output."""

        class TestIndexer(GenericSCIPIndexer):
            def get_language_name(self) -> str:
                return "test"

            def get_file_extensions(self) -> list[str]:
                return [".test"]

            def get_excluded_dirs(self) -> list[str]:
                return []

            def _run_scip_indexer(self, repo_path: Path) -> Path:  # pragma: no cover
                raise NotImplementedError

        run_calls: dict[str, object] = {}

        def fake_run(*args, **kwargs):
            run_calls["args"] = args
            run_calls["kwargs"] = kwargs

            class Result:
                returncode = 0
                stdout = "ok"
                stderr = ""

            # Simulate scip-typescript style output
            output_path = tmp_path / "index.scip"
            output_path.write_bytes(b"dummy scip contents")
            return Result()

        monkeypatch.setattr(subprocess, "run", fake_run)

        indexer = TestIndexer(verbose=True)
        output_path = tmp_path / "index.scip"
        result = indexer._run_scip_command(
            repo_path=tmp_path, command=["scip"], output_path=output_path
        )

        assert result == output_path
        assert result.exists()
        assert run_calls
        captured = capsys.readouterr()
        assert "Running: scip" in captured.out

    def test_run_scip_command_non_zero_exit_raises_runtime_error(self, tmp_path, monkeypatch):
        """_run_scip_command should raise when subprocess fails."""

        class TestIndexer(GenericSCIPIndexer):
            def get_language_name(self) -> str:
                return "test"

            def get_file_extensions(self) -> list[str]:
                return [".test"]

            def get_excluded_dirs(self) -> list[str]:
                return []

            def _run_scip_indexer(self, repo_path: Path) -> Path:  # pragma: no cover
                raise NotImplementedError

        def fake_run(*_args, **_kwargs):
            class Result:
                returncode = 1
                stdout = ""
                stderr = "error"

            return Result()

        monkeypatch.setattr(subprocess, "run", fake_run)

        indexer = TestIndexer(verbose=False)
        with pytest.raises(RuntimeError) as exc_info:
            indexer._run_scip_command(
                repo_path=tmp_path, command=["scip"], output_path=tmp_path / "index.scip"
            )

        assert "error" in str(exc_info.value)

    def test_run_scip_command_timeout_cleans_output(self, tmp_path, monkeypatch):
        """Timeouts should raise and clean temp outputs created by helper."""

        class TestIndexer(GenericSCIPIndexer):
            def get_language_name(self) -> str:
                return "test"

            def get_file_extensions(self) -> list[str]:
                return [".test"]

            def get_excluded_dirs(self) -> list[str]:
                return []

            def _run_scip_indexer(self, repo_path: Path) -> Path:  # pragma: no cover
                raise NotImplementedError

        output_path = tmp_path / "index.scip"
        output_path.write_bytes(b"stale")

        def fake_run(*_args, **_kwargs):
            raise subprocess.TimeoutExpired(cmd="scip", timeout=10)

        monkeypatch.setattr(subprocess, "run", fake_run)

        indexer = TestIndexer(verbose=False)
        with pytest.raises(RuntimeError) as exc_info:
            indexer._run_scip_command(repo_path=tmp_path, command=["scip"], output_path=output_path)

        assert "scip indexing timed out" in str(exc_info.value).lower()
        assert not output_path.exists()

    def test_run_scip_command_missing_output_raises(self, tmp_path, monkeypatch):
        """Should raise when command succeeds but output is missing."""

        class TestIndexer(GenericSCIPIndexer):
            def get_language_name(self) -> str:
                return "test"

            def get_file_extensions(self) -> list[str]:
                return [".test"]

            def get_excluded_dirs(self) -> list[str]:
                return []

            def _run_scip_indexer(self, repo_path: Path) -> Path:  # pragma: no cover
                raise NotImplementedError

        def fake_run(*_args, **_kwargs):
            class Result:
                returncode = 0
                stdout = ""
                stderr = ""

            return Result()

        monkeypatch.setattr(subprocess, "run", fake_run)

        indexer = TestIndexer(verbose=False)
        with pytest.raises(RuntimeError) as exc_info:
            indexer._run_scip_command(
                repo_path=tmp_path, command=["scip"], output_path=tmp_path / "index.scip"
            )

        assert "did not generate" in str(exc_info.value)
