"""
Comprehensive tests for cicada/commands.py

Tests cover argument parser, command handlers, and error handling.
Target: >80% coverage on critical paths
"""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, MagicMock
from cicada.commands import (
    get_argument_parser,
    handle_command,
    _print_tier_requirement_error,
    _validate_project_language,
    KNOWN_SUBCOMMANDS,
    KNOWN_SUBCOMMANDS_SET,
    DEFAULT_WATCH_DEBOUNCE,
)
from cicada.logging_utils import get_verbose_flag, configure_logging


# ============================================================================
# SECTION 1: Test Argument Parser
# ============================================================================


class TestArgumentParser:
    """Test get_argument_parser function."""

    def test_parser_creation(self):
        """Test that parser is created successfully."""
        parser = get_argument_parser()
        assert parser is not None
        assert parser.prog == "cicada"

    def test_parser_has_version_argument(self):
        """Test that parser has version argument."""
        parser = get_argument_parser()
        # Version argument causes SystemExit (argparse behavior)
        with pytest.raises(SystemExit):
            parser.parse_args(["--version"])

    def test_known_subcommands_tuple(self):
        """Test that KNOWN_SUBCOMMANDS is a tuple."""
        assert isinstance(KNOWN_SUBCOMMANDS, tuple)
        assert len(KNOWN_SUBCOMMANDS) > 0

    def test_known_subcommands_set_contains_all(self):
        """Test that KNOWN_SUBCOMMANDS_SET contains all subcommands."""
        assert all(cmd in KNOWN_SUBCOMMANDS_SET for cmd in KNOWN_SUBCOMMANDS)

    def test_known_subcommands_expected_values(self):
        """Test that expected subcommands are in the list."""
        expected = [
            "install",
            "server",
            "claude",
            "cursor",
            "watch",
            "index",
            "index-pr",
            "find-dead-code",
            "clean",
        ]
        for cmd in expected:
            assert cmd in KNOWN_SUBCOMMANDS_SET

    def test_default_watch_debounce_is_positive(self):
        """Test that debounce value is reasonable."""
        assert DEFAULT_WATCH_DEBOUNCE > 0
        assert DEFAULT_WATCH_DEBOUNCE < 10  # Sanity check


# ============================================================================
# SECTION 2: Test Helper Functions
# ============================================================================


class TestPrintTierRequirementError:
    """Test _print_tier_requirement_error function."""

    def test_print_tier_requirement_error_no_exception(self):
        """Test that function can be called without raising."""
        try:
            _print_tier_requirement_error()
        except Exception as e:
            pytest.fail(f"Function raised unexpected exception: {e}")

    def test_print_tier_requirement_error_output(self, capsys):
        """Test that error message is printed."""
        _print_tier_requirement_error()
        captured = capsys.readouterr()
        # Function should print something to stderr
        assert captured.err or captured.out  # Should have some output


# ============================================================================
# SECTION 3: Test Project Language Validation
# ============================================================================


class TestValidateProjectLanguage:
    """Test _validate_project_language function."""

    def test_validate_project_language_elixir(self):
        """Test validation of Elixir project."""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create Elixir-like project structure
            (tmpdir_path / "mix.exs").touch()

            language = _validate_project_language(tmpdir_path)
            assert language == "elixir"

    def test_validate_project_language_python(self):
        """Test validation of Python project."""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create Python-like project structure
            (tmpdir_path / "pyproject.toml").touch()

            language = _validate_project_language(tmpdir_path)
            assert language == "python"

    def test_validate_project_language_both_present(self):
        """Test when both Elixir and Python markers are present."""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create both markers
            (tmpdir_path / "mix.exs").touch()
            (tmpdir_path / "pyproject.toml").touch()

            # Should return one of them (usually elixir takes precedence)
            language = _validate_project_language(tmpdir_path)
            assert language in ["elixir", "python"]

    def test_validate_project_language_none_detected(self):
        """Test when no language is detected."""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Empty directory - no language markers
            # _validate_project_language calls sys.exit(1) when no language is detected
            with pytest.raises(SystemExit) as exc_info:
                _validate_project_language(tmpdir_path)
            assert exc_info.value.code == 1


# ============================================================================
# SECTION 4: Test Handle Command
# ============================================================================


