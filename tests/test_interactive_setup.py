"""
Comprehensive tests for interactive setup menu

Tests the first-time setup experience for cicada
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
    """Tests for show_first_time_setup function"""

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_fast_tier_skip_pr_indexing(self, mock_menu_class, mock_ascii):
        """Test selecting Fast tier (Regular extraction + Lemmi expansion), skip PR indexing, and skip CLAUDE.md"""
        from cicada.interactive_setup import show_first_time_setup

        # Mock ASCII art
        mock_ascii.return_value = "ASCII ART"

        # Mock menu selections: tier=0 (Fast), pr_indexing=0 (No), claude_md=1 (No)
        mock_menu_instance = configure_menu(mock_menu_class, [0, 0, 1])

        extraction, expansion, index_prs, add_to_claude_md = show_first_time_setup()

        assert extraction == "regular"
        assert expansion == "lemmi"
        assert index_prs is False
        assert add_to_claude_md is False
        mock_ascii.assert_called_once()
        # Should call three times: step 1 (tier), step 2 (pr indexing), and step 3 (CLAUDE.md)
        assert mock_menu_instance.show.call_count == 3

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_balanced_tier_with_pr_indexing(self, mock_menu_class, mock_ascii):
        """Test selecting Balanced tier (KeyBERT + GloVe), index PRs, and add to CLAUDE.md"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"

        mock_menu_instance = configure_menu(
            mock_menu_class,
            [
                1,
                1,
                0,
            ],
        )

        extraction, expansion, index_prs, add_to_claude_md = show_first_time_setup()

        assert extraction == "bert"
        assert expansion == "glove"
        assert index_prs is True
        assert add_to_claude_md is True

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_maximum_tier_skip_pr_indexing(self, mock_menu_class, mock_ascii):
        """Test selecting Maximum tier (KeyBERT + FastText), skip PR indexing, and add to CLAUDE.md"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"

        mock_menu_instance = configure_menu(
            mock_menu_class,
            [
                2,
                0,
                0,
            ],
        )

        extraction, expansion, index_prs, add_to_claude_md = show_first_time_setup()

        assert extraction == "bert"
        assert expansion == "fasttext"
        assert index_prs is False
        assert add_to_claude_md is True

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_keyboard_interrupt_on_tier_selection(self, mock_menu_class, mock_ascii):
        """Test Ctrl+C during tier selection exits gracefully"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"

        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = KeyboardInterrupt()
        mock_menu_class.return_value = mock_menu_instance

        with pytest.raises(SystemExit) as exc_info:
            show_first_time_setup()

        assert exc_info.value.code == 1

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_keyboard_interrupt_on_pr_indexing_selection(self, mock_menu_class, mock_ascii):
        """Test Ctrl+C during PR indexing selection exits gracefully"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"

        mock_menu_instance = MagicMock()
        # First call returns 1 (Balanced tier), second raises KeyboardInterrupt (PR indexing)
        mock_menu_instance.show.side_effect = [1, KeyboardInterrupt()]
        mock_menu_class.return_value = mock_menu_instance

        with pytest.raises(SystemExit) as exc_info:
            show_first_time_setup()

        assert exc_info.value.code == 1

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_keyboard_interrupt_on_claude_md_selection(self, mock_menu_class, mock_ascii):
        """Test Ctrl+C during CLAUDE.md selection exits gracefully"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"

        mock_menu_instance = MagicMock()
        # First call returns 1 (Balanced tier), second returns 0 (No PR), third raises KeyboardInterrupt (CLAUDE.md)
        mock_menu_instance.show.side_effect = [1, 0, KeyboardInterrupt()]
        mock_menu_class.return_value = mock_menu_instance

        with pytest.raises(SystemExit) as exc_info:
            show_first_time_setup()

        assert exc_info.value.code == 1

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_none_selection_on_tier(self, mock_menu_class, mock_ascii):
        """Test ESC/cancel on tier selection exits gracefully"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"

        mock_menu_instance = MagicMock()
        mock_menu_instance.show.return_value = None  # User pressed ESC
        mock_menu_class.return_value = mock_menu_instance

        with pytest.raises(SystemExit) as exc_info:
            show_first_time_setup()

        assert exc_info.value.code == 1

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_none_selection_on_pr_indexing(self, mock_menu_class, mock_ascii):
        """Test ESC/cancel on PR indexing selection exits gracefully"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"

        mock_menu_instance = MagicMock()
        # First call returns 1 (Balanced tier), second returns None (cancel)
        mock_menu_instance.show.side_effect = [1, None]
        mock_menu_class.return_value = mock_menu_instance

        with pytest.raises(SystemExit) as exc_info:
            show_first_time_setup()

        assert exc_info.value.code == 1

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_none_selection_on_claude_md(self, mock_menu_class, mock_ascii):
        """Test ESC/cancel on CLAUDE.md selection exits gracefully"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"

        mock_menu_instance = MagicMock()
        # First call returns 1 (Balanced tier), second returns 0 (No PR), third returns None (cancel)
        mock_menu_instance.show.side_effect = [1, 0, None]
        mock_menu_class.return_value = mock_menu_instance

        with pytest.raises(SystemExit) as exc_info:
            show_first_time_setup()

        assert exc_info.value.code == 1

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_return_value_is_tuple(self, mock_menu_class, mock_ascii):
        """Test that return value is a tuple of two strings and two booleans"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"

        mock_menu_instance = configure_menu(
            mock_menu_class,
            [
                0,
                1,
                0,
            ],
        )

        result = show_first_time_setup()

        assert isinstance(result, tuple)
        assert len(result) == 4
        assert isinstance(result[0], str)
        assert isinstance(result[1], str)
        assert isinstance(result[2], bool)
        assert isinstance(result[3], bool)

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_menu_created_with_correct_items(self, mock_menu_class, mock_ascii):
        """Test that TerminalMenu is created with correct tier, PR indexing, and CLAUDE.md items"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"

        mock_menu_instance = configure_menu(
            mock_menu_class,
            [
                0,
                1,
                0,
            ],
        )

        show_first_time_setup()

        # Check that TerminalMenu was called three times (tier, PR indexing, and CLAUDE.md)
        assert mock_menu_class.call_count == 3

        # Check first call (tier selection)
        first_call_args = mock_menu_class.call_args_list[0]
        tier_items = first_call_args[0][0]
        assert len(tier_items) == 3
        assert "Fast" in tier_items[0]
        assert "Balanced" in tier_items[1]
        assert "Maximum" in tier_items[2]

        # Check second call (PR indexing selection)
        second_call_args = mock_menu_class.call_args_list[1]
        pr_items = second_call_args[0][0]
        assert len(pr_items) == 2
        assert "No" in pr_items[0]
        assert "Yes" in pr_items[1]

        # Check third call (CLAUDE.md selection)
        third_call_args = mock_menu_class.call_args_list[2]
        claude_md_items = third_call_args[0][0]
        assert len(claude_md_items) == 2
        assert "Yes" in claude_md_items[0]  # Default is Yes
        assert "No" in claude_md_items[1]

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_ascii_art_displayed(self, mock_menu_class, mock_ascii, capsys):
        """Test that ASCII art is displayed at start"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "🦗 CICADA ASCII ART"

        mock_menu_instance = configure_menu(mock_menu_class, [0, 0, 0])

        show_first_time_setup()

        # Verify ASCII art was called
        mock_ascii.assert_called_once()

        # Verify it was printed
        captured = capsys.readouterr()
        assert "🦗 CICADA ASCII ART" in captured.out

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_welcome_message_displayed(self, mock_menu_class, mock_ascii, capsys):
        """Test that welcome message is displayed"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = ""

        mock_menu_instance = configure_menu(mock_menu_class, [0, 0, 0])

        show_first_time_setup()

        captured = capsys.readouterr()
        assert "Welcome to CICADA" in captured.out
        assert "first time running CICADA" in captured.out

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_success_message_displayed(self, mock_menu_class, mock_ascii, capsys):
        """Test that success message is displayed after tier selection"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = ""

        mock_menu_instance = configure_menu(
            mock_menu_class,
            [
                0,
                0,
                0,
            ],
        )

        show_first_time_setup()

        captured = capsys.readouterr()
        assert "Selected:" in captured.out or "✓" in captured.out
        assert "FAST" in captured.out

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_fast_tier_explanation_shown(self, mock_menu_class, mock_ascii, capsys):
        """Test that Fast tier explanation is shown when Fast tier is selected"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = ""

        mock_menu_instance = configure_menu(
            mock_menu_class,
            [
                0,
                0,
                0,
            ],
        )

        show_first_time_setup()

        captured = capsys.readouterr()
        assert "FAST tier" in captured.out
        assert "Term frequency" in captured.out or "term frequency" in captured.out

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_balanced_tier_explanation_shown(self, mock_menu_class, mock_ascii, capsys):
        """Test that Balanced tier explanation is shown when Balanced tier is selected"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = ""

        mock_menu_instance = configure_menu(
            mock_menu_class,
            [
                1,
                0,
                0,
            ],
        )

        show_first_time_setup()

        captured = capsys.readouterr()
        assert "BALANCED tier" in captured.out
        assert "KeyBERT" in captured.out
        assert "GloVe" in captured.out

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_menu_cursor_style(self, mock_menu_class, mock_ascii):
        """Test that menu is created with correct styling"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = ""

        mock_menu_instance = configure_menu(mock_menu_class, [0, 0, 0])

        show_first_time_setup()

        # Check that menu was created with correct style parameters
        first_call_kwargs = mock_menu_class.call_args_list[0][1]
        assert first_call_kwargs["menu_cursor"] == "» "
        assert first_call_kwargs["cycle_cursor"] == True
        assert first_call_kwargs["clear_screen"] == False

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_tier_map_correctness(self, mock_menu_class, mock_ascii):
        """Test that tier mapping is correct for all tier indices"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = ""

        mock_menu_instance = MagicMock()
        mock_menu_class.return_value = mock_menu_instance

        # Test all tier indices
        test_cases = [
            (0, "regular", "lemmi"),  # Fast tier
            (1, "bert", "glove"),  # Balanced tier
            (2, "bert", "fasttext"),  # Maximum tier
        ]

        for tier_index, expected_extraction, expected_expansion in test_cases:
            mock_menu_instance.show.side_effect = [
                tier_index,
                0,
                0,
            ]  # tier + pr indexing + claude_md
            extraction_method, expansion_method, index_prs, add_to_claude_md = (
                show_first_time_setup()
            )
            assert (
                extraction_method == expected_extraction
            ), f"Expected {expected_extraction} for tier index {tier_index}"
            assert (
                expansion_method == expected_expansion
            ), f"Expected {expected_expansion} for tier index {tier_index}"

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_tier_index_as_tuple(self, mock_menu_class, mock_ascii):
        """Test that tier_index as tuple is handled correctly"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = ""

        mock_menu_instance = MagicMock()
        # Return tuple instead of int for tier selection (some terminals do this)
        mock_menu_instance.show.side_effect = [(1, "some_extra_data"), 0, 0]  # tier, pr, claude_md
        mock_menu_class.return_value = mock_menu_instance

        extraction_method, expansion_method, index_prs, add_to_claude_md = show_first_time_setup()

        assert extraction_method == "bert"
        assert expansion_method == "glove"
        assert index_prs is False
        assert add_to_claude_md is True


class TestTextBasedSetup:
    """Tests for _text_based_setup fallback function"""

    @patch("builtins.input")
    def test_text_default_fast_tier_skip_pr_indexing(self, mock_input):
        """Test text-based setup with default values (empty input)"""
        from cicada.interactive_setup import _text_based_setup

        # User presses enter for defaults: tier=1 (Fast), pr=2 (No), claude_md=1 (Yes)
        mock_input.side_effect = ["", "", ""]

        extraction, expansion, index_prs, add_to_claude_md = _text_based_setup()

        assert extraction == "regular"
        assert expansion == "lemmi"
        assert index_prs is False
        assert add_to_claude_md is True

    @patch("builtins.input")
    def test_text_fast_tier_with_pr_indexing(self, mock_input):
        """Test text-based setup selecting Fast tier with PR indexing and add to CLAUDE.md"""
        from cicada.interactive_setup import _text_based_setup

        mock_input.side_effect = ["1", "1", "1"]  # tier=1 (Fast), pr=1 (Yes), claude_md=1 (Yes)

        extraction, expansion, index_prs, add_to_claude_md = _text_based_setup()

        assert extraction == "regular"
        assert expansion == "lemmi"
        assert index_prs is True
        assert add_to_claude_md is True

    @patch("builtins.input")
    def test_text_balanced_tier_skip_pr_indexing(self, mock_input):
        """Test text-based setup selecting Balanced tier, skip PR indexing, and skip CLAUDE.md"""
        from cicada.interactive_setup import _text_based_setup

        mock_input.side_effect = ["2", "2", "2"]  # tier=2 (Balanced), pr=2 (No), claude_md=2 (No)

        extraction, expansion, index_prs, add_to_claude_md = _text_based_setup()

        assert extraction == "bert"
        assert expansion == "glove"
        assert index_prs is False
        assert add_to_claude_md is False

    @patch("builtins.input")
    def test_text_maximum_tier_with_pr_indexing(self, mock_input):
        """Test text-based setup selecting Maximum tier with PR indexing and add to CLAUDE.md"""
        from cicada.interactive_setup import _text_based_setup

        mock_input.side_effect = ["3", "1", "1"]  # tier=3 (Maximum), pr=1 (Yes), claude_md=1 (Yes)

        extraction, expansion, index_prs, add_to_claude_md = _text_based_setup()

        assert extraction == "bert"
        assert expansion == "fasttext"
        assert index_prs is True
        assert add_to_claude_md is True

    @patch("builtins.input")
    def test_text_invalid_tier_then_valid(self, mock_input, capsys):
        """Test text-based setup with invalid tier input followed by valid"""
        from cicada.interactive_setup import _text_based_setup

        # First invalid (4), then valid (1), then pr indexing (2), then claude_md (1)
        mock_input.side_effect = ["4", "1", "2", "1"]

        extraction, expansion, index_prs, add_to_claude_md = _text_based_setup()

        assert extraction == "regular"
        assert expansion == "lemmi"
        assert index_prs is False
        assert add_to_claude_md is True

        captured = capsys.readouterr()
        assert "Invalid choice" in captured.out

    @patch("builtins.input")
    def test_text_invalid_pr_indexing_then_valid(self, mock_input, capsys):
        """Test text-based setup with invalid PR indexing input followed by valid"""
        from cicada.interactive_setup import _text_based_setup

        # Valid tier (2=Balanced), then invalid pr indexing (3), then valid pr indexing (1=Yes), then claude_md (2=No)
        mock_input.side_effect = ["2", "3", "1", "2"]

        extraction, expansion, index_prs, add_to_claude_md = _text_based_setup()

        assert extraction == "bert"
        assert expansion == "glove"
        assert index_prs is True
        assert add_to_claude_md is False

        captured = capsys.readouterr()
        assert "Invalid choice" in captured.out

    @patch("builtins.input")
    def test_text_keyboard_interrupt_on_tier_selection(self, mock_input):
        """Test text-based setup with Ctrl+C during tier selection"""
        from cicada.interactive_setup import _text_based_setup

        mock_input.side_effect = KeyboardInterrupt()

        with pytest.raises(SystemExit) as exc_info:
            _text_based_setup()

        assert exc_info.value.code == 1

    @patch("builtins.input")
    def test_text_keyboard_interrupt_on_pr_indexing(self, mock_input):
        """Test text-based setup with Ctrl+C during PR indexing selection"""
        from cicada.interactive_setup import _text_based_setup

        # Valid tier (2=Balanced), then KeyboardInterrupt on PR indexing
        mock_input.side_effect = ["2", KeyboardInterrupt()]

        with pytest.raises(SystemExit) as exc_info:
            _text_based_setup()

        assert exc_info.value.code == 1

    @patch("builtins.input")
    def test_text_keyboard_interrupt_on_claude_md_selection(self, mock_input):
        """Test text-based setup with Ctrl+C during CLAUDE.md selection"""
        from cicada.interactive_setup import _text_based_setup

        # Valid tier (2=Balanced), valid PR indexing (1=Yes), then KeyboardInterrupt on CLAUDE.md
        mock_input.side_effect = ["2", "1", KeyboardInterrupt()]

        with pytest.raises(SystemExit) as exc_info:
            _text_based_setup()

        assert exc_info.value.code == 1

    @patch("builtins.input")
    def test_text_eof_error_on_tier_selection(self, mock_input):
        """Test text-based setup with EOF (Ctrl+D) during tier selection"""
        from cicada.interactive_setup import _text_based_setup

        mock_input.side_effect = EOFError()

        with pytest.raises(SystemExit) as exc_info:
            _text_based_setup()

        assert exc_info.value.code == 1

    @patch("builtins.input")
    def test_text_eof_error_on_pr_indexing(self, mock_input):
        """Test text-based setup with EOF (Ctrl+D) during PR indexing selection"""
        from cicada.interactive_setup import _text_based_setup

        # Valid tier, then EOFError on PR indexing
        mock_input.side_effect = ["2", EOFError()]

        with pytest.raises(SystemExit) as exc_info:
            _text_based_setup()

        assert exc_info.value.code == 1

    @patch("builtins.input")
    def test_text_eof_error_on_claude_md_selection(self, mock_input):
        """Test text-based setup with EOF (Ctrl+D) during CLAUDE.md selection"""
        from cicada.interactive_setup import _text_based_setup

        # Valid tier, valid PR indexing, then EOFError on CLAUDE.md
        mock_input.side_effect = ["2", "1", EOFError()]

        with pytest.raises(SystemExit) as exc_info:
            _text_based_setup()

        assert exc_info.value.code == 1

    @patch("builtins.input")
    def test_text_shows_fast_tier_explanation(self, mock_input, capsys):
        """Test that text-based setup shows Fast tier explanation"""
        from cicada.interactive_setup import _text_based_setup

        mock_input.side_effect = ["1", "1", "1"]  # tier=1 (Fast), pr=1 (Yes), claude_md=1 (Yes)

        _text_based_setup()

        captured = capsys.readouterr()
        assert "FAST tier" in captured.out
        assert "Term frequency" in captured.out or "term frequency" in captured.out

    @patch("builtins.input")
    def test_text_shows_balanced_tier_explanation(self, mock_input, capsys):
        """Test that text-based setup shows Balanced tier explanation"""
        from cicada.interactive_setup import _text_based_setup

        mock_input.side_effect = ["2", "1", "1"]  # tier=2 (Balanced), pr=1 (Yes), claude_md=1 (Yes)

        _text_based_setup()

        captured = capsys.readouterr()
        assert "BALANCED tier" in captured.out
        assert "KeyBERT" in captured.out
        assert "GloVe" in captured.out

    @patch("builtins.input")
    def test_text_shows_welcome_message(self, mock_input, capsys):
        """Test that text-based setup shows welcome message"""
        from cicada.interactive_setup import _text_based_setup

        mock_input.side_effect = ["1", "1", "1"]  # tier, pr, claude_md

        _text_based_setup()

        captured = capsys.readouterr()
        assert "Welcome to CICADA" in captured.out
        assert "first time running CICADA" in captured.out

    @patch("builtins.input")
    def test_text_shows_success_message(self, mock_input, capsys):
        """Test that text-based setup shows success message"""
        from cicada.interactive_setup import _text_based_setup

        mock_input.side_effect = ["1", "1", "1"]  # tier, pr, claude_md

        _text_based_setup()

        captured = capsys.readouterr()
        assert "Selected:" in captured.out or "✓" in captured.out
        # Should show extraction and expansion method selection success


class TestFallbackScenarios:
    """Tests for fallback to text-based setup"""

    @patch("cicada.interactive_setup.has_terminal_menu", False)
    @patch("builtins.input")
    def test_fallback_when_terminal_menu_not_available(self, mock_input):
        """Test fallback to text-based setup when simple-term-menu not installed"""
        from cicada.interactive_setup import show_first_time_setup

        mock_input.side_effect = ["1", "1", "1"]  # tier=1 (Fast), pr=1 (Yes), claude_md=1 (Yes)

        extraction_method, expansion_method, index_prs, add_to_claude_md = show_first_time_setup()

        assert extraction_method == "regular"
        assert expansion_method == "lemmi"
        assert index_prs is True
        assert add_to_claude_md is True

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu", None)
    @patch("builtins.input")
    def test_fallback_when_terminal_menu_is_none(self, mock_input, mock_ascii):
        """Test fallback when TerminalMenu is None"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"
        mock_input.side_effect = ["2", "2", "2"]  # tier=2 (Balanced), pr=2 (No), claude_md=2 (No)

        extraction_method, expansion_method, index_prs, add_to_claude_md = show_first_time_setup()

        assert extraction_method == "bert"
        assert expansion_method == "glove"
        assert index_prs is False
        assert add_to_claude_md is False

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    @patch("builtins.input")
    def test_fallback_on_exception_during_tier_menu(self, mock_input, mock_menu_class, mock_ascii):
        """Test fallback to text-based setup when TerminalMenu raises exception"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"

        # Make TerminalMenu.show() raise an exception
        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = Exception("Terminal not supported")
        mock_menu_class.return_value = mock_menu_instance

        mock_input.side_effect = ["1", "1", "1"]  # tier=1 (Fast), pr=1 (Yes), claude_md=1 (Yes)

        extraction_method, expansion_method, index_prs, add_to_claude_md = show_first_time_setup()

        assert extraction_method == "regular"
        assert expansion_method == "lemmi"
        assert index_prs is True
        assert add_to_claude_md is True

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    @patch("builtins.input")
    def test_fallback_on_exception_during_pr_indexing_menu(
        self, mock_input, mock_menu_class, mock_ascii
    ):
        """Test fallback when exception occurs during PR indexing selection"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"

        # First menu succeeds (tier), second menu raises exception (PR indexing)
        mock_menu_instance = configure_menu(mock_menu_class, [1, Exception("Terminal error")])

        # Text-based setup will be called after exception
        mock_input.side_effect = ["2", "1", "1"]  # tier=2 (Balanced), pr=1 (Yes), claude_md=1 (Yes)

        extraction_method, expansion_method, index_prs, add_to_claude_md = show_first_time_setup()

        assert extraction_method == "bert"
        assert expansion_method == "glove"
        assert index_prs is True
        assert add_to_claude_md is True

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    @patch("builtins.input")
    def test_fallback_message_shown(self, mock_input, mock_menu_class, mock_ascii, capsys):
        """Test that fallback message is shown when terminal menu fails"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"

        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = Exception("Terminal not supported")
        mock_menu_class.return_value = mock_menu_instance

        mock_input.side_effect = ["1", "1", "1"]  # tier, pr, claude_md

        show_first_time_setup()

        captured = capsys.readouterr()
        assert "Terminal menu not supported" in captured.err

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_eoferror_on_tier_selection(self, mock_menu_class, mock_ascii):
        """Test EOFError during tier selection exits gracefully"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"

        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = EOFError()
        mock_menu_class.return_value = mock_menu_instance

        with pytest.raises(SystemExit) as exc_info:
            show_first_time_setup()

        assert exc_info.value.code == 1

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_eoferror_on_pr_indexing_selection(self, mock_menu_class, mock_ascii):
        """Test EOFError during PR indexing selection exits gracefully"""
        from cicada.interactive_setup import show_first_time_setup

        mock_ascii.return_value = "ASCII ART"

        mock_menu_instance = MagicMock()
        # First call succeeds (Balanced tier), second raises EOFError (PR indexing)
        mock_menu_instance.show.side_effect = [1, EOFError()]
        mock_menu_class.return_value = mock_menu_instance

        with pytest.raises(SystemExit) as exc_info:
            show_first_time_setup()

        assert exc_info.value.code == 1


