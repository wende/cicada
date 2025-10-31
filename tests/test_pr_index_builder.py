"""
Comprehensive tests for cicada/pr_indexer/pr_index_builder.py
"""

import json

from cicada.pr_indexer.pr_index_builder import PRIndexBuilder


class TestPRIndexBuilderInit:
    """Tests for PRIndexBuilder.__init__ method"""

    def test_init_basic(self):
        """Test basic initialization"""
        builder = PRIndexBuilder("owner", "repo")
        assert builder.repo_owner == "owner"
        assert builder.repo_name == "repo"

    def test_init_with_different_values(self):
        """Test initialization with different values"""
        builder = PRIndexBuilder("facebook", "react")
        assert builder.repo_owner == "facebook"
        assert builder.repo_name == "react"


class TestBuildIndex:
    """Tests for PRIndexBuilder.build_index method"""

    def test_build_index_empty_prs(self, capsys):
        """Test building index with empty PR list"""
        builder = PRIndexBuilder("owner", "repo")
        result = builder.build_index([])

        assert result["metadata"]["repo_owner"] == "owner"
        assert result["metadata"]["repo_name"] == "repo"
        assert result["metadata"]["total_prs"] == 0
        assert result["metadata"]["total_commits_mapped"] == 0
        assert result["metadata"]["total_comments"] == 0
        assert result["metadata"]["total_files"] == 0
        assert "last_pr_number" not in result["metadata"]
        assert result["prs"] == {}
        assert result["commit_to_pr"] == {}
        assert result["file_to_prs"] == {}

        captured = capsys.readouterr()
        assert "Building index..." in captured.out

    def test_build_index_single_pr(self):
        """Test building index with single PR"""
        builder = PRIndexBuilder("owner", "repo")
        prs = [
            {
                "number": 100,
                "title": "Test PR",
                "commits": ["abc123", "def456"],
                "files_changed": ["lib/user.ex", "test/user_test.ex"],
                "comments": [{"body": "LGTM"}],
            }
        ]
        result = builder.build_index(prs)

        assert result["metadata"]["total_prs"] == 1
        assert result["metadata"]["total_commits_mapped"] == 2
        assert result["metadata"]["total_comments"] == 1
        assert result["metadata"]["total_files"] == 2
        assert result["metadata"]["last_pr_number"] == 100
        assert "100" in result["prs"]
        assert result["commit_to_pr"]["abc123"] == 100
        assert result["commit_to_pr"]["def456"] == 100
        assert result["file_to_prs"]["lib/user.ex"] == [100]

    def test_build_index_multiple_prs(self):
        """Test building index with multiple PRs"""
        builder = PRIndexBuilder("owner", "repo")
        prs = [
            {
                "number": 100,
                "commits": ["abc123"],
                "files_changed": ["lib/user.ex"],
                "comments": [],
            },
            {
                "number": 101,
                "commits": ["def456"],
                "files_changed": ["lib/user.ex", "lib/admin.ex"],
                "comments": [{"body": "Comment 1"}, {"body": "Comment 2"}],
            },
        ]
        result = builder.build_index(prs)

        assert result["metadata"]["total_prs"] == 2
        assert result["metadata"]["total_commits_mapped"] == 2
        assert result["metadata"]["total_comments"] == 2
        assert result["metadata"]["total_files"] == 2
        assert result["metadata"]["last_pr_number"] == 101

    def test_build_index_with_preserve_last_pr(self):
        """Test building index with preserved last PR number"""
        builder = PRIndexBuilder("owner", "repo")
        prs = [
            {
                "number": 100,
                "commits": ["abc123"],
                "files_changed": ["lib/user.ex"],
                "comments": [],
            }
        ]
        result = builder.build_index(prs, preserve_last_pr=200)

        # Should use preserved value, not calculated max
        assert result["metadata"]["last_pr_number"] == 200

    def test_build_index_file_sorting(self):
        """Test that files are mapped with PRs sorted newest first"""
        builder = PRIndexBuilder("owner", "repo")
        prs = [
            {
                "number": 100,
                "commits": ["abc"],
                "files_changed": ["lib/user.ex"],
                "comments": [],
            },
            {
                "number": 105,
                "commits": ["def"],
                "files_changed": ["lib/user.ex"],
                "comments": [],
            },
            {
                "number": 103,
                "commits": ["ghi"],
                "files_changed": ["lib/user.ex"],
                "comments": [],
            },
        ]
        result = builder.build_index(prs)

        # PRs should be sorted newest (highest number) first
        assert result["file_to_prs"]["lib/user.ex"] == [105, 103, 100]


