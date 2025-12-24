"""Tests for JavaScript SCIP indexer."""

import pytest
from unittest.mock import Mock, patch

from cicada.languages.typescript.indexer import JavaScriptSCIPIndexer


class TestJavaScriptSCIPIndexer:
    """Test JavaScript SCIP indexer functionality."""

    @pytest.fixture
    def indexer(self):
        """Create a JavaScriptSCIPIndexer instance."""
        return JavaScriptSCIPIndexer(verbose=False)

    def test_get_language_name(self, indexer):
        """Should return 'javascript' as language name."""
        assert indexer.get_language_name() == "javascript"

    def test_get_file_extensions(self, indexer):
        """Should return JavaScript file extensions."""
        extensions = indexer.get_file_extensions()
        assert extensions == [".js", ".jsx", ".mjs", ".cjs"]
        assert ".js" in extensions
        assert ".jsx" in extensions
        assert ".mjs" in extensions
        assert ".cjs" in extensions

    def test_get_file_extensions_excludes_typescript(self, indexer):
        """Should not include TypeScript extensions."""
        extensions = indexer.get_file_extensions()
        assert ".ts" not in extensions
        assert ".tsx" not in extensions

    def test_get_excluded_dirs(self, indexer):
        """Should return list of JavaScript-specific excluded directories."""
        excluded = indexer.get_excluded_dirs()

        # JavaScript/Node.js exclusions (same as TypeScript)
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

    def test_shares_base_class_with_typescript_indexer(self, indexer):
        """Should share base class with TypeScriptSCIPIndexer."""
        from cicada.languages.typescript.indexer import (
            TypeScriptSCIPIndexer,
            _ScipTypeScriptIndexerBase,
        )
        # Both indexers share the same base class
        assert isinstance(indexer, _ScipTypeScriptIndexerBase)
        ts_indexer = TypeScriptSCIPIndexer()
        assert isinstance(ts_indexer, _ScipTypeScriptIndexerBase)

    def test_excluded_dirs_is_set(self, indexer):
        """Should have excluded_dirs as instance variable."""
        assert hasattr(indexer, "excluded_dirs")
        assert isinstance(indexer.excluded_dirs, set)
        assert len(indexer.excluded_dirs) > 0

    def test_initialization_verbose_false(self):
        """Should initialize with verbose=False by default."""
        indexer = JavaScriptSCIPIndexer()
        assert indexer.verbose is False

    def test_initialization_verbose_true(self):
        """Should initialize with verbose=True when specified."""
        indexer = JavaScriptSCIPIndexer(verbose=True)
        assert indexer.verbose is True

    @patch("subprocess.run")
    def test_run_scip_indexer_uses_same_tool_as_typescript(self, mock_run, indexer, tmp_path):
        """Should use scip-typescript for JavaScript (same tool)."""
        # Setup mock
        mock_run.return_value = Mock(returncode=0, stderr="")

        # Create index.scip file
        scip_file = tmp_path / "index.scip"
        scip_file.write_text("mock scip content")

        # Run indexer
        indexer._run_scip_indexer(tmp_path)

        # Verify subprocess call uses scip-typescript
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ["npx", "@sourcegraph/scip-typescript", "index"]


class TestJavaScriptLanguageRegistry:
    """Test JavaScript registration in language registry."""

    def test_javascript_is_registered(self):
        """JavaScript should be registered in the language registry."""
        from cicada.languages import LanguageRegistry

        assert LanguageRegistry.is_language_supported("javascript")

    def test_javascript_indexer_class(self):
        """Should get JavaScriptSCIPIndexer from registry."""
        from cicada.languages import LanguageRegistry

        indexer = LanguageRegistry.get_indexer("javascript")
        assert isinstance(indexer, JavaScriptSCIPIndexer)

    def test_javascript_config(self):
        """Should get JavaScript config from registry."""
        from cicada.languages import LanguageRegistry

        config = LanguageRegistry.get_config("javascript")
        assert config is not None
        assert config.language == "javascript"
        assert ".js" in config.file_extensions
        assert ".jsx" in config.file_extensions
        assert ".mjs" in config.file_extensions
        assert ".cjs" in config.file_extensions


class TestJavaScriptLanguageConfig:
    """Test JavaScript language configuration."""

    def test_default_javascript_config(self):
        """Should create correct default JavaScript configuration."""
        from cicada.parsing.language_config import LanguageConfig

        config = LanguageConfig.default_javascript()

        assert config.language == "javascript"
        assert config.file_extensions == [".js", ".jsx", ".mjs", ".cjs"]
        assert "node_modules" in config.excluded_dirs
        assert config.tree_sitter_grammar == "tree-sitter-javascript"
        assert config.comment_syntax == {
            "line": "//",
            "block_start": "/*",
            "block_end": "*/",
        }

    def test_javascript_config_to_dict(self):
        """Should serialize JavaScript config to dictionary."""
        from cicada.parsing.language_config import LanguageConfig

        config = LanguageConfig.default_javascript()
        data = config.to_dict()

        assert data["language"] == "javascript"
        assert data["file_extensions"] == [".js", ".jsx", ".mjs", ".cjs"]
        assert "tree_sitter_grammar" in data
