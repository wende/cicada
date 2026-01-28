# DUPLICATED FROM: tests/test_base_indexer.py
# This test file was duplicated from the main cicada tests.
# Once these tests pass independently, the originals can be cleaned up.
"""
Tests for cicada_mcp_core.BaseIndexer

Tests cover the concrete methods of BaseIndexer and verify the interface contract.
"""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from cicada_mcp_core import BaseIndexer


# ============================================================================
# SECTION 1: Mock Implementation for Testing
# ============================================================================


class MockIndexer(BaseIndexer):
    """Concrete implementation of BaseIndexer for testing."""

    def get_language_name(self) -> str:
        return "mock"

    def get_file_extensions(self) -> list[str]:
        return [".mock", ".test"]

    def get_excluded_dirs(self) -> list[str]:
        return ["__pycache__", ".venv", "node_modules"]

    def index_repository(
        self,
        repo_path: str | Path,
        output_path: str | Path,
        force: bool = False,
        verbose: bool = False,
        config_path: str | Path | None = None,
    ) -> dict:
        """Minimal implementation that returns success."""
        return {
            "success": True,
            "modules_count": 0,
            "functions_count": 0,
            "files_indexed": 0,
            "errors": [],
        }


# ============================================================================
# SECTION 2: Test _find_source_files
# ============================================================================


class TestFindSourceFiles:
    """Test BaseIndexer._find_source_files method."""

    def test_find_source_files_basic(self):
        """Test finding source files with basic structure."""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create test files
            (tmpdir_path / "file1.mock").touch()
            (tmpdir_path / "file2.test").touch()
            (tmpdir_path / "file3.txt").touch()  # Should be excluded

            indexer = MockIndexer()
            found_files = indexer._find_source_files(tmpdir_path)

            # Should find both .mock and .test files
            assert len(found_files) == 2
            assert tmpdir_path / "file1.mock" in found_files
            assert tmpdir_path / "file2.test" in found_files
            assert tmpdir_path / "file3.txt" not in found_files

    def test_find_source_files_nested(self):
        """Test finding source files in nested directories."""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create nested structure
            (tmpdir_path / "src").mkdir()
            (tmpdir_path / "src" / "module1.mock").touch()
            (tmpdir_path / "src" / "deep").mkdir()
            (tmpdir_path / "src" / "deep" / "module2.test").touch()

            indexer = MockIndexer()
            found_files = indexer._find_source_files(tmpdir_path)

            assert len(found_files) == 2
            assert tmpdir_path / "src" / "module1.mock" in found_files
            assert tmpdir_path / "src" / "deep" / "module2.test" in found_files

    def test_find_source_files_excluded_dirs(self):
        """Test that excluded directories are skipped."""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create files in excluded directories
            (tmpdir_path / "src").mkdir()
            (tmpdir_path / "src" / "file.mock").touch()
            (tmpdir_path / "__pycache__").mkdir()
            (tmpdir_path / "__pycache__" / "file.mock").touch()
            (tmpdir_path / ".venv").mkdir()
            (tmpdir_path / ".venv" / "file.test").touch()

            indexer = MockIndexer()
            found_files = indexer._find_source_files(tmpdir_path)

            # Should only find file in src directory
            assert len(found_files) == 1
            assert tmpdir_path / "src" / "file.mock" in found_files

    def test_find_source_files_nested_excluded_dirs(self):
        """Test excluded directories in nested paths."""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create nested excluded directory
            (tmpdir_path / "src").mkdir()
            (tmpdir_path / "src" / "file1.mock").touch()
            (tmpdir_path / "src" / "__pycache__").mkdir()
            (tmpdir_path / "src" / "__pycache__" / "file2.mock").touch()

            indexer = MockIndexer()
            found_files = indexer._find_source_files(tmpdir_path)

            # Should only find file1.mock, not the one in __pycache__
            assert len(found_files) == 1
            assert tmpdir_path / "src" / "file1.mock" in found_files

    def test_find_source_files_sorted_output(self):
        """Test that results are sorted."""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create multiple files
            (tmpdir_path / "z_file.mock").touch()
            (tmpdir_path / "a_file.mock").touch()
            (tmpdir_path / "m_file.test").touch()

            indexer = MockIndexer()
            found_files = indexer._find_source_files(tmpdir_path)

            # Verify files are sorted
            assert found_files == sorted(found_files)

    def test_find_source_files_empty_directory(self):
        """Test with empty directory."""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            indexer = MockIndexer()
            found_files = indexer._find_source_files(tmpdir_path)

            assert found_files == []

    def test_find_source_files_only_excluded_dirs(self):
        """Test directory with only excluded directories."""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "__pycache__").mkdir()
            (tmpdir_path / "__pycache__" / "file.mock").touch()
            (tmpdir_path / ".venv").mkdir()
            (tmpdir_path / ".venv" / "file.test").touch()

            indexer = MockIndexer()
            found_files = indexer._find_source_files(tmpdir_path)

            assert found_files == []


# ============================================================================
# SECTION 3: Test should_index_file
# ============================================================================


class TestShouldIndexFile:
    """Test BaseIndexer.should_index_file method."""

    def test_should_index_file_default_returns_true(self):
        """Test that default implementation returns True for all files."""
        indexer = MockIndexer()

        assert indexer.should_index_file(Path("any_file.mock")) is True
        assert indexer.should_index_file(Path("/path/to/file.test")) is True
        assert indexer.should_index_file(Path("nonexistent.mock")) is True

    def test_should_index_file_with_custom_override(self):
        """Test that method can be overridden."""

        class CustomIndexer(MockIndexer):
            def should_index_file(self, file_path: Path) -> bool:
                # Don't index files starting with underscore
                return not file_path.name.startswith("_")

        indexer = CustomIndexer()
        assert indexer.should_index_file(Path("file.mock")) is True
        assert indexer.should_index_file(Path("_file.mock")) is False
        assert indexer.should_index_file(Path("_cached.mock")) is False


