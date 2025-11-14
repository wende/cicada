"""
Comprehensive tests for cicada/utils/storage.py
"""

from pathlib import Path

import pytest

from cicada.utils.storage import (
    create_link,
    create_storage_dir,
    get_config_path,
    get_hashes_path,
    get_index_path,
    get_link_info,
    get_link_path,
    get_pr_index_path,
    get_repo_hash,
    get_storage_dir,
    is_linked,
    remove_link,
    resolve_storage_dir,
)


class TestGetRepoHash:
    """Tests for get_repo_hash function"""

    def test_hash_generation_consistency(self, tmp_path):
        """Hash should be consistent for the same path"""
        repo_path = tmp_path / "my_repo"
        repo_path.mkdir()

        hash1 = get_repo_hash(repo_path)
        hash2 = get_repo_hash(repo_path)

        assert hash1 == hash2, "Hash should be consistent for same path"

    def test_hash_length(self, tmp_path):
        """Hash should be 16 characters (truncated SHA-256)"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        repo_hash = get_repo_hash(repo_path)

        assert len(repo_hash) == 16, "Hash should be 16 hex characters"
        assert all(c in "0123456789abcdef" for c in repo_hash), "Hash should be hex"

    def test_different_paths_different_hashes(self, tmp_path):
        """Different paths should generate different hashes"""
        repo1 = tmp_path / "repo1"
        repo2 = tmp_path / "repo2"
        repo1.mkdir()
        repo2.mkdir()

        hash1 = get_repo_hash(repo1)
        hash2 = get_repo_hash(repo2)

        assert hash1 != hash2, "Different paths should have different hashes"

    def test_path_resolution(self, tmp_path):
        """Relative and absolute paths should resolve to same hash"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Get hash with absolute path
        hash_absolute = get_repo_hash(repo_path.resolve())

        # Get hash with string path
        hash_string = get_repo_hash(str(repo_path.resolve()))

        assert hash_absolute == hash_string, "String and Path should produce same hash"

    def test_accepts_string_and_path(self, tmp_path):
        """Function should accept both str and Path types"""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        hash_from_path = get_repo_hash(repo_path)
        hash_from_str = get_repo_hash(str(repo_path))

        assert hash_from_path == hash_from_str, "Should accept both Path and str"

    def test_symlink_resolution(self, tmp_path):
        """Symlinks should resolve to target's hash"""
        real_repo = tmp_path / "real_repo"
        real_repo.mkdir()

        link_repo = tmp_path / "link_repo"
        link_repo.symlink_to(real_repo)

        hash_real = get_repo_hash(real_repo)
        hash_link = get_repo_hash(link_repo)

        assert hash_real == hash_link, "Symlink should resolve to same hash"


class TestGetStorageDir:
    """Tests for get_storage_dir function"""

    def test_storage_dir_structure(self, tmp_path):
        """Storage dir should follow ~/.cicada/projects/<hash> pattern"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        storage_dir = get_storage_dir(repo_path)

        # Should be under home directory
        assert str(storage_dir).startswith(str(Path.home())), "Should be under home dir"

        # Should contain .cicada/projects
        assert ".cicada" in str(storage_dir), "Should contain .cicada"
        assert "projects" in str(storage_dir), "Should contain projects"

    def test_storage_dir_uses_hash(self, tmp_path):
        """Storage dir should use repo hash as final component"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        repo_hash = get_repo_hash(repo_path)
        storage_dir = get_storage_dir(repo_path)

        assert storage_dir.name == repo_hash, "Dir name should be repo hash"

    def test_different_repos_different_dirs(self, tmp_path):
        """Different repos should get different storage directories"""
        repo1 = tmp_path / "repo1"
        repo2 = tmp_path / "repo2"
        repo1.mkdir()
        repo2.mkdir()

        storage1 = get_storage_dir(repo1)
        storage2 = get_storage_dir(repo2)

        assert storage1 != storage2, "Different repos should have different storage"