class TestBuildCommitMapping:
    """Tests for PRIndexBuilder._build_commit_mapping method"""

    def test_build_commit_mapping_empty(self):
        """Test building commit mapping with empty PR list"""
        builder = PRIndexBuilder("owner", "repo")
        result = builder._build_commit_mapping([])
        assert result == {}

    def test_build_commit_mapping_single_pr(self):
        """Test building commit mapping with single PR"""
        builder = PRIndexBuilder("owner", "repo")
        prs = [{"number": 100, "commits": ["abc123", "def456"]}]
        result = builder._build_commit_mapping(prs)

        assert result["abc123"] == 100
        assert result["def456"] == 100
        assert len(result) == 2

    def test_build_commit_mapping_multiple_prs(self):
        """Test building commit mapping with multiple PRs"""
        builder = PRIndexBuilder("owner", "repo")
        prs = [
            {"number": 100, "commits": ["abc123"]},
            {"number": 101, "commits": ["def456", "ghi789"]},
        ]
        result = builder._build_commit_mapping(prs)

        assert result["abc123"] == 100
        assert result["def456"] == 101
        assert result["ghi789"] == 101
        assert len(result) == 3


class TestBuildFileMapping:
    """Tests for PRIndexBuilder._build_file_mapping method"""

    def test_build_file_mapping_empty(self):
        """Test building file mapping with empty PR list"""
        builder = PRIndexBuilder("owner", "repo")
        result = builder._build_file_mapping([])
        assert result == {}

    def test_build_file_mapping_single_pr(self):
        """Test building file mapping with single PR"""
        builder = PRIndexBuilder("owner", "repo")
        prs = [{"number": 100, "files_changed": ["lib/user.ex", "test/user_test.ex"]}]
        result = builder._build_file_mapping(prs)

        assert result["lib/user.ex"] == [100]
        assert result["test/user_test.ex"] == [100]
        assert len(result) == 2

    def test_build_file_mapping_multiple_prs_same_file(self):
        """Test file mapping with multiple PRs touching same file"""
        builder = PRIndexBuilder("owner", "repo")
        prs = [
            {"number": 100, "files_changed": ["lib/user.ex"]},
            {"number": 105, "files_changed": ["lib/user.ex"]},
            {"number": 103, "files_changed": ["lib/user.ex"]},
        ]
        result = builder._build_file_mapping(prs)

        # Should be sorted newest first (highest PR number first)
        assert result["lib/user.ex"] == [105, 103, 100]

    def test_build_file_mapping_no_files_changed(self):
        """Test file mapping when files_changed is missing"""
        builder = PRIndexBuilder("owner", "repo")
        prs = [{"number": 100}]  # No files_changed key
        result = builder._build_file_mapping(prs)
        assert result == {}

    def test_build_file_mapping_empty_files_changed(self):
        """Test file mapping when files_changed is empty"""
        builder = PRIndexBuilder("owner", "repo")
        prs = [{"number": 100, "files_changed": []}]
        result = builder._build_file_mapping(prs)
        assert result == {}


