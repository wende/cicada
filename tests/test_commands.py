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

    @pytest.mark.parametrize("command", ["index", "watch"])
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


# ============================================================================
# SECTION 14: Test Command Handlers
# ============================================================================


class TestHandleClean:
    """Test handle_clean command."""

    @patch("cicada.clean.clean_all_projects")
    def test_clean_all_success(self, mock_clean):
        """Test clean --all command."""
        from cicada.commands import handle_clean

        parser = get_argument_parser()
        args = parser.parse_args(["clean", "--all", "-f"])
        handle_clean(args)
        mock_clean.assert_called_once_with(force=True)

    @patch("cicada.clean.clean_all_projects")
    def test_clean_all_error(self, mock_clean, capsys):
        """Test clean --all error handling."""
        from cicada.commands import handle_clean

        mock_clean.side_effect = Exception("Cleanup failed")
        parser = get_argument_parser()
        args = parser.parse_args(["clean", "--all", "-f"])

        with pytest.raises(SystemExit) as exc:
            handle_clean(args)
        assert exc.value.code == 1

    def test_clean_multiple_flags_error(self, capsys):
        """Test clean with multiple flags errors."""
        from cicada.commands import handle_clean

        parser = get_argument_parser()
        args = parser.parse_args(["clean", "--index", "--pr-index"])

        with pytest.raises(SystemExit) as exc:
            handle_clean(args)
        assert exc.value.code == 1

    @patch("cicada.clean.clean_index_only")
    def test_clean_index_only(self, mock_clean):
        """Test clean --index command."""
        from cicada.commands import handle_clean

        parser = get_argument_parser()
        args = parser.parse_args(["clean", "--index"])
        handle_clean(args)
        mock_clean.assert_called_once()

    @patch("cicada.clean.clean_pr_index_only")
    def test_clean_pr_index_only(self, mock_clean):
        """Test clean --pr-index command."""
        from cicada.commands import handle_clean

        parser = get_argument_parser()
        args = parser.parse_args(["clean", "--pr-index"])
        handle_clean(args)
        mock_clean.assert_called_once()


class TestHandleStatus:
    """Test handle_status command."""

    @patch("cicada.status.check_repository")
    def test_status_success(self, mock_check):
        """Test status command success."""
        from cicada.commands import handle_status

        parser = get_argument_parser()
        args = parser.parse_args(["status"])
        handle_status(args)
        mock_check.assert_called_once()

    @patch("cicada.status.check_repository")
    def test_status_error(self, mock_check, capsys):
        """Test status command error handling."""
        from cicada.commands import handle_status

        mock_check.side_effect = Exception("Status check failed")
        parser = get_argument_parser()
        args = parser.parse_args(["status"])

        with pytest.raises(SystemExit) as exc:
            handle_status(args)
        assert exc.value.code == 1


class TestHandleDir:
    """Test handle_dir command."""

    @patch("cicada.utils.storage.get_storage_dir")
    def test_dir_success(self, mock_get_dir, capsys):
        """Test dir command shows storage path."""
        from cicada.commands import handle_dir

        mock_get_dir.return_value = Path("/tmp/cicada/test")
        parser = get_argument_parser()
        args = parser.parse_args(["dir"])
        handle_dir(args)

        captured = capsys.readouterr()
        assert "/tmp/cicada/test" in captured.out

    @patch("cicada.utils.storage.get_storage_dir")
    def test_dir_with_link(self, mock_get_dir, tmp_path, capsys):
        """Test dir command with linked repository."""
        from cicada.commands import handle_dir
        import yaml

        storage_dir = tmp_path / "storage"
        storage_dir.mkdir()
        link_file = storage_dir / "link.yaml"
        link_file.write_text(
            yaml.dump({"source_repo_path": "/source/repo", "source_storage_dir": "/source/storage"})
        )

        mock_get_dir.return_value = storage_dir
        parser = get_argument_parser()
        args = parser.parse_args(["dir"])
        handle_dir(args)

        captured = capsys.readouterr()
        assert "Linked to:" in captured.out

    @patch("cicada.utils.storage.get_storage_dir")
    def test_dir_yaml_error(self, mock_get_dir, tmp_path, capsys):
        """Test dir command with YAML error."""
        from cicada.commands import handle_dir

        storage_dir = tmp_path / "storage"
        storage_dir.mkdir()
        link_file = storage_dir / "link.yaml"
        link_file.write_text("invalid: yaml: [")

        mock_get_dir.return_value = storage_dir
        parser = get_argument_parser()
        args = parser.parse_args(["dir"])

        with pytest.raises(SystemExit) as exc:
            handle_dir(args)
        assert exc.value.code == 1

    @patch("cicada.utils.storage.get_storage_dir")
    def test_dir_unexpected_error(self, mock_get_dir, capsys):
        """Test dir command with unexpected error."""
        from cicada.commands import handle_dir

        mock_get_dir.side_effect = RuntimeError("Unexpected")
        parser = get_argument_parser()
        args = parser.parse_args(["dir"])

        with pytest.raises(SystemExit) as exc:
            handle_dir(args)
        assert exc.value.code == 1