class TestCreateStorageDir:
    """Tests for create_storage_dir function"""

    def test_creates_directory(self, tmp_path, mock_home_dir):
        """Should create storage directory if it doesn't exist"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        storage_dir = create_storage_dir(repo_path)

        assert storage_dir.exists(), "Storage directory should be created"
        assert storage_dir.is_dir(), "Storage should be a directory"

    def test_creates_parent_directories(self, tmp_path, mock_home_dir):
        """Should create all parent directories if needed"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        storage_dir = create_storage_dir(repo_path)

        # Check that all parents exist
        assert (mock_home_dir / ".cicada").exists(), ".cicada should exist"
        assert (mock_home_dir / ".cicada" / "projects").exists(), "projects should exist"
        assert storage_dir.exists(), "Storage dir should exist"

    def test_idempotent_creation(self, tmp_path, mock_home_dir):
        """Creating storage dir multiple times should be safe"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        storage_dir1 = create_storage_dir(repo_path)
        storage_dir2 = create_storage_dir(repo_path)

        assert storage_dir1 == storage_dir2, "Should return same dir"
        assert storage_dir1.exists(), "Directory should still exist"

    def test_returns_path_object(self, tmp_path, mock_home_dir):
        """Should return a Path object"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        storage_dir = create_storage_dir(repo_path)

        assert isinstance(storage_dir, Path), "Should return Path object"


