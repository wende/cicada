"""
Tests for interactive setup menu (keywords/embeddings modes).
"""

from unittest.mock import MagicMock, patch

import pytest


def configure_menu(mock_menu_class, selections):
    """Helper to configure TerminalMenu mock responses."""
    mock_menu_instance = MagicMock()
    mock_menu_instance.show.side_effect = selections
    mock_menu_class.return_value = mock_menu_instance
    return mock_menu_instance


class TestInteractiveSetup:
    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_keywords_mode_skip_pr_indexing(self, mock_menu_class, mock_ascii):
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"
        configure_menu(mock_menu_class, [0, 0, 1])

        indexing_mode, index_prs, add_to_claude_md, embeddings_config = show_first_time_setup()

        assert indexing_mode == "keywords"
        assert index_prs is False
        assert add_to_claude_md is False
        assert embeddings_config is None

    @patch("cicada.interactive_setup._configure_embeddings")
    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_embeddings_mode_with_pr_indexing(
        self, mock_menu_class, mock_ascii, mock_configure_embeddings
    ):
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"
        mock_configure_embeddings.return_value = {
            "ollama_host": "http://localhost:11434",
            "model": "nomic-embed-text",
        }
        configure_menu(mock_menu_class, [1, 1, 0])

        indexing_mode, index_prs, add_to_claude_md, embeddings_config = show_first_time_setup()

        assert indexing_mode == "embeddings"
        assert index_prs is True
        assert add_to_claude_md is True
        assert embeddings_config == {
            "ollama_host": "http://localhost:11434",
            "model": "nomic-embed-text",
        }

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_keyboard_interrupt_on_mode_selection(self, mock_menu_class, mock_ascii):
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"
        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = KeyboardInterrupt()
        mock_menu_class.return_value = mock_menu_instance

        with pytest.raises(SystemExit) as exc_info:
            show_first_time_setup()

        assert exc_info.value.code == 1


class TestTextBasedSetup:
    def test_text_default_keywords_skip_pr(self):
        from cicada.interactive_setup import _text_based_setup

        with patch("builtins.input", side_effect=["", "2", "2"]):
            indexing_mode, index_prs, add_to_claude_md, embeddings_config = _text_based_setup()

        assert indexing_mode == "keywords"
        assert index_prs is False
        assert add_to_claude_md is False
        assert embeddings_config is None

    @patch("cicada.interactive_setup._configure_embeddings")
    def test_text_embeddings_with_pr(self, mock_configure_embeddings):
        from cicada.interactive_setup import _text_based_setup

        mock_configure_embeddings.return_value = {
            "ollama_host": "http://localhost:11434",
            "model": "nomic-embed-text",
        }

        with patch("builtins.input", side_effect=["2", "1", "1"]):
            indexing_mode, index_prs, add_to_claude_md, embeddings_config = _text_based_setup()

        assert indexing_mode == "embeddings"
        assert index_prs is True
        assert add_to_claude_md is True
        assert embeddings_config == {
            "ollama_host": "http://localhost:11434",
            "model": "nomic-embed-text",
        }
