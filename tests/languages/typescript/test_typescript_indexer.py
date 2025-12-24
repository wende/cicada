"""Comprehensive tests for TypeScript and JavaScript SCIP indexers."""

import pytest
import subprocess
from unittest.mock import Mock, patch

from cicada.languages.typescript.indexer import TypeScriptSCIPIndexer, JavaScriptSCIPIndexer


class TestTypeScriptSCIPIndexer:
    """Test TypeScript SCIP indexer functionality."""

    @pytest.fixture
    def indexer(self):
        """Create a TypeScriptSCIPIndexer instance."""
        return TypeScriptSCIPIndexer(verbose=False)

    @pytest.fixture
    def verbose_indexer(self):
        """Create a verbose indexer."""
        return TypeScriptSCIPIndexer(verbose=True)

    def test_get_language_name(self, indexer):
        """Should return 'typescript' as language name."""
        assert indexer.get_language_name() == "typescript"

    def test_get_file_extensions(self, indexer):
        """Should return TypeScript and JavaScript extensions (including ES modules)."""
        extensions = indexer.get_file_extensions()
        assert extensions == [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"]
        assert ".ts" in extensions
        assert ".tsx" in extensions
        assert ".js" in extensions
        assert ".jsx" in extensions
        assert ".mjs" in extensions
        assert ".cjs" in extensions

    def test_get_excluded_dirs(self, indexer):
        """Should return list of TypeScript-specific excluded directories."""
        excluded = indexer.get_excluded_dirs()

        # TypeScript-specific exclusions
        assert "node_modules" in excluded
        assert "dist" in excluded
        assert "build" in excluded
        assert "coverage" in excluded
        assert ".next" in excluded
        assert ".nuxt" in excluded
        assert "out" in excluded
        assert ".cache" in excluded

        # Common exclusion
        assert ".git" in excluded

    @patch("subprocess.run")
    def test_run_scip_indexer_success(self, mock_run, indexer, tmp_path):
        """Should successfully run scip-typescript indexer."""
        # Setup mock
        mock_run.return_value = Mock(returncode=0, stderr="")

        # Create index.scip file (simulating scip-typescript output)
        scip_file = tmp_path / "index.scip"
        scip_file.write_text("mock scip content")

        # Run indexer
        result = indexer._run_scip_indexer(tmp_path)

        # Verify subprocess call
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ["npx", "@sourcegraph/scip-typescript", "index"]
        assert call_args[1]["cwd"] == tmp_path
        assert call_args[1]["timeout"] == 600

        # Verify result
        assert result == scip_file
        assert result.exists()

    @patch("subprocess.run")
    def test_run_scip_indexer_verbose_output(self, mock_run, verbose_indexer, tmp_path, capsys):
        """Should print verbose output when running scip-typescript."""
        # Setup mock
        mock_run.return_value = Mock(returncode=0, stderr="")

        # Create index.scip file
        scip_file = tmp_path / "index.scip"
        scip_file.write_text("mock scip content")

        # Run indexer
        verbose_indexer._run_scip_indexer(tmp_path)

        # Check verbose output
        captured = capsys.readouterr()
        assert "Running: npx @sourcegraph/scip-typescript index" in captured.out
        assert "This may take several minutes" in captured.out

    @patch("subprocess.run")
    def test_run_scip_indexer_failure(self, mock_run, indexer, tmp_path):
        """Should raise error when scip-typescript fails."""
        # Setup mock to simulate failure
        mock_run.return_value = Mock(returncode=1, stderr="Error: TypeScript compilation failed")

        # Run indexer - should raise
        with pytest.raises(RuntimeError) as exc_info:
            indexer._run_scip_indexer(tmp_path)

        assert "scip indexing failed" in str(exc_info.value).lower()
        assert "TypeScript compilation failed" in str(exc_info.value)

    @patch("subprocess.run")
    def test_run_scip_indexer_missing_output(self, mock_run, indexer, tmp_path):
        """Should raise error when index.scip is not generated."""
        # Setup mock - success but no file created
        mock_run.return_value = Mock(returncode=0, stderr="")

        # Run indexer - should raise because index.scip doesn't exist
        with pytest.raises(RuntimeError) as exc_info:
            indexer._run_scip_indexer(tmp_path)

        assert "scip indexer did not generate" in str(exc_info.value).lower()
        assert "index.scip" in str(exc_info.value)

    @patch("subprocess.run")
    def test_run_scip_indexer_timeout(self, mock_run, indexer, tmp_path):
        """Should raise error when scip-typescript times out."""
        # Setup mock to simulate timeout
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd=["npx", "@sourcegraph/scip-typescript", "index"], timeout=600
        )

        # Run indexer - should raise
        with pytest.raises(RuntimeError) as exc_info:
            indexer._run_scip_indexer(tmp_path)

        assert "scip indexing timed out" in str(exc_info.value).lower()
        assert "600 seconds" in str(exc_info.value)

    @patch("subprocess.run")
    def test_run_scip_indexer_uses_fixed_filename(self, mock_run, indexer, tmp_path):
        """Should use fixed 'index.scip' filename (not temp file)."""
        # Setup mock
        mock_run.return_value = Mock(returncode=0, stderr="")

        # Create index.scip with specific content
        scip_file = tmp_path / "index.scip"
        scip_file.write_text("typescript scip data")

        # Run indexer
        result = indexer._run_scip_indexer(tmp_path)

        # Verify the exact path
        assert result == tmp_path / "index.scip"
        assert result.name == "index.scip"

        # Verify it's the actual file, not a temp file
        assert result.read_text() == "typescript scip data"

    def test_excluded_dirs_is_set(self, indexer):
        """Should have excluded_dirs as instance variable."""
        assert hasattr(indexer, "excluded_dirs")
        assert isinstance(indexer.excluded_dirs, set)
        assert len(indexer.excluded_dirs) > 0

    def test_initialization_verbose_false(self):
        """Should initialize with verbose=False by default."""
        indexer = TypeScriptSCIPIndexer()
        assert indexer.verbose is False

    def test_initialization_verbose_true(self):
        """Should initialize with verbose=True when specified."""
        indexer = TypeScriptSCIPIndexer(verbose=True)
        assert indexer.verbose is True

    @patch("subprocess.run")
    def test_subprocess_uses_list_args(self, mock_run, indexer, tmp_path):
        """Should pass command as list (not string) to prevent shell injection."""
        # Setup mock
        mock_run.return_value = Mock(returncode=0, stderr="")

        # Create index.scip file
        scip_file = tmp_path / "index.scip"
        scip_file.write_text("mock scip content")

        # Run indexer
        indexer._run_scip_indexer(tmp_path)

        # Verify command is a list, not a string
        call_args = mock_run.call_args
        command = call_args[0][0]
        assert isinstance(command, list)
        assert all(isinstance(arg, str) for arg in command)

        # Verify shell=True is not used
        assert "shell" not in call_args[1] or call_args[1].get("shell") is False