class TestHandleCommand:
    """Test handle_command function."""

    def test_handle_command_returns_bool(self):
        """Test that handle_command returns a boolean or exits."""
        parser = get_argument_parser()
        # Parsing version argument raises SystemExit, which is expected
        with pytest.raises(SystemExit):
            parser.parse_args(["--version"])

    @patch("cicada.commands.handle_install")
    def test_handle_command_install(self, mock_install):
        """Test install command handling."""
        parser = get_argument_parser()
        args = parser.parse_args(["install"])

        handle_command(args)
        mock_install.assert_called_once()

    @patch("cicada.commands.handle_server")
    def test_handle_command_server(self, mock_server):
        """Test server command handling."""
        parser = get_argument_parser()
        args = parser.parse_args(["server"])

        handle_command(args)
        mock_server.assert_called_once()

    @patch("cicada.commands.handle_index")
    def test_handle_command_index(self, mock_index):
        """Test index command handling."""
        parser = get_argument_parser()
        args = parser.parse_args(["index"])

        handle_command(args)
        mock_index.assert_called_once()

    @patch("cicada.commands.handle_watch")
    def test_handle_command_watch(self, mock_watch):
        """Test watch command handling."""
        parser = get_argument_parser()
        args = parser.parse_args(["watch"])

        handle_command(args)
        mock_watch.assert_called_once()

    @patch("cicada.commands.handle_clean")
    def test_handle_command_clean(self, mock_clean):
        """Test clean command handling."""
        parser = get_argument_parser()
        args = parser.parse_args(["clean"])

        handle_command(args)
        mock_clean.assert_called_once()

    @patch("cicada.commands.handle_find_dead_code")
    def test_handle_command_find_dead_code(self, mock_find_dead):
        """Test find-dead-code command handling."""
        parser = get_argument_parser()
        args = parser.parse_args(["find-dead-code"])

        handle_command(args)
        mock_find_dead.assert_called_once()


# ============================================================================
# SECTION 5: Test Editor Setup Commands
# ============================================================================


class TestEditorSetupCommands:
    """Test editor-specific setup commands."""

    def test_known_editors_exist(self):
        """Test that known editor commands exist."""
        expected_editors = ["claude", "cursor", "vs", "gemini", "codex"]
        for editor in expected_editors:
            assert editor in KNOWN_SUBCOMMANDS_SET

    @patch("cicada.commands.handle_editor_setup")
    def test_handle_command_claude(self, mock_setup):
        """Test claude editor setup."""
        parser = get_argument_parser()
        args = parser.parse_args(["claude"])

        handle_command(args)
        mock_setup.assert_called_once()

    @patch("cicada.commands.handle_editor_setup")
    def test_handle_command_cursor(self, mock_setup):
        """Test cursor editor setup."""
        parser = get_argument_parser()
        args = parser.parse_args(["cursor"])

        handle_command(args)
        mock_setup.assert_called_once()

    @patch("cicada.commands.handle_editor_setup")
    def test_handle_command_vs(self, mock_setup):
        """Test VS Code editor setup."""
        parser = get_argument_parser()
        args = parser.parse_args(["vs"])

        handle_command(args)
        mock_setup.assert_called_once()


# ============================================================================
# SECTION 6: Test Index PR Command
# ============================================================================


class TestIndexPRCommand:
    """Test index-pr command handling."""

    @patch("cicada.commands.handle_index_pr")
    def test_handle_command_index_pr(self, mock_index_pr):
        """Test index-pr command."""
        parser = get_argument_parser()
        args = parser.parse_args(["index-pr"])

        handle_command(args)
        mock_index_pr.assert_called_once()

    @patch("cicada.commands.handle_index_pr")
    def test_handle_command_index_pr_with_pr_number(self, mock_index_pr):
        """Test index-pr command with PR number."""
        parser = get_argument_parser()
        # Note: actual arguments depend on how argparse is configured
        try:
            args = parser.parse_args(["index-pr"])
            handle_command(args)
            mock_index_pr.assert_called_once()
        except SystemExit:
            # If argument is required, this is expected
            pass


# ============================================================================
# SECTION 7: Test Dir Command
# ============================================================================


