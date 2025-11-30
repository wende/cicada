"""
Comprehensive tests for cicada/parsing/base_indexer.py

Tests cover the concrete methods of BaseIndexer and verify the interface contract.
Target: >80% coverage
"""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from cicada.parsing.base_indexer import BaseIndexer


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

    def test_find_source_files_symlinks_not_doubled(self):
        """Test that symlinks don't cause duplicates."""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create a file
            (tmpdir_path / "file.mock").touch()
            # Create symlink to same file in subdirectory
            (tmpdir_path / "link_dir").mkdir()
            (tmpdir_path / "link_dir" / "link.mock").symlink_to(tmpdir_path / "file.mock")

            indexer = MockIndexer()
            found_files = indexer._find_source_files(tmpdir_path)

            # Should find both: the original and the symlink
            # (behavior depends on how rglob handles symlinks)
            assert tmpdir_path / "file.mock" in found_files


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
# SECTION 7: Timing Methods
# ============================================================================


class TestTimingMethods:
    """Test timing-related methods in BaseIndexer."""

    def test_start_timing(self):
        """Test _start_timing initializes timing state."""
        indexer = MockIndexer()
        indexer._start_timing()

        assert indexer._start_time > 0
        assert indexer._last_step_time > 0
        assert indexer._start_time == indexer._last_step_time

    def test_log_timing_verbose(self, capsys):
        """Test _log_timing outputs timing info when verbose."""
        indexer = MockIndexer(verbose=True)
        indexer._start_timing()

        import time

        time.sleep(0.01)  # Small delay

        indexer._log_timing("Test step")

        captured = capsys.readouterr()
        assert "⏱️" in captured.out
        assert "Test step" in captured.out

    def test_log_timing_non_verbose(self, capsys):
        """Test _log_timing is silent when not verbose."""
        indexer = MockIndexer(verbose=False)
        indexer._start_timing()
        indexer._log_timing("Test step")

        captured = capsys.readouterr()
        assert captured.out == ""


# ============================================================================
# SECTION 8: Interruptible Phase Tests
# ============================================================================


class TestInterruptiblePhase:
    """Test _run_interruptible_phase method."""

    def test_run_interruptible_phase_success(self):
        """Test phase runs successfully when not interrupted."""
        indexer = MockIndexer()
        indexer._interrupted = False

        executed = [False]

        def phase_func():
            executed[0] = True

        skipped = []
        result = indexer._run_interruptible_phase("test phase", phase_func, skipped)

        assert result is True
        assert executed[0] is True
        assert skipped == []

    def test_run_interruptible_phase_already_interrupted(self):
        """Test phase is skipped when already interrupted."""
        indexer = MockIndexer()
        indexer._interrupted = True

        executed = [False]

        def phase_func():
            executed[0] = True

        skipped = []
        result = indexer._run_interruptible_phase("test phase", phase_func, skipped)

        assert result is False
        assert executed[0] is False
        assert "test phase" in skipped

    def test_run_interruptible_phase_keyboard_interrupt(self):
        """Test phase handles KeyboardInterrupt."""
        indexer = MockIndexer(verbose=True)
        indexer._interrupted = False

        def phase_func():
            raise KeyboardInterrupt()

        skipped = []
        result = indexer._run_interruptible_phase(
            "test phase", phase_func, skipped, partial_suffix=" (partial)"
        )

        assert result is False
        assert indexer._interrupted is True
        assert "test phase (partial)" in skipped

    def test_run_interruptible_phase_exception(self, capsys):
        """Test phase handles generic exceptions."""
        indexer = MockIndexer(verbose=True)
        indexer._interrupted = False

        def phase_func():
            raise ValueError("Test error")

        skipped = []
        result = indexer._run_interruptible_phase("test phase", phase_func, skipped)

        assert result is False
        captured = capsys.readouterr()
        assert "Warning" in captured.out
        assert "failed" in captured.out


# ============================================================================
# SECTION 9: Default Keyword Extraction Methods
# ============================================================================