class TestMergeIndexes:
    """Tests for PRIndexBuilder.merge_indexes method"""

    def test_merge_indexes_empty_new_prs(self, capsys):
        """Test merging with no new PRs"""
        builder = PRIndexBuilder("owner", "repo")
        existing_index = {
            "prs": {
                "100": {
                    "number": 100,
                    "commits": ["abc"],
                    "files_changed": ["lib/user.ex"],
                }
            },
            "commit_to_pr": {"abc": 100},
            "file_to_prs": {"lib/user.ex": [100]},
            "metadata": {"total_prs": 1},
        }
        result = builder.merge_indexes(existing_index, [])

        assert result["metadata"]["total_prs"] == 1
        assert "Merging new PRs" in capsys.readouterr().out

    def test_merge_indexes_add_new_pr(self):
        """Test merging with new PR"""
        builder = PRIndexBuilder("owner", "repo")
        existing_index = {
            "prs": {
                "100": {
                    "number": 100,
                    "commits": ["abc123"],
                    "files_changed": ["lib/user.ex"],
                    "comments": [],
                }
            },
            "commit_to_pr": {"abc123": 100},
            "file_to_prs": {"lib/user.ex": [100]},
            "metadata": {"total_prs": 1},
        }

        new_prs = [
            {
                "number": 101,
                "commits": ["def456"],
                "files_changed": ["lib/admin.ex"],
                "comments": [{"body": "Test"}],
            }
        ]

        result = builder.merge_indexes(existing_index, new_prs)

        assert result["metadata"]["total_prs"] == 2
        assert result["metadata"]["total_commits_mapped"] == 2
        assert result["metadata"]["total_comments"] == 1
        assert result["metadata"]["total_files"] == 2
        assert result["metadata"]["last_pr_number"] == 101
        assert "101" in result["prs"]
        assert result["commit_to_pr"]["def456"] == 101

    def test_merge_indexes_update_existing_pr(self):
        """Test merging when PR already exists (should update it)"""
        builder = PRIndexBuilder("owner", "repo")
        existing_index = {
            "prs": {
                "100": {
                    "number": 100,
                    "title": "Old Title",
                    "commits": ["abc123"],
                    "files_changed": ["lib/user.ex"],
                }
            },
            "commit_to_pr": {"abc123": 100},
            "file_to_prs": {"lib/user.ex": [100]},
            "metadata": {},
        }

        new_prs = [
            {
                "number": 100,
                "title": "Updated Title",
                "commits": ["abc123", "def456"],
                "files_changed": ["lib/user.ex", "lib/admin.ex"],
            }
        ]

        result = builder.merge_indexes(existing_index, new_prs)

        # Should have updated the PR
        assert result["prs"]["100"]["title"] == "Updated Title"
        assert len(result["prs"]["100"]["commits"]) == 2


class TestMergePartialClean:
    """Tests for PRIndexBuilder.merge_partial_clean method"""

    def test_merge_partial_clean_basic(self, capsys):
        """Test merging partial clean index"""
        builder = PRIndexBuilder("owner", "repo")
        existing_index = {
            "prs": {
                "100": {
                    "number": 100,
                    "commits": ["abc"],
                    "files_changed": ["lib/user.ex"],
                }
            },
            "commit_to_pr": {"abc": 100},
            "file_to_prs": {"lib/user.ex": [100]},
            "metadata": {"last_pr_number": 100},
        }

        partial_index = {
            "prs": {
                "101": {
                    "number": 101,
                    "commits": ["def"],
                    "files_changed": ["lib/admin.ex"],
                }
            },
            "metadata": {"last_pr_number": 200},  # Preserved from interrupted fetch
        }

        result = builder.merge_partial_clean(existing_index, partial_index)

        assert len(result["prs"]) == 2
        assert "100" in result["prs"]
        assert "101" in result["prs"]
        assert result["metadata"]["last_pr_number"] == 200  # Should preserve this
        assert "Merging partial index" in capsys.readouterr().out

    def test_merge_partial_clean_rebuild_mappings(self):
        """Test that partial merge rebuilds commit and file mappings"""
        builder = PRIndexBuilder("owner", "repo")
        existing_index = {
            "prs": {
                "100": {
                    "number": 100,
                    "commits": ["abc"],
                    "files_changed": ["lib/user.ex"],
                }
            },
            "commit_to_pr": {},  # Empty, should be rebuilt
            "file_to_prs": {},  # Empty, should be rebuilt
            "metadata": {},
        }

        partial_index = {
            "prs": {
                "101": {
                    "number": 101,
                    "commits": ["def"],
                    "files_changed": ["lib/user.ex"],
                }
            },
            "metadata": {"last_pr_number": 101},
        }

        result = builder.merge_partial_clean(existing_index, partial_index)

        # Should have rebuilt both mappings
        assert "abc" in result["commit_to_pr"]
        assert "def" in result["commit_to_pr"]
        assert result["commit_to_pr"]["abc"] == 100
        assert result["commit_to_pr"]["def"] == 101
        assert "lib/user.ex" in result["file_to_prs"]
        assert set(result["file_to_prs"]["lib/user.ex"]) == {100, 101}

    def test_merge_partial_clean_comment_count(self):
        """Test that partial merge counts comments correctly"""
        builder = PRIndexBuilder("owner", "repo")
        existing_index = {
            "prs": {"100": {"number": 100, "commits": [], "comments": [{"body": "c1"}]}},
            "commit_to_pr": {},
            "file_to_prs": {},
            "metadata": {},
        }

        partial_index = {
            "prs": {
                "101": {
                    "number": 101,
                    "commits": [],
                    "comments": [{"body": "c2"}, {"body": "c3"}],
                }
            },
            "metadata": {},
        }

        result = builder.merge_partial_clean(existing_index, partial_index)

        assert result["metadata"]["total_comments"] == 3


