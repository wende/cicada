"""
Comprehensive tests for cicada/cli.py
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cicada.commands import (
    _setup_and_start_watcher,
    handle_clean,
    handle_dir,
    handle_editor_setup,
    handle_find_dead_code,
    handle_index,
    handle_index_pr,
    handle_install as handle_install_command,
    handle_watch,
)
from cicada.cli import main


def make_index_args(**overrides):
    """Build a MagicMock with sensible defaults for index command args."""
    defaults = {
        "fast": False,
        "max": False,
        "regular": False,
        "force": False,
        "repo": ".",
        "test": False,
        "test_expansion": False,
        "watch": False,
        "debounce": 2.0,
    }
    defaults.update(overrides)
    return MagicMock(**defaults)


class TestMain:
    """Tests for main() entry point"""

    def test_main_with_claude_subcommand(self):
        """Should route to handle_editor_setup for claude"""
        with (
            patch.object(sys, "argv", ["cicada", "claude"]),
            patch("cicada.commands.handle_editor_setup") as mock_handler,
        ):
            main()
            mock_handler.assert_called_once()
            args, editor = mock_handler.call_args[0]
            assert editor == "claude"

    def test_main_with_cursor_subcommand(self):
        """Should route to handle_editor_setup for cursor"""
        with (
            patch.object(sys, "argv", ["cicada", "cursor"]),
            patch("cicada.commands.handle_editor_setup") as mock_handler,
        ):
            main()
            mock_handler.assert_called_once()
            args, editor = mock_handler.call_args[0]
            assert editor == "cursor"

    def test_main_with_vs_subcommand(self):
        """Should route to handle_editor_setup for vs"""
        with (
            patch.object(sys, "argv", ["cicada", "vs"]),
            patch("cicada.commands.handle_editor_setup") as mock_handler,
        ):
            main()
            mock_handler.assert_called_once()
            args, editor = mock_handler.call_args[0]
            assert editor == "vs"

    def test_main_with_gemini_subcommand(self):
        """Should route to handle_editor_setup for gemini"""
        with (
            patch.object(sys, "argv", ["cicada", "gemini"]),
            patch("cicada.commands.handle_editor_setup") as mock_handler,
        ):
            main()
            mock_handler.assert_called_once()
            args, editor = mock_handler.call_args[0]
            assert editor == "gemini"

    def test_main_with_codex_subcommand(self):
        """Should route to handle_editor_setup for codex"""
        with (
            patch.object(sys, "argv", ["cicada", "codex"]),
            patch("cicada.commands.handle_editor_setup") as mock_handler,
        ):
            main()
            mock_handler.assert_called_once()
            args, editor = mock_handler.call_args[0]
            assert editor == "codex"

    def test_main_with_index_subcommand(self):
        """Should route to handle_index"""
        with (
            patch.object(sys, "argv", ["cicada", "index"]),
            patch("cicada.commands.handle_index") as mock_handler,
        ):
            main()
            mock_handler.assert_called_once()

    def test_main_with_index_pr_subcommand(self):
        """Should route to handle_index_pr"""
        with (
            patch.object(sys, "argv", ["cicada", "index-pr"]),
            patch("cicada.commands.handle_index_pr") as mock_handler,
        ):
            main()
            mock_handler.assert_called_once()

    def test_main_with_find_dead_code_subcommand(self):
        """Should route to handle_find_dead_code"""
        with (
            patch.object(sys, "argv", ["cicada", "find-dead-code"]),
            patch("cicada.commands.handle_find_dead_code") as mock_handler,
        ):
            main()
            mock_handler.assert_called_once()

    def test_main_with_clean_subcommand(self):
        """Should route to handle_clean"""
        with (
            patch.object(sys, "argv", ["cicada", "clean", "-f"]),
            patch("cicada.commands.handle_clean") as mock_handler,
        ):
            main()
            mock_handler.assert_called_once()

    def test_main_with_dir_subcommand(self):
        """Should route to handle_dir"""
        with (
            patch.object(sys, "argv", ["cicada", "dir"]),
            patch("cicada.commands.handle_dir") as mock_handler,
        ):
            main()
            mock_handler.assert_called_once()

    def test_main_no_args_shows_help(self):
        """Should show help when no args provided"""
        with (
            patch.object(sys, "argv", ["cicada"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()
        assert exc_info.value.code == 1

    def test_main_with_dot_path_calls_install(self):
        """Should route to install command when path is '.'"""
        with (
            patch.object(sys, "argv", ["cicada", "."]),
            patch("cicada.commands.handle_install") as mock_handler,
        ):
            main()
            mock_handler.assert_called_once()
            args = mock_handler.call_args[0][0]
            assert args.repo == "."

    def test_main_with_relative_path_calls_install(self):
        """Should route to install command when path starts with './'"""
        with (
            patch.object(sys, "argv", ["cicada", "./some/path"]),
            patch("cicada.commands.handle_install") as mock_handler,
        ):
            main()
            mock_handler.assert_called_once()
            args = mock_handler.call_args[0][0]
            assert args.repo == "./some/path"

    def test_main_with_absolute_path_calls_install(self):
        """Should route to install command when path starts with '/'"""
        with (
            patch.object(sys, "argv", ["cicada", "/absolute/path"]),
            patch("cicada.commands.handle_install") as mock_handler,
        ):
            main()
            mock_handler.assert_called_once()
            args = mock_handler.call_args[0][0]
            assert args.repo == "/absolute/path"

    def test_main_with_parent_directory_calls_install(self):
        """Should route to install command when path is '..'"""
        with (
            patch.object(sys, "argv", ["cicada", ".."]),
            patch("cicada.commands.handle_install") as mock_handler,
        ):
            main()
            mock_handler.assert_called_once()
            args = mock_handler.call_args[0][0]
            assert args.repo == ".."


class TestHandleEditorSetup:
    """Tests for handle_editor_setup function"""

    @pytest.fixture
    def mock_elixir_repo(self, tmp_path):
        """Create a mock Elixir repository"""
        (tmp_path / "mix.exs").write_text("# Mock mix file")
        return tmp_path

    def test_cannot_specify_multiple_tiers(self, mock_elixir_repo, capsys):
        """Should error if multiple tier flags specified"""
        args = make_index_args(fast=True, max=True)

        with (
            patch("pathlib.Path.cwd", return_value=mock_elixir_repo),
            pytest.raises(SystemExit) as exc_info,
        ):
            handle_editor_setup(args, "claude")

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Can only specify one tier flag" in captured.err

    def test_requires_elixir_project(self, tmp_path, capsys):
        """Should error if not an Elixir project"""
        args = make_index_args()

        with (
            patch("pathlib.Path.cwd", return_value=tmp_path),
            pytest.raises(SystemExit) as exc_info,
        ):
            handle_editor_setup(args, "claude")

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "does not appear to be an Elixir project" in captured.err

    def test_fast_flag_sets_regular_extraction(self, mock_elixir_repo):
        """--fast should set extraction to regular + lemmi expansion"""
        args = make_index_args(fast=True)

        with (
            patch("pathlib.Path.cwd", return_value=mock_elixir_repo),
            patch("cicada.setup.setup") as mock_setup,
        ):
            handle_editor_setup(args, "claude")

            # Check that setup was called with regular extraction
            call_kwargs = mock_setup.call_args[1]
            assert call_kwargs["extraction_method"] == "regular"
            assert call_kwargs["expansion_method"] == "lemmi"

    def test_regular_flag_sets_bert_glove(self, mock_elixir_repo):
        """--regular should set extraction to bert + glove expansion"""
        args = make_index_args(regular=True)

        with (
            patch("pathlib.Path.cwd", return_value=mock_elixir_repo),
            patch("cicada.setup.setup") as mock_setup,
        ):
            handle_editor_setup(args, "claude")

            # Check that setup was called with bert + glove
            call_kwargs = mock_setup.call_args[1]
            assert call_kwargs["extraction_method"] == "bert"
            assert call_kwargs["expansion_method"] == "glove"

    def test_max_flag_sets_bert_fasttext(self, mock_elixir_repo):
        """--max should set extraction to bert + fasttext expansion"""
        args = make_index_args(max=True)

        with (
            patch("pathlib.Path.cwd", return_value=mock_elixir_repo),
            patch("cicada.setup.setup") as mock_setup,
        ):
            handle_editor_setup(args, "claude")

            call_kwargs = mock_setup.call_args[1]
            assert call_kwargs["extraction_method"] == "bert"
            assert call_kwargs["expansion_method"] == "fasttext"

    def test_no_flags_with_existing_index(self, mock_elixir_repo, tmp_path):
        """Should read existing config when no flags and index exists"""
        args = make_index_args()

        with (
            patch("pathlib.Path.cwd", return_value=mock_elixir_repo),
            patch("cicada.utils.storage.get_config_path") as mock_get_config,
            patch("cicada.utils.storage.get_index_path") as mock_get_index,
            patch("cicada.setup.setup") as mock_setup,
            patch(
                "builtins.open",
                MagicMock(return_value=MagicMock(__enter__=lambda s: s, read=lambda: "")),
            ),
            patch(
                "yaml.safe_load",
                return_value={
                    "keyword_extraction": {"method": "bert"},
                    "keyword_expansion": {"method": "glove"},
                },
            ),
        ):
            # Mock paths to exist
            mock_config_path = MagicMock()
            mock_config_path.exists.return_value = True
            mock_get_config.return_value = mock_config_path

            mock_index_path = MagicMock()
            mock_index_path.exists.return_value = True
            mock_get_index.return_value = mock_index_path

            handle_editor_setup(args, "claude")

            # Check that setup was called with existing config
            call_kwargs = mock_setup.call_args[1]
            assert call_kwargs["extraction_method"] == "bert"
            assert call_kwargs["expansion_method"] == "glove"
            assert call_kwargs["index_exists"] is True

    def test_setup_exception_exits(self, mock_elixir_repo, capsys):
        """Should exit with error if setup fails"""
        args = make_index_args(fast=True)

        with (
            patch("pathlib.Path.cwd", return_value=mock_elixir_repo),
            patch("cicada.setup.setup", side_effect=Exception("Setup failed")),
            pytest.raises(SystemExit) as exc_info,
        ):
            handle_editor_setup(args, "claude")

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Setup failed" in captured.err


class TestHandleIndex:
    """Tests for handle_index function"""

    @pytest.fixture
    def mock_repo(self, tmp_path):
        """Create a mock repository"""
        (tmp_path / "mix.exs").write_text("# Mock")
        return tmp_path

    def test_fast_flag_creates_config(self, mock_repo):
        """--fast should create config with regular extraction and lemmi expansion"""
        args = make_index_args(fast=True, force=True, repo=str(mock_repo))

        with (
            patch("cicada.version_check.check_for_updates"),
            patch("cicada.utils.storage.get_config_path") as mock_get_config,
            patch("cicada.utils.storage.create_storage_dir") as mock_storage,
            patch("cicada.utils.storage.get_index_path"),
            patch("cicada.setup.create_config_yaml") as mock_create_config,
            patch("cicada.indexer.ElixirIndexer"),
        ):
            mock_config_path = MagicMock()
            mock_config_path.exists.return_value = False
            mock_get_config.return_value = mock_config_path

            mock_storage.return_value = mock_repo / ".cicada"

            handle_index(args)

            # Verify config was created with regular extraction
            mock_create_config.assert_called()
            call_args = mock_create_config.call_args[0]
            assert call_args[2] == "regular"  # extraction_method is 3rd positional arg
            assert call_args[3] == "lemmi"  # expansion_method is 4th positional arg

    def test_regular_flag_creates_config_with_bert_glove(self, mock_repo):
        """--regular should create config with bert extraction and glove expansion"""
        args = make_index_args(regular=True, force=True, repo=str(mock_repo))

        with (
            patch("cicada.version_check.check_for_updates"),
            patch("cicada.utils.storage.get_config_path") as mock_get_config,
            patch("cicada.utils.storage.create_storage_dir") as mock_storage,
            patch("cicada.utils.storage.get_index_path"),
            patch("cicada.setup.create_config_yaml") as mock_create_config,
            patch("cicada.indexer.ElixirIndexer"),
        ):
            mock_config_path = MagicMock()
            mock_config_path.exists.return_value = False
            mock_get_config.return_value = mock_config_path

            mock_storage.return_value = mock_repo / ".cicada"

            handle_index(args)

            # Verify config was created with bert + glove
            mock_create_config.assert_called()
            call_args = mock_create_config.call_args[0]
            assert call_args[2] == "bert"  # extraction_method is 3rd positional arg
            assert call_args[3] == "glove"  # expansion_method is 4th positional arg

    def test_no_flags_no_config_shows_error(self, mock_repo, capsys):
        """Should show error message when no flags and no config"""
        args = make_index_args(repo=str(mock_repo))

        with (
            patch("cicada.version_check.check_for_updates"),
            patch("cicada.utils.storage.get_config_path") as mock_get_config,
            patch("cicada.utils.storage.create_storage_dir"),
            patch("cicada.utils.storage.get_index_path"),
            pytest.raises(SystemExit) as exc_info,
        ):
            mock_config_path = MagicMock()
            mock_config_path.exists.return_value = False
            mock_get_config.return_value = mock_config_path

            handle_index(args)

        # Verify it exits with code 2
        assert exc_info.value.code == 2

        # Verify error message is shown
        captured = capsys.readouterr()
        assert "No tier configured" in captured.err
        assert "--force" in captured.err

    def test_force_requires_tier_flag(self, mock_repo, capsys):
        """--force without a tier flag should exit with error."""
        args = make_index_args(force=True, repo=str(mock_repo))

        with (
            patch("cicada.version_check.check_for_updates"),
            patch("cicada.utils.storage.get_config_path"),
            patch("cicada.utils.storage.create_storage_dir"),
            patch("cicada.utils.storage.get_index_path"),
            pytest.raises(SystemExit) as exc_info,
        ):
            handle_index(args)

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "--force requires specifying a tier flag" in captured.err

    def test_tier_flag_without_force_errors(self, mock_repo, capsys):
        """Tier flags without --force should exit with error."""
        args = make_index_args(fast=True, repo=str(mock_repo))

        with (
            patch("cicada.version_check.check_for_updates"),
            patch("cicada.utils.storage.get_config_path"),
            patch("cicada.utils.storage.create_storage_dir"),
            patch("cicada.utils.storage.get_index_path"),
            pytest.raises(SystemExit) as exc_info,
        ):
            handle_index(args)

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "Tier flags now require --force" in captured.err

    def test_changing_method_exits_with_error(self, mock_repo, capsys):
        """Changing extraction method should exit with error and suggest cicada clean"""
        args = make_index_args(regular=True, force=True, repo=str(mock_repo))

        with (
            patch("cicada.version_check.check_for_updates"),
            patch("cicada.utils.storage.get_config_path") as mock_get_config,
            patch("cicada.utils.storage.create_storage_dir"),
            patch("cicada.utils.storage.get_index_path"),
            patch("cicada.setup.create_config_yaml"),
            patch("cicada.indexer.ElixirIndexer") as mock_indexer_class,
            patch("builtins.open", MagicMock()),
            patch(
                "yaml.safe_load",
                return_value={
                    "keyword_extraction": {"method": "regular"},
                    "keyword_expansion": {"method": "lemmi"},
                },
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            mock_config_path = MagicMock()
            mock_config_path.exists.return_value = True
            mock_get_config.return_value = mock_config_path

            mock_indexer = MagicMock()
            mock_indexer_class.return_value = mock_indexer

            handle_index(args)

        # Verify it exits with code 1
        assert exc_info.value.code == 1

        # Verify error message was printed
        captured = capsys.readouterr()
        assert "Cannot change extraction" in captured.err
        assert "regular" in captured.err and "bert" in captured.err
        assert "cicada clean" in captured.err

    def test_changing_expansion_method_exits_with_error(self, mock_repo, capsys):
        """Changing expansion method should exit with error and suggest cicada clean"""
        args = make_index_args(max=True, force=True, repo=str(mock_repo))

        with (
            patch("cicada.version_check.check_for_updates"),
            patch("cicada.utils.storage.get_config_path") as mock_get_config,
            patch("cicada.utils.storage.create_storage_dir"),
            patch("cicada.utils.storage.get_index_path"),
            patch("cicada.setup.create_config_yaml"),
            patch("cicada.indexer.ElixirIndexer") as mock_indexer_class,
            patch("builtins.open", MagicMock()),
            patch(
                "yaml.safe_load",
                return_value={
                    "keyword_extraction": {"method": "bert"},
                    "keyword_expansion": {"method": "glove"},
                },
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            mock_config_path = MagicMock()
            mock_config_path.exists.return_value = True
            mock_get_config.return_value = mock_config_path

            mock_indexer = MagicMock()
            mock_indexer_class.return_value = mock_indexer

            handle_index(args)

        # Verify it exits with code 1
        assert exc_info.value.code == 1

        # Verify error message was printed
        captured = capsys.readouterr()
        assert (
            "Cannot change expansion method" in captured.err or "settings" in captured.err.lower()
        )
        assert "cicada clean" in captured.err


class TestHandleIndexPR:
    """Tests for handle_index_pr function"""

    def test_calls_pr_indexer(self):
        """Should call PRIndexer with correct arguments"""
        args = MagicMock(repo=".", clean=False)

        with (
            patch("cicada.version_check.check_for_updates"),
            patch("cicada.utils.get_pr_index_path") as mock_get_path,
            patch("cicada.pr_indexer.PRIndexer") as mock_indexer_class,
        ):
            mock_get_path.return_value = "/test/path/pr_index.json"
            mock_indexer = MagicMock()
            mock_indexer_class.return_value = mock_indexer

            handle_index_pr(args)

            # Verify PRIndexer was created and index_repository called
            mock_indexer_class.assert_called_once_with(repo_path=".")
            mock_get_path.assert_called_once_with(".")
            mock_indexer.index_repository.assert_called_once_with(
                output_path="/test/path/pr_index.json", incremental=True
            )

    def test_clean_flag_disables_incremental(self):
        """--clean should disable incremental indexing"""
        args = MagicMock(repo=".", clean=True)

        with (
            patch("cicada.version_check.check_for_updates"),
            patch("cicada.utils.get_pr_index_path") as mock_get_path,
            patch("cicada.pr_indexer.PRIndexer") as mock_indexer_class,
        ):
            mock_get_path.return_value = "/test/path/pr_index.json"
            mock_indexer = MagicMock()
            mock_indexer_class.return_value = mock_indexer

            handle_index_pr(args)

            # Verify incremental=False
            call_kwargs = mock_indexer.index_repository.call_args[1]
            assert call_kwargs["incremental"] is False

    def test_keyboard_interrupt_exits_gracefully(self, capsys):
        """Should handle KeyboardInterrupt gracefully"""
        args = MagicMock(repo=".", clean=False)

        with (
            patch("cicada.version_check.check_for_updates"),
            patch("cicada.utils.get_pr_index_path") as mock_get_path,
            patch("cicada.pr_indexer.PRIndexer") as mock_indexer_class,
            pytest.raises(SystemExit) as exc_info,
        ):
            mock_get_path.return_value = "/test/path/pr_index.json"
            mock_indexer = MagicMock()
            mock_indexer.index_repository.side_effect = KeyboardInterrupt()
            mock_indexer_class.return_value = mock_indexer

            handle_index_pr(args)

        assert exc_info.value.code == 130
        captured = capsys.readouterr()
        assert "interrupted by user" in captured.out

    def test_exception_exits_with_error(self, capsys):
        """Should exit with error on exception"""
        args = MagicMock(repo=".", clean=False)

        with (
            patch("cicada.version_check.check_for_updates"),
            patch("cicada.utils.get_pr_index_path") as mock_get_path,
            patch("cicada.pr_indexer.PRIndexer") as mock_indexer_class,
            pytest.raises(SystemExit) as exc_info,
        ):
            mock_get_path.return_value = "/test/path/pr_index.json"
            mock_indexer = MagicMock()
            mock_indexer.index_repository.side_effect = Exception("PR indexing failed")
            mock_indexer_class.return_value = mock_indexer

            handle_index_pr(args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "PR indexing failed" in captured.err


class TestHandleFindDeadCode:
    """Tests for handle_find_dead_code function"""

    @pytest.fixture
    def mock_index_file(self, tmp_path):
        """Create a mock index file"""
        index_path = tmp_path / "index.json"
        index_path.write_text(json.dumps({"modules": [], "functions": []}))
        return index_path

    def test_requires_index_file(self, tmp_path, capsys):
        """Should error if index file not found"""
        args = MagicMock(format="markdown", min_confidence="high")
        missing_path = tmp_path / "missing.json"

        with (
            patch("cicada.utils.get_index_path", return_value=missing_path),
            pytest.raises(SystemExit) as exc_info,
        ):
            handle_find_dead_code(args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Index file not found" in captured.err

    def test_calls_analyzer(self, mock_index_file):
        """Should call DeadCodeAnalyzer and format results"""
        args = MagicMock(format="markdown", min_confidence="high")

        with (
            patch("cicada.utils.get_index_path", return_value=mock_index_file),
            patch("cicada.utils.load_index") as mock_load,
            patch("cicada.dead_code.analyzer.DeadCodeAnalyzer") as mock_analyzer_class,
            patch("cicada.dead_code.finder.filter_by_confidence") as mock_filter,
            patch(
                "cicada.dead_code.finder.format_markdown", return_value="# Dead Code"
            ) as mock_format,
        ):
            mock_load.return_value = {"modules": [], "functions": []}
            mock_analyzer = MagicMock()
            mock_analyzer.analyze.return_value = []
            mock_analyzer_class.return_value = mock_analyzer
            mock_filter.return_value = []

            handle_find_dead_code(args)

            # Verify analyzer was called
            mock_analyzer_class.assert_called_once()
            mock_analyzer.analyze.assert_called_once()
            mock_filter.assert_called_once()
            mock_format.assert_called_once()

    def test_json_format(self, mock_index_file):
        """Should use JSON formatter when requested"""
        args = MagicMock(format="json", min_confidence="high")

        with (
            patch("cicada.utils.get_index_path", return_value=mock_index_file),
            patch("cicada.utils.load_index") as mock_load,
            patch("cicada.dead_code.analyzer.DeadCodeAnalyzer") as mock_analyzer_class,
            patch("cicada.dead_code.finder.filter_by_confidence") as mock_filter,
            patch("cicada.dead_code.finder.format_json", return_value="{}") as mock_format_json,
            patch("cicada.dead_code.finder.format_markdown") as mock_format_md,
        ):
            mock_load.return_value = {"modules": [], "functions": []}
            mock_analyzer = MagicMock()
            mock_analyzer.analyze.return_value = []
            mock_analyzer_class.return_value = mock_analyzer
            mock_filter.return_value = []

            handle_find_dead_code(args)

            # Verify JSON formatter was used, not markdown
            mock_format_json.assert_called_once()
            mock_format_md.assert_not_called()


class TestHandleClean:
    """Tests for handle_clean function"""

    def test_clean_all_flag(self):
        """Should call clean_all_projects when --all specified"""
        args = MagicMock(all=True, force=False, index=False, pr_index=False)

        with patch("cicada.clean.clean_all_projects") as mock_clean_all:
            handle_clean(args)
            mock_clean_all.assert_called_once_with(force=False)

    def test_clean_all_with_force(self):
        """Should pass force flag to clean_all_projects"""
        args = MagicMock(all=True, force=True, index=False, pr_index=False)

        with patch("cicada.clean.clean_all_projects") as mock_clean_all:
            handle_clean(args)
            mock_clean_all.assert_called_once_with(force=True)

    def test_clean_current_repo(self, tmp_path):
        """Should call clean_repository for current directory"""
        args = MagicMock(all=False, force=False, index=False, pr_index=False)

        with (
            patch("pathlib.Path.cwd", return_value=tmp_path),
            patch("cicada.clean.clean_repository") as mock_clean_repo,
        ):
            handle_clean(args)
            mock_clean_repo.assert_called_once_with(tmp_path, force=False)

    def test_clean_exception_exits(self, tmp_path, capsys):
        """Should exit with error on exception"""
        args = MagicMock(all=False, force=False, index=False, pr_index=False)

        with (
            patch("pathlib.Path.cwd", return_value=tmp_path),
            patch("cicada.clean.clean_repository", side_effect=Exception("Clean failed")),
            pytest.raises(SystemExit) as exc_info,
        ):
            handle_clean(args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Clean failed" in captured.err


class TestHandleDir:
    """Tests for handle_dir function"""

    def test_prints_storage_directory_with_default_repo(self, tmp_path, capsys):
        """Should print storage directory path with default repo"""
        args = MagicMock(repo=".")
        expected_path = tmp_path / ".cicada"

        with (
            patch("pathlib.Path.resolve", return_value=tmp_path),
            patch(
                "cicada.utils.storage.get_storage_dir", return_value=expected_path
            ) as mock_get_storage_dir,
        ):
            handle_dir(args)

            mock_get_storage_dir.assert_called_once()
            captured = capsys.readouterr()
            assert str(expected_path) in captured.out

    def test_prints_storage_directory_with_explicit_repo(self, tmp_path, capsys):
        """Should print storage directory path with explicit repo path"""
        repo_path = tmp_path / "test-repo"
        args = MagicMock(repo=str(repo_path))
        expected_path = tmp_path / ".cicada" / "project"

        with (
            patch("pathlib.Path.resolve", return_value=repo_path),
            patch(
                "cicada.utils.storage.get_storage_dir", return_value=expected_path
            ) as mock_get_storage_dir,
        ):
            handle_dir(args)

            mock_get_storage_dir.assert_called_once()
            captured = capsys.readouterr()
            assert str(expected_path) in captured.out

    def test_exception_exits_with_error(self, capsys):
        """Should exit with error if get_storage_dir fails"""
        args = MagicMock(repo=".")

        with (
            patch("cicada.utils.storage.get_storage_dir", side_effect=Exception("Storage error")),
            pytest.raises(SystemExit) as exc_info,
        ):
            handle_dir(args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Storage error" in captured.err


class TestHandleWatch:
    """Tests for handle_watch() command"""

    def test_handle_watch_calls_version_check(self):
        """Should call version check before starting watcher"""
        args = MagicMock(repo=".", fast=True, max=False, regular=False, debounce=2.0)

        with (
            patch("cicada.version_check.check_for_updates") as mock_check,
            patch("cicada.commands._setup_and_start_watcher") as mock_setup,
        ):
            handle_watch(args)

            mock_check.assert_called_once()
            mock_setup.assert_called_once_with(args, ".")

    def test_handle_watch_calls_setup_and_start_watcher(self):
        """Should call _setup_and_start_watcher with correct args"""
        args = MagicMock(repo="/path/to/repo", fast=False, max=True, regular=False, debounce=3.0)

        with (
            patch("cicada.version_check.check_for_updates"),
            patch("cicada.commands._setup_and_start_watcher") as mock_setup,
        ):
            handle_watch(args)

            mock_setup.assert_called_once_with(args, "/path/to/repo")

    def test_handle_watch_handles_exceptions(self, capsys):
        """Should handle exceptions from _setup_and_start_watcher"""
        args = MagicMock(repo=".", fast=True, max=False, regular=False)

        with (
            patch("cicada.version_check.check_for_updates"),
            patch(
                "cicada.commands._setup_and_start_watcher",
                side_effect=Exception("Watcher failed"),
            ),
            pytest.raises(Exception, match="Watcher failed"),
        ):
            handle_watch(args)


class TestSetupAndStartWatcher:
    """Tests for _setup_and_start_watcher() helper"""

    def test_setup_and_start_watcher_validates_tier_flags(self, tmp_path):
        """Should validate tier flags before starting"""
        args = MagicMock(
            fast=True,
            max=True,
            regular=False,
            repo=".",
            debounce=2.0,
        )

        with (
            patch("cicada.commands.validate_tier_flags") as mock_validate,
            patch("cicada.utils.storage.get_config_path"),
            patch("cicada.commands.determine_tier", return_value="fast"),
            patch("cicada.watcher.FileWatcher"),
        ):
            try:
                _setup_and_start_watcher(args, str(tmp_path))
            except SystemExit:
                pass

            mock_validate.assert_called_once_with(args, require_force=True)

    def test_setup_and_start_watcher_determines_tier_from_args(self, tmp_path):
        """Should determine tier from args or config"""
        args = MagicMock(
            fast=True,
            max=False,
            regular=False,
            debounce=2.0,
        )

        config_path = tmp_path / "config.yaml"

        with (
            patch("cicada.commands.validate_tier_flags"),
            patch("cicada.utils.storage.get_config_path", return_value=config_path),
            patch("cicada.commands.determine_tier", return_value="fast") as mock_determine,
            patch("cicada.watcher.FileWatcher") as mock_watcher_class,
        ):
            mock_watcher = MagicMock()
            mock_watcher_class.return_value = mock_watcher

            _setup_and_start_watcher(args, str(tmp_path))

            # Should call determine_tier with args and repo_path
            mock_determine.assert_called_once()
            call_args = mock_determine.call_args[0]
            assert call_args[0] == args
            assert isinstance(call_args[1], Path)

    def test_setup_and_start_watcher_error_when_no_tier_and_no_config(self, tmp_path, capsys):
        """Should exit with error when no tier specified and no config exists"""
        args = MagicMock(
            fast=False,
            max=False,
            regular=False,
            debounce=2.0,
        )

        config_path = tmp_path / "nonexistent" / "config.yaml"

        with (
            patch("cicada.commands.validate_tier_flags"),
            patch("cicada.utils.storage.get_config_path", return_value=config_path),
            patch("cicada.commands.determine_tier", return_value="regular"),
            pytest.raises(SystemExit) as exc_info,
        ):
            _setup_and_start_watcher(args, str(tmp_path))

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "No tier configured" in captured.err

    def test_setup_and_start_watcher_creates_file_watcher(self, tmp_path):
        """Should create FileWatcher with correct parameters"""
        args = MagicMock(
            fast=True,
            max=False,
            regular=False,
            debounce=3.5,
        )

        config_path = tmp_path / "config.yaml"
        config_path.write_text("test")

        with (
            patch("cicada.commands.validate_tier_flags"),
            patch("cicada.utils.storage.get_config_path", return_value=config_path),
            patch("cicada.commands.determine_tier", return_value="fast"),
            patch("cicada.watcher.FileWatcher") as mock_watcher_class,
        ):
            mock_watcher = MagicMock()
            mock_watcher_class.return_value = mock_watcher

            _setup_and_start_watcher(args, str(tmp_path))

            # Should create FileWatcher with correct params
            mock_watcher_class.assert_called_once()
            call_kwargs = mock_watcher_class.call_args[1]
            assert call_kwargs["debounce_seconds"] == 3.5
            assert call_kwargs["verbose"] is True
            assert call_kwargs["tier"] == "fast"

            # Should call start_watching
            mock_watcher.start_watching.assert_called_once()

    def test_setup_and_start_watcher_handles_debounce_param(self, tmp_path):
        """Should handle debounce parameter correctly"""
        args = MagicMock(
            fast=True,
            max=False,
            regular=False,
            debounce=5.0,
        )

        config_path = tmp_path / "config.yaml"
        config_path.write_text("test")

        with (
            patch("cicada.commands.validate_tier_flags"),
            patch("cicada.utils.storage.get_config_path", return_value=config_path),
            patch("cicada.commands.determine_tier", return_value="fast"),
            patch("cicada.watcher.FileWatcher") as mock_watcher_class,
        ):
            mock_watcher = MagicMock()
            mock_watcher_class.return_value = mock_watcher

            _setup_and_start_watcher(args, str(tmp_path))

            call_kwargs = mock_watcher_class.call_args[1]
            assert call_kwargs["debounce_seconds"] == 5.0

    def test_setup_and_start_watcher_handles_keyboard_interrupt(self, tmp_path, capsys):
        """Should handle KeyboardInterrupt gracefully"""
        args = MagicMock(
            fast=True,
            max=False,
            regular=False,
            debounce=2.0,
        )

        config_path = tmp_path / "config.yaml"
        config_path.write_text("test")

        with (
            patch("cicada.commands.validate_tier_flags"),
            patch("cicada.utils.storage.get_config_path", return_value=config_path),
            patch("cicada.commands.determine_tier", return_value="fast"),
            patch("cicada.watcher.FileWatcher") as mock_watcher_class,
            pytest.raises(SystemExit) as exc_info,
        ):
            mock_watcher = MagicMock()
            mock_watcher.start_watching.side_effect = KeyboardInterrupt()
            mock_watcher_class.return_value = mock_watcher

            _setup_and_start_watcher(args, str(tmp_path))

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "Watch mode stopped by user" in captured.out

    def test_setup_and_start_watcher_handles_exceptions(self, tmp_path, capsys):
        """Should handle exceptions from FileWatcher"""
        args = MagicMock(
            fast=True,
            max=False,
            regular=False,
            debounce=2.0,
        )

        config_path = tmp_path / "config.yaml"
        config_path.write_text("test")

        with (
            patch("cicada.commands.validate_tier_flags"),
            patch("cicada.utils.storage.get_config_path", return_value=config_path),
            patch("cicada.commands.determine_tier", return_value="fast"),
            patch("cicada.watcher.FileWatcher") as mock_watcher_class,
            pytest.raises(SystemExit) as exc_info,
        ):
            mock_watcher = MagicMock()
            mock_watcher.start_watching.side_effect = Exception("Watcher error")
            mock_watcher_class.return_value = mock_watcher

            _setup_and_start_watcher(args, str(tmp_path))

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Watcher error" in captured.err


class TestHandleIndexWithWatch:
    """Tests for handle_index() with --watch flag"""

    def test_handle_index_routes_to_watcher_when_watch_true(self):
        """Should route to _setup_and_start_watcher when --watch flag is set"""
        args = MagicMock(
            repo="/path/to/repo",
            test=False,
            test_expansion=False,
            watch=True,
            fast=False,
            max=False,
            regular=False,
            force=False,
        )

        with (
            patch("cicada.version_check.check_for_updates"),
            patch("cicada.commands._setup_and_start_watcher") as mock_setup,
        ):
            handle_index(args)

            # Should route to watcher, not normal indexing
            mock_setup.assert_called_once_with(args, "/path/to/repo")

    def test_handle_index_does_not_run_normal_indexing_when_watch_true(self):
        """Should not execute normal indexing when watch=True"""
        args = MagicMock(
            repo=".",
            test=False,
            test_expansion=False,
            watch=True,
            fast=False,
            max=False,
            regular=False,
            force=False,
        )

        with (
            patch("cicada.version_check.check_for_updates"),
            patch("cicada.commands._setup_and_start_watcher"),
            patch("cicada.commands.handle_index_main") as mock_main,
        ):
            handle_index(args)

            # handle_index_main should not be called
            mock_main.assert_not_called()

    def test_handle_index_passes_correct_repo_path_to_watcher(self):
        """Should pass correct repo path to _setup_and_start_watcher"""
        test_repo = "/custom/repo/path"
        args = MagicMock(
            repo=test_repo,
            test=False,
            test_expansion=False,
            watch=True,
            fast=False,
            max=False,
            regular=False,
            force=False,
        )

        with (
            patch("cicada.version_check.check_for_updates"),
            patch("cicada.commands._setup_and_start_watcher") as mock_setup,
        ):
            handle_index(args)

            mock_setup.assert_called_once_with(args, test_repo)