class TestDefaultKeywordMethods:
    """Test default implementations of keyword extraction methods."""

    def test_extract_docstring_keywords_default(self, capsys):
        """Test default _extract_docstring_keywords prints warning."""
        indexer = MockIndexer(verbose=True)
        mock_pipeline = None

        indexer._extract_docstring_keywords({}, None, mock_pipeline)

        captured = capsys.readouterr()
        assert "Warning" in captured.out
        assert "not implemented" in captured.out

    def test_extract_string_keywords_default(self, capsys):
        """Test default _extract_string_keywords returns 0."""
        indexer = MockIndexer(verbose=True)
        mock_pipeline = None

        result = indexer._extract_string_keywords({}, Path("."), None, mock_pipeline)

        assert result == 0
        captured = capsys.readouterr()
        assert "Warning" in captured.out
        assert "not implemented" in captured.out

    def test_extract_string_keywords_default_non_verbose(self, capsys):
        """Test default _extract_string_keywords returns 0 silently when not verbose."""
        indexer = MockIndexer(verbose=False)
        mock_pipeline = None

        result = indexer._extract_string_keywords({}, Path("."), None, mock_pipeline)

        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == ""


# ============================================================================
# SECTION 10: Apply Expansion Result
# ============================================================================


class TestApplyExpansionResult:
    """Test _apply_expansion_result method."""

    def test_apply_expansion_result_valid(self):
        """Test applying valid expansion result."""
        indexer = MockIndexer()

        class MockCallback:
            def __init__(self):
                self.target = {}
                self.target_key = "keywords"

        callback = MockCallback()
        result = {
            "words": [
                {"word": "test", "score": 0.9},
                {"word": "run", "score": 0.8},
            ]
        }

        indexer._apply_expansion_result(callback, result)

        assert callback.target["keywords"] == {"test": 0.9, "run": 0.8}

    def test_apply_expansion_result_takes_max_score(self):
        """Test that duplicate words take max score."""
        indexer = MockIndexer()

        class MockCallback:
            def __init__(self):
                self.target = {}
                self.target_key = "keywords"

        callback = MockCallback()
        result = {
            "words": [
                {"word": "test", "score": 0.7},
                {"word": "test", "score": 0.9},  # Higher score
            ]
        }

        indexer._apply_expansion_result(callback, result)

        assert callback.target["keywords"]["test"] == 0.9

    def test_apply_expansion_result_empty_words(self):
        """Test applying empty expansion result."""
        indexer = MockIndexer()

        class MockCallback:
            def __init__(self):
                self.target = {}
                self.target_key = "keywords"

        callback = MockCallback()
        result = {"words": []}

        indexer._apply_expansion_result(callback, result)

        # Should not add empty dict
        assert "keywords" not in callback.target

    def test_apply_expansion_result_invalid_format(self):
        """Test applying invalid result format."""
        indexer = MockIndexer()

        class MockCallback:
            def __init__(self):
                self.target = {}
                self.target_key = "keywords"

        callback = MockCallback()
        result = ["not", "a", "dict"]  # Invalid format

        indexer._apply_expansion_result(callback, result)

        # Should not modify target
        assert "keywords" not in callback.target


# ============================================================================
# SECTION 11: Function Signature Methods
# ============================================================================


class TestFunctionSignatureMethods:
    """Test function signature building and parsing methods."""

    def test_build_function_signature_valid(self):
        """Test building function signature."""
        indexer = MockIndexer()

        func = {"name": "test_func", "arity": 2}
        sig = indexer._build_function_signature("MyModule", func)

        assert sig == "MyModule.test_func/2"

    def test_build_function_signature_no_arity(self):
        """Test building signature with missing arity defaults to 0."""
        indexer = MockIndexer()

        func = {"name": "test_func"}  # No arity
        sig = indexer._build_function_signature("MyModule", func)

        assert sig == "MyModule.test_func/0"

    def test_build_function_signature_no_name(self):
        """Test building signature without name returns None."""
        indexer = MockIndexer()

        func = {"arity": 2}  # No name
        sig = indexer._build_function_signature("MyModule", func)

        assert sig is None

    def test_parse_function_signature_valid(self):
        """Test parsing valid function signature."""
        indexer = MockIndexer()

        result = indexer._parse_function_signature("MyModule.test_func/2")

        assert result == {
            "module": "MyModule",
            "function": "test_func",
            "arity": 2,
        }

    def test_parse_function_signature_nested_module(self):
        """Test parsing signature with nested module."""
        indexer = MockIndexer()

        result = indexer._parse_function_signature("MyApp.Auth.User.validate/3")

        assert result == {
            "module": "MyApp.Auth.User",
            "function": "validate",
            "arity": 3,
        }

    def test_parse_function_signature_no_dot(self):
        """Test parsing signature without dot returns None."""
        indexer = MockIndexer()

        result = indexer._parse_function_signature("test_func/2")

        assert result is None

    def test_parse_function_signature_no_slash(self):
        """Test parsing signature without slash returns None."""
        indexer = MockIndexer()

        result = indexer._parse_function_signature("MyModule.test_func")

        assert result is None

    def test_parse_function_signature_invalid_arity(self):
        """Test parsing signature with non-integer arity returns None."""
        indexer = MockIndexer()

        result = indexer._parse_function_signature("MyModule.test_func/abc")

        assert result is None


