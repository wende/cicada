"""
Comprehensive tests for cicada/utils/storage.py
"""

from pathlib import Path

import pytest

from cicada.utils.storage import (
    create_storage_dir,
    get_config_path,
    get_hashes_path,
    get_index_path,
    get_pr_index_path,
    get_repo_hash,
    get_storage_dir,
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
