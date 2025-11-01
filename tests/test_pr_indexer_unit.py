#!/usr/bin/env python
"""
Unit tests for the pr_indexer package.

Tests the PRIndexer class methods with proper mocking of external dependencies.

Author: Cursor(Auto)
"""

import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cicada.pr_indexer import PRIndexer


class TestPRIndexerInitialization:
    """Test PRIndexer initialization and validation."""

    def test_init_with_valid_git_repo(self, tmp_path):
        """Test initialization with a valid git repository."""
        # Create a fake git repo
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        with (
            patch("cicada.pr_indexer.indexer.GitHubAPIClient") as mock_api,
            patch("cicada.pr_indexer.indexer.PRIndexBuilder") as mock_builder,
            patch("cicada.pr_indexer.indexer.LineMapper") as mock_mapper,
        ):

            # Mock the API client methods
            mock_api_instance = Mock()
            mock_api_instance.validate_gh_cli.return_value = None
            mock_api_instance.get_repo_info.return_value = ("owner", "repo")
            mock_api.return_value = mock_api_instance

            indexer = PRIndexer(str(tmp_path))

            assert indexer.repo_path == tmp_path.resolve()
            assert indexer.repo_owner == "owner"
            assert indexer.repo_name == "repo"
            mock_api_instance.validate_gh_cli.assert_called_once()

    def test_init_without_git_repo_raises_error(self, tmp_path):
        """Test that initialization fails when path is not a git repo."""
        # Don't create .git directory

        with pytest.raises(ValueError, match="Not a git repository"):
            PRIndexer(str(tmp_path))

    def test_init_initializes_components(self, tmp_path):
        """Test that all components are properly initialized."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        with (
            patch("cicada.pr_indexer.indexer.GitHubAPIClient") as mock_api,
            patch("cicada.pr_indexer.indexer.PRIndexBuilder") as mock_builder,
            patch("cicada.pr_indexer.indexer.LineMapper") as mock_mapper,
        ):

            mock_api_instance = Mock()
            mock_api_instance.validate_gh_cli.return_value = None
            mock_api_instance.get_repo_info.return_value = ("owner", "repo")
            mock_api.return_value = mock_api_instance

            indexer = PRIndexer(str(tmp_path))

            # Verify all components were created
            assert indexer.api_client is not None
            assert indexer.index_builder is not None
            assert indexer.line_mapper is not None

            # Verify components were initialized with correct args
            assert mock_builder.called
            assert mock_mapper.called


class TestFetchAllPRs:
    """Test PR fetching functionality."""

    @pytest.fixture
    def mock_indexer(self, tmp_path):
        """Create a mock indexer for testing."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        with (
            patch("cicada.pr_indexer.indexer.GitHubAPIClient") as mock_api,
            patch("cicada.pr_indexer.indexer.PRIndexBuilder"),
            patch("cicada.pr_indexer.indexer.LineMapper"),
        ):

            mock_api_instance = Mock()
            mock_api_instance.validate_gh_cli.return_value = None
            mock_api_instance.get_repo_info.return_value = ("owner", "repo")
            mock_api.return_value = mock_api_instance

            indexer = PRIndexer(str(tmp_path))
            yield indexer

    def test_fetch_all_prs_success(self, mock_indexer):
        """Test successful PR fetching."""
        # Mock API responses - all 3 PRs in one batch (batch_size=10)
        mock_indexer.api_client.fetch_pr_list.return_value = [1, 2, 3]
        mock_indexer.api_client.fetch_prs_batch_graphql.return_value = [
            {"number": 1, "title": "PR 1"},
            {"number": 2, "title": "PR 2"},
            {"number": 3, "title": "PR 3"},
        ]

        prs = mock_indexer.fetch_all_prs()

        assert len(prs) == 3
        assert prs[0]["number"] == 1
        assert prs[1]["number"] == 2
        assert prs[2]["number"] == 3

    def test_fetch_all_prs_with_state_filter(self, mock_indexer):
        """Test fetching PRs with state filter."""
        mock_indexer.api_client.fetch_pr_list.return_value = [1]
        mock_indexer.api_client.fetch_prs_batch_graphql.return_value = [
            {"number": 1, "state": "merged"}
        ]

        prs = mock_indexer.fetch_all_prs(state="merged")

        mock_indexer.api_client.fetch_pr_list.assert_called_once_with(state="merged", limit=100000)

    def test_fetch_all_prs_batch_processing(self, mock_indexer):
        """Test that PRs are fetched in batches."""
        # Create 25 PRs (3 batches of 10)
        pr_numbers = list(range(1, 26))
        mock_indexer.api_client.fetch_pr_list.return_value = pr_numbers

        # Mock batch responses
        def batch_response(numbers):
            return [{"number": n} for n in numbers]

        mock_indexer.api_client.fetch_prs_batch_graphql.side_effect = [
            batch_response(pr_numbers[i : i + 10]) for i in range(0, 25, 10)
        ]

        prs = mock_indexer.fetch_all_prs()

        assert len(prs) == 25
        # Should have called batch fetch 3 times
        assert mock_indexer.api_client.fetch_prs_batch_graphql.call_count == 3

    def test_fetch_all_prs_keyboard_interrupt(self, mock_indexer):
        """Test handling of KeyboardInterrupt during fetching."""
        mock_indexer.api_client.fetch_pr_list.return_value = [1, 2, 3, 4, 5]

        # Simulate interrupt on second batch
        mock_indexer.api_client.fetch_prs_batch_graphql.side_effect = [
            [{"number": 1}],
            KeyboardInterrupt(),
        ]

        prs = mock_indexer.fetch_all_prs()

        # Should return partial results
        assert len(prs) == 1
        assert prs[0]["number"] == 1

    def test_fetch_all_prs_runtime_error(self, mock_indexer):
        """Test handling of RuntimeError."""
        mock_indexer.api_client.fetch_pr_list.side_effect = RuntimeError("API error")

        with pytest.raises(RuntimeError, match="Failed to fetch PRs"):
            mock_indexer.fetch_all_prs()