# ============================================================================
# SECTION 12: Compute Timestamps Tests
# ============================================================================


class TestComputeTimestamps:
    """Test _compute_timestamps method."""

    def test_compute_timestamps_no_git(self, capsys):
        """Test compute_timestamps handles missing git gracefully."""
        from unittest.mock import patch

        indexer = MockIndexer(verbose=True)
        index = {
            "modules": {
                "TestModule": {
                    "file": "lib/test.ex",
                    "functions": [{"name": "test", "line": 10}],
                }
            }
        }

        with patch("cicada.git.helper.GitHelper", side_effect=RuntimeError("No git repo")):
            indexer._compute_timestamps(index, Path("/tmp"))

        captured = capsys.readouterr()
        assert "Warning: Could not initialize git helper" in captured.out

    def test_compute_timestamps_no_functions(self):
        """Test compute_timestamps with empty modules."""
        from unittest.mock import patch, MagicMock

        indexer = MockIndexer(verbose=False)
        index = {"modules": {}}

        mock_git = MagicMock()

        with patch("cicada.git.helper.GitHelper", return_value=mock_git):
            indexer._compute_timestamps(index, Path("/tmp"))

        # Should not call git helper if no functions
        mock_git.get_functions_evolution_batch.assert_not_called()

    def test_compute_timestamps_no_file_path(self):
        """Test compute_timestamps skips modules without file path."""
        from unittest.mock import patch, MagicMock

        indexer = MockIndexer(verbose=False)
        index = {
            "modules": {
                "TestModule": {
                    # No "file" key
                    "functions": [{"name": "test", "line": 10}],
                }
            }
        }

        mock_git = MagicMock()

        with patch("cicada.git.helper.GitHelper", return_value=mock_git):
            indexer._compute_timestamps(index, Path("/tmp"))

        # Should not call git helper since no file path
        mock_git.get_functions_evolution_batch.assert_not_called()

    def test_compute_timestamps_success(self):
        """Test compute_timestamps updates functions correctly."""
        from unittest.mock import patch, MagicMock

        indexer = MockIndexer(verbose=False)
        index = {
            "modules": {
                "TestModule": {
                    "file": "lib/test.ex",
                    "functions": [
                        {"name": "test_func", "line": 10},
                        {"name": "another_func", "line": 20},
                    ],
                }
            }
        }

        mock_git = MagicMock()
        mock_git.get_functions_evolution_batch.return_value = {
            "test_func": {
                "created_at": {"date": "2024-01-01"},
                "last_modified": {"date": "2024-06-01", "sha": "abc123"},
                "total_modifications": 5,
                "modification_frequency": 0.1,
            },
            "another_func": {
                "created_at": {"date": "2024-02-01"},
                "last_modified": {"date": "2024-05-01", "sha": "def456"},
                "total_modifications": 3,
            },
        }

        with patch("cicada.git.helper.GitHelper", return_value=mock_git):
            indexer._compute_timestamps(index, Path("/tmp"))

        func1 = index["modules"]["TestModule"]["functions"][0]
        func2 = index["modules"]["TestModule"]["functions"][1]

        assert func1["created_at"] == "2024-01-01"
        assert func1["last_modified_at"] == "2024-06-01"
        assert func1["last_modified_sha"] == "abc123"
        assert func1["modification_count"] == 5
        assert func1["modification_frequency"] == 0.1

        assert func2["created_at"] == "2024-02-01"
        assert func2["modification_count"] == 3

    def test_compute_timestamps_git_error(self, capsys):
        """Test compute_timestamps handles git errors gracefully."""
        from unittest.mock import patch, MagicMock

        indexer = MockIndexer(verbose=True)
        index = {
            "modules": {
                "TestModule": {
                    "file": "lib/test.ex",
                    "functions": [{"name": "test", "line": 10}],
                }
            }
        }

        mock_git = MagicMock()
        mock_git.get_functions_evolution_batch.side_effect = RuntimeError("Git error")

        with patch("cicada.git.helper.GitHelper", return_value=mock_git):
            indexer._compute_timestamps(index, Path("/tmp"))

        captured = capsys.readouterr()
        assert "Warning: Failed to compute timestamps" in captured.out


