"""
Tests for interactive setup menu (keywords/embeddings modes).
"""

import sys
from unittest.mock import MagicMock, patch

import pytest


def configure_menu(mock_menu_class, selections):
    """Helper to configure TerminalMenu mock responses."""
    mock_menu_instance = MagicMock()
    mock_menu_instance.show.side_effect = selections
    mock_menu_class.return_value = mock_menu_instance
    return mock_menu_instance


class TestMenuUnavailableError:
    """Tests for MenuUnavailableError exception."""

    def test_menu_unavailable_error_is_exception(self):
        from cicada.interactive_setup import MenuUnavailableError

        assert issubclass(MenuUnavailableError, Exception)

    def test_menu_unavailable_error_can_be_raised(self):
        from cicada.interactive_setup import MenuUnavailableError

        with pytest.raises(MenuUnavailableError):
            raise MenuUnavailableError()


class TestPrintFirstTimeIntro:
    """Tests for _print_first_time_intro function."""

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    def test_prints_header_when_show_header_true(self, mock_ascii, capsys):
        from cicada.interactive_setup import _print_first_time_intro

        mock_ascii.return_value = "ASCII ART"
        _print_first_time_intro(show_header=True)

        captured = capsys.readouterr()
        assert "ASCII ART" in captured.out
        assert "Welcome to CICADA" in captured.out

    def test_skips_header_when_show_header_false(self, capsys):
        from cicada.interactive_setup import _print_first_time_intro

        _print_first_time_intro(show_header=False)

        captured = capsys.readouterr()
        assert "Welcome to CICADA" not in captured.out
        assert "first time running CICADA" in captured.out


class TestPromptMenuSelection:
    """Tests for _prompt_menu_selection function."""

    @patch("cicada.interactive_setup.TerminalMenu")
    def test_returns_selection_index(self, mock_menu_class):
        from cicada.interactive_setup import _prompt_menu_selection

        mock_menu = MagicMock()
        mock_menu.show.return_value = 2
        mock_menu_class.return_value = mock_menu

        result = _prompt_menu_selection(["a", "b", "c"], "cancelled")

        assert result == 2

    @patch("cicada.interactive_setup.TerminalMenu")
    def test_handles_tuple_selection(self, mock_menu_class):
        from cicada.interactive_setup import _prompt_menu_selection

        mock_menu = MagicMock()
        mock_menu.show.return_value = (1, "extra")
        mock_menu_class.return_value = mock_menu

        result = _prompt_menu_selection(["a", "b"], "cancelled")

        assert result == 1

    @patch("cicada.interactive_setup.TerminalMenu", None)
    def test_raises_menu_unavailable_when_no_terminal_menu(self):
        from cicada.interactive_setup import MenuUnavailableError, _prompt_menu_selection

        with pytest.raises(MenuUnavailableError):
            _prompt_menu_selection(["a", "b"], "cancelled")

    @patch("cicada.interactive_setup.TerminalMenu")
    def test_raises_menu_unavailable_on_init_exception(self, mock_menu_class):
        from cicada.interactive_setup import MenuUnavailableError, _prompt_menu_selection

        mock_menu_class.side_effect = Exception("init failed")

        with pytest.raises(MenuUnavailableError):
            _prompt_menu_selection(["a", "b"], "cancelled")

    @patch("cicada.interactive_setup.TerminalMenu")
    def test_exits_on_keyboard_interrupt(self, mock_menu_class):
        from cicada.interactive_setup import _prompt_menu_selection

        mock_menu = MagicMock()
        mock_menu.show.side_effect = KeyboardInterrupt()
        mock_menu_class.return_value = mock_menu

        with pytest.raises(SystemExit) as exc_info:
            _prompt_menu_selection(["a", "b"], "cancelled")

        assert exc_info.value.code == 1

    @patch("cicada.interactive_setup.TerminalMenu")
    def test_exits_on_eof_error(self, mock_menu_class):
        from cicada.interactive_setup import _prompt_menu_selection

        mock_menu = MagicMock()
        mock_menu.show.side_effect = EOFError()
        mock_menu_class.return_value = mock_menu

        with pytest.raises(SystemExit) as exc_info:
            _prompt_menu_selection(["a", "b"], "cancelled")

        assert exc_info.value.code == 1

    @patch("cicada.interactive_setup.TerminalMenu")
    def test_raises_menu_unavailable_on_show_exception(self, mock_menu_class):
        from cicada.interactive_setup import MenuUnavailableError, _prompt_menu_selection

        mock_menu = MagicMock()
        mock_menu.show.side_effect = Exception("show failed")
        mock_menu_class.return_value = mock_menu

        with pytest.raises(MenuUnavailableError):
            _prompt_menu_selection(["a", "b"], "cancelled")

    @patch("cicada.interactive_setup.TerminalMenu")
    def test_exits_on_none_selection(self, mock_menu_class):
        from cicada.interactive_setup import _prompt_menu_selection

        mock_menu = MagicMock()
        mock_menu.show.return_value = None
        mock_menu_class.return_value = mock_menu

        with pytest.raises(SystemExit) as exc_info:
            _prompt_menu_selection(["a", "b"], "cancelled")

        assert exc_info.value.code == 1