class TestIncrementalUpdate:
    """Test incremental update functionality."""

    @pytest.fixture
    def mock_indexer(self, tmp_path):
        """Create a mock indexer for testing."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        with (
            patch("cicada.pr_indexer.indexer.GitHubAPIClient") as mock_api,
            patch("cicada.pr_indexer.indexer.PRIndexBuilder"),
            patch("cicada.pr_indexer.indexer.LineMapper"),
        ):

            mock_api_instance = Mock()
            mock_api_instance.validate_gh_cli.return_value = None
            mock_api_instance.get_repo_info.return_value = ("owner", "repo")
            mock_api.return_value = mock_api_instance

            indexer = PRIndexer(str(tmp_path))
            yield indexer

    def test_incremental_update_with_empty_index(self, mock_indexer):
        """Test incremental update falls back to full fetch when index is empty."""
        existing_index = {"prs": {}}

        with patch.object(mock_indexer, "fetch_all_prs", return_value=[]) as mock_fetch:
            result = mock_indexer.incremental_update(existing_index)

            mock_fetch.assert_called_once()
            assert result == []

    def test_incremental_update_fetches_newer_prs(self, mock_indexer):
        """Test that newer PRs are fetched."""
        existing_index = {
            "prs": {
                "10": {"number": 10},
                "15": {"number": 15},
                "20": {"number": 20},
            }
        }

        # Mock API to return newer and older PRs
        mock_indexer.api_client.get_total_pr_count.return_value = 25
        mock_indexer.api_client.fetch_pr_list.side_effect = [
            [
                25,
                24,
                23,
                22,
                21,
                20,
            ],  # Newer PRs call (6 PRs, but 20 is already in index)
            [10, 9, 8, 7, 6],  # Older PRs call (5 PRs, but 10 is already in index)
        ]
        # Mock batch fetching - first call for newer, second for older
        mock_indexer.api_client.fetch_prs_batch_graphql.side_effect = [
            [
                {"number": 25},
                {"number": 24},
                {"number": 23},
                {"number": 22},
                {"number": 21},
            ],  # Newer PRs
            [{"number": 9}, {"number": 8}, {"number": 7}, {"number": 6}],  # Older PRs
        ]

        result = mock_indexer.incremental_update(existing_index)

        # Should have 5 newer + 4 older = 9 new PRs
        assert len(result) == 9
        assert result[0]["number"] == 25

    def test_incremental_update_fetches_older_prs(self, mock_indexer):
        """Test that older PRs are fetched."""
        existing_index = {
            "prs": {
                "10": {"number": 10},
                "15": {"number": 15},
            }
        }

        mock_indexer.api_client.get_total_pr_count.return_value = 15
        mock_indexer.api_client.fetch_pr_list.side_effect = [
            [15, 14, 13, 12, 11, 10],  # Newer PRs (none newer than max=15)
            [9, 8, 7, 6, 5, 4, 3, 2, 1],  # All PRs for older check
        ]
        mock_indexer.api_client.fetch_prs_batch_graphql.return_value = [
            {"number": 9},
            {"number": 8},
            {"number": 7},
        ]

        result = mock_indexer.incremental_update(existing_index)

        # Should fetch older PRs (< 10)
        assert len(result) == 3

    def test_incremental_update_no_new_prs(self, mock_indexer):
        """Test when there are no new PRs to fetch."""
        existing_index = {
            "prs": {
                "1": {"number": 1},
                "10": {"number": 10},
            }
        }

        mock_indexer.api_client.get_total_pr_count.return_value = 10
        mock_indexer.api_client.fetch_pr_list.side_effect = [
            [10, 9, 8, 7, 6, 5, 4, 3, 2, 1],  # No newer PRs
            [],  # min_pr is 1, so no older PRs
        ]

        result = mock_indexer.incremental_update(existing_index)

        assert result == []

    def test_incremental_update_bidirectional_fetch(self, mock_indexer):
        """Test fetching both newer and older PRs."""
        existing_index = {
            "prs": {
                "5": {"number": 5},
                "6": {"number": 6},
                "7": {"number": 7},
            }
        }

        mock_indexer.api_client.get_total_pr_count.return_value = 12
        mock_indexer.api_client.fetch_pr_list.side_effect = [
            [12, 11, 10, 9, 8, 7],  # Newer call
            [7, 6, 5, 4, 3, 2, 1],  # All PRs for older check
        ]

        # Mock batch fetching for newer and older PRs
        mock_indexer.api_client.fetch_prs_batch_graphql.side_effect = [
            [{"number": 12}, {"number": 11}],  # Newer batch
            [{"number": 4}, {"number": 3}],  # Older batch
        ]

        result = mock_indexer.incremental_update(existing_index)

        # Should have both newer (12, 11) and older (4, 3)
        assert len(result) == 4


class TestIndexRepository:
    """Test index_repository method."""

    @pytest.fixture
    def mock_indexer(self, tmp_path):
        """Create a mock indexer for testing."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        with (
            patch("cicada.pr_indexer.indexer.GitHubAPIClient") as mock_api,
            patch("cicada.pr_indexer.indexer.PRIndexBuilder") as mock_builder,
            patch("cicada.pr_indexer.indexer.LineMapper") as mock_mapper,
        ):

            mock_api_instance = Mock()
            mock_api_instance.validate_gh_cli.return_value = None
            mock_api_instance.get_repo_info.return_value = ("owner", "repo")
            mock_api.return_value = mock_api_instance

            mock_builder_instance = Mock()
            mock_builder.return_value = mock_builder_instance

            mock_mapper_instance = Mock()
            mock_mapper.return_value = mock_mapper_instance

            indexer = PRIndexer(str(tmp_path))
            yield indexer

    def test_index_repository_incremental_with_existing_index(self, mock_indexer, tmp_path):
        """Test incremental indexing with existing index."""
        output_path = tmp_path / ".cicada" / "pr_index.json"
        output_path.parent.mkdir(exist_ok=True)

        existing_index = {
            "prs": {"1": {"number": 1}},
            "metadata": {"last_pr_number": 1},
        }
        output_path.write_text(json.dumps(existing_index))

        # Mock the methods
        mock_indexer.index_builder.load_existing_index.return_value = existing_index
        mock_indexer.incremental_update = Mock(return_value=[{"number": 2}])
        mock_indexer.line_mapper.map_all_comment_lines = Mock()
        mock_indexer.index_builder.merge_indexes.return_value = {"prs": {"1": {}, "2": {}}}
        mock_indexer.index_builder.save_index = Mock()

        result = mock_indexer.index_repository(str(output_path), incremental=True)

        mock_indexer.incremental_update.assert_called_once()
        mock_indexer.line_mapper.map_all_comment_lines.assert_called_once()
        mock_indexer.index_builder.merge_indexes.assert_called_once()
        mock_indexer.index_builder.save_index.assert_called_once()

    def test_index_repository_incremental_no_new_prs(self, mock_indexer, tmp_path):
        """Test incremental indexing when no new PRs are found."""
        output_path = tmp_path / ".cicada" / "pr_index.json"
        existing_index = {"prs": {"1": {"number": 1}}}

        mock_indexer.index_builder.load_existing_index.return_value = existing_index
        mock_indexer.incremental_update = Mock(return_value=[])

        result = mock_indexer.index_repository(str(output_path), incremental=True)

        assert result == existing_index

    def test_index_repository_incremental_no_existing_index(self, mock_indexer, tmp_path):
        """Test incremental mode falls back to full index when no existing index."""
        output_path = tmp_path / ".cicada" / "pr_index.json"

        mock_indexer.index_builder.load_existing_index.return_value = None
        mock_indexer._perform_full_index = Mock(return_value={"prs": {}})

        result = mock_indexer.index_repository(str(output_path), incremental=True)

        mock_indexer._perform_full_index.assert_called_once()

    def test_index_repository_clean_rebuild(self, mock_indexer, tmp_path):
        """Test clean rebuild (not incremental)."""
        output_path = tmp_path / ".cicada" / "pr_index.json"

        mock_indexer.index_builder.load_existing_index.return_value = None
        mock_indexer._perform_full_index = Mock(return_value={"prs": {}})

        result = mock_indexer.index_repository(str(output_path), incremental=False)

        mock_indexer._perform_full_index.assert_called_once()