class TestTextBasedEditorSelection:
    """Tests for _text_based_editor_selection function"""

    @patch("builtins.input")
    def test_claude_selection(self, mock_input):
        """Test selecting Claude Code"""
        from cicada.interactive_setup import _text_based_editor_selection

        mock_input.return_value = "1"

        editor = _text_based_editor_selection()

        assert editor == "claude"

    @patch("builtins.input")
    def test_cursor_selection(self, mock_input):
        """Test selecting Cursor"""
        from cicada.interactive_setup import _text_based_editor_selection

        mock_input.return_value = "2"

        editor = _text_based_editor_selection()

        assert editor == "cursor"

    @patch("builtins.input")
    def test_vs_selection(self, mock_input):
        """Test selecting VS Code"""
        from cicada.interactive_setup import _text_based_editor_selection

        mock_input.return_value = "3"

        editor = _text_based_editor_selection()

        assert editor == "vs"

    @patch("builtins.input")
    def test_gemini_selection(self, mock_input):
        """Test selecting Gemini CLI"""
        from cicada.interactive_setup import _text_based_editor_selection

        mock_input.return_value = "4"

        editor = _text_based_editor_selection()

        assert editor == "gemini"

    @patch("builtins.input")
    def test_codex_selection(self, mock_input):
        """Test selecting Codex"""
        from cicada.interactive_setup import _text_based_editor_selection

        mock_input.return_value = "5"

        editor = _text_based_editor_selection()

        assert editor == "codex"

    @patch("builtins.input")
    def test_opencode_selection(self, mock_input):
        """Test selecting OpenCode"""
        from cicada.interactive_setup import _text_based_editor_selection

        mock_input.return_value = "6"

        editor = _text_based_editor_selection()

        assert editor == "opencode"

    @patch("builtins.input")
    def test_default_selection(self, mock_input):
        """Test default selection (empty input defaults to Claude)"""
        from cicada.interactive_setup import _text_based_editor_selection

        mock_input.return_value = ""

        editor = _text_based_editor_selection()

        assert editor == "claude"

    @patch("builtins.input")
    def test_invalid_then_valid(self, mock_input, capsys):
        """Test invalid input followed by valid input"""
        from cicada.interactive_setup import _text_based_editor_selection

        mock_input.side_effect = ["7", "invalid", "2"]

        editor = _text_based_editor_selection()

        assert editor == "cursor"
        captured = capsys.readouterr()
        assert "Invalid choice" in captured.out

    @patch("builtins.input")
    def test_keyboard_interrupt(self, mock_input):
        """Test Ctrl+C exits gracefully"""
        from cicada.interactive_setup import _text_based_editor_selection

        mock_input.side_effect = KeyboardInterrupt()

        with pytest.raises(SystemExit) as exc_info:
            _text_based_editor_selection()

        assert exc_info.value.code == 1

    @patch("builtins.input")
    def test_eof_error(self, mock_input):
        """Test EOF (Ctrl+D) exits gracefully"""
        from cicada.interactive_setup import _text_based_editor_selection

        mock_input.side_effect = EOFError()

        with pytest.raises(SystemExit) as exc_info:
            _text_based_editor_selection()

        assert exc_info.value.code == 1

    @patch("builtins.input")
    def test_shows_editor_options(self, mock_input, capsys):
        """Test that all editor options are displayed"""
        from cicada.interactive_setup import _text_based_editor_selection

        mock_input.return_value = "1"

        _text_based_editor_selection()

        captured = capsys.readouterr()
        assert "Claude Code" in captured.out
        assert "Cursor" in captured.out
        assert "VS Code" in captured.out
        assert "Gemini CLI" in captured.out
        assert "Codex" in captured.out
        assert "OpenCode" in captured.out