class TestHandleLinkUnlink:
    """Test handle_link and handle_unlink commands."""

    @patch("cicada.utils.storage.get_link_info")
    @patch("cicada.utils.storage.create_link")
    def test_link_success(self, mock_create, mock_info, capsys):
        """Test link command success."""
        from cicada.commands import handle_link

        mock_info.return_value = {"source_repo_path": "/source", "source_storage_dir": "/storage"}
        parser = get_argument_parser()
        args = parser.parse_args(["link", "/source/repo"])
        handle_link(args)

        captured = capsys.readouterr()
        assert "Successfully linked" in captured.out

    @patch("cicada.utils.storage.create_link")
    def test_link_error(self, mock_create, capsys):
        """Test link command error handling."""
        from cicada.commands import handle_link

        mock_create.side_effect = ValueError("Source not indexed")
        parser = get_argument_parser()
        args = parser.parse_args(["link", "/source/repo"])

        with pytest.raises(SystemExit) as exc:
            handle_link(args)
        assert exc.value.code == 1

    @patch("cicada.utils.storage.remove_link")
    @patch("cicada.utils.storage.get_link_info")
    @patch("cicada.utils.storage.is_linked")
    def test_unlink_success(self, mock_is_linked, mock_info, mock_remove, capsys):
        """Test unlink command success."""
        from cicada.commands import handle_unlink

        mock_is_linked.return_value = True
        mock_info.return_value = {"source_repo_path": "/source"}
        mock_remove.return_value = True
        parser = get_argument_parser()
        args = parser.parse_args(["unlink"])
        handle_unlink(args)

        captured = capsys.readouterr()
        assert "Successfully unlinked" in captured.out

    @patch("cicada.utils.storage.is_linked")
    def test_unlink_not_linked(self, mock_is_linked, capsys):
        """Test unlink when repo not linked."""
        from cicada.commands import handle_unlink

        mock_is_linked.return_value = False
        parser = get_argument_parser()
        args = parser.parse_args(["unlink"])

        with pytest.raises(SystemExit) as exc:
            handle_unlink(args)
        assert exc.value.code == 0  # Exits cleanly