class TestPathGetters:
    """Tests for path getter functions"""

    @pytest.fixture
    def setup_paths(self, tmp_path, mock_home_dir):
        """Setup mock paths for testing"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        return repo_path

    def test_get_index_path(self, setup_paths):
        """Should return correct index.json path"""
        repo_path = setup_paths
        index_path = get_index_path(repo_path)

        assert index_path.name == "index.json", "Should end with index.json"
        assert str(index_path).endswith("index.json"), "Path should end correctly"

        # Should be under storage dir
        storage_dir = get_storage_dir(repo_path)
        assert index_path.parent == storage_dir, "Should be in storage dir"

    def test_get_config_path(self, setup_paths):
        """Should return correct config.yaml path"""
        repo_path = setup_paths
        config_path = get_config_path(repo_path)

        assert config_path.name == "config.yaml", "Should end with config.yaml"

        # Should be under storage dir
        storage_dir = get_storage_dir(repo_path)
        assert config_path.parent == storage_dir, "Should be in storage dir"

    def test_get_hashes_path(self, setup_paths):
        """Should return correct hashes.json path"""
        repo_path = setup_paths
        hashes_path = get_hashes_path(repo_path)

        assert hashes_path.name == "hashes.json", "Should end with hashes.json"

        # Should be under storage dir
        storage_dir = get_storage_dir(repo_path)
        assert hashes_path.parent == storage_dir, "Should be in storage dir"

    def test_get_pr_index_path(self, setup_paths):
        """Should return correct pr_index.json path"""
        repo_path = setup_paths
        pr_index_path = get_pr_index_path(repo_path)

        assert pr_index_path.name == "pr_index.json", "Should end with pr_index.json"

        # Should be under storage dir
        storage_dir = get_storage_dir(repo_path)
        assert pr_index_path.parent == storage_dir, "Should be in storage dir"

    def test_all_paths_under_same_storage(self, setup_paths):
        """All paths should be under the same storage directory"""
        repo_path = setup_paths

        storage_dir = get_storage_dir(repo_path)
        index_path = get_index_path(repo_path)
        config_path = get_config_path(repo_path)
        hashes_path = get_hashes_path(repo_path)
        pr_index_path = get_pr_index_path(repo_path)

        assert index_path.parent == storage_dir
        assert config_path.parent == storage_dir
        assert hashes_path.parent == storage_dir
        assert pr_index_path.parent == storage_dir


class TestEdgeCases:
    """Edge case tests for storage utilities"""

    def test_nonexistent_path_hash(self, tmp_path):
        """Should generate hash even for non-existent path"""
        nonexistent = tmp_path / "does_not_exist"

        # Should not raise an error
        repo_hash = get_repo_hash(nonexistent)

        assert isinstance(repo_hash, str), "Should return a hash string"
        assert len(repo_hash) == 16, "Hash should be correct length"

    def test_long_path_handling(self, tmp_path):
        """Should handle very long paths correctly"""
        # Create a deeply nested path
        deep_path = tmp_path / "a" / "b" / "c" / "d" / "e" / "f" / "g" / "h"
        deep_path.mkdir(parents=True)

        repo_hash = get_repo_hash(deep_path)
        storage_dir = get_storage_dir(deep_path)

        assert len(repo_hash) == 16, "Hash should be correct length"
        assert storage_dir.exists() or not storage_dir.exists(), "Should handle path"

    def test_path_with_spaces(self, tmp_path):
        """Should handle paths with spaces correctly"""
        repo_path = tmp_path / "my repo with spaces"
        repo_path.mkdir()

        repo_hash = get_repo_hash(repo_path)
        storage_dir = get_storage_dir(repo_path)

        assert len(repo_hash) == 16, "Hash should be correct length"
        assert "my repo with spaces" not in storage_dir.name, "Storage should use hash"

    def test_path_with_unicode(self, tmp_path):
        """Should handle paths with unicode characters"""
        repo_path = tmp_path / "репозиторий"  # Russian for "repository"
        repo_path.mkdir()

        repo_hash = get_repo_hash(repo_path)

        assert isinstance(repo_hash, str), "Should return hash string"
        assert len(repo_hash) == 16, "Hash should be correct length"


class TestLinkFunctionality:
    """Tests for repository linking functionality"""

    @pytest.fixture
    def setup_repos(self, tmp_path, mock_home_dir):
        """Setup source and target repositories for testing"""
        # Create source repository with an index
        source_repo = tmp_path / "source_repo"
        source_repo.mkdir()

        # Create target repository
        target_repo = tmp_path / "target_repo"
        target_repo.mkdir()

        # Create storage and index for source
        source_storage = create_storage_dir(source_repo)
        source_index = source_storage / "index.json"
        source_index.write_text('{"modules": {}}')

        return source_repo, target_repo

    def test_get_link_path(self, tmp_path, mock_home_dir):
        """Should return correct link.yaml path"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        link_path = get_link_path(repo_path)

        assert link_path.name == "link.yaml", "Should end with link.yaml"

        # Should be under storage dir
        storage_dir = get_storage_dir(repo_path)
        assert link_path.parent == storage_dir, "Should be in storage dir"

    def test_is_linked_false_for_unlinked_repo(self, tmp_path, mock_home_dir):
        """Should return False for repository without link"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        assert not is_linked(repo_path), "Unlinked repo should return False"

    def test_is_linked_true_for_linked_repo(self, setup_repos):
        """Should return True for repository with link"""
        source_repo, target_repo = setup_repos

        # Create link
        create_link(target_repo, source_repo)

        assert is_linked(target_repo), "Linked repo should return True"

    def test_create_link_success(self, setup_repos):
        """Should successfully create link between repositories"""
        source_repo, target_repo = setup_repos

        # Create link
        create_link(target_repo, source_repo)

        # Verify link file exists
        link_path = get_link_path(target_repo)
        assert link_path.exists(), "Link file should be created"

        # Verify link info
        link_info = get_link_info(target_repo)
        assert link_info is not None, "Link info should be available"
        assert link_info["source_repo_path"] == str(source_repo.resolve())
        assert "source_storage_dir" in link_info
        assert "linked_at" in link_info

    def test_create_link_fails_if_source_not_indexed(self, tmp_path, mock_home_dir):
        """Should fail if source repository has no index"""
        source_repo = tmp_path / "source_repo"
        source_repo.mkdir()

        target_repo = tmp_path / "target_repo"
        target_repo.mkdir()

        # Don't create index for source
        with pytest.raises(ValueError, match="Source repository is not indexed"):
            create_link(target_repo, source_repo)

    def test_create_link_fails_if_already_linked(self, setup_repos):
        """Should fail if target is already linked"""
        source_repo, target_repo = setup_repos

        # Create first link
        create_link(target_repo, source_repo)

        # Try to create second link
        with pytest.raises(ValueError, match="already linked"):
            create_link(target_repo, source_repo)

    def test_create_link_fails_if_source_not_exists(self, tmp_path, mock_home_dir):
        """Should fail if source repository doesn't exist"""
        source_repo = tmp_path / "nonexistent_source"
        target_repo = tmp_path / "target_repo"
        target_repo.mkdir()

        with pytest.raises(FileNotFoundError, match="Source repository not found"):
            create_link(target_repo, source_repo)

    def test_create_link_fails_if_target_not_exists(self, tmp_path, mock_home_dir):
        """Should fail if target repository doesn't exist"""
        source_repo = tmp_path / "source_repo"
        source_repo.mkdir()

        # Create index for source
        source_storage = create_storage_dir(source_repo)
        source_index = source_storage / "index.json"
        source_index.write_text('{"modules": {}}')

        target_repo = tmp_path / "nonexistent_target"

        with pytest.raises(FileNotFoundError, match="Target repository not found"):
            create_link(target_repo, source_repo)

    def test_get_link_info_returns_none_for_unlinked(self, tmp_path, mock_home_dir):
        """Should return None for repository without link"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        link_info = get_link_info(repo_path)

        assert link_info is None, "Unlinked repo should have no link info"

    def test_get_link_info_returns_data_for_linked(self, setup_repos):
        """Should return link data for linked repository"""
        source_repo, target_repo = setup_repos

        # Create link
        create_link(target_repo, source_repo)

        # Get link info
        link_info = get_link_info(target_repo)

        assert link_info is not None, "Link info should exist"
        assert "source_repo_path" in link_info
        assert "source_storage_dir" in link_info
        assert "linked_at" in link_info

    def test_resolve_storage_dir_unlinked(self, tmp_path, mock_home_dir):
        """Should return own storage dir for unlinked repository"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        storage_dir = get_storage_dir(repo_path)
        resolved_dir = resolve_storage_dir(repo_path)

        assert storage_dir == resolved_dir, "Should resolve to own storage"

    def test_resolve_storage_dir_linked(self, setup_repos):
        """Should return source storage dir for linked repository"""
        source_repo, target_repo = setup_repos

        # Create link
        create_link(target_repo, source_repo)

        # Resolve storage
        source_storage = get_storage_dir(source_repo)
        resolved_target = resolve_storage_dir(target_repo)

        assert resolved_target == source_storage, "Should resolve to source storage"

    def test_remove_link_success(self, setup_repos):
        """Should successfully remove link"""
        source_repo, target_repo = setup_repos

        # Create link
        create_link(target_repo, source_repo)
        assert is_linked(target_repo), "Should be linked"

        # Remove link
        result = remove_link(target_repo)

        assert result is True, "Should return True when link removed"
        assert not is_linked(target_repo), "Should no longer be linked"

        # Verify link file is gone
        link_path = get_link_path(target_repo)
        assert not link_path.exists(), "Link file should be removed"

    def test_remove_link_returns_false_for_unlinked(self, tmp_path, mock_home_dir):
        """Should return False when removing non-existent link"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        result = remove_link(repo_path)

        assert result is False, "Should return False for unlinked repo"

    def test_link_creates_target_storage_dir(self, setup_repos):
        """Should create target storage directory if it doesn't exist"""
        source_repo, target_repo = setup_repos

        # Remove target storage if it exists
        target_storage = get_storage_dir(target_repo)
        if target_storage.exists():
            import shutil

            shutil.rmtree(target_storage)

        # Create link
        create_link(target_repo, source_repo)

        # Verify target storage exists
        assert target_storage.exists(), "Target storage should be created"

    def test_create_link_prevents_circular_links(self, tmp_path, mock_home_dir):
        """Should prevent circular links (A → B when B → A exists)"""
        # Create three repositories
        repo_a = tmp_path / "repo_a"
        repo_b = tmp_path / "repo_b"
        repo_a.mkdir()
        repo_b.mkdir()

        # Create indices for both
        storage_a = create_storage_dir(repo_a)
        storage_b = create_storage_dir(repo_b)
        (storage_a / "index.json").write_text('{"modules": {}}')
        (storage_b / "index.json").write_text('{"modules": {}}')

        # Create link A → B
        create_link(repo_a, repo_b)

        # Try to create link B → A (should fail)
        with pytest.raises(ValueError, match="circular link"):
            create_link(repo_b, repo_a)

    def test_create_link_allows_link_chain(self, tmp_path, mock_home_dir):
        """Should allow linking to a repository that is itself linked to another source."""
        repo_a = tmp_path / "repo_a"
        repo_b = tmp_path / "repo_b"
        repo_c = tmp_path / "repo_c"

        for repo in (repo_a, repo_b, repo_c):
            repo.mkdir()

        source_storage = create_storage_dir(repo_a)
        (source_storage / "index.json").write_text('{"modules": {}}')

        # Link B → A and ensure it resolves correctly
        create_link(repo_b, repo_a)
        resolved_a = resolve_storage_dir(repo_a)
        assert resolve_storage_dir(repo_b) == resolved_a

        # Link C → B (which is already linked to A)
        create_link(repo_c, repo_b)

        resolved_c = resolve_storage_dir(repo_c)
        assert resolved_c == resolved_a

        link_info = get_link_info(repo_c)
        assert link_info is not None
        assert link_info["source_storage_dir"] == str(resolved_a)

    def test_resolve_storage_dir_detects_broken_link(self, setup_repos):
        """Should detect and report broken links when source index is deleted"""
        source_repo, target_repo = setup_repos

        # Create link
        create_link(target_repo, source_repo)

        # Delete source index to break the link
        source_index = get_index_path(source_repo)
        source_index.unlink()

        # Attempting to resolve should raise ValueError
        with pytest.raises(ValueError, match="Link is broken"):
            resolve_storage_dir(target_repo)

    def test_get_link_info_handles_corrupted_yaml(self, setup_repos):
        """Should return None for corrupted link.yaml file"""
        source_repo, target_repo = setup_repos

        # Create link
        create_link(target_repo, source_repo)

        # Corrupt the link file
        link_path = get_link_path(target_repo)
        link_path.write_text("invalid: yaml: content: [[[")

        # Should return None for corrupted file
        link_info = get_link_info(target_repo)
        assert link_info is None, "Should return None for corrupted YAML"

    def test_get_index_path_follows_link(self, setup_repos):
        """get_index_path should return source repo's index path when linked"""
        source_repo, target_repo = setup_repos

        # Create link
        create_link(target_repo, source_repo)

        # Get paths
        target_index_path = get_index_path(target_repo)
        source_index_path = get_index_path(source_repo)

        # Target should point to source's index
        assert target_index_path == source_index_path, "Target should use source's index"
        assert target_index_path.exists(), "Source index should exist"

    def test_get_config_path_follows_link(self, setup_repos):
        """get_config_path should return source repo's config path when linked"""
        source_repo, target_repo = setup_repos

        # Create source config
        source_storage = get_storage_dir(source_repo)
        source_config = source_storage / "config.yaml"
        source_config.write_text("test: config")

        # Create link
        create_link(target_repo, source_repo)

        # Get paths
        target_config_path = get_config_path(target_repo)
        source_config_path = get_config_path(source_repo)

        # Target should point to source's config
        assert target_config_path == source_config_path, "Target should use source's config"
        assert target_config_path.exists(), "Source config should exist"

    def test_get_hashes_path_follows_link(self, setup_repos):
        """get_hashes_path should return source repo's hashes path when linked"""
        source_repo, target_repo = setup_repos

        # Create link
        create_link(target_repo, source_repo)

        # Get paths
        target_hashes_path = get_hashes_path(target_repo)
        source_hashes_path = get_hashes_path(source_repo)

        # Target should point to source's hashes
        assert target_hashes_path == source_hashes_path, "Target should use source's hashes"

    def test_get_pr_index_path_follows_link(self, setup_repos):
        """get_pr_index_path should return source repo's PR index path when linked"""
        source_repo, target_repo = setup_repos

        # Create link
        create_link(target_repo, source_repo)

        # Get paths
        target_pr_index_path = get_pr_index_path(target_repo)
        source_pr_index_path = get_pr_index_path(source_repo)

        # Target should point to source's PR index
        assert target_pr_index_path == source_pr_index_path, "Target should use source's PR index"

    def test_path_helpers_return_own_paths_when_not_linked(self, tmp_path, mock_home_dir):
        """Path helpers should return own paths when repository is not linked"""
        repo = tmp_path / "test_repo"
        repo.mkdir()

        # Get all paths
        index_path = get_index_path(repo)
        config_path = get_config_path(repo)
        hashes_path = get_hashes_path(repo)
        pr_index_path = get_pr_index_path(repo)

        # All should be under repo's own storage
        repo_storage = get_storage_dir(repo)
        assert index_path.parent == repo_storage, "Index should be in repo's storage"
        assert config_path.parent == repo_storage, "Config should be in repo's storage"
        assert hashes_path.parent == repo_storage, "Hashes should be in repo's storage"
        assert pr_index_path.parent == repo_storage, "PR index should be in repo's storage"