class TestHandleMenuUnavailable:
    """Tests for _handle_menu_unavailable function."""

    def test_falls_back_to_text_based_setup(self, capsys):
        from cicada.interactive_setup import _handle_menu_unavailable

        with patch("cicada.interactive_setup._text_based_setup") as mock_text:
            mock_text.return_value = ("keywords", False, False, None)
            result = _handle_menu_unavailable()

        assert result == ("keywords", False, False, None)
        captured = capsys.readouterr()
        assert "Terminal menu not supported" in captured.err


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

    def test_text_invalid_mode_then_valid(self):
        """Tests that invalid input is rejected and retried."""
        from cicada.interactive_setup import _text_based_setup

        with patch("builtins.input", side_effect=["invalid", "1", "2", "2"]):
            indexing_mode, index_prs, add_to_claude_md, embeddings_config = _text_based_setup()

        assert indexing_mode == "keywords"

    def test_text_invalid_pr_choice_then_valid(self):
        """Tests that invalid PR choice is rejected and retried."""
        from cicada.interactive_setup import _text_based_setup

        with patch("builtins.input", side_effect=["1", "invalid", "2", "2"]):
            indexing_mode, index_prs, add_to_claude_md, embeddings_config = _text_based_setup()

        assert index_prs is False

    def test_text_invalid_claude_md_then_valid(self):
        """Tests that invalid CLAUDE.md choice is rejected and retried."""
        from cicada.interactive_setup import _text_based_setup

        with patch("builtins.input", side_effect=["1", "2", "invalid", "1"]):
            indexing_mode, index_prs, add_to_claude_md, embeddings_config = _text_based_setup()

        assert add_to_claude_md is True

    def test_text_keyboard_interrupt_on_mode(self):
        """Tests that KeyboardInterrupt during mode selection exits."""
        from cicada.interactive_setup import _text_based_setup

        with patch("builtins.input", side_effect=KeyboardInterrupt()):
            with pytest.raises(SystemExit) as exc_info:
                _text_based_setup()

        assert exc_info.value.code == 1

    def test_text_keyboard_interrupt_on_pr(self):
        """Tests that KeyboardInterrupt during PR selection exits."""
        from cicada.interactive_setup import _text_based_setup

        with patch("builtins.input", side_effect=["1", KeyboardInterrupt()]):
            with pytest.raises(SystemExit) as exc_info:
                _text_based_setup()

        assert exc_info.value.code == 1

    def test_text_keyboard_interrupt_on_claude_md(self):
        """Tests that KeyboardInterrupt during CLAUDE.md selection exits."""
        from cicada.interactive_setup import _text_based_setup

        with patch("builtins.input", side_effect=["1", "2", KeyboardInterrupt()]):
            with pytest.raises(SystemExit) as exc_info:
                _text_based_setup()

        assert exc_info.value.code == 1


class TestPromptOllamaUrl:
    """Tests for _prompt_ollama_url function."""

    @patch("cicada.embeddings.ollama.check_ollama_connection")
    def test_uses_default_url_when_empty(self, mock_check):
        from cicada.interactive_setup import _prompt_ollama_url

        mock_check.return_value = True

        with patch("builtins.input", return_value=""):
            result = _prompt_ollama_url()

        assert result == "http://localhost:11434"

    @patch("cicada.embeddings.ollama.check_ollama_connection")
    def test_accepts_custom_url(self, mock_check):
        from cicada.interactive_setup import _prompt_ollama_url

        mock_check.return_value = True

        with patch("builtins.input", return_value="http://custom:11434"):
            result = _prompt_ollama_url()

        assert result == "http://custom:11434"

    @patch("cicada.embeddings.ollama.check_ollama_connection")
    def test_rejects_invalid_url_format(self, mock_check, capsys):
        from cicada.interactive_setup import _prompt_ollama_url

        mock_check.return_value = True

        with patch("builtins.input", side_effect=["invalid-url", "http://valid:11434"]):
            result = _prompt_ollama_url()

        assert result == "http://valid:11434"
        captured = capsys.readouterr()
        assert "Invalid URL format" in captured.out

    @patch("cicada.embeddings.ollama.check_ollama_connection")
    def test_connection_failed_retry(self, mock_check, capsys):
        from cicada.interactive_setup import _prompt_ollama_url

        mock_check.side_effect = [False, True]

        with patch("builtins.input", side_effect=["http://first:11434", "", "http://second:11434"]):
            result = _prompt_ollama_url()

        assert result == "http://second:11434"

    @patch("cicada.embeddings.ollama.check_ollama_connection")
    def test_connection_failed_use_anyway(self, mock_check):
        from cicada.interactive_setup import _prompt_ollama_url

        mock_check.return_value = False

        with patch("builtins.input", side_effect=["http://test:11434", "n"]):
            result = _prompt_ollama_url()

        assert result == "http://test:11434"

    def test_keyboard_interrupt(self):
        from cicada.interactive_setup import _prompt_ollama_url

        with patch("builtins.input", side_effect=KeyboardInterrupt()):
            with pytest.raises(SystemExit) as exc_info:
                _prompt_ollama_url()

        assert exc_info.value.code == 1