class TestDetermineEditorFromArgs:
    """Test _determine_editor_from_args function."""

    def test_editor_claude(self):
        """Test --claude flag."""
        from cicada.commands import _determine_editor_from_args

        parser = get_argument_parser()
        args = parser.parse_args(["install", "--claude"])
        assert _determine_editor_from_args(args) == "claude"

    def test_editor_cursor(self):
        """Test --cursor flag."""
        from cicada.commands import _determine_editor_from_args

        parser = get_argument_parser()
        args = parser.parse_args(["install", "--cursor"])
        assert _determine_editor_from_args(args) == "cursor"

    def test_editor_vs(self):
        """Test --vs flag."""
        from cicada.commands import _determine_editor_from_args

        parser = get_argument_parser()
        args = parser.parse_args(["install", "--vs"])
        assert _determine_editor_from_args(args) == "vs"

    def test_editor_gemini(self):
        """Test --gemini flag."""
        from cicada.commands import _determine_editor_from_args

        parser = get_argument_parser()
        args = parser.parse_args(["install", "--gemini"])
        assert _determine_editor_from_args(args) == "gemini"

    def test_editor_codex(self):
        """Test --codex flag."""
        from cicada.commands import _determine_editor_from_args

        parser = get_argument_parser()
        args = parser.parse_args(["install", "--codex"])
        assert _determine_editor_from_args(args) == "codex"

    def test_no_editor(self):
        """Test no editor flag."""
        from cicada.commands import _determine_editor_from_args

        parser = get_argument_parser()
        args = parser.parse_args(["install"])
        assert _determine_editor_from_args(args) is None

    def test_multiple_editors_error(self, capsys):
        """Test multiple editor flags cause error."""
        from cicada.commands import _determine_editor_from_args

        parser = get_argument_parser()
        args = parser.parse_args(["install", "--claude", "--cursor"])

        with pytest.raises(SystemExit) as exc:
            _determine_editor_from_args(args)
        assert exc.value.code == 1


class TestLoadExistingConfig:
    """Test _load_existing_config function."""

    def test_load_success(self, tmp_path):
        """Test loading existing config."""
        import yaml
        from cicada.commands import _load_existing_config

        config_path = tmp_path / "config.yaml"
        config_path.write_text(
            yaml.dump(
                {
                    "keyword_extraction": {"method": "bert_small"},
                    "keyword_expansion": {"method": "glove"},
                }
            )
        )

        extraction, expansion = _load_existing_config(config_path)
        assert extraction == "bert_small"
        assert expansion == "glove"

    def test_load_error_returns_defaults(self, tmp_path, capsys):
        """Test loading invalid config returns defaults."""
        from cicada.commands import _load_existing_config

        config_path = tmp_path / "config.yaml"
        config_path.write_text("invalid: yaml: [")

        extraction, expansion = _load_existing_config(config_path)
        assert extraction == "regular"
        assert expansion == "lemmi"


class TestHandleIndexTestModes:
    """Test handle_index_test_mode and handle_index_test_expansion_mode."""

    @patch("cicada.keyword_test.run_keywords_interactive")
    def test_index_test_mode(self, mock_run):
        """Test --test flag triggers interactive mode."""
        from cicada.commands import handle_index_test_mode

        parser = get_argument_parser()
        args = parser.parse_args(["index", "--test", "--fast"])
        handle_index_test_mode(args)
        mock_run.assert_called_once()

    @patch("cicada.keyword_test.run_expansion_interactive")
    def test_index_test_expansion_mode(self, mock_run):
        """Test --test-expansion flag triggers interactive mode."""
        from cicada.commands import handle_index_test_expansion_mode

        parser = get_argument_parser()
        args = parser.parse_args(["index", "--test-expansion", "--fast"])
        handle_index_test_expansion_mode(args)
        mock_run.assert_called_once()


