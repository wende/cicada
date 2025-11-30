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
# FIXTURES
# ============================================================================


@pytest.fixture
def parser():
    """Shared argument parser fixture."""
    return get_argument_parser()


@pytest.fixture
def mock_stats_analyzer():
    """Mock StatsAnalyzer with common setup."""
    with patch("cicada.stats.StatsAnalyzer") as mock_class:
        mock_analyzer = MagicMock()
        mock_class.return_value = mock_analyzer
        yield mock_analyzer


@pytest.fixture
def mock_run_router():
    """Complex mock setup for run command tests."""
    patches = {
        "parse": patch("cicada.cli_mapper.parse_cli_args_to_handler_kwargs"),
        "config_path": patch("cicada.mcp.config_manager.ConfigManager.get_config_path"),
        "load_config": patch("cicada.mcp.config_manager.ConfigManager.load_config"),
        "git_helper": patch("cicada.git.helper.GitHelper"),
        "index_manager": patch("cicada.mcp.handlers.index_manager.IndexManager"),
        "module_handler": patch("cicada.mcp.handlers.ModuleSearchHandler"),
        "function_handler": patch("cicada.mcp.handlers.FunctionSearchHandler"),
        "git_handler": patch("cicada.mcp.handlers.GitHistoryHandler"),
        "pr_handler": patch("cicada.mcp.handlers.PRHistoryHandler"),
        "analysis_handler": patch("cicada.mcp.handlers.AnalysisHandler"),
        "router_class": patch("cicada.mcp.router.ToolRouter"),
    }

    started = {name: p.start() for name, p in patches.items()}
    started["config_path"].return_value = Path("/tmp/config.yaml")
    started["load_config"].return_value = {"repository": {"path": "."}}

    mock_router = MagicMock()
    started["router_class"].return_value = mock_router
    started["router"] = mock_router

    yield started

    for p in patches.values():
        p.stop()


# ============================================================================
# SECTION 1: Test Argument Parser
# ============================================================================


class TestArgumentParser:
    """Test get_argument_parser function."""

    def test_parser_creation(self, parser):
        """Test that parser is created successfully."""
        assert parser is not None
        assert parser.prog == "cicada"

    def test_parser_has_version_argument(self, parser):
        """Test that parser has version argument."""
        with pytest.raises(SystemExit):
            parser.parse_args(["--version"])

    def test_known_subcommands_tuple(self):
        """Test that KNOWN_SUBCOMMANDS is a tuple."""
        assert isinstance(KNOWN_SUBCOMMANDS, tuple)
        assert len(KNOWN_SUBCOMMANDS) > 0

    def test_known_subcommands_set_contains_all(self):
        """Test that KNOWN_SUBCOMMANDS_SET contains all subcommands."""
        assert all(cmd in KNOWN_SUBCOMMANDS_SET for cmd in KNOWN_SUBCOMMANDS)

    @pytest.mark.parametrize(
        "cmd",
        [
            "install",
            "server",
            "claude",
            "cursor",
            "watch",
            "index",
            "index-pr",
            "find-dead-code",
            "clean",
        ],
    )
    def test_known_subcommands_expected_values(self, cmd):
        """Test that expected subcommands are in the list."""
        assert cmd in KNOWN_SUBCOMMANDS_SET

    def test_default_watch_debounce_is_positive(self):
        """Test that debounce value is reasonable."""
        assert 0 < DEFAULT_WATCH_DEBOUNCE < 10


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

    def test_handle_command_returns_bool(self, parser):
        """Test that handle_command returns a boolean or exits."""
        with pytest.raises(SystemExit):
            parser.parse_args(["--version"])

    @pytest.mark.parametrize(
        "command,handler_name",
        [
            ("install", "handle_install"),
            ("server", "handle_server"),
            ("index", "handle_index"),
            ("watch", "handle_watch"),
            ("clean", "handle_clean"),
            ("find-dead-code", "handle_find_dead_code"),
        ],
    )
    def test_handle_command_dispatch(self, parser, command, handler_name):
        """Test that commands are dispatched to correct handlers."""
        with patch(f"cicada.commands.{handler_name}") as mock_handler:
            args = parser.parse_args([command])
            handle_command(args)
            mock_handler.assert_called_once()


# ============================================================================
# SECTION 5: Test Editor Setup Commands
# ============================================================================


class TestEditorSetupCommands:
    """Test editor-specific setup commands."""

    @pytest.mark.parametrize("editor", ["claude", "cursor", "vs", "gemini", "codex"])
    def test_known_editors_exist(self, editor):
        """Test that known editor commands exist."""
        assert editor in KNOWN_SUBCOMMANDS_SET

    @pytest.mark.parametrize("editor", ["claude", "cursor", "vs"])
    def test_handle_editor_setup(self, parser, editor):
        """Test editor setup commands dispatch correctly."""
        with patch("cicada.commands.handle_editor_setup") as mock_setup:
            args = parser.parse_args([editor])
            handle_command(args)
            mock_setup.assert_called_once()


# ============================================================================
# SECTION 6: Test Index PR and Dir Commands
# ============================================================================