class TestPerformFullIndex:
    """Test _perform_full_index method."""

    @pytest.fixture
    def mock_indexer(self, tmp_path):
        """Create a mock indexer for testing."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        with (
            patch("cicada.pr_indexer.indexer.GitHubAPIClient") as mock_api,
            patch("cicada.pr_indexer.indexer.PRIndexBuilder") as mock_builder,
            patch("cicada.pr_indexer.indexer.LineMapper") as mock_mapper,
        ):

            mock_api_instance = Mock()
            mock_api_instance.validate_gh_cli.return_value = None
            mock_api_instance.get_repo_info.return_value = ("owner", "repo")
            mock_api.return_value = mock_api_instance

            mock_builder_instance = Mock()
            mock_builder.return_value = mock_builder_instance

            indexer = PRIndexer(str(tmp_path))
            yield indexer

    def test_perform_full_index_complete_fetch(self, mock_indexer):
        """Test full index with complete fetch."""
        mock_indexer.api_client.get_total_pr_count.return_value = 10
        mock_indexer.fetch_all_prs = Mock(return_value=[{"number": i} for i in range(1, 11)])
        mock_indexer.line_mapper.map_all_comment_lines = Mock()
        mock_indexer.index_builder.build_index.return_value = {"prs": {}}

        result = mock_indexer._perform_full_index("output.json", None)

        assert result == {"prs": {}}
        mock_indexer.index_builder.build_index.assert_called_once()

    def test_perform_full_index_partial_fetch(self, mock_indexer):
        """Test full index with partial/interrupted fetch."""
        mock_indexer.api_client.get_total_pr_count.return_value = 100
        mock_indexer.fetch_all_prs = Mock(
            return_value=[{"number": i} for i in range(1, 51)]  # Only 50 of 100
        )
        mock_indexer.line_mapper.map_all_comment_lines = Mock()
        mock_indexer.index_builder.build_index.return_value = {
            "prs": {},
            "metadata": {},
        }

        result = mock_indexer._perform_full_index("output.json", None)

        # Should build with preserve_last_pr=0
        mock_indexer.index_builder.build_index.assert_called_once()
        call_args = mock_indexer.index_builder.build_index.call_args
        assert call_args[1]["preserve_last_pr"] == 0

    def test_perform_full_index_partial_with_existing_index(self, mock_indexer):
        """Test partial fetch merges with existing index."""
        existing_index = {"prs": {"1": {"number": 1}}}

        mock_indexer.api_client.get_total_pr_count.return_value = 100
        mock_indexer.fetch_all_prs = Mock(return_value=[{"number": 50}])  # Partial
        mock_indexer.line_mapper.map_all_comment_lines = Mock()
        mock_indexer.index_builder.build_index.return_value = {"prs": {}}
        mock_indexer.index_builder.merge_partial_clean.return_value = {"prs": {"merged": True}}

        result = mock_indexer._perform_full_index("output.json", existing_index)

        mock_indexer.index_builder.merge_partial_clean.assert_called_once()
        assert result == {"prs": {"merged": True}}


class TestCLIMain:
    """Test CLI entry point."""

    def test_main_with_defaults(self, tmp_path):
        """Test main function with default arguments."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        with (
            patch("sys.argv", ["pr_indexer.py", str(tmp_path)]),
            patch("cicada.pr_indexer.cli.PRIndexer") as mock_indexer_class,
            patch("cicada.version_check.check_for_updates"),
        ):

            mock_indexer = Mock()
            mock_indexer.index_repository.return_value = None
            mock_indexer_class.return_value = mock_indexer

            from cicada.pr_indexer import main

            main()

            # Should call with incremental=True (default)
            mock_indexer.index_repository.assert_called_once_with(
                output_path=".cicada/pr_index.json", incremental=True
            )

    def test_main_with_clean_flag(self, tmp_path):
        """Test main function with --clean flag."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        with (
            patch("sys.argv", ["pr_indexer.py", str(tmp_path), "--clean"]),
            patch("cicada.pr_indexer.cli.PRIndexer") as mock_indexer_class,
            patch("cicada.version_check.check_for_updates"),
        ):

            mock_indexer = Mock()
            mock_indexer.index_repository.return_value = None
            mock_indexer_class.return_value = mock_indexer

            from cicada.pr_indexer import main

            main()

            # Should call with incremental=False
            mock_indexer.index_repository.assert_called_once_with(
                output_path=".cicada/pr_index.json", incremental=False
            )

    def test_main_keyboard_interrupt(self, tmp_path):
        """Test handling of KeyboardInterrupt."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        with (
            patch("sys.argv", ["pr_indexer.py", str(tmp_path)]),
            patch("cicada.pr_indexer.cli.PRIndexer") as mock_indexer_class,
            patch("cicada.version_check.check_for_updates"),
        ):

            mock_indexer = Mock()
            mock_indexer.index_repository.side_effect = KeyboardInterrupt()
            mock_indexer_class.return_value = mock_indexer

            from cicada.pr_indexer import main

            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 130

    def test_main_error_handling(self, tmp_path):
        """Test error handling in main."""
        with (
            patch("sys.argv", ["pr_indexer.py", str(tmp_path)]),
            patch("cicada.pr_indexer.cli.PRIndexer") as mock_indexer_class,
            patch("cicada.version_check.check_for_updates"),
        ):

            mock_indexer_class.side_effect = Exception("Test error")

            from cicada.pr_indexer import main

            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