class TestShowFullInteractiveSetup:
    """Tests for show_full_interactive_setup function"""

    @pytest.fixture
    def mock_elixir_repo(self, tmp_path):
        """Create a mock Elixir repository"""
        (tmp_path / "mix.exs").write_text("# Mock mix file")
        return tmp_path

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    @patch("cicada.setup.setup")
    @patch("cicada.utils.storage.get_config_path")
    @patch("cicada.utils.storage.get_index_path")
    def test_full_setup_claude_fast_tier_skip_pr(
        self,
        mock_get_index,
        mock_get_config,
        mock_setup,
        mock_menu_class,
        mock_ascii,
        mock_elixir_repo,
    ):
        """Test full interactive setup with Claude, Fast tier, skip PR indexing, and add to CLAUDE.md"""
        from cicada.interactive_setup import show_full_interactive_setup

        mock_ascii.return_value = "ASCII ART"

        # Mock paths to not exist (no existing index)
        mock_config_path = MagicMock()
        mock_config_path.exists.return_value = False
        mock_get_config.return_value = mock_config_path

        mock_index_path = MagicMock()
        mock_index_path.exists.return_value = False
        mock_get_index.return_value = mock_index_path

        # Menu selections: editor=0 (Claude), tier=0 (Fast), pr=0 (No), claude_md=0 (Yes)
        mock_menu_instance = configure_menu(mock_menu_class, [0, 0, 0, 0])

        show_full_interactive_setup(mock_elixir_repo)

        # Verify setup was called with correct parameters
        mock_setup.assert_called_once()
        call_args = mock_setup.call_args[0]
        call_kwargs = mock_setup.call_args[1]
        assert call_args[0] == "claude"
        assert call_kwargs["extraction_method"] == "regular"
        assert call_kwargs["expansion_method"] == "lemmi"

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    @patch("cicada.setup.setup")
    @patch("cicada.utils.storage.get_config_path")
    @patch("cicada.utils.storage.get_index_path")
    def test_full_setup_cursor_balanced_tier_with_pr(
        self,
        mock_get_index,
        mock_get_config,
        mock_setup,
        mock_menu_class,
        mock_ascii,
        mock_elixir_repo,
    ):
        """Test full interactive setup with Cursor, Balanced tier, with PR indexing, and skip CLAUDE.md"""
        from cicada.interactive_setup import show_full_interactive_setup

        mock_ascii.return_value = "ASCII ART"

        # Mock paths to not exist
        mock_config_path = MagicMock()
        mock_config_path.exists.return_value = False
        mock_get_config.return_value = mock_config_path

        mock_index_path = MagicMock()
        mock_index_path.exists.return_value = False
        mock_get_index.return_value = mock_index_path

        # Menu selections: editor=1 (Cursor), tier=1 (Balanced), pr=1 (Yes), claude_md=1 (No)
        mock_menu_instance = configure_menu(mock_menu_class, [1, 1, 1, 1])

        # Need to mock PR indexer
        with patch("cicada.interactive_setup_helpers.run_pr_indexing"):
            show_full_interactive_setup(mock_elixir_repo)

        mock_setup.assert_called_once()
        call_args = mock_setup.call_args[0]
        call_kwargs = mock_setup.call_args[1]
        assert call_args[0] == "cursor"
        assert call_kwargs["extraction_method"] == "bert"
        assert call_kwargs["expansion_method"] == "glove"

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    @patch("cicada.setup.setup")
    @patch("cicada.utils.storage.get_config_path")
    @patch("cicada.utils.storage.get_index_path")
    def test_full_setup_vs_maximum_tier_skip_pr(
        self,
        mock_get_index,
        mock_get_config,
        mock_setup,
        mock_menu_class,
        mock_ascii,
        mock_elixir_repo,
    ):
        """Test full interactive setup with VS Code, Maximum tier, skip PR indexing, and add to CLAUDE.md"""
        from cicada.interactive_setup import show_full_interactive_setup

        mock_ascii.return_value = "ASCII ART"

        # Mock paths to not exist
        mock_config_path = MagicMock()
        mock_config_path.exists.return_value = False
        mock_get_config.return_value = mock_config_path

        mock_index_path = MagicMock()
        mock_index_path.exists.return_value = False
        mock_get_index.return_value = mock_index_path

        # Menu selections: editor=2 (VS), tier=2 (Maximum), pr=0 (No), claude_md=0 (Yes)
        mock_menu_instance = configure_menu(mock_menu_class, [2, 2, 0, 0])

        show_full_interactive_setup(mock_elixir_repo)

        mock_setup.assert_called_once()
        call_args = mock_setup.call_args[0]
        call_kwargs = mock_setup.call_args[1]
        assert call_args[0] == "vs"
        assert call_kwargs["extraction_method"] == "bert"
        assert call_kwargs["expansion_method"] == "fasttext"

    def test_non_elixir_project_exits(self, tmp_path, capsys):
        """Test that non-Elixir project shows error and exits"""
        from cicada.interactive_setup import show_full_interactive_setup

        # No mix.exs file
        with pytest.raises(SystemExit) as exc_info:
            show_full_interactive_setup(tmp_path)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "does not appear to be an Elixir project" in captured.out
        assert "mix.exs not found" in captured.out

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    @patch("cicada.setup.setup")
    @patch("cicada.utils.storage.get_config_path")
    @patch("cicada.utils.storage.get_index_path")
    def test_existing_index_uses_existing_config(
        self,
        mock_get_index,
        mock_get_config,
        mock_setup,
        mock_menu_class,
        mock_ascii,
        mock_elixir_repo,
    ):
        """Test that existing index causes existing config to be read and used"""
        from cicada.interactive_setup import show_full_interactive_setup

        mock_ascii.return_value = "ASCII ART"

        # Mock paths to exist
        mock_config_path = MagicMock()
        mock_config_path.exists.return_value = True
        mock_get_config.return_value = mock_config_path

        mock_index_path = MagicMock()
        mock_index_path.exists.return_value = True
        mock_get_index.return_value = mock_index_path

        # Mock reading the config file
        with (
            patch("builtins.open", MagicMock()),
            patch(
                "yaml.safe_load",
                return_value={
                    "keyword_extraction": {"method": "bert"},
                    "keyword_expansion": {"method": "glove"},
                },
            ),
        ):
            # Only editor selection should happen (index 0 = Claude)
            mock_menu_instance = MagicMock()
            mock_menu_instance.show.return_value = 0
            mock_menu_class.return_value = mock_menu_instance

            show_full_interactive_setup(mock_elixir_repo)

            # Should call setup with existing settings
            mock_setup.assert_called_once()
            call_kwargs = mock_setup.call_args[1]
            assert call_kwargs["extraction_method"] == "bert"
            assert call_kwargs["expansion_method"] == "glove"
            assert call_kwargs["index_exists"] is True

            # Should only show editor menu, not extraction/expansion menus
            assert mock_menu_instance.show.call_count == 1

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    def test_keyboard_interrupt_on_editor_selection(
        self, mock_menu_class, mock_ascii, mock_elixir_repo
    ):
        """Test Ctrl+C during editor selection exits gracefully"""
        from cicada.interactive_setup import show_full_interactive_setup

        mock_ascii.return_value = "ASCII ART"

        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = KeyboardInterrupt()
        mock_menu_class.return_value = mock_menu_instance

        with pytest.raises(SystemExit) as exc_info:
            show_full_interactive_setup(mock_elixir_repo)

        assert exc_info.value.code == 1

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    @patch("cicada.utils.storage.get_config_path")
    @patch("cicada.utils.storage.get_index_path")
    def test_keyboard_interrupt_on_tier_selection_full_setup(
        self, mock_get_index, mock_get_config, mock_menu_class, mock_ascii, mock_elixir_repo
    ):
        """Test Ctrl+C during tier selection exits gracefully"""
        from cicada.interactive_setup import show_full_interactive_setup

        mock_ascii.return_value = "ASCII ART"

        # No existing index
        mock_config_path = MagicMock()
        mock_config_path.exists.return_value = False
        mock_get_config.return_value = mock_config_path

        mock_index_path = MagicMock()
        mock_index_path.exists.return_value = False
        mock_get_index.return_value = mock_index_path

        # Editor selection succeeds, tier selection gets Ctrl+C
        mock_menu_instance = configure_menu(mock_menu_class, [0, KeyboardInterrupt()])

        with pytest.raises(SystemExit) as exc_info:
            show_full_interactive_setup(mock_elixir_repo)

        assert exc_info.value.code == 1

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    @patch("cicada.utils.storage.get_config_path")
    @patch("cicada.utils.storage.get_index_path")
    def test_keyboard_interrupt_on_pr_indexing_selection_full_setup(
        self, mock_get_index, mock_get_config, mock_menu_class, mock_ascii, mock_elixir_repo
    ):
        """Test Ctrl+C during PR indexing selection exits gracefully"""
        from cicada.interactive_setup import show_full_interactive_setup

        mock_ascii.return_value = "ASCII ART"

        # No existing index
        mock_config_path = MagicMock()
        mock_config_path.exists.return_value = False
        mock_get_config.return_value = mock_config_path

        mock_index_path = MagicMock()
        mock_index_path.exists.return_value = False
        mock_get_index.return_value = mock_index_path

        # Editor + tier succeed, PR indexing gets Ctrl+C
        mock_menu_instance = configure_menu(mock_menu_class, [0, 1, KeyboardInterrupt()])

        with pytest.raises(SystemExit) as exc_info:
            show_full_interactive_setup(mock_elixir_repo)

        assert exc_info.value.code == 1

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    @patch("cicada.utils.storage.get_config_path")
    @patch("cicada.utils.storage.get_index_path")
    def test_keyboard_interrupt_on_claude_md_selection_full_setup(
        self, mock_get_index, mock_get_config, mock_menu_class, mock_ascii, mock_elixir_repo
    ):
        """Test Ctrl+C during CLAUDE.md selection exits gracefully"""
        from cicada.interactive_setup import show_full_interactive_setup

        mock_ascii.return_value = "ASCII ART"

        # No existing index
        mock_config_path = MagicMock()
        mock_config_path.exists.return_value = False
        mock_get_config.return_value = mock_config_path

        mock_index_path = MagicMock()
        mock_index_path.exists.return_value = False
        mock_get_index.return_value = mock_index_path

        # Editor + tier + PR succeed, CLAUDE.md gets Ctrl+C
        mock_menu_instance = configure_menu(mock_menu_class, [0, 1, 0, KeyboardInterrupt()])

        with pytest.raises(SystemExit) as exc_info:
            show_full_interactive_setup(mock_elixir_repo)

        assert exc_info.value.code == 1

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    @patch("cicada.utils.storage.get_config_path")
    @patch("cicada.utils.storage.get_index_path")
    def test_none_selection_on_editor(
        self, mock_get_index, mock_get_config, mock_menu_class, mock_ascii, mock_elixir_repo
    ):
        """Test ESC on editor selection exits gracefully"""
        from cicada.interactive_setup import show_full_interactive_setup

        mock_ascii.return_value = "ASCII ART"

        mock_menu_instance = MagicMock()
        mock_menu_instance.show.return_value = None
        mock_menu_class.return_value = mock_menu_instance

        with pytest.raises(SystemExit) as exc_info:
            show_full_interactive_setup(mock_elixir_repo)

        assert exc_info.value.code == 1

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    @patch("cicada.utils.storage.get_config_path")
    @patch("cicada.utils.storage.get_index_path")
    def test_none_selection_on_tier_full_setup(
        self, mock_get_index, mock_get_config, mock_menu_class, mock_ascii, mock_elixir_repo
    ):
        """Test ESC on tier selection exits gracefully"""
        from cicada.interactive_setup import show_full_interactive_setup

        mock_ascii.return_value = "ASCII ART"

        # No existing index
        mock_config_path = MagicMock()
        mock_config_path.exists.return_value = False
        mock_get_config.return_value = mock_config_path

        mock_index_path = MagicMock()
        mock_index_path.exists.return_value = False
        mock_get_index.return_value = mock_index_path

        # Editor succeeds, tier returns None
        mock_menu_instance = configure_menu(mock_menu_class, [0, None])

        with pytest.raises(SystemExit) as exc_info:
            show_full_interactive_setup(mock_elixir_repo)

        assert exc_info.value.code == 1

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    @patch("cicada.utils.storage.get_config_path")
    @patch("cicada.utils.storage.get_index_path")
    def test_none_selection_on_pr_indexing_full_setup(
        self, mock_get_index, mock_get_config, mock_menu_class, mock_ascii, mock_elixir_repo
    ):
        """Test ESC on PR indexing selection exits gracefully"""
        from cicada.interactive_setup import show_full_interactive_setup

        mock_ascii.return_value = "ASCII ART"

        # No existing index
        mock_config_path = MagicMock()
        mock_config_path.exists.return_value = False
        mock_get_config.return_value = mock_config_path

        mock_index_path = MagicMock()
        mock_index_path.exists.return_value = False
        mock_get_index.return_value = mock_index_path

        # Editor + tier succeed, PR indexing returns None
        mock_menu_instance = configure_menu(mock_menu_class, [0, 1, None])

        with pytest.raises(SystemExit) as exc_info:
            show_full_interactive_setup(mock_elixir_repo)

        assert exc_info.value.code == 1

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    @patch("cicada.utils.storage.get_config_path")
    @patch("cicada.utils.storage.get_index_path")
    def test_none_selection_on_claude_md_full_setup(
        self, mock_get_index, mock_get_config, mock_menu_class, mock_ascii, mock_elixir_repo
    ):
        """Test ESC on CLAUDE.md selection exits gracefully"""
        from cicada.interactive_setup import show_full_interactive_setup

        mock_ascii.return_value = "ASCII ART"

        # No existing index
        mock_config_path = MagicMock()
        mock_config_path.exists.return_value = False
        mock_get_config.return_value = mock_config_path

        mock_index_path = MagicMock()
        mock_index_path.exists.return_value = False
        mock_get_index.return_value = mock_index_path

        # Editor + tier + PR succeed, CLAUDE.md returns None
        mock_menu_instance = configure_menu(mock_menu_class, [0, 1, 0, None])

        with pytest.raises(SystemExit) as exc_info:
            show_full_interactive_setup(mock_elixir_repo)

        assert exc_info.value.code == 1

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    @patch("cicada.setup.setup")
    @patch("cicada.utils.storage.get_config_path")
    @patch("cicada.utils.storage.get_index_path")
    def test_setup_failure_exits_with_error(
        self,
        mock_get_index,
        mock_get_config,
        mock_setup,
        mock_menu_class,
        mock_ascii,
        mock_elixir_repo,
        capsys,
    ):
        """Test that setup failure shows error and exits"""
        from cicada.interactive_setup import show_full_interactive_setup

        mock_ascii.return_value = "ASCII ART"

        # No existing index
        mock_config_path = MagicMock()
        mock_config_path.exists.return_value = False
        mock_get_config.return_value = mock_config_path

        mock_index_path = MagicMock()
        mock_index_path.exists.return_value = False
        mock_get_index.return_value = mock_index_path

        mock_menu_instance = configure_menu(mock_menu_class, [0, 0, 0, 0])

        mock_setup.side_effect = Exception("Setup failed")

        with pytest.raises(SystemExit) as exc_info:
            show_full_interactive_setup(mock_elixir_repo)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Setup failed" in captured.out

    @patch("cicada.interactive_setup.has_terminal_menu", False)
    @patch("builtins.input")
    @patch("cicada.utils.storage.get_config_path")
    @patch("cicada.utils.storage.get_index_path")
    def test_fallback_to_text_based_editor_selection(
        self, mock_get_index, mock_get_config, mock_input, mock_elixir_repo
    ):
        """Test fallback to text-based editor selection when terminal menu unavailable"""
        from cicada.interactive_setup import show_full_interactive_setup

        # No existing index
        mock_config_path = MagicMock()
        mock_config_path.exists.return_value = False
        mock_get_config.return_value = mock_config_path

        mock_index_path = MagicMock()
        mock_index_path.exists.return_value = False
        mock_get_index.return_value = mock_index_path

        # Text-based inputs: editor=2 (VS), tier=1 (Fast), pr=2 (No), claude_md=1 (Yes)
        # When has_terminal_menu=False, it calls show_first_time_setup and returns early
        mock_input.side_effect = [
            "2",
            "1",
            "2",
            "1",
        ]  # VS, tier=1 (Fast), pr=2 (No), claude_md=1 (Yes)

        # Should run without errors and use text-based fallback
        # Note: When has_terminal_menu=False and there's no existing index,
        # it calls show_first_time_setup which returns with extraction/expansion/index_prs/add_to_claude_md
        with patch("cicada.setup.setup"):
            show_full_interactive_setup(mock_elixir_repo)

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    @patch("builtins.input")
    @patch("cicada.utils.storage.get_config_path")
    @patch("cicada.utils.storage.get_index_path")
    def test_fallback_on_exception_during_editor_menu(
        self,
        mock_get_index,
        mock_get_config,
        mock_input,
        mock_menu_class,
        mock_ascii,
        mock_elixir_repo,
    ):
        """Test fallback when editor menu raises exception"""
        from cicada.interactive_setup import show_full_interactive_setup

        mock_ascii.return_value = "ASCII ART"

        mock_menu_instance = MagicMock()
        mock_menu_instance.show.side_effect = Exception("Terminal error")
        mock_menu_class.return_value = mock_menu_instance

        # Text-based fallback input
        mock_input.side_effect = ["1"]

        # Should not raise, should fall back to text-based
        with patch("cicada.setup.setup"), pytest.raises((SystemExit, Exception)):
            show_full_interactive_setup(mock_elixir_repo)

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    @patch("builtins.input")
    @patch("cicada.utils.storage.get_config_path")
    @patch("cicada.utils.storage.get_index_path")
    def test_fallback_on_exception_during_tier_menu_full_setup(
        self,
        mock_get_index,
        mock_get_config,
        mock_input,
        mock_menu_class,
        mock_ascii,
        mock_elixir_repo,
    ):
        """Test fallback when tier menu raises exception"""
        from cicada.interactive_setup import show_full_interactive_setup

        mock_ascii.return_value = "ASCII ART"

        # No existing index
        mock_config_path = MagicMock()
        mock_config_path.exists.return_value = False
        mock_get_config.return_value = mock_config_path

        mock_index_path = MagicMock()
        mock_index_path.exists.return_value = False
        mock_get_index.return_value = mock_index_path

        # Editor succeeds, tier menu fails
        mock_menu_instance = configure_menu(mock_menu_class, [0, Exception("Terminal error")])

        # Text-based fallback for tier, PR indexing, and CLAUDE.md
        mock_input.side_effect = ["1", "2", "1"]  # tier=1 (Fast), pr=2 (No), claude_md=1 (Yes)

        # Should fall back and complete
        with patch("cicada.setup.setup"):
            show_full_interactive_setup(mock_elixir_repo)

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    @patch("builtins.input")
    @patch("cicada.utils.storage.get_config_path")
    @patch("cicada.utils.storage.get_index_path")
    def test_fallback_on_exception_during_pr_indexing_menu_full_setup(
        self,
        mock_get_index,
        mock_get_config,
        mock_input,
        mock_menu_class,
        mock_ascii,
        mock_elixir_repo,
    ):
        """Test fallback when PR indexing menu raises exception"""
        from cicada.interactive_setup import show_full_interactive_setup

        mock_ascii.return_value = "ASCII ART"

        # No existing index
        mock_config_path = MagicMock()
        mock_config_path.exists.return_value = False
        mock_get_config.return_value = mock_config_path

        mock_index_path = MagicMock()
        mock_index_path.exists.return_value = False
        mock_get_index.return_value = mock_index_path

        # Editor + tier succeed, PR indexing menu fails
        mock_menu_instance = configure_menu(mock_menu_class, [0, 1, Exception("Terminal error")])

        # Text-based fallback (re-runs full setup)
        mock_input.side_effect = ["2", "1", "1"]  # tier=2 (Balanced), pr=1 (Yes), claude_md=1 (Yes)

        # Should fall back and complete
        with patch("cicada.setup.setup"), patch("cicada.interactive_setup_helpers.run_pr_indexing"):
            show_full_interactive_setup(mock_elixir_repo)

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    @patch("cicada.setup.setup")
    @patch("cicada.utils.storage.get_config_path")
    @patch("cicada.utils.storage.get_index_path")
    def test_config_read_error_continues_with_tier_selection(
        self,
        mock_get_index,
        mock_get_config,
        mock_setup,
        mock_menu_class,
        mock_ascii,
        mock_elixir_repo,
    ):
        """Test that config read error causes tier selection to be shown"""
        from cicada.interactive_setup import show_full_interactive_setup

        mock_ascii.return_value = "ASCII ART"

        # Mock paths to exist
        mock_config_path = MagicMock()
        mock_config_path.exists.return_value = True
        mock_get_config.return_value = mock_config_path

        mock_index_path = MagicMock()
        mock_index_path.exists.return_value = True
        mock_get_index.return_value = mock_index_path

        # But reading config fails
        with patch("builtins.open", side_effect=Exception("Read error")):
            mock_menu_instance = MagicMock()
            # Editor, tier, PR indexing, CLAUDE.md (all 4 menus shown due to config error)
            mock_menu_instance.show.side_effect = [0, 0, 0, 0]
            mock_menu_class.return_value = mock_menu_instance

            show_full_interactive_setup(mock_elixir_repo)

            # Should show all 4 menus due to config read failure
            assert (
                mock_menu_instance.show.call_count == 4
            )  # Editor + tier + PR indexing + CLAUDE.md

    @patch("cicada.interactive_setup.generate_gradient_ascii_art")
    @patch("cicada.interactive_setup.TerminalMenu")
    @patch("cicada.setup.setup")
    @patch("cicada.utils.storage.get_config_path")
    @patch("cicada.utils.storage.get_index_path")
    def test_defaults_to_current_directory(
        self,
        mock_get_index,
        mock_get_config,
        mock_setup,
        mock_menu_class,
        mock_ascii,
        mock_elixir_repo,
    ):
        """Test that None repo_path defaults to current directory"""
        from cicada.interactive_setup import show_full_interactive_setup

        mock_ascii.return_value = "ASCII ART"

        # No existing index
        mock_config_path = MagicMock()
        mock_config_path.exists.return_value = False
        mock_get_config.return_value = mock_config_path

        mock_index_path = MagicMock()
        mock_index_path.exists.return_value = False
        mock_get_index.return_value = mock_index_path

        mock_menu_instance = configure_menu(mock_menu_class, [0, 0, 0, 0])

        with patch("pathlib.Path.cwd", return_value=mock_elixir_repo):
            show_full_interactive_setup(None)

            # Should call setup with the current directory
            mock_setup.assert_called_once()
            call_args = mock_setup.call_args[0]
            assert call_args[1] == mock_elixir_repo