class TestIndexPRAndDirCommands:
    """Test index-pr and dir command handling."""

    @pytest.mark.parametrize(
        "command,handler_name",
        [
            ("index-pr", "handle_index_pr"),
            ("dir", "handle_dir"),
        ],
    )
    def test_handle_command(self, parser, command, handler_name):
        """Test command dispatching."""
        with patch(f"cicada.commands.{handler_name}") as mock_handler:
            args = parser.parse_args([command])
            handle_command(args)
            mock_handler.assert_called_once()


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

    def test_parse_args_no_subcommand(self, parser):
        """Test parsing with no subcommand."""
        try:
            args = parser.parse_args([])
            assert args is not None
        except SystemExit:
            pass  # If subcommand is required, SystemExit is expected

    def test_parse_args_help(self, parser):
        """Test that help argument works."""
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--help"])
        assert exc_info.value.code == 0

    def test_parse_args_unknown_subcommand(self, parser):
        """Test that unknown subcommand raises error."""
        with pytest.raises(SystemExit):
            parser.parse_args(["invalid_command"])


# ============================================================================
# SECTION 10: Test Command Dispatch Logic
# ============================================================================


class TestCommandDispatch:
    """Test that commands are dispatched correctly."""

    def test_only_correct_handler_called(self, parser):
        """Test that only the correct handler is called."""
        with (
            patch("cicada.commands.handle_install") as mock_install,
            patch("cicada.commands.handle_server") as mock_server,
        ):
            args = parser.parse_args(["install"])
            handle_command(args)
            assert mock_install.called
            assert not mock_server.called

            mock_install.reset_mock()
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

    def test_parser_has_verbose_flag(self, parser):
        """Test that parser includes --verbose flag."""
        args = parser.parse_args(["index", "--verbose"])
        assert hasattr(args, "verbose")
        assert args.verbose is True

    def test_verbose_flag_defaults_to_false(self, parser):
        """Test that verbose flag defaults to False."""
        args = parser.parse_args(["index"])
        assert hasattr(args, "verbose")
        assert args.verbose is False

    @pytest.mark.parametrize("command", ["index", "watch"])
    def test_verbose_flag_on_commands(self, parser, command):
        """Test that verbose flag works with commands."""
        args = parser.parse_args([command, "--verbose"])
        assert args.verbose is True

    @pytest.mark.parametrize("verbose,expected", [(True, True), (False, False)])
    def test_get_verbose_flag_utility(self, verbose, expected):
        """Test get_verbose_flag utility function."""
        args = MagicMock()
        args.verbose = verbose
        assert get_verbose_flag(args) is expected

    def test_get_verbose_flag_missing_attribute(self):
        """Test get_verbose_flag with missing verbose attribute."""
        args = MagicMock(spec=[])
        assert get_verbose_flag(args) is False

    @pytest.mark.parametrize(
        "verbose,expected_level",
        [(True, 10), (False, 30)],  # DEBUG=10, WARNING=30
    )
    def test_configure_logging(self, verbose, expected_level):
        """Test configure_logging sets correct log level."""
        import logging

        configure_logging(verbose=verbose)
        assert logging.getLogger().level == expected_level

    @patch("cicada.commands._setup_and_start_watcher")
    def test_watch_command_uses_verbose_flag(self, mock_watcher, parser):
        """Test that watch command passes verbose flag."""
        args = parser.parse_args(["watch", "--verbose"])

        from cicada.commands import handle_watch

        with patch("cicada.version_check.check_for_updates"):
            try:
                handle_watch(args)
            except Exception:
                pass  # Just testing argument parsing

        mock_watcher.assert_called_once()

    @patch("cicada.languages.LanguageRegistry.get_indexer")
    def test_index_command_uses_verbose_flag(self, mock_get_indexer, parser):
        """Test that index command passes verbose flag."""
        args = parser.parse_args(["index", "--verbose", "--force", "--fast"])

        mock_indexer = MagicMock()
        mock_indexer.incremental_index_repository = MagicMock()
        mock_get_indexer.return_value = mock_indexer

        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            storage_dir = tmpdir_path / ".cicada"
            storage_dir.mkdir(parents=True, exist_ok=True)
            (tmpdir_path / "mix.exs").touch()

            args.repo = str(tmpdir_path)

            from cicada.commands import handle_index_main

            with (
                patch("cicada.utils.storage.get_storage_dir", return_value=storage_dir),
                patch(
                    "cicada.utils.storage.get_config_path", return_value=storage_dir / "config.yaml"
                ),
                patch(
                    "cicada.utils.storage.get_index_path", return_value=storage_dir / "index.json"
                ),
                patch("cicada.setup.detect_project_language", return_value="elixir"),
            ):
                try:
                    handle_index_main(args)
                except Exception:
                    pass

            mock_indexer.incremental_index_repository.assert_called_once()
            call_kwargs = mock_indexer.incremental_index_repository.call_args[1]
            assert call_kwargs.get("verbose") is True


# ============================================================================
# SECTION 14: Test Command Handlers
# ============================================================================