# ============================================================================
# SECTION 4: Test get_default_config
# ============================================================================


class TestGetDefaultConfig:
    """Test BaseIndexer.get_default_config method."""

    def test_get_default_config_structure(self):
        """Test that default config has expected structure."""
        indexer = MockIndexer()
        config = indexer.get_default_config()

        assert isinstance(config, dict)
        assert "language" in config
        assert "file_extensions" in config
        assert "excluded_dirs" in config

    def test_get_default_config_values(self):
        """Test that config values match indexer properties."""
        indexer = MockIndexer()
        config = indexer.get_default_config()

        assert config["language"] == "mock"
        assert config["file_extensions"] == [".mock", ".test"]
        assert config["excluded_dirs"] == ["__pycache__", ".venv", "node_modules"]

    def test_get_default_config_custom_language(self):
        """Test default config for different language."""

        class PythonMockIndexer(MockIndexer):
            def get_language_name(self) -> str:
                return "python"

            def get_file_extensions(self) -> list[str]:
                return [".py", ".pyi"]

            def get_excluded_dirs(self) -> list[str]:
                return ["__pycache__", ".venv", "*.egg-info"]

        indexer = PythonMockIndexer()
        config = indexer.get_default_config()

        assert config["language"] == "python"
        assert config["file_extensions"] == [".py", ".pyi"]
        assert "__pycache__" in config["excluded_dirs"]

    def test_get_default_config_override(self):
        """Test that get_default_config can be overridden."""

        class CustomConfigIndexer(MockIndexer):
            def get_default_config(self) -> dict:
                base_config = super().get_default_config()
                base_config["custom_setting"] = "value"
                return base_config

        indexer = CustomConfigIndexer()
        config = indexer.get_default_config()

        assert config["custom_setting"] == "value"


# ============================================================================
# SECTION 5: Test Abstract Method Requirements
# ============================================================================


class TestAbstractMethodRequirements:
    """Test that abstract methods must be implemented."""

    def test_cannot_instantiate_base_indexer_directly(self):
        """Test that BaseIndexer cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseIndexer()

    def test_missing_language_name_raises(self):
        """Test that missing get_language_name raises TypeError."""

        class IncompleteIndexer(BaseIndexer):
            def get_file_extensions(self) -> list[str]:
                return []

            def get_excluded_dirs(self) -> list[str]:
                return []

            def index_repository(
                self,
                repo_path: str | Path,
                output_path: str | Path,
                force: bool = False,
                verbose: bool = False,
                config_path: str | Path | None = None,
            ) -> dict:
                return {}

        with pytest.raises(TypeError):
            IncompleteIndexer()

    def test_missing_extensions_raises(self):
        """Test that missing get_file_extensions raises TypeError."""

        class IncompleteIndexer(BaseIndexer):
            def get_language_name(self) -> str:
                return "test"

            def get_excluded_dirs(self) -> list[str]:
                return []

            def index_repository(
                self,
                repo_path: str | Path,
                output_path: str | Path,
                force: bool = False,
                verbose: bool = False,
                config_path: str | Path | None = None,
            ) -> dict:
                return {}

        with pytest.raises(TypeError):
            IncompleteIndexer()


# ============================================================================
# SECTION 6: Integration Tests
# ============================================================================


class TestBaseIndexerIntegration:
    """Test BaseIndexer in realistic scenarios."""

    def test_full_workflow_with_multiple_extensions(self):
        """Test complete workflow with multiple file extensions."""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create realistic directory structure
            (tmpdir_path / "src").mkdir()
            (tmpdir_path / "src" / "module1.mock").touch()
            (tmpdir_path / "src" / "module2.test").touch()
            (tmpdir_path / "tests").mkdir()
            (tmpdir_path / "tests" / "test1.mock").touch()
            (tmpdir_path / "tests" / "test2.test").touch()
            (tmpdir_path / "build").mkdir()
            (tmpdir_path / "build" / "file.mock").touch()

            indexer = MockIndexer()
            found_files = indexer._find_source_files(tmpdir_path)

            assert len(found_files) == 5

    def test_config_and_file_discovery_consistency(self):
        """Test that config matches actual file discovery."""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "file.mock").touch()

            indexer = MockIndexer()
            config = indexer.get_default_config()
            found_files = indexer._find_source_files(tmpdir_path)

            # Verify config extensions match what can be found
            config_exts = set(config["file_extensions"])
            found_exts = set(f.suffix for f in found_files)

            assert found_exts.issubset(config_exts)


# ============================================================================
# SECTION 7: Test incremental_index_repository
# ============================================================================


class TestIncrementalIndexRepository:
    """Test BaseIndexer.incremental_index_repository method."""

    def test_incremental_not_supported_by_default(self):
        """Test that incremental indexing raises NotImplementedError by default."""
        indexer = MockIndexer()

        with pytest.raises(NotImplementedError) as exc_info:
            indexer.incremental_index_repository("/tmp", "/tmp/index.json")

        assert "does not support incremental indexing" in str(exc_info.value)

    def test_supports_incremental_flag(self):
        """Test supports_incremental class variable."""
        assert MockIndexer.supports_incremental is False

        class IncrementalIndexer(MockIndexer):
            supports_incremental = True

        assert IncrementalIndexer.supports_incremental is True