class TestPromptModelSelectionText:
    """Tests for _prompt_model_selection_text function."""

    @patch("cicada.embeddings.ollama.get_embedding_models")
    def test_uses_default_when_no_models(self, mock_get_models):
        from cicada.interactive_setup import _prompt_model_selection_text

        mock_get_models.return_value = []

        result = _prompt_model_selection_text("http://localhost:11434")

        assert result == "nomic-embed-text"

    @patch("cicada.embeddings.ollama.get_embedding_models")
    def test_selects_model_by_number(self, mock_get_models):
        from cicada.interactive_setup import _prompt_model_selection_text

        mock_get_models.return_value = ["model1", "model2", "model3"]

        with patch("builtins.input", return_value="2"):
            result = _prompt_model_selection_text("http://localhost:11434")

        assert result == "model2"

    @patch("cicada.embeddings.ollama.get_embedding_models")
    def test_selects_model_by_name(self, mock_get_models):
        from cicada.interactive_setup import _prompt_model_selection_text

        mock_get_models.return_value = ["model1", "model2", "model3"]

        with patch("builtins.input", return_value="model3"):
            result = _prompt_model_selection_text("http://localhost:11434")

        assert result == "model3"

    @patch("cicada.embeddings.ollama.get_embedding_models")
    def test_uses_default_on_empty_input(self, mock_get_models):
        from cicada.interactive_setup import _prompt_model_selection_text

        mock_get_models.return_value = ["model1", "nomic-embed-text"]

        with patch("builtins.input", return_value=""):
            result = _prompt_model_selection_text("http://localhost:11434")

        assert result == "nomic-embed-text"

    @patch("cicada.embeddings.ollama.get_embedding_models")
    def test_invalid_number_then_valid(self, mock_get_models):
        from cicada.interactive_setup import _prompt_model_selection_text

        mock_get_models.return_value = ["model1", "model2"]

        with patch("builtins.input", side_effect=["99", "1"]):
            result = _prompt_model_selection_text("http://localhost:11434")

        assert result == "model1"

    @patch("cicada.embeddings.ollama.get_embedding_models")
    def test_custom_model_confirmed(self, mock_get_models):
        from cicada.interactive_setup import _prompt_model_selection_text

        mock_get_models.return_value = ["model1"]

        with patch("builtins.input", side_effect=["custom-model", "y"]):
            result = _prompt_model_selection_text("http://localhost:11434")

        assert result == "custom-model"

    @patch("cicada.embeddings.ollama.get_embedding_models")
    def test_custom_model_rejected_then_valid(self, mock_get_models):
        from cicada.interactive_setup import _prompt_model_selection_text

        mock_get_models.return_value = ["model1"]

        with patch("builtins.input", side_effect=["custom-model", "n", "1"]):
            result = _prompt_model_selection_text("http://localhost:11434")

        assert result == "model1"

    @patch("cicada.embeddings.ollama.get_embedding_models")
    def test_connection_error_uses_default(self, mock_get_models):
        from cicada.interactive_setup import _prompt_model_selection_text

        mock_get_models.side_effect = ConnectionError("Failed")

        result = _prompt_model_selection_text("http://localhost:11434")

        assert result == "nomic-embed-text"

    @patch("cicada.embeddings.ollama.get_embedding_models")
    def test_keyboard_interrupt(self, mock_get_models):
        from cicada.interactive_setup import _prompt_model_selection_text

        mock_get_models.return_value = ["model1"]

        with patch("builtins.input", side_effect=KeyboardInterrupt()):
            with pytest.raises(SystemExit) as exc_info:
                _prompt_model_selection_text("http://localhost:11434")

        assert exc_info.value.code == 1