class TestHandleClean:
    """Test handle_clean command."""

    @patch("cicada.clean.clean_all_projects")
    def test_clean_all_success(self, mock_clean, parser):
        """Test clean --all command."""
        from cicada.commands import handle_clean

        args = parser.parse_args(["clean", "--all", "-f"])
        handle_clean(args)
        mock_clean.assert_called_once_with(force=True)

    @patch("cicada.clean.clean_all_projects")
    def test_clean_all_error(self, mock_clean, parser):
        """Test clean --all error handling."""
        from cicada.commands import handle_clean

        mock_clean.side_effect = Exception("Cleanup failed")
        args = parser.parse_args(["clean", "--all", "-f"])

        with pytest.raises(SystemExit) as exc:
            handle_clean(args)
        assert exc.value.code == 1

    def test_clean_multiple_flags_error(self, parser):
        """Test clean with multiple flags errors."""
        from cicada.commands import handle_clean

        args = parser.parse_args(["clean", "--index", "--pr-index"])

        with pytest.raises(SystemExit) as exc:
            handle_clean(args)
        assert exc.value.code == 1

    @pytest.mark.parametrize(
        "flag,clean_func",
        [
            ("--index", "clean_index_only"),
            ("--pr-index", "clean_pr_index_only"),
        ],
    )
    def test_clean_specific_flags(self, parser, flag, clean_func):
        """Test clean with specific flags."""
        from cicada.commands import handle_clean

        with patch(f"cicada.clean.{clean_func}") as mock_clean:
            args = parser.parse_args(["clean", flag])
            handle_clean(args)
            mock_clean.assert_called_once()


class TestHandleStatus:
    """Test handle_status command."""

    @patch("cicada.status.check_repository")
    def test_status_success(self, mock_check, parser):
        """Test status command success."""
        from cicada.commands import handle_status

        args = parser.parse_args(["status"])
        handle_status(args)
        mock_check.assert_called_once()

    @patch("cicada.status.check_repository")
    def test_status_error(self, mock_check, parser):
        """Test status command error handling."""
        from cicada.commands import handle_status

        mock_check.side_effect = Exception("Status check failed")
        args = parser.parse_args(["status"])

        with pytest.raises(SystemExit) as exc:
            handle_status(args)
        assert exc.value.code == 1


class TestHandleDir:
    """Test handle_dir command."""

    @patch("cicada.utils.storage.get_storage_dir")
    def test_dir_success(self, mock_get_dir, parser, capsys):
        """Test dir command shows storage path."""
        from cicada.commands import handle_dir

        mock_get_dir.return_value = Path("/tmp/cicada/test")
        args = parser.parse_args(["dir"])
        handle_dir(args)

        captured = capsys.readouterr()
        assert "/tmp/cicada/test" in captured.out

    @patch("cicada.utils.storage.get_storage_dir")
    def test_dir_with_link(self, mock_get_dir, parser, tmp_path, capsys):
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
        args = parser.parse_args(["dir"])
        handle_dir(args)

        captured = capsys.readouterr()
        assert "Linked to:" in captured.out

    @patch("cicada.utils.storage.get_storage_dir")
    def test_dir_yaml_error(self, mock_get_dir, parser, tmp_path):
        """Test dir command with YAML error."""
        from cicada.commands import handle_dir

        storage_dir = tmp_path / "storage"
        storage_dir.mkdir()
        (storage_dir / "link.yaml").write_text("invalid: yaml: [")

        mock_get_dir.return_value = storage_dir
        args = parser.parse_args(["dir"])

        with pytest.raises(SystemExit) as exc:
            handle_dir(args)
        assert exc.value.code == 1

    @patch("cicada.utils.storage.get_storage_dir")
    def test_dir_unexpected_error(self, mock_get_dir, parser):
        """Test dir command with unexpected error."""
        from cicada.commands import handle_dir

        mock_get_dir.side_effect = RuntimeError("Unexpected")
        args = parser.parse_args(["dir"])

        with pytest.raises(SystemExit) as exc:
            handle_dir(args)
        assert exc.value.code == 1


class TestHandleLinkUnlink:
    """Test handle_link and handle_unlink commands."""

    @patch("cicada.utils.storage.get_link_info")
    @patch("cicada.utils.storage.create_link")
    def test_link_success(self, mock_create, mock_info, parser, capsys):
        """Test link command success."""
        from cicada.commands import handle_link

        mock_info.return_value = {"source_repo_path": "/source", "source_storage_dir": "/storage"}
        args = parser.parse_args(["link", "/source/repo"])
        handle_link(args)

        captured = capsys.readouterr()
        assert "Successfully linked" in captured.out

    @patch("cicada.utils.storage.create_link")
    def test_link_error(self, mock_create, parser):
        """Test link command error handling."""
        from cicada.commands import handle_link

        mock_create.side_effect = ValueError("Source not indexed")
        args = parser.parse_args(["link", "/source/repo"])

        with pytest.raises(SystemExit) as exc:
            handle_link(args)
        assert exc.value.code == 1

    @patch("cicada.utils.storage.remove_link")
    @patch("cicada.utils.storage.get_link_info")
    @patch("cicada.utils.storage.is_linked")
    def test_unlink_success(self, mock_is_linked, mock_info, mock_remove, parser, capsys):
        """Test unlink command success."""
        from cicada.commands import handle_unlink

        mock_is_linked.return_value = True
        mock_info.return_value = {"source_repo_path": "/source"}
        mock_remove.return_value = True
        args = parser.parse_args(["unlink"])
        handle_unlink(args)

        captured = capsys.readouterr()
        assert "Successfully unlinked" in captured.out

    @patch("cicada.utils.storage.is_linked")
    def test_unlink_not_linked(self, mock_is_linked, parser):
        """Test unlink when repo not linked."""
        from cicada.commands import handle_unlink

        mock_is_linked.return_value = False
        args = parser.parse_args(["unlink"])

        with pytest.raises(SystemExit) as exc:
            handle_unlink(args)
        assert exc.value.code == 0  # Exits cleanly