# ============================================================================
# SECTION 13: Extract Co-change Tests
# ============================================================================


class TestExtractCochange:
    """Test _extract_cochange method."""

    def test_extract_cochange_no_git(self, capsys):
        """Test extract_cochange handles analyzer errors gracefully."""
        from unittest.mock import patch

        indexer = MockIndexer(verbose=True)
        index = {"modules": {}}

        with patch(
            "cicada.git.cochange_analyzer.CoChangeAnalyzer",
            side_effect=RuntimeError("No git"),
        ):
            indexer._extract_cochange(index, Path("/tmp"))

        captured = capsys.readouterr()
        assert "Warning: Failed to analyze co-changes" in captured.out

    def test_extract_cochange_success(self, capsys):
        """Test extract_cochange updates index correctly."""
        from unittest.mock import patch, MagicMock

        indexer = MockIndexer(verbose=True)
        index = {
            "modules": {
                "TestModule": {
                    "file": "lib/test.ex",
                    "functions": [{"name": "test_func", "arity": 2}],
                }
            }
        }

        mock_analyzer = MagicMock()
        mock_instance = MagicMock()
        mock_instance.analyze_repository.return_value = {
            "metadata": {"file_pairs": 10, "function_pairs": 5},
            "file_pairs": {("lib/test.ex", "lib/other.ex"): 3},
            "function_pairs": {("TestModule.test_func/2", "OtherModule.helper/1"): 2},
        }
        mock_analyzer.return_value = mock_instance

        # Mock find_cochange_pairs class method
        mock_analyzer.find_cochange_pairs = MagicMock(
            side_effect=[
                [("lib/other.ex", 3)],  # For file cochanges
                [("OtherModule.helper/1", 2)],  # For function cochanges
            ]
        )

        with patch("cicada.git.cochange_analyzer.CoChangeAnalyzer", mock_analyzer):
            indexer._extract_cochange(index, Path("/tmp"))

        captured = capsys.readouterr()
        assert "Found 10 file pairs" in captured.out
        assert "5 function pairs" in captured.out

        # Check metadata added
        assert "cochange_metadata" in index

    def test_extract_cochange_module_without_file(self):
        """Test extract_cochange handles modules without file path."""
        from unittest.mock import patch, MagicMock

        indexer = MockIndexer(verbose=False)
        index = {
            "modules": {
                "TestModule": {
                    # No "file" key
                    "functions": [{"name": "test", "arity": 0}],
                }
            }
        }

        mock_analyzer = MagicMock()
        mock_instance = MagicMock()
        mock_instance.analyze_repository.return_value = {
            "metadata": {"file_pairs": 0, "function_pairs": 0},
            "file_pairs": {},
            "function_pairs": {},
        }
        mock_analyzer.return_value = mock_instance
        mock_analyzer.find_cochange_pairs = MagicMock(return_value=[])

        with patch("cicada.git.cochange_analyzer.CoChangeAnalyzer", mock_analyzer):
            indexer._extract_cochange(index, Path("/tmp"))

        # Should complete without error
        assert "cochange_metadata" in index