class TestLoadExistingIndex:
    """Tests for PRIndexBuilder.load_existing_index method"""

    def test_load_existing_index_file_not_exists(self, tmp_path):
        """Test loading when file doesn't exist"""
        builder = PRIndexBuilder("owner", "repo")
        result = builder.load_existing_index(str(tmp_path / "nonexistent.json"))
        assert result is None

    def test_load_existing_index_valid_file(self, tmp_path):
        """Test loading valid index file"""
        builder = PRIndexBuilder("owner", "repo")
        index_data = {"prs": {"100": {"number": 100}}, "metadata": {"total_prs": 1}}

        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(index_data, f)

        result = builder.load_existing_index(str(index_path))
        assert result is not None
        assert result["metadata"]["total_prs"] == 1
        assert "100" in result["prs"]

    def test_load_existing_index_invalid_json(self, tmp_path, capsys):
        """Test loading file with invalid JSON"""
        builder = PRIndexBuilder("owner", "repo")
        index_path = tmp_path / "bad.json"

        with open(index_path, "w") as f:
            f.write("{invalid json")

        result = builder.load_existing_index(str(index_path))
        assert result is None
        assert "Warning: Could not" in capsys.readouterr().err

    def test_load_existing_index_io_error(self, tmp_path, capsys, monkeypatch):
        """Test loading when IO error occurs"""
        builder = PRIndexBuilder("owner", "repo")
        index_path = tmp_path / "index.json"

        # Create a valid file first
        with open(index_path, "w") as f:
            f.write('{"test": "data"}')

        # Mock open to raise IOError
        original_open = open

        def mock_open(*args, **kwargs):
            if str(index_path) in str(args[0]):
                raise OSError("Mocked IO error")
            return original_open(*args, **kwargs)

        monkeypatch.setattr("builtins.open", mock_open)
        result = builder.load_existing_index(str(index_path))
        assert result is None


class TestSaveIndex:
    """Tests for PRIndexBuilder.save_index method"""

    def test_save_index_basic(self, tmp_path, capsys):
        """Test saving index to file"""
        builder = PRIndexBuilder("owner", "repo")
        index = {"prs": {"100": {"number": 100}}, "metadata": {"total_prs": 1}}

        output_path = tmp_path / "index.json"
        builder.save_index(index, str(output_path))

        # Verify file was created
        assert output_path.exists()

        # Verify content
        with open(output_path) as f:
            loaded = json.load(f)
        assert loaded["metadata"]["total_prs"] == 1

        # Verify output message
        captured = capsys.readouterr()
        assert "Index saved to:" in captured.out

    def test_save_index_creates_parent_directory(self, tmp_path):
        """Test that save_index creates parent directories"""
        builder = PRIndexBuilder("owner", "repo")
        index = {"prs": {}, "metadata": {}}

        # Use nested directory that doesn't exist
        output_path = tmp_path / "subdir" / "nested" / "index.json"
        builder.save_index(index, str(output_path))

        assert output_path.exists()
        assert output_path.parent.exists()

    def test_save_index_overwrites_existing(self, tmp_path):
        """Test that save_index overwrites existing file"""
        builder = PRIndexBuilder("owner", "repo")
        output_path = tmp_path / "index.json"

        # Create initial file
        index1 = {"metadata": {"version": 1}}
        builder.save_index(index1, str(output_path))

        # Overwrite with new data
        index2 = {"metadata": {"version": 2}}
        builder.save_index(index2, str(output_path))

        # Verify it was overwritten
        with open(output_path) as f:
            loaded = json.load(f)
        assert loaded["metadata"]["version"] == 2