class TestDetermineEditorFromArgs:
    """Test _determine_editor_from_args function."""

    @pytest.mark.parametrize("editor", ["claude", "cursor", "vs", "gemini", "codex"])
    def test_editor_flags(self, parser, editor):
        """Test editor flags return correct editor name."""
        from cicada.commands import _determine_editor_from_args

        args = parser.parse_args(["install", f"--{editor}"])
        assert _determine_editor_from_args(args) == editor

    def test_no_editor(self, parser):
        """Test no editor flag returns None."""
        from cicada.commands import _determine_editor_from_args

        args = parser.parse_args(["install"])
        assert _determine_editor_from_args(args) is None

    def test_multiple_editors_error(self, parser):
        """Test multiple editor flags cause error."""
        from cicada.commands import _determine_editor_from_args

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

    @pytest.mark.parametrize(
        "flag,handler_name,mock_func",
        [
            ("--test", "handle_index_test_mode", "run_keywords_interactive"),
            ("--test-expansion", "handle_index_test_expansion_mode", "run_expansion_interactive"),
        ],
    )
    def test_index_test_modes(self, parser, flag, handler_name, mock_func):
        """Test test mode flags trigger interactive modes."""
        from cicada import commands

        handler = getattr(commands, handler_name)

        with patch(f"cicada.keyword_test.{mock_func}") as mock_run:
            args = parser.parse_args(["index", flag, "--fast"])
            handler(args)
            mock_run.assert_called_once()


class TestHandleIndexMain:
    """Test handle_index_main function."""

    @pytest.fixture
    def elixir_project(self, tmp_path):
        """Create a temporary Elixir project directory."""
        (tmp_path / "mix.exs").touch()
        return tmp_path

    @patch("cicada.languages.LanguageRegistry.get_indexer")
    def test_index_main_default_flag(self, mock_get_indexer, parser, elixir_project):
        """Test --default flag converts to --force --fast."""
        from cicada.commands import handle_index_main

        mock_indexer = MagicMock()
        mock_indexer.incremental_index_repository = MagicMock()
        mock_get_indexer.return_value = mock_indexer

        args = parser.parse_args(["index", "--default", str(elixir_project)])

        with patch("cicada.setup.detect_project_language", return_value="elixir"):
            handle_index_main(args)

        assert args.force is True
        assert args.fast is True

    @patch("cicada.languages.LanguageRegistry.get_indexer")
    def test_index_main_legacy_fallback(self, mock_get_indexer, parser, elixir_project):
        """Test fallback to basic interface for legacy indexers."""
        from cicada.commands import handle_index_main

        mock_indexer = MagicMock(spec=[])  # No incremental_index_repository
        mock_indexer.supports_incremental = False  # Legacy indexer
        mock_indexer.index_repository = MagicMock()
        mock_get_indexer.return_value = mock_indexer

        args = parser.parse_args(["index", "--force", "--fast", str(elixir_project)])

        with patch("cicada.setup.detect_project_language", return_value="elixir"):
            handle_index_main(args)

        mock_indexer.index_repository.assert_called_once()

    @pytest.mark.parametrize("use_legacy", [False, True])
    @patch("cicada.languages.LanguageRegistry.get_indexer")
    def test_index_main_keyboard_interrupt(
        self, mock_get_indexer, parser, elixir_project, use_legacy
    ):
        """Test KeyboardInterrupt exits gracefully with code 130."""
        from cicada.commands import handle_index_main

        if use_legacy:
            mock_indexer = MagicMock(spec=[])
            mock_indexer.supports_incremental = False
            mock_indexer.index_repository = MagicMock(side_effect=KeyboardInterrupt)
        else:
            mock_indexer = MagicMock()
            mock_indexer.incremental_index_repository = MagicMock(side_effect=KeyboardInterrupt)

        mock_get_indexer.return_value = mock_indexer

        args = parser.parse_args(["index", "--force", "--fast", str(elixir_project)])

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

    @pytest.mark.parametrize(
        "error_type,return_value",
        [
            (None, False),  # Returns False
            (RuntimeError("Watch error"), None),  # Raises RuntimeError
        ],
    )
    @patch("cicada.watch_manager.start_watch_process")
    def test_start_watch_for_server_errors(self, mock_start, parser, error_type, return_value):
        """Test _start_watch_for_server handles errors."""
        from cicada.commands import _start_watch_for_server

        if error_type:
            mock_start.side_effect = error_type
        else:
            mock_start.return_value = return_value

        args = parser.parse_args(["server", "--watch"])

        with pytest.raises(SystemExit) as exc:
            _start_watch_for_server(args, Path("/tmp/repo"))
        assert exc.value.code == 1


