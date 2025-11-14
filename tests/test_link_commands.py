"""
Tests for link/unlink commands in cicada/commands.py
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from cicada.commands import handle_link, handle_unlink


@pytest.fixture
def create_repo_with_index(tmp_path, mock_home_dir):
    """Helper fixture that returns a function to create a repository with an index"""
    from cicada.utils.storage import create_storage_dir

    def _create_repo(name: str, index_content: str = '{"modules": {}}') -> Path:
        """Create a repository with an index file"""
        repo = tmp_path / name
        repo.mkdir()
        storage = create_storage_dir(repo)
        (storage / "index.json").write_text(index_content)
        return repo

    return _create_repo


@pytest.fixture
def create_repo(tmp_path):
    """Helper fixture that returns a function to create an empty repository"""

    def _create_repo(name: str) -> Path:
        """Create an empty repository"""
        repo = tmp_path / name
        repo.mkdir()
        return repo

    return _create_repo


@pytest.fixture
def make_args():
    """Helper fixture that returns a function to create Mock args"""

    def _make_args(**kwargs) -> Mock:
        """Create Mock args with specified attributes"""
        args = Mock()
        for key, value in kwargs.items():
            setattr(args, key, str(value))
        return args

    return _make_args


class TestHandleLink:
    """Tests for handle_link function"""

    @pytest.fixture
    def setup_repos(self, create_repo_with_index, create_repo):
        """Setup source and target repositories"""
        source_repo = create_repo_with_index("source_repo")
        target_repo = create_repo("target_repo")
        return source_repo, target_repo

    def test_link_success(self, setup_repos, make_args, capsys):
        """Should successfully link repositories"""
        source_repo, target_repo = setup_repos
        args = make_args(target=target_repo, source=source_repo)

        handle_link(args)

        captured = capsys.readouterr()
        assert "✓ Successfully linked" in captured.out
        assert str(target_repo) in captured.out
        assert str(source_repo) in captured.out

    def test_link_fails_source_not_indexed(self, create_repo, make_args, capsys):
        """Should fail when source is not indexed"""
        source_repo = create_repo("source_repo")
        target_repo = create_repo("target_repo")
        args = make_args(target=target_repo, source=source_repo)

        with pytest.raises(SystemExit) as exc_info:
            handle_link(args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "not indexed" in captured.err

    def test_link_fails_source_not_exists(self, tmp_path, create_repo, make_args, capsys):
        """Should fail when source doesn't exist"""
        source_repo = tmp_path / "nonexistent_source"
        target_repo = create_repo("target_repo")
        args = make_args(target=target_repo, source=source_repo)

        with pytest.raises(SystemExit) as exc_info:
            handle_link(args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err

    def test_link_fails_target_not_exists(
        self, tmp_path, create_repo_with_index, make_args, capsys
    ):
        """Should fail when target doesn't exist"""
        source_repo = create_repo_with_index("source_repo")
        target_repo = tmp_path / "nonexistent_target"
        args = make_args(target=target_repo, source=source_repo)

        with pytest.raises(SystemExit) as exc_info:
            handle_link(args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err

    def test_link_fails_already_linked(self, setup_repos, make_args, capsys):
        """Should fail when target is already linked"""
        from cicada.utils.storage import create_link

        source_repo, target_repo = setup_repos
        create_link(target_repo, source_repo)

        args = make_args(target=target_repo, source=source_repo)

        with pytest.raises(SystemExit) as exc_info:
            handle_link(args)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "already linked" in captured.err

    def test_link_resolves_relative_paths(self, setup_repos, make_args, capsys):
        """Should resolve relative paths to absolute paths"""
        source_repo, target_repo = setup_repos
        args = make_args(target=target_repo, source=source_repo)

        handle_link(args)

        captured = capsys.readouterr()
        assert "✓ Successfully linked" in captured.out

    def test_link_handles_unexpected_error(self, setup_repos, make_args, capsys):
        """Should handle unexpected errors gracefully"""
        source_repo, target_repo = setup_repos
        args = make_args(target=target_repo, source=source_repo)

        with patch(
            "cicada.utils.storage.create_link", side_effect=RuntimeError("Unexpected error")
        ):
            with pytest.raises(SystemExit) as exc_info:
                handle_link(args)

            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "Unexpected error" in captured.err

    def test_link_chained_links(self, create_repo_with_index, create_repo, make_args, capsys):
        """Should support chained links: C → B → A"""
        from cicada.utils.storage import create_link, get_index_path

        # Create repo A with an index (the source of truth)
        repo_a = create_repo_with_index("repo_a", '{"modules": {"test": "data"}}')

        # Create repo B and link it to A
        repo_b = create_repo("repo_b")
        create_link(repo_b, repo_a)

        # Create repo C and link it to B (which is already linked to A)
        repo_c = create_repo("repo_c")
        args = make_args(target=repo_c, source=repo_b)

        handle_link(args)

        captured = capsys.readouterr()
        assert "✓ Successfully linked" in captured.out

        # Verify that C can access A's index through the chain
        index_path_c = get_index_path(repo_c)
        assert index_path_c.exists()
        assert index_path_c.read_text() == '{"modules": {"test": "data"}}'

        # Verify that both B and C resolve to A's storage
        index_path_b = get_index_path(repo_b)
        assert index_path_b == index_path_c


class TestHandleUnlink:
    """Tests for handle_unlink function"""

    @pytest.fixture
    def setup_linked_repo(self, create_repo_with_index, create_repo):
        """Setup a linked repository"""
        from cicada.utils.storage import create_link

        source_repo = create_repo_with_index("source_repo")
        target_repo = create_repo("target_repo")
        create_link(target_repo, source_repo)
        return source_repo, target_repo

    def test_unlink_success(self, setup_linked_repo, make_args, capsys):
        """Should successfully unlink repository"""
        source_repo, target_repo = setup_linked_repo
        args = make_args(repo=target_repo)

        handle_unlink(args)

        captured = capsys.readouterr()
        assert "✓ Successfully unlinked" in captured.out
        assert str(target_repo) in captured.out
        assert str(source_repo) in captured.out

    def test_unlink_not_linked(self, create_repo, make_args, capsys):
        """Should handle repository that is not linked"""
        repo_path = create_repo("unlinked_repo")
        args = make_args(repo=repo_path)

        with pytest.raises(SystemExit) as exc_info:
            handle_unlink(args)

        assert exc_info.value.code == 0  # Exit 0 for "nothing to do"
        captured = capsys.readouterr()
        assert "not linked" in captured.out
        assert "Nothing to do" in captured.out

    def test_unlink_resolves_relative_paths(self, setup_linked_repo, make_args, capsys):
        """Should resolve relative paths to absolute paths"""
        source_repo, target_repo = setup_linked_repo
        args = make_args(repo=target_repo)

        handle_unlink(args)

        captured = capsys.readouterr()
        assert "✓ Successfully unlinked" in captured.out

    def test_unlink_handles_remove_failure(self, setup_linked_repo, make_args, capsys):
        """Should handle failure to remove link file"""
        source_repo, target_repo = setup_linked_repo
        args = make_args(repo=target_repo)

        with patch("cicada.utils.storage.remove_link", return_value=False):
            with pytest.raises(SystemExit) as exc_info:
                handle_unlink(args)

            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "Failed to remove link" in captured.out

    def test_unlink_handles_unexpected_error(self, setup_linked_repo, make_args, capsys):
        """Should handle unexpected errors gracefully"""
        source_repo, target_repo = setup_linked_repo
        args = make_args(repo=target_repo)

        with patch("cicada.utils.storage.is_linked", side_effect=RuntimeError("Unexpected error")):
            with pytest.raises(SystemExit) as exc_info:
                handle_unlink(args)

            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "Unexpected error" in captured.err

    def test_unlink_shows_instructions(self, setup_linked_repo, make_args, capsys):
        """Should show instructions after unlinking"""
        source_repo, target_repo = setup_linked_repo
        args = make_args(repo=target_repo)

        handle_unlink(args)

        captured = capsys.readouterr()
        assert "can now have its own index" in captured.out
        assert "cicada index" in captured.out