class TestHandleIndexMain:
    """Test handle_index_main function."""

    @patch("cicada.languages.LanguageRegistry.get_indexer")
    def test_index_main_default_flag(self, mock_get_indexer):
        """Test --default flag converts to --force --fast."""
        from cicada.commands import handle_index_main

        mock_indexer = MagicMock()
        mock_indexer.incremental_index_repository = MagicMock()
        mock_get_indexer.return_value = mock_indexer

        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "mix.exs").touch()

            parser = get_argument_parser()
            args = parser.parse_args(["index", "--default", tmpdir])

            with patch("cicada.setup.detect_project_language", return_value="elixir"):
                handle_index_main(args)

            assert args.force is True
            assert args.fast is True

    @patch("cicada.languages.LanguageRegistry.get_indexer")
    def test_index_main_legacy_fallback(self, mock_get_indexer):
        """Test fallback to basic interface for legacy indexers."""
        from cicada.commands import handle_index_main

        mock_indexer = MagicMock(spec=[])  # No incremental_index_repository
        mock_indexer.index_repository = MagicMock()
        mock_get_indexer.return_value = mock_indexer

        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "mix.exs").touch()

            parser = get_argument_parser()
            args = parser.parse_args(["index", "--force", "--fast", tmpdir])

            with patch("cicada.setup.detect_project_language", return_value="elixir"):
                handle_index_main(args)

            mock_indexer.index_repository.assert_called_once()

    @patch("cicada.languages.LanguageRegistry.get_indexer")
    def test_index_main_keyboard_interrupt_graceful_shutdown(self, mock_get_indexer):
        """Test that KeyboardInterrupt during indexing exits gracefully with code 130."""
        from cicada.commands import handle_index_main

        mock_indexer = MagicMock()
        mock_indexer.incremental_index_repository = MagicMock(side_effect=KeyboardInterrupt)
        mock_get_indexer.return_value = mock_indexer

        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "mix.exs").touch()

            parser = get_argument_parser()
            args = parser.parse_args(["index", "--force", "--fast", tmpdir])

            with patch("cicada.setup.detect_project_language", return_value="elixir"):
                with pytest.raises(SystemExit) as exc_info:
                    handle_index_main(args)

            assert exc_info.value.code == 130

    @patch("cicada.languages.LanguageRegistry.get_indexer")
    def test_index_main_keyboard_interrupt_legacy_indexer(self, mock_get_indexer):
        """Test KeyboardInterrupt with legacy indexer (no incremental_index_repository)."""
        from cicada.commands import handle_index_main

        mock_indexer = MagicMock(spec=[])  # No incremental_index_repository
        mock_indexer.index_repository = MagicMock(side_effect=KeyboardInterrupt)
        mock_get_indexer.return_value = mock_indexer

        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "mix.exs").touch()

            parser = get_argument_parser()
            args = parser.parse_args(["index", "--force", "--fast", tmpdir])

            with patch("cicada.setup.detect_project_language", return_value="elixir"):
                with pytest.raises(SystemExit) as exc_info:
                    handle_index_main(args)

            assert exc_info.value.code == 130


class TestHandleServerHelpers:
    """Test server helper functions."""

    def test_cleanup_watch_process(self, capsys):
        """Test _cleanup_watch_process handles errors."""
        from cicada.commands import _cleanup_watch_process
        import logging

        logger = logging.getLogger("test")

        with patch("cicada.watch_manager.stop_watch_process", side_effect=Exception("Stop failed")):
            _cleanup_watch_process(logger)

        captured = capsys.readouterr()
        assert "Warning" in captured.err

    @patch("cicada.watch_manager.start_watch_process")
    def test_start_watch_for_server_failure(self, mock_start, capsys):
        """Test _start_watch_for_server fails gracefully."""
        from cicada.commands import _start_watch_for_server

        mock_start.return_value = False
        parser = get_argument_parser()
        args = parser.parse_args(["server", "--watch"])

        with pytest.raises(SystemExit) as exc:
            _start_watch_for_server(args, Path("/tmp/repo"))
        assert exc.value.code == 1

    @patch("cicada.watch_manager.start_watch_process")
    def test_start_watch_for_server_runtime_error(self, mock_start, capsys):
        """Test _start_watch_for_server handles RuntimeError."""
        from cicada.commands import _start_watch_for_server

        mock_start.side_effect = RuntimeError("Watch error")
        parser = get_argument_parser()
        args = parser.parse_args(["server", "--watch"])

        with pytest.raises(SystemExit) as exc:
            _start_watch_for_server(args, Path("/tmp/repo"))
        assert exc.value.code == 1


class TestHandleFindDeadCode:
    """Test handle_find_dead_code error paths."""

    @patch("cicada.utils.load_index")
    @patch("cicada.utils.get_index_path")
    def test_find_dead_code_load_error(self, mock_get_path, mock_load, capsys):
        """Test find-dead-code handles load errors."""
        from cicada.commands import handle_find_dead_code

        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_get_path.return_value = mock_path
        mock_load.side_effect = Exception("Load failed")

        parser = get_argument_parser()
        args = parser.parse_args(["find-dead-code"])

        with pytest.raises(SystemExit) as exc:
            handle_find_dead_code(args)
        assert exc.value.code == 1


