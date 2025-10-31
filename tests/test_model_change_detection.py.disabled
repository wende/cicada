"""
Tests for model change detection in incremental indexing.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from cicada.indexer import ElixirIndexer, prompt_model_change


class TestModelChangeDetection:
    """Tests for model configuration change detection during indexing"""

    @pytest.fixture
    def sample_repo(self, tmp_path):
        """Create a sample Elixir repository"""
        test_file = tmp_path / "lib" / "test.ex"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text(
            """
defmodule TestModule do
  @moduledoc "Test module"

  def test_function(x), do: x
end
"""
        )
        return tmp_path

    @pytest.fixture
    def existing_index_with_model(self, tmp_path):
        """Create an existing index with model configuration"""
        from cicada.utils.hash_utils import compute_hashes_for_files

        # Create the actual test file
        test_file = tmp_path / "lib" / "test.ex"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text(
            """
defmodule TestModule do
  @moduledoc "Test module"

  def test_function(x), do: x
end
"""
        )

        cicada_dir = tmp_path / ".cicada"
        cicada_dir.mkdir(parents=True, exist_ok=True)

        index = {
            "modules": {
                "TestModule": {
                    "file": "lib/test.ex",
                    "line": 2,
                    "moduledoc": "Test module",
                    "functions": [],
                    "total_functions": 0,
                    "public_functions": 0,
                    "private_functions": 0,
                }
            },
            "metadata": {
                "indexed_at": "2024-01-01T00:00:00",
                "repo_path": str(tmp_path),
                "keyword_method": "spacy",
                "model_tier": "regular",
            },
        }

        index_path = cicada_dir / "index.json"
        with open(index_path, "w") as f:
            json.dump(index, f)

        # Compute actual hashes for the files
        hashes = compute_hashes_for_files(["lib/test.ex"], str(tmp_path))
        hashes_path = cicada_dir / "hashes.json"
        with open(hashes_path, "w") as f:
            json.dump({"hashes": hashes}, f)

        return tmp_path, index_path

    def test_model_change_detection_different_method(self, existing_index_with_model):
        """Test that model change is detected when method changes"""
        repo_path, index_path = existing_index_with_model

        indexer = ElixirIndexer()

        # Mock the prompt to return False (abort)
        with patch("cicada.indexer.prompt_model_change", return_value=False) as mock_prompt:
            result = indexer.incremental_index_repository(
                str(repo_path),
                str(index_path),
                extract_keywords=True,
                keyword_method="bert",  # Different from spacy
                model_tier="regular",
            )

            # Should have called the prompt
            mock_prompt.assert_called_once_with("spacy", "regular", "bert", "regular")

            # Should return the existing index (no changes)
            assert result is not None
            assert "metadata" in result

    def test_model_change_detection_different_tier(self, existing_index_with_model):
        """Test that model change is detected when tier changes"""
        repo_path, index_path = existing_index_with_model

        indexer = ElixirIndexer()

        # Mock the prompt to return False (abort)
        with patch("cicada.indexer.prompt_model_change", return_value=False) as mock_prompt:
            result = indexer.incremental_index_repository(
                str(repo_path),
                str(index_path),
                extract_keywords=True,
                keyword_method="spacy",
                model_tier="fast",  # Different from regular
            )

            # Should have called the prompt
            mock_prompt.assert_called_once_with("spacy", "regular", "spacy", "fast")

            # Should return the existing index
            assert result is not None

    def test_model_change_user_continues_triggers_full_reindex(self, existing_index_with_model):
        """Test that choosing to continue triggers a full reindex"""
        repo_path, index_path = existing_index_with_model

        indexer = ElixirIndexer()

        # Mock the prompt to return True (continue with reindex)
        with patch("cicada.indexer.prompt_model_change", return_value=True) as mock_prompt:
            # Also mock index_repository to track that it's called
            with patch.object(indexer, "index_repository") as mock_index_repo:
                mock_index_repo.return_value = {"modules": {}, "metadata": {}}

                result = indexer.incremental_index_repository(
                    str(repo_path),
                    str(index_path),
                    extract_keywords=True,
                    keyword_method="bert",
                    model_tier="max",
                )

                # Should have called the prompt
                mock_prompt.assert_called_once()

                # Should have called full reindex
                mock_index_repo.assert_called_once_with(
                    str(repo_path), str(index_path), True, "bert", "max"
                )

    def test_no_prompt_when_model_unchanged(self, existing_index_with_model):
        """Test that no prompt is shown when model config is the same"""
        repo_path, index_path = existing_index_with_model

        indexer = ElixirIndexer()

        # Mock the prompt - it should NOT be called
        with patch("cicada.indexer.prompt_model_change") as mock_prompt:
            result = indexer.incremental_index_repository(
                str(repo_path),
                str(index_path),
                extract_keywords=True,
                keyword_method="spacy",  # Same as existing
                model_tier="regular",  # Same as existing
            )

            # Should NOT have called the prompt
            mock_prompt.assert_not_called()

            # Should return index normally
            assert result is not None

    def test_no_prompt_when_keywords_not_extracted(self, existing_index_with_model):
        """Test that no prompt is shown when extract_keywords=False"""
        repo_path, index_path = existing_index_with_model

        indexer = ElixirIndexer()

        # Mock the prompt - it should NOT be called
        with patch("cicada.indexer.prompt_model_change") as mock_prompt:
            result = indexer.incremental_index_repository(
                str(repo_path),
                str(index_path),
                extract_keywords=False,  # Not extracting keywords
                keyword_method="bert",
                model_tier="max",
            )

            # Should NOT have called the prompt
            mock_prompt.assert_not_called()

    def test_metadata_includes_model_config_after_indexing(self, sample_repo):
        """Test that metadata includes model config after indexing"""
        indexer = ElixirIndexer()
        index_path = sample_repo / ".cicada" / "index.json"

        # Do a full index with keywords
        result = indexer.index_repository(
            str(sample_repo),
            str(index_path),
            extract_keywords=True,
            keyword_method="spacy",
            model_tier="fast",
        )

        # Check metadata includes model config
        assert "metadata" in result
        assert result["metadata"]["keyword_method"] == "spacy"
        assert result["metadata"]["model_tier"] == "fast"

    def test_metadata_model_config_none_when_no_keywords(self, sample_repo):
        """Test that model config is None when not extracting keywords"""
        indexer = ElixirIndexer()
        index_path = sample_repo / ".cicada" / "index.json"

        # Do a full index without keywords
        result = indexer.index_repository(
            str(sample_repo),
            str(index_path),
            extract_keywords=False,
        )

        # Check metadata has None for model config
        assert "metadata" in result
        assert result["metadata"]["keyword_method"] is None
        assert result["metadata"]["model_tier"] is None


class TestPromptModelChange:
    """Tests for the prompt_model_change function"""

    def test_prompt_with_terminal_menu_continue(self):
        """Test prompt with terminal menu choosing to continue"""
        with patch("simple_term_menu.TerminalMenu") as mock_menu_class:
            mock_menu = MagicMock()
            mock_menu.show.return_value = 0  # First option (Continue)
            mock_menu_class.return_value = mock_menu

            result = prompt_model_change("spacy", "regular", "bert", "max")

            assert result is True
            mock_menu.show.assert_called_once()

    def test_prompt_with_terminal_menu_abort(self):
        """Test prompt with terminal menu choosing to abort"""
        with patch("simple_term_menu.TerminalMenu") as mock_menu_class:
            mock_menu = MagicMock()
            mock_menu.show.return_value = 1  # Second option (Abort)
            mock_menu_class.return_value = mock_menu

            result = prompt_model_change("spacy", "regular", "bert", "max")

            assert result is False
            mock_menu.show.assert_called_once()

    def test_prompt_fallback_to_text_input_continue(self):
        """Test text-based fallback when terminal menu not available"""
        import sys

        # Temporarily remove simple_term_menu from sys.modules to simulate ImportError
        simple_term_menu_backup = sys.modules.get("simple_term_menu")
        if "simple_term_menu" in sys.modules:
            del sys.modules["simple_term_menu"]

        try:
            # Mock the import to fail
            with patch.dict("sys.modules", {"simple_term_menu": None}):
                with patch("builtins.input", return_value="1"):
                    result = prompt_model_change("spacy", "regular", "bert", "max")
                    assert result is True
        finally:
            # Restore the module
            if simple_term_menu_backup is not None:
                sys.modules["simple_term_menu"] = simple_term_menu_backup

    def test_prompt_fallback_to_text_input_abort(self):
        """Test text-based fallback choosing to abort"""
        import sys

        # Temporarily remove simple_term_menu from sys.modules to simulate ImportError
        simple_term_menu_backup = sys.modules.get("simple_term_menu")
        if "simple_term_menu" in sys.modules:
            del sys.modules["simple_term_menu"]

        try:
            # Mock the import to fail
            with patch.dict("sys.modules", {"simple_term_menu": None}):
                with patch("builtins.input", return_value="2"):
                    result = prompt_model_change("spacy", "regular", "bert", "max")
                    assert result is False
        finally:
            # Restore the module
            if simple_term_menu_backup is not None:
                sys.modules["simple_term_menu"] = simple_term_menu_backup

    def test_prompt_keyboard_interrupt_exits(self):
        """Test that keyboard interrupt exits the program"""
        with patch("simple_term_menu.TerminalMenu") as mock_menu_class:
            mock_menu = MagicMock()
            mock_menu.show.side_effect = KeyboardInterrupt()
            mock_menu_class.return_value = mock_menu

            with pytest.raises(SystemExit):
                prompt_model_change("spacy", "regular", "bert", "max")