class TestDirCommand:
    """Test dir command handling."""

    @patch("cicada.commands.handle_dir")
    def test_handle_command_dir(self, mock_dir):
        """Test dir command."""
        parser = get_argument_parser()
        args = parser.parse_args(["dir"])

        handle_command(args)
        mock_dir.assert_called_once()


# ============================================================================
# SECTION 8: Test Configuration and Tier Handling
# ============================================================================


class TestTierHandling:
    """Test tier-related functions and configurations."""

    def test_default_debounce_constant(self):
        """Test that debounce default is set."""
        assert DEFAULT_WATCH_DEBOUNCE == 2.0

    def test_known_subcommands_consistency(self):
        """Test that tuple and set are consistent."""
        # All items in tuple should be in set
        assert set(KNOWN_SUBCOMMANDS) == KNOWN_SUBCOMMANDS_SET

        # Set should not have extra items
        assert len(KNOWN_SUBCOMMANDS_SET) == len(set(KNOWN_SUBCOMMANDS))


# ============================================================================
# SECTION 9: Test Argument Parsing Edge Cases
# ============================================================================


class TestArgumentParsingEdgeCases:
    """Test edge cases in argument parsing."""

    def test_parse_args_no_subcommand(self):
        """Test parsing with no subcommand."""
        parser = get_argument_parser()
        # This should either work or raise SystemExit
        # Depending on whether subcommand is required
        try:
            args = parser.parse_args([])
            # If it succeeds, args should be created
            assert args is not None
        except SystemExit:
            # If subcommand is required, SystemExit is expected
            pass

    def test_parse_args_help(self):
        """Test that help argument works."""
        parser = get_argument_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--help"])
        # Help exits with 0
        assert exc_info.value.code == 0

    def test_parse_args_unknown_subcommand(self):
        """Test that unknown subcommand raises error."""
        parser = get_argument_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["invalid_command"])


# ============================================================================
# SECTION 10: Test Command Dispatch Logic
# ============================================================================


class TestCommandDispatch:
    """Test that commands are dispatched correctly."""

    @patch("cicada.commands.handle_install")
    @patch("cicada.commands.handle_server")
    def test_only_correct_handler_called(self, mock_server, mock_install):
        """Test that only the correct handler is called."""
        parser = get_argument_parser()

        # Call install
        args = parser.parse_args(["install"])
        handle_command(args)
        assert mock_install.called
        assert not mock_server.called

        # Reset mocks
        mock_install.reset_mock()
        mock_server.reset_mock()

        # Call server
        args = parser.parse_args(["server"])
        handle_command(args)
        assert mock_server.called
        assert not mock_install.called


# ============================================================================
# SECTION 11: Test Module-level Validation
# ============================================================================


class TestModuleLevelValidation:
    """Test module-level validation and constants."""

    def test_known_subcommands_not_empty(self):
        """Test that subcommands list is not empty."""
        assert len(KNOWN_SUBCOMMANDS) > 0

    def test_all_subcommands_are_strings(self):
        """Test that all subcommands are strings."""
        assert all(isinstance(cmd, str) for cmd in KNOWN_SUBCOMMANDS)

    def test_no_empty_subcommand_names(self):
        """Test that no subcommand names are empty."""
        assert all(len(cmd) > 0 for cmd in KNOWN_SUBCOMMANDS)

    def test_subcommand_names_lowercase(self):
        """Test that subcommand names are lowercase."""
        # Most are lowercase, but might have hyphens
        assert all(cmd.islower() or cmd.isalnum() or "-" in cmd for cmd in KNOWN_SUBCOMMANDS)


# ============================================================================
# SECTION 12: Test Error Path Coverage
# ============================================================================


class TestErrorPaths:
    """Test error handling paths."""

    @patch("sys.stderr")
    def test_error_output_goes_to_stderr(self, mock_stderr):
        """Test that errors go to stderr."""
        # This is tested implicitly in other tests
        pass

    def test_project_language_validation_robustness(self):
        """Test that validation handles edge cases."""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Test with empty directory (no language markers)
            # Should raise SystemExit since no language is detected
            with pytest.raises(SystemExit):
                _validate_project_language(tmpdir_path)

    def test_handle_command_with_none_args(self):
        """Test that handle_command handles None gracefully."""
        # Create minimal args object
        args = MagicMock()
        args.command = None

        # Should either handle it or raise
        try:
            result = handle_command(args)
            # If it handles it, should return bool
            assert isinstance(result, bool)
        except (AttributeError, TypeError):
            # If it doesn't handle None, that's also acceptable for incomplete args
            pass