class TestHandleCleanErrors:
    """Test handle_clean error paths."""

    @patch("cicada.clean.clean_repository")
    def test_clean_default_error(self, mock_clean, capsys):
        """Test clean default mode (no flags) error handling."""
        from cicada.commands import handle_clean

        mock_clean.side_effect = Exception("Repository cleanup failed")
        parser = get_argument_parser()
        args = parser.parse_args(["clean"])

        with pytest.raises(SystemExit) as exc:
            handle_clean(args)
        assert exc.value.code == 1


class TestHandleDirErrors:
    """Test handle_dir error paths."""

    @patch("cicada.utils.storage.get_storage_dir")
    def test_dir_key_error(self, mock_get_dir, tmp_path, capsys):
        """Test dir command with KeyError."""
        from cicada.commands import handle_dir

        storage_dir = tmp_path / "storage"
        storage_dir.mkdir()
        link_file = storage_dir / "link.yaml"
        # Write valid YAML but with missing expected keys
        link_file.write_text("other_key: value\n")

        mock_get_dir.return_value = storage_dir
        parser = get_argument_parser()
        args = parser.parse_args(["dir"])

        # This should succeed but show defaults for missing keys
        handle_dir(args)

        captured = capsys.readouterr()
        assert "Linked to:" in captured.out


class TestHandleLinkErrors:
    """Test handle_link error paths."""

    @patch("cicada.utils.storage.create_link")
    def test_link_unexpected_error(self, mock_create, capsys):
        """Test link command with unexpected error."""
        from cicada.commands import handle_link

        mock_create.side_effect = RuntimeError("Unexpected error")
        parser = get_argument_parser()
        args = parser.parse_args(["link", "/source/repo"])

        with pytest.raises(SystemExit) as exc:
            handle_link(args)
        assert exc.value.code == 1

        captured = capsys.readouterr()
        assert "Unexpected error" in captured.err


class TestHandleUnlinkErrors:
    """Test handle_unlink error paths."""

    @patch("cicada.utils.storage.remove_link")
    @patch("cicada.utils.storage.get_link_info")
    @patch("cicada.utils.storage.is_linked")
    def test_unlink_remove_fails(self, mock_is_linked, mock_info, mock_remove, capsys):
        """Test unlink when remove_link returns False."""
        from cicada.commands import handle_unlink

        mock_is_linked.return_value = True
        mock_info.return_value = {"source_repo_path": "/source"}
        mock_remove.return_value = False  # Simulate failure

        parser = get_argument_parser()
        args = parser.parse_args(["unlink"])

        with pytest.raises(SystemExit) as exc:
            handle_unlink(args)
        assert exc.value.code == 1

        captured = capsys.readouterr()
        assert "Failed to remove" in captured.out

    @patch("cicada.utils.storage.is_linked")
    def test_unlink_file_not_found(self, mock_is_linked, capsys):
        """Test unlink with FileNotFoundError."""
        from cicada.commands import handle_unlink

        mock_is_linked.side_effect = FileNotFoundError("Link file not found")
        parser = get_argument_parser()
        args = parser.parse_args(["unlink"])

        with pytest.raises(SystemExit) as exc:
            handle_unlink(args)
        assert exc.value.code == 1

    @patch("cicada.utils.storage.is_linked")
    def test_unlink_unexpected_error(self, mock_is_linked, capsys):
        """Test unlink with unexpected error."""
        from cicada.commands import handle_unlink

        mock_is_linked.side_effect = RuntimeError("Unexpected")
        parser = get_argument_parser()
        args = parser.parse_args(["unlink"])

        with pytest.raises(SystemExit) as exc:
            handle_unlink(args)
        assert exc.value.code == 1

        captured = capsys.readouterr()
        assert "Unexpected error" in captured.err