class TestTextBasedEditorSelection:
    """Tests for _text_based_editor_selection function."""

    def test_selects_claude_by_default(self):
        from cicada.interactive_setup import _text_based_editor_selection

        with patch("builtins.input", return_value=""):
            result = _text_based_editor_selection()

        assert result == "claude"

    def test_selects_cursor(self):
        from cicada.interactive_setup import _text_based_editor_selection

        with patch("builtins.input", return_value="2"):
            result = _text_based_editor_selection()

        assert result == "cursor"

    def test_selects_vs_code(self):
        from cicada.interactive_setup import _text_based_editor_selection

        with patch("builtins.input", return_value="3"):
            result = _text_based_editor_selection()

        assert result == "vs"

    def test_selects_gemini(self):
        from cicada.interactive_setup import _text_based_editor_selection

        with patch("builtins.input", return_value="4"):
            result = _text_based_editor_selection()

        assert result == "gemini"

    def test_selects_codex(self):
        from cicada.interactive_setup import _text_based_editor_selection

        with patch("builtins.input", return_value="5"):
            result = _text_based_editor_selection()

        assert result == "codex"

    def test_selects_opencode(self):
        from cicada.interactive_setup import _text_based_editor_selection

        with patch("builtins.input", return_value="6"):
            result = _text_based_editor_selection()

        assert result == "opencode"

    def test_invalid_then_valid(self):
        from cicada.interactive_setup import _text_based_editor_selection

        with patch("builtins.input", side_effect=["invalid", "1"]):
            result = _text_based_editor_selection()

        assert result == "claude"

    def test_keyboard_interrupt(self):
        from cicada.interactive_setup import _text_based_editor_selection

        with patch("builtins.input", side_effect=KeyboardInterrupt()):
            with pytest.raises(SystemExit) as exc_info:
                _text_based_editor_selection()

        assert exc_info.value.code == 1


class TestShowFirstTimeSetupDefaults:
    """Tests for show_first_time_setup with default values."""

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_default_index_prs_skips_pr_menu(self, mock_menu_class, mock_ascii):
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"
        configure_menu(mock_menu_class, [0, 0])  # Only 2 selections: mode, claude_md

        indexing_mode, index_prs, add_to_claude_md, _ = show_first_time_setup(
            default_index_prs=True
        )

        assert index_prs is True

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_default_add_to_claude_skips_menu(self, mock_menu_class, mock_ascii):
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"
        configure_menu(mock_menu_class, [0, 0])  # Only 2 selections: mode, pr

        indexing_mode, index_prs, add_to_claude_md, _ = show_first_time_setup(
            default_add_to_claude=True
        )

        assert add_to_claude_md is True

    @patch("cicada.interactive_setup.has_terminal_menu", False)
    def test_falls_back_when_no_terminal_menu(self):
        from cicada.interactive_setup import show_first_time_setup

        with patch("cicada.interactive_setup._text_based_setup") as mock_text:
            mock_text.return_value = ("keywords", False, False, None)
            result = show_first_time_setup()

        assert result == ("keywords", False, False, None)


class TestConfigureEmbeddings:
    """Tests for _configure_embeddings function."""

    @patch("cicada.interactive_setup._prompt_model_selection_text")
    @patch("cicada.interactive_setup._prompt_ollama_url")
    def test_returns_config_dict(self, mock_url, mock_model):
        from cicada.interactive_setup import _configure_embeddings

        mock_url.return_value = "http://custom:11434"
        mock_model.return_value = "custom-model"

        with patch("cicada.interactive_setup.has_terminal_menu", False):
            result = _configure_embeddings()

        assert result == {"ollama_host": "http://custom:11434", "model": "custom-model"}

    @patch("cicada.interactive_setup._prompt_model_selection_menu")
    @patch("cicada.interactive_setup._prompt_ollama_url")
    def test_uses_menu_when_available(self, mock_url, mock_menu_model):
        from cicada.interactive_setup import _configure_embeddings

        mock_url.return_value = "http://localhost:11434"
        mock_menu_model.return_value = "menu-model"

        with patch("cicada.interactive_setup.has_terminal_menu", True):
            result = _configure_embeddings()

        assert result["model"] == "menu-model"

    @patch("cicada.interactive_setup._prompt_model_selection_text")
    @patch("cicada.interactive_setup._prompt_model_selection_menu")
    @patch("cicada.interactive_setup._prompt_ollama_url")
    def test_falls_back_to_text_when_menu_returns_none(self, mock_url, mock_menu, mock_text):
        from cicada.interactive_setup import _configure_embeddings

        mock_url.return_value = "http://localhost:11434"
        mock_menu.return_value = None
        mock_text.return_value = "text-model"

        with patch("cicada.interactive_setup.has_terminal_menu", True):
            result = _configure_embeddings()

        assert result["model"] == "text-model"
