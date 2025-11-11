"""
Tests for link/unlink commands in cicada/commands.py
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from cicada.commands import handle_link, handle_unlink


class TestHandleLink:
    """Tests for handle_link function"""

    @pytest.fixture
    def setup_repos(self, tmp_path, mock_home_dir):
        """Setup source and target repositories"""
        from cicada.utils.storage import create_storage_dir

        # Create source repository with index
        source_repo = tmp_path / "source_repo"
        source_repo.mkdir()

        # Create target repository
        target_repo = tmp_path / "target_repo"
        target_repo.mkdir()

        # Create storage and index for source
        source_storage = create_storage_dir(source_repo)
        (source_storage / "index.json").write_text('{"modules": {}}')

        return source_repo, target_repo

    def test_link_success(self, setup_repos, capsys):
        """Should successfully link repositories"""
        source_repo, target_repo = setup_repos

        args = Mock()
        args.target = str(target_repo)
        args.source = str(source_repo)

        handle_link(args)

        captured = capsys.readouterr()
        assert "✓ Successfully linked" in captured.out
        assert str(target_repo) in captured.out
        assert str(source_repo) in captured.out

    def test_link_fails_source_not_indexed(self, tmp_path, mock_home_dir, capsys):
        """Should fail when source is not indexed"""
        source_repo = tmp_path / "source_repo"
        source_repo.mkdir()

        target_repo = tmp_path / "target_repo"
        target_repo.mkdir()

        args = Mock()
        args.target = str(target_repo)
        args.source = str(source_repo)

        with pytest.raises(SystemExit) as exc_info:
            handle_link(args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "not indexed" in captured.err

    def test_link_fails_source_not_exists(self, tmp_path, mock_home_dir, capsys):
        """Should fail when source doesn't exist"""
        source_repo = tmp_path / "nonexistent_source"

        target_repo = tmp_path / "target_repo"
        target_repo.mkdir()

        args = Mock()
        args.target = str(target_repo)
        args.source = str(source_repo)

        with pytest.raises(SystemExit) as exc_info:
            handle_link(args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err

    def test_link_fails_target_not_exists(self, tmp_path, mock_home_dir, capsys):
        """Should fail when target doesn't exist"""
        from cicada.utils.storage import create_storage_dir

        source_repo = tmp_path / "source_repo"
        source_repo.mkdir()

        # Create index for source
        source_storage = create_storage_dir(source_repo)
        (source_storage / "index.json").write_text('{"modules": {}}')

        target_repo = tmp_path / "nonexistent_target"

        args = Mock()
        args.target = str(target_repo)
        args.source = str(source_repo)

        with pytest.raises(SystemExit) as exc_info:
            handle_link(args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err

    def test_link_fails_already_linked(self, setup_repos, capsys):
        """Should fail when target is already linked"""
        from cicada.utils.storage import create_link

        source_repo, target_repo = setup_repos

        # Create initial link
        create_link(target_repo, source_repo)

        # Try to link again
        args = Mock()
        args.target = str(target_repo)
        args.source = str(source_repo)

        with pytest.raises(SystemExit) as exc_info:
            handle_link(args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "already linked" in captured.err

    def test_link_resolves_relative_paths(self, setup_repos, capsys):
        """Should resolve relative paths to absolute paths"""
        source_repo, target_repo = setup_repos

        args = Mock()
        args.target = str(target_repo)
        args.source = str(source_repo)

        handle_link(args)

        # Should succeed without errors
        captured = capsys.readouterr()
        assert "✓ Successfully linked" in captured.out

    def test_link_handles_unexpected_error(self, setup_repos, capsys):
        """Should handle unexpected errors gracefully"""
        source_repo, target_repo = setup_repos

        args = Mock()
        args.target = str(target_repo)
        args.source = str(source_repo)

        with patch(
            "cicada.utils.storage.create_link", side_effect=RuntimeError("Unexpected error")
        ):
            with pytest.raises(SystemExit) as exc_info:
                handle_link(args)

            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "Unexpected error" in captured.err


class TestHandleUnlink:
    """Tests for handle_unlink function"""

    @pytest.fixture
    def setup_linked_repo(self, tmp_path, mock_home_dir):
        """Setup a linked repository"""
        from cicada.utils.storage import create_link, create_storage_dir

        # Create source repository with index
        source_repo = tmp_path / "source_repo"
        source_repo.mkdir()

        # Create target repository
        target_repo = tmp_path / "target_repo"
        target_repo.mkdir()

        # Create storage and index for source
        source_storage = create_storage_dir(source_repo)
        (source_storage / "index.json").write_text('{"modules": {}}')

        # Create link
        create_link(target_repo, source_repo)

        return source_repo, target_repo

    def test_unlink_success(self, setup_linked_repo, capsys):
        """Should successfully unlink repository"""
        source_repo, target_repo = setup_linked_repo

        args = Mock()
        args.repo = str(target_repo)

        handle_unlink(args)

        captured = capsys.readouterr()
        assert "✓ Successfully unlinked" in captured.out
        assert str(target_repo) in captured.out
        assert str(source_repo) in captured.out

    def test_unlink_not_linked(self, tmp_path, mock_home_dir, capsys):
        """Should handle repository that is not linked"""
        repo_path = tmp_path / "unlinked_repo"
        repo_path.mkdir()

        args = Mock()
        args.repo = str(repo_path)

        with pytest.raises(SystemExit) as exc_info:
            handle_unlink(args)

        assert exc_info.value.code == 0  # Exit 0 for "nothing to do"
        captured = capsys.readouterr()
        assert "not linked" in captured.out
        assert "Nothing to do" in captured.out

    def test_unlink_resolves_relative_paths(self, setup_linked_repo, capsys):
        """Should resolve relative paths to absolute paths"""
        source_repo, target_repo = setup_linked_repo

        args = Mock()
        args.repo = str(target_repo)

        handle_unlink(args)

        # Should succeed without errors
        captured = capsys.readouterr()
        assert "✓ Successfully unlinked" in captured.out

    def test_unlink_handles_remove_failure(self, setup_linked_repo, capsys):
        """Should handle failure to remove link file"""
        source_repo, target_repo = setup_linked_repo

        args = Mock()
        args.repo = str(target_repo)

        with patch("cicada.utils.storage.remove_link", return_value=False):
            with pytest.raises(SystemExit) as exc_info:
                handle_unlink(args)

            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "Failed to remove link" in captured.out

    def test_unlink_handles_unexpected_error(self, setup_linked_repo, capsys):
        """Should handle unexpected errors gracefully"""
        source_repo, target_repo = setup_linked_repo

        args = Mock()
        args.repo = str(target_repo)

        with patch("cicada.utils.storage.is_linked", side_effect=RuntimeError("Unexpected error")):
            with pytest.raises(SystemExit) as exc_info:
                handle_unlink(args)

            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "Error" in captured.err

    def test_unlink_shows_instructions(self, setup_linked_repo, capsys):
        """Should show instructions after unlinking"""
        source_repo, target_repo = setup_linked_repo

        args = Mock()
        args.repo = str(target_repo)

        handle_unlink(args)

        captured = capsys.readouterr()
        assert "can now have its own index" in captured.out
        assert "cicada index" in captured.out