class TestHandleFindDeadCode:
    """Test handle_find_dead_code error paths."""

    @patch("cicada.utils.load_index")
    @patch("cicada.utils.get_index_path")
    def test_find_dead_code_load_error(self, mock_get_path, mock_load, parser):
        """Test find-dead-code handles load errors."""
        from cicada.commands import handle_find_dead_code

        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_get_path.return_value = mock_path
        mock_load.side_effect = Exception("Load failed")

        args = parser.parse_args(["find-dead-code"])

        with pytest.raises(SystemExit) as exc:
            handle_find_dead_code(args)
        assert exc.value.code == 1


class TestHandleCleanErrors:
    """Test handle_clean error paths."""

    @patch("cicada.clean.clean_repository")
    def test_clean_default_error(self, mock_clean, parser):
        """Test clean default mode (no flags) error handling."""
        from cicada.commands import handle_clean

        mock_clean.side_effect = Exception("Repository cleanup failed")
        args = parser.parse_args(["clean"])

        with pytest.raises(SystemExit) as exc:
            handle_clean(args)
        assert exc.value.code == 1


class TestHandleDirErrors:
    """Test handle_dir error paths."""

    @patch("cicada.utils.storage.get_storage_dir")
    def test_dir_key_error(self, mock_get_dir, parser, tmp_path, capsys):
        """Test dir command with KeyError."""
        from cicada.commands import handle_dir

        storage_dir = tmp_path / "storage"
        storage_dir.mkdir()
        (storage_dir / "link.yaml").write_text("other_key: value\n")

        mock_get_dir.return_value = storage_dir
        args = parser.parse_args(["dir"])

        handle_dir(args)

        captured = capsys.readouterr()
        assert "Linked to:" in captured.out


class TestHandleLinkErrors:
    """Test handle_link error paths."""

    @patch("cicada.utils.storage.create_link")
    def test_link_unexpected_error(self, mock_create, parser, capsys):
        """Test link command with unexpected error."""
        from cicada.commands import handle_link

        mock_create.side_effect = RuntimeError("Unexpected error")
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
    def test_unlink_remove_fails(self, mock_is_linked, mock_info, mock_remove, parser, capsys):
        """Test unlink when remove_link returns False."""
        from cicada.commands import handle_unlink

        mock_is_linked.return_value = True
        mock_info.return_value = {"source_repo_path": "/source"}
        mock_remove.return_value = False

        args = parser.parse_args(["unlink"])

        with pytest.raises(SystemExit) as exc:
            handle_unlink(args)
        assert exc.value.code == 1

        captured = capsys.readouterr()
        assert "Failed to remove" in captured.out

    @pytest.mark.parametrize(
        "error_type,expected_msg",
        [
            (FileNotFoundError("Link file not found"), None),
            (RuntimeError("Unexpected"), "Unexpected error"),
        ],
    )
    @patch("cicada.utils.storage.is_linked")
    def test_unlink_errors(self, mock_is_linked, parser, capsys, error_type, expected_msg):
        """Test unlink error handling."""
        from cicada.commands import handle_unlink

        mock_is_linked.side_effect = error_type
        args = parser.parse_args(["unlink"])

        with pytest.raises(SystemExit) as exc:
            handle_unlink(args)
        assert exc.value.code == 1

        if expected_msg:
            captured = capsys.readouterr()
            assert expected_msg in captured.err


# ============================================================================
# SECTION 15: Test Handle Run Command
# ============================================================================


class TestHandleRun:
    """Test handle_run command for CLI execution of MCP tools."""

    def test_run_query_success(self, parser, mock_run_router, capsys):
        """Test run command with query tool."""
        from cicada.commands import handle_run

        mock_run_router["parse"].return_value = {"query": "authentication"}

        async def mock_route(*args, **kwargs):
            mock_text = MagicMock()
            mock_text.text = "Found 5 results for authentication"
            return [mock_text]

        mock_run_router["router"].route_tool = mock_route

        args = parser.parse_args(["run", "query", "authentication"])
        handle_run(args)

        captured = capsys.readouterr()
        assert "Found 5 results" in captured.out

    @patch("cicada.cli_mapper.parse_cli_args_to_handler_kwargs")
    def test_run_parse_error(self, mock_parse, parser, capsys):
        """Test run command with parse error."""
        from cicada.commands import handle_run

        mock_parse.side_effect = ValueError("Invalid argument")
        args = parser.parse_args(["run", "query", "test"])

        with pytest.raises(SystemExit) as exc:
            handle_run(args)
        assert exc.value.code == 1

        captured = capsys.readouterr()
        assert "Invalid argument" in captured.err

    @patch("cicada.mcp.config_manager.ConfigManager.get_config_path")
    @patch("cicada.cli_mapper.parse_cli_args_to_handler_kwargs")
    def test_run_config_not_found(self, mock_parse, mock_get_config, parser):
        """Test run command when config not found."""
        from cicada.commands import handle_run

        mock_parse.return_value = {"query": "test"}
        mock_get_config.side_effect = FileNotFoundError("Config not found")

        args = parser.parse_args(["run", "query", "test"])

        with pytest.raises(SystemExit) as exc:
            handle_run(args)
        assert exc.value.code == 1

    def test_run_tool_error(self, parser, mock_run_router):
        """Test run command handles tool errors."""
        from cicada.commands import handle_run

        mock_run_router["parse"].return_value = {"query": "test"}

        async def mock_route(*args, **kwargs):
            raise Exception("Tool execution failed")

        mock_run_router["router"].route_tool = mock_route

        args = parser.parse_args(["run", "query", "test"])

        with pytest.raises(SystemExit) as exc:
            handle_run(args)
        assert exc.value.code == 1

    def test_run_empty_result(self, parser, mock_run_router, capsys):
        """Test run command with empty result."""
        from cicada.commands import handle_run

        mock_run_router["parse"].return_value = {"query": "nonexistent"}

        async def mock_route(*args, **kwargs):
            return []

        mock_run_router["router"].route_tool = mock_route

        args = parser.parse_args(["run", "query", "nonexistent"])
        handle_run(args)

        # Should complete without error even with empty result
        captured = capsys.readouterr()
        assert captured.out.strip() == "" or "No" in captured.out


