"""
Comprehensive tests for cicada/cli.py
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cicada.cli import (
    handle_clean,
    handle_editor_setup,
    handle_find_dead_code,
    handle_index,
    handle_index_pr,
    handle_install_command,
    main,
)


class TestMain:
    """Tests for main() entry point"""

    def test_main_with_claude_subcommand(self):
        """Should route to handle_editor_setup for claude"""
        with (
            patch.object(sys, "argv", ["cicada", "claude"]),
            patch("cicada.cli.handle_editor_setup") as mock_handler,
        ):
            main()
            mock_handler.assert_called_once()
            args, editor = mock_handler.call_args[0]
            assert editor == "claude"

    def test_main_with_cursor_subcommand(self):
        """Should route to handle_editor_setup for cursor"""
        with (
            patch.object(sys, "argv", ["cicada", "cursor"]),
            patch("cicada.cli.handle_editor_setup") as mock_handler,
        ):
            main()
            mock_handler.assert_called_once()
            args, editor = mock_handler.call_args[0]
            assert editor == "cursor"

    def test_main_with_vs_subcommand(self):
        """Should route to handle_editor_setup for vs"""
        with (
            patch.object(sys, "argv", ["cicada", "vs"]),
            patch("cicada.cli.handle_editor_setup") as mock_handler,
        ):
            main()
            mock_handler.assert_called_once()
            args, editor = mock_handler.call_args[0]
            assert editor == "vs"

    def test_main_with_index_subcommand(self):
        """Should route to handle_index"""
        with (
            patch.object(sys, "argv", ["cicada", "index"]),
            patch("cicada.cli.handle_index") as mock_handler,
        ):
            main()
            mock_handler.assert_called_once()

    def test_main_with_index_pr_subcommand(self):
        """Should route to handle_index_pr"""
        with (
            patch.object(sys, "argv", ["cicada", "index-pr"]),
            patch("cicada.cli.handle_index_pr") as mock_handler,
        ):
            main()
            mock_handler.assert_called_once()

    def test_main_with_find_dead_code_subcommand(self):
        """Should route to handle_find_dead_code"""
        with (
            patch.object(sys, "argv", ["cicada", "find-dead-code"]),
            patch("cicada.cli.handle_find_dead_code") as mock_handler,
        ):
            main()
            mock_handler.assert_called_once()

    def test_main_with_clean_subcommand(self):
        """Should route to handle_clean"""
        with (
            patch.object(sys, "argv", ["cicada", "clean", "-f"]),
            patch("cicada.cli.handle_clean") as mock_handler,
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
            patch("cicada.mcp_entry.handle_install") as mock_handler,
        ):
            main()
            mock_handler.assert_called_once()
            args = mock_handler.call_args[0][0]
            assert args.repo == "."

    def test_main_with_relative_path_calls_install(self):
        """Should route to install command when path starts with './'"""
        with (
            patch.object(sys, "argv", ["cicada", "./some/path"]),
            patch("cicada.mcp_entry.handle_install") as mock_handler,
        ):
            main()
            mock_handler.assert_called_once()
            args = mock_handler.call_args[0][0]
            assert args.repo == "./some/path"

    def test_main_with_absolute_path_calls_install(self):
        """Should route to install command when path starts with '/'"""
        with (
            patch.object(sys, "argv", ["cicada", "/absolute/path"]),
            patch("cicada.mcp_entry.handle_install") as mock_handler,
        ):
            main()
            mock_handler.assert_called_once()
            args = mock_handler.call_args[0][0]
            assert args.repo == "/absolute/path"

    def test_main_with_parent_directory_calls_install(self):
        """Should route to install command when path is '..'"""
        with (
            patch.object(sys, "argv", ["cicada", ".."]),
            patch("cicada.mcp_entry.handle_install") as mock_handler,
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

    def test_requires_nlp_or_rag_for_fast(self, mock_elixir_repo, capsys):
        """Should error if --fast used without --rag"""
        args = MagicMock(fast=True, max=False, nlp=False, rag=False)

        with (
            patch("pathlib.Path.cwd", return_value=mock_elixir_repo),
            pytest.raises(SystemExit) as exc_info,
        ):
            handle_editor_setup(args, "claude")

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "--fast or --max requires --rag" in captured.err

    def test_requires_nlp_or_rag_for_max(self, mock_elixir_repo, capsys):
        """Should error if --max used without --rag"""
        args = MagicMock(fast=False, max=True, nlp=False, rag=False)

        with (
            patch("pathlib.Path.cwd", return_value=mock_elixir_repo),
            pytest.raises(SystemExit) as exc_info,
        ):
            handle_editor_setup(args, "claude")

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "--fast or --max requires --rag" in captured.err

    def test_cannot_specify_both_nlp_and_rag(self, mock_elixir_repo, capsys):
        """Should error if both --nlp and --rag specified"""
        args = MagicMock(fast=False, max=False, nlp=True, rag=True)

        with (
            patch("pathlib.Path.cwd", return_value=mock_elixir_repo),
            pytest.raises(SystemExit) as exc_info,
        ):
            handle_editor_setup(args, "claude")

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Cannot specify both --nlp and --rag" in captured.err

    def test_requires_elixir_project(self, tmp_path, capsys):
        """Should error if not an Elixir project"""
        args = MagicMock(fast=False, max=False, nlp=False, rag=False)

        with (
            patch("pathlib.Path.cwd", return_value=tmp_path),
            pytest.raises(SystemExit) as exc_info,
        ):
            handle_editor_setup(args, "claude")

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "does not appear to be an Elixir project" in captured.err

    def test_nlp_flag_sets_lemminflect(self, mock_elixir_repo):
        """--nlp should set method to lemminflect"""
        args = MagicMock(fast=False, max=False, nlp=True, rag=False)

        with (
            patch("pathlib.Path.cwd", return_value=mock_elixir_repo),
            patch("cicada.setup.setup") as mock_setup,
        ):
            handle_editor_setup(args, "claude")

            # Check that setup was called with lemminflect
            call_kwargs = mock_setup.call_args[1]
            assert call_kwargs["keyword_method"] == "lemminflect"
            assert call_kwargs["keyword_tier"] == "regular"

    def test_rag_flag_sets_bert(self, mock_elixir_repo):
        """--rag should set method to bert"""
        args = MagicMock(fast=False, max=False, nlp=False, rag=True)

        with (
            patch("pathlib.Path.cwd", return_value=mock_elixir_repo),
            patch("cicada.setup.setup") as mock_setup,
        ):
            handle_editor_setup(args, "claude")

            # Check that setup was called with bert
            call_kwargs = mock_setup.call_args[1]
            assert call_kwargs["keyword_method"] == "bert"
            assert call_kwargs["keyword_tier"] == "regular"

    def test_rag_with_fast_tier(self, mock_elixir_repo):
        """--rag --fast should set bert with fast tier"""
        args = MagicMock(fast=True, max=False, nlp=False, rag=True)

        with (
            patch("pathlib.Path.cwd", return_value=mock_elixir_repo),
            patch("cicada.setup.setup") as mock_setup,
        ):
            handle_editor_setup(args, "claude")

            call_kwargs = mock_setup.call_args[1]
            assert call_kwargs["keyword_method"] == "bert"
            assert call_kwargs["keyword_tier"] == "fast"

    def test_rag_with_max_tier(self, mock_elixir_repo):
        """--rag --max should set bert with max tier"""
        args = MagicMock(fast=False, max=True, nlp=False, rag=True)

        with (
            patch("pathlib.Path.cwd", return_value=mock_elixir_repo),
            patch("cicada.setup.setup") as mock_setup,
        ):
            handle_editor_setup(args, "claude")

            call_kwargs = mock_setup.call_args[1]
            assert call_kwargs["keyword_method"] == "bert"
            assert call_kwargs["keyword_tier"] == "max"

    def test_no_flags_with_existing_index(self, mock_elixir_repo, tmp_path):
        """Should read existing config when no flags and index exists"""
        args = MagicMock(fast=False, max=False, nlp=False, rag=False)

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
                return_value={"keyword_extraction": {"method": "bert", "tier": "fast"}},
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
            assert call_kwargs["keyword_method"] == "bert"
            assert call_kwargs["keyword_tier"] == "fast"
            assert call_kwargs["index_exists"] is True

    def test_setup_exception_exits(self, mock_elixir_repo, capsys):
        """Should exit with error if setup fails"""
        args = MagicMock(fast=False, max=False, nlp=True, rag=False)

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

    def test_requires_nlp_or_rag_for_fast(self, capsys):
        """Should error if --fast used without --rag"""
        args = MagicMock(fast=True, max=False, nlp=False, rag=False, repo=".")

        with patch("cicada.version_check.check_for_updates"), pytest.raises(SystemExit) as exc_info:
            handle_index(args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "--fast or --max requires --rag" in captured.err

    def test_cannot_specify_both_nlp_and_rag(self, capsys):
        """Should error if both --nlp and --rag specified"""
        args = MagicMock(fast=False, max=False, nlp=True, rag=True, repo=".")

        with patch("cicada.version_check.check_for_updates"), pytest.raises(SystemExit) as exc_info:
            handle_index(args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Cannot specify both --nlp and --rag" in captured.err

    def test_nlp_flag_creates_config(self, mock_repo):
        """--nlp should create config with lemminflect"""
        args = MagicMock(
            fast=False, max=False, nlp=True, rag=False, repo=str(mock_repo), test=False
        )

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

            # Verify config was created with lemminflect
            mock_create_config.assert_called()
            call_args = mock_create_config.call_args[0]
            assert call_args[2] == "lemminflect"  # keyword_method
            assert call_args[3] == "regular"  # keyword_tier

    def test_rag_flag_creates_config_with_bert(self, mock_repo):
        """--rag should create config with bert"""
        args = MagicMock(
            fast=False, max=False, nlp=False, rag=True, repo=str(mock_repo), test=False
        )

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

            # Verify config was created with bert
            mock_create_config.assert_called()
            call_args = mock_create_config.call_args[0]
            assert call_args[2] == "bert"
            assert call_args[3] == "regular"

    def test_no_flags_no_config_shows_error(self, mock_repo, capsys):
        """Should show error message when no flags and no config"""
        args = MagicMock(
            fast=False, max=False, nlp=False, rag=False, repo=str(mock_repo), test=False
        )

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
        assert "No keyword extraction method specified" in captured.err
        assert "--nlp" in captured.err
        assert "--rag" in captured.err

    def test_changing_method_exits_with_error(self, mock_repo, capsys):
        """Changing extraction method should exit with error and suggest cicada clean"""
        args = MagicMock(
            fast=False, max=False, nlp=False, rag=True, repo=str(mock_repo), test=False
        )

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
                return_value={"keyword_extraction": {"method": "lemminflect", "tier": "regular"}},
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
        assert "Cannot change extraction method" in captured.err
        assert "lemminflect to bert" in captured.err
        assert "cicada clean" in captured.err

    def test_changing_tier_exits_with_error(self, mock_repo, capsys):
        """Changing tier should exit with error and suggest cicada clean"""
        args = MagicMock(fast=False, max=True, nlp=False, rag=True, repo=str(mock_repo), test=False)

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
                return_value={"keyword_extraction": {"method": "bert", "tier": "fast"}},
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
        assert "Cannot change tier from fast to max" in captured.err
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
            patch("cicada.dead_code_analyzer.DeadCodeAnalyzer") as mock_analyzer_class,
            patch("cicada.find_dead_code.filter_by_confidence") as mock_filter,
            patch(
                "cicada.find_dead_code.format_markdown", return_value="# Dead Code"
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
            patch("cicada.dead_code_analyzer.DeadCodeAnalyzer") as mock_analyzer_class,
            patch("cicada.find_dead_code.filter_by_confidence") as mock_filter,
            patch("cicada.find_dead_code.format_json", return_value="{}") as mock_format_json,
            patch("cicada.find_dead_code.format_markdown") as mock_format_md,
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