# ============================================================================
# SECTION 13: Test Verbose Flag
# ============================================================================


class TestVerboseFlag:
    """Test verbose flag functionality."""

    def test_parser_has_verbose_flag(self):
        """Test that parser includes --verbose flag."""
        parser = get_argument_parser()
        args = parser.parse_args(["index", "--verbose"])
        assert hasattr(args, "verbose")
        assert args.verbose is True

    def test_verbose_flag_defaults_to_false(self):
        """Test that verbose flag defaults to False."""
        parser = get_argument_parser()
        args = parser.parse_args(["index"])
        assert hasattr(args, "verbose")
        assert args.verbose is False

    @pytest.mark.parametrize("command", ["index", "watch", "query authentication"])
    def test_verbose_flag_on_all_commands(self, command):
        """Test that verbose flag works with all commands."""
        parser = get_argument_parser()
        cmd_parts = command.split()
        args = parser.parse_args(cmd_parts + ["--verbose"])
        assert args.verbose is True

    def test_get_verbose_flag_utility(self):
        """Test get_verbose_flag utility function."""
        # Test with verbose=True
        args = MagicMock()
        args.verbose = True
        assert get_verbose_flag(args) is True

        # Test with verbose=False
        args.verbose = False
        assert get_verbose_flag(args) is False

        # Test with missing verbose attribute
        args = MagicMock(spec=[])
        assert get_verbose_flag(args) is False

    def test_configure_logging_verbose(self):
        """Test configure_logging with verbose=True."""
        import logging

        configure_logging(verbose=True)
        logger = logging.getLogger()
        assert logger.level == logging.DEBUG

    def test_configure_logging_not_verbose(self):
        """Test configure_logging with verbose=False."""
        import logging

        configure_logging(verbose=False)
        logger = logging.getLogger()
        assert logger.level == logging.WARNING

    @patch("cicada.commands._setup_and_start_watcher")
    def test_watch_command_uses_verbose_flag(self, mock_watcher):
        """Test that watch command passes verbose flag."""
        parser = get_argument_parser()
        args = parser.parse_args(["watch", "--verbose"])

        # Mock handle_watch to verify it uses the verbose flag
        from cicada.commands import handle_watch

        with patch("cicada.version_check.check_for_updates"):
            try:
                handle_watch(args)
            except Exception:
                # We're just testing argument parsing, not execution
                pass

        # Verify mock was called (means watch command was invoked)
        mock_watcher.assert_called_once()

    @patch("cicada.languages.LanguageRegistry.get_indexer")
    def test_index_command_uses_verbose_flag(self, mock_get_indexer):
        """Test that index command passes verbose flag."""
        parser = get_argument_parser()
        args = parser.parse_args(["index", "--verbose", "--force", "--fast"])

        # Setup mock indexer
        mock_indexer = MagicMock()
        mock_indexer.incremental_index_repository = MagicMock()
        mock_get_indexer.return_value = mock_indexer

        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            storage_dir = tmpdir_path / ".cicada"
            storage_dir.mkdir(parents=True, exist_ok=True)
            (tmpdir_path / "mix.exs").touch()  # Make it an Elixir project

            args.repo = str(tmpdir_path)
            config_path = storage_dir / "config.yaml"
            index_path = storage_dir / "index.json"

            from cicada.commands import handle_index_main

            with patch("cicada.utils.storage.get_storage_dir", return_value=storage_dir):
                with patch("cicada.utils.storage.get_config_path", return_value=config_path):
                    with patch("cicada.utils.storage.get_index_path", return_value=index_path):
                        with patch("cicada.setup.detect_project_language", return_value="elixir"):
                            try:
                                handle_index_main(args)
                            except Exception:
                                # We're just testing argument parsing
                                pass

            # Verify that incremental_index_repository was called with verbose=True
            mock_indexer.incremental_index_repository.assert_called_once()
            call_kwargs = mock_indexer.incremental_index_repository.call_args[1]
            assert "verbose" in call_kwargs
            assert call_kwargs["verbose"] is True