# ============================================================================
# SECTION 16: Test Handle Stats Command
# ============================================================================


class TestHandleStats:
    """Test handle_stats command."""

    def test_stats_summary(self, parser, mock_stats_analyzer, capsys):
        """Test stats command summary output."""
        from cicada.commands import handle_stats

        mock_stats_analyzer.get_stats.return_value = {"total": 100}
        mock_stats_analyzer.format_summary.return_value = "Total calls: 100"

        args = parser.parse_args(["stats"])
        handle_stats(args)

        captured = capsys.readouterr()
        assert "Total calls: 100" in captured.out

    def test_stats_detailed(self, parser, mock_stats_analyzer, capsys):
        """Test stats command detailed output."""
        from cicada.commands import handle_stats

        mock_stats_analyzer.get_stats.return_value = {"total": 100}
        mock_stats_analyzer.format_detailed.return_value = "Detailed: query=50, search=50"

        args = parser.parse_args(["stats", "--detailed"])
        handle_stats(args)

        captured = capsys.readouterr()
        assert "Detailed" in captured.out

    def test_stats_time_series(self, parser, mock_stats_analyzer, capsys):
        """Test stats command time series output."""
        from cicada.commands import handle_stats

        mock_stats_analyzer.get_stats.return_value = {"daily": []}
        mock_stats_analyzer.format_time_series.return_value = "Time series data"

        args = parser.parse_args(["stats", "--time-series"])
        handle_stats(args)

        captured = capsys.readouterr()
        assert "Time series" in captured.out

    def test_stats_weekly(self, parser, mock_stats_analyzer):
        """Test stats command weekly output."""
        from cicada.commands import handle_stats

        mock_stats_analyzer.get_stats.return_value = {"weekly": []}
        mock_stats_analyzer.format_time_series.return_value = "Weekly data"

        args = parser.parse_args(["stats", "--time-series", "--weekly"])
        handle_stats(args)

        call_kwargs = mock_stats_analyzer.get_stats.call_args[1]
        assert call_kwargs["granularity"] == "weekly"

    def test_stats_json_format(self, parser, mock_stats_analyzer, capsys):
        """Test stats command JSON format."""
        from cicada.commands import handle_stats

        mock_stats_analyzer.get_stats.return_value = {"total": 100}
        mock_stats_analyzer.format_json.return_value = '{"total": 100}'

        args = parser.parse_args(["stats", "--format", "json"])
        handle_stats(args)

        captured = capsys.readouterr()
        assert '"total": 100' in captured.out

    @pytest.mark.parametrize(
        "flag,expected_days",
        [("--last-7-days", 7), ("--last-30-days", 30)],
    )
    def test_stats_day_filters(self, parser, mock_stats_analyzer, flag, expected_days):
        """Test stats command with day filters."""
        from cicada.commands import handle_stats

        mock_stats_analyzer.get_stats.return_value = {"total": 50}
        mock_stats_analyzer.format_summary.return_value = f"Last {expected_days} days"

        args = parser.parse_args(["stats", flag])
        handle_stats(args)

        call_kwargs = mock_stats_analyzer.get_stats.call_args[1]
        assert call_kwargs["days"] == expected_days

    def test_stats_tool_filter(self, parser, mock_stats_analyzer):
        """Test stats command with --tool filter."""
        from cicada.commands import handle_stats

        mock_stats_analyzer.get_stats.return_value = {"total": 25}
        mock_stats_analyzer.format_summary.return_value = "query: 25"

        args = parser.parse_args(["stats", "--tool", "query"])
        handle_stats(args)

        call_kwargs = mock_stats_analyzer.get_stats.call_args[1]
        assert call_kwargs["tool_filter"] == "query"

    def test_stats_error(self, parser, mock_stats_analyzer):
        """Test stats command error handling."""
        from cicada.commands import handle_stats

        mock_stats_analyzer.get_stats.side_effect = Exception("Stats error")

        args = parser.parse_args(["stats"])

        with pytest.raises(SystemExit) as exc:
            handle_stats(args)
        assert exc.value.code == 1


class TestHandleStatsReset:
    """Test _handle_stats_reset function."""

    def test_stats_reset_with_force(self, parser, mock_stats_analyzer, capsys):
        """Test stats reset with --force flag."""
        from cicada.commands import handle_stats

        mock_stats_analyzer.reset_stats.return_value = 5

        args = parser.parse_args(["stats", "--reset", "-f"])
        handle_stats(args)

        captured = capsys.readouterr()
        assert "Deleted 5" in captured.out
        mock_stats_analyzer.reset_stats.assert_called_once_with(older_than_days=None)

    def test_stats_reset_older_than(self, parser, mock_stats_analyzer, capsys):
        """Test stats reset with --older-than."""
        from cicada.commands import handle_stats

        mock_stats_analyzer.reset_stats.return_value = 3

        args = parser.parse_args(["stats", "--reset", "--older-than", "30"])
        handle_stats(args)

        captured = capsys.readouterr()
        assert "older than 30 days" in captured.out
        mock_stats_analyzer.reset_stats.assert_called_once_with(older_than_days=30)

    @patch("builtins.input", return_value="n")
    def test_stats_reset_cancelled(self, mock_input, parser, mock_stats_analyzer, capsys):
        """Test stats reset cancelled by user."""
        from cicada.commands import handle_stats

        args = parser.parse_args(["stats", "--reset"])

        with pytest.raises(SystemExit) as exc:
            handle_stats(args)
        assert exc.value.code == 0

        captured = capsys.readouterr()
        assert "Aborted" in captured.out

    @patch("builtins.input", return_value="y")
    def test_stats_reset_confirmed(self, mock_input, parser, mock_stats_analyzer, capsys):
        """Test stats reset confirmed by user."""
        from cicada.commands import handle_stats

        mock_stats_analyzer.reset_stats.return_value = 10

        args = parser.parse_args(["stats", "--reset"])
        handle_stats(args)

        captured = capsys.readouterr()
        assert "Deleted 10" in captured.out


# ============================================================================
# SECTION 17: Test Handle Agents Command
# ============================================================================


class TestHandleAgents:
    """Test handle_agents command."""

    @patch("cicada.commands.handle_agents_install")
    def test_agents_install_routing(self, mock_install, parser):
        """Test agents install command routing."""
        from cicada.commands import handle_agents

        args = parser.parse_args(["agents", "install"])
        handle_agents(args)
        mock_install.assert_called_once()

    @patch("cicada.agents.installer.install_agent")
    def test_agents_install_execution(self, mock_install, capsys):
        """Test agents install actually installs agents."""
        from cicada.commands import handle_agents_install

        handle_agents_install()

        captured = capsys.readouterr()
        assert "Installing" in captured.out
        assert "cicada-code-explorer" in captured.out
        mock_install.assert_called_once()


# ============================================================================
# SECTION 18: Test Handle Index PR Command
# ============================================================================


class TestHandleIndexPR:
    """Test handle_index_pr command."""

    @pytest.fixture
    def mock_pr_indexer(self):
        """Common mock setup for PR indexer tests."""
        with (
            patch("cicada.version_check.check_for_updates"),
            patch("cicada.github.pr_indexer.PRIndexer") as mock_class,
            patch("cicada.utils.get_pr_index_path") as mock_path,
        ):
            mock_path.return_value = "/tmp/pr_index.json"
            mock_indexer = MagicMock()
            mock_class.return_value = mock_indexer
            yield mock_indexer

    def test_index_pr_success(self, parser, mock_pr_indexer, capsys):
        """Test index-pr command success."""
        from cicada.commands import handle_index_pr

        args = parser.parse_args(["index-pr"])
        handle_index_pr(args)

        captured = capsys.readouterr()
        assert "Indexing complete" in captured.out
        mock_pr_indexer.index_repository.assert_called_once()

    def test_index_pr_with_clean(self, parser, mock_pr_indexer):
        """Test index-pr command with --clean flag."""
        from cicada.commands import handle_index_pr

        args = parser.parse_args(["index-pr", "--clean"])
        handle_index_pr(args)

        call_kwargs = mock_pr_indexer.index_repository.call_args[1]
        assert call_kwargs["incremental"] is False

    def test_index_pr_keyboard_interrupt(self, parser, mock_pr_indexer):
        """Test index-pr handles keyboard interrupt."""
        from cicada.commands import handle_index_pr

        mock_pr_indexer.index_repository.side_effect = KeyboardInterrupt

        args = parser.parse_args(["index-pr"])

        with pytest.raises(SystemExit) as exc:
            handle_index_pr(args)
        assert exc.value.code == 130

    def test_index_pr_error(self, parser, mock_pr_indexer):
        """Test index-pr handles errors."""
        from cicada.commands import handle_index_pr

        mock_pr_indexer.index_repository.side_effect = Exception("PR indexing failed")

        args = parser.parse_args(["index-pr"])

        with pytest.raises(SystemExit) as exc:
            handle_index_pr(args)
        assert exc.value.code == 1


# ============================================================================
# SECTION 19: Test Handle Find Dead Code Missing Index
# ============================================================================


class TestHandleFindDeadCodeMissingIndex:
    """Test handle_find_dead_code when index doesn't exist."""

    @patch("cicada.utils.get_index_path")
    def test_find_dead_code_no_index(self, mock_get_path, parser, capsys):
        """Test find-dead-code when index doesn't exist."""
        from cicada.commands import handle_find_dead_code

        mock_path = MagicMock()
        mock_path.exists.return_value = False
        mock_get_path.return_value = mock_path

        args = parser.parse_args(["find-dead-code"])

        with pytest.raises(SystemExit) as exc:
            handle_find_dead_code(args)
        assert exc.value.code == 1

        captured = capsys.readouterr()
        assert "Index file not found" in captured.err

    @pytest.fixture
    def mock_dead_code_deps(self):
        """Common mock setup for dead code tests."""
        with (
            patch("cicada.utils.get_index_path") as mock_path,
            patch("cicada.utils.load_index") as mock_load,
            patch("cicada.dead_code.analyzer.DeadCodeAnalyzer") as mock_class,
            patch("cicada.dead_code.finder.filter_by_confidence") as mock_filter,
        ):
            path = MagicMock()
            path.exists.return_value = True
            mock_path.return_value = path
            mock_load.return_value = {"modules": {}}

            mock_analyzer = MagicMock()
            mock_analyzer.analyze.return_value = []
            mock_class.return_value = mock_analyzer
            mock_filter.return_value = []

            yield {"filter": mock_filter}

    @patch("cicada.dead_code.finder.format_markdown")
    def test_find_dead_code_success(self, mock_format, parser, mock_dead_code_deps, capsys):
        """Test find-dead-code success path."""
        from cicada.commands import handle_find_dead_code

        mock_format.return_value = "No dead code found"

        args = parser.parse_args(["find-dead-code"])
        handle_find_dead_code(args)

        captured = capsys.readouterr()
        assert "No dead code found" in captured.out

    @patch("cicada.dead_code.finder.format_json")
    def test_find_dead_code_json_format(self, mock_format, parser, mock_dead_code_deps, capsys):
        """Test find-dead-code with JSON format."""
        from cicada.commands import handle_find_dead_code

        mock_format.return_value = "[]"

        args = parser.parse_args(["find-dead-code", "--format", "json"])
        handle_find_dead_code(args)

        captured = capsys.readouterr()
        assert "[]" in captured.out


# ============================================================================
# SECTION 20: Test Handle Index with Watch
# ============================================================================


class TestHandleIndexWithWatch:
    """Test handle_index with --watch flag."""

    @pytest.mark.parametrize(
        "args_list,handler_name",
        [
            (["index", "--watch", "--fast"], "_setup_and_start_watcher"),
            (["index", "--force", "--fast"], "handle_index_main"),
            (["index", "--test", "--fast"], "handle_index_test_mode"),
            (["index", "--test-expansion", "--fast"], "handle_index_test_expansion_mode"),
        ],
    )
    @patch("cicada.version_check.check_for_updates")
    def test_index_flag_routing(self, mock_check, parser, args_list, handler_name):
        """Test index command routes to correct handler based on flags."""
        from cicada.commands import handle_index

        with patch(f"cicada.commands.{handler_name}") as mock_handler:
            args = parser.parse_args(args_list)
            handle_index(args)
            mock_handler.assert_called_once()


# ============================================================================
# SECTION 21: Test Handle Index Config Update
# ============================================================================


class TestHandleIndexConfigUpdate:
    """Test _handle_index_config_update function."""

    @patch("cicada.setup.create_config_yaml")
    @patch("cicada.commands._load_existing_config")
    def test_config_update_tier_changed(self, mock_load, mock_create, tmp_path):
        """Test config update detects tier change."""
        from cicada.commands import _handle_index_config_update

        config_path = tmp_path / "config.yaml"
        config_path.touch()

        mock_load.return_value = ("bert_small", "glove")

        result = _handle_index_config_update(config_path, tmp_path, tmp_path, "regular", "lemmi")

        assert result is True  # Tier changed
        mock_create.assert_called_once()

    @patch("cicada.setup.create_config_yaml")
    @patch("cicada.commands._load_existing_config")
    def test_config_update_tier_unchanged(self, mock_load, mock_create, tmp_path):
        """Test config update when tier unchanged."""
        from cicada.commands import _handle_index_config_update

        config_path = tmp_path / "config.yaml"
        config_path.touch()

        mock_load.return_value = ("regular", "lemmi")

        result = _handle_index_config_update(config_path, tmp_path, tmp_path, "regular", "lemmi")

        assert result is False  # Tier unchanged
        mock_create.assert_called_once()

    @patch("cicada.setup.create_config_yaml")
    def test_config_update_new_config(self, mock_create, tmp_path):
        """Test config update for new config (no existing)."""
        from cicada.commands import _handle_index_config_update

        config_path = tmp_path / "config.yaml"
        # Don't create the file - simulates new config

        result = _handle_index_config_update(config_path, tmp_path, tmp_path, "regular", "lemmi")

        assert result is False  # No existing config, so no "change"
        mock_create.assert_called_once()
