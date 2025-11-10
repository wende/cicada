"""
Comprehensive tests for cicada/utils/index_utils.py
"""

import json

import pytest

from cicada.utils.index_utils import (
    get_index_stats,
    load_index,
    merge_indexes,
    merge_indexes_incremental,
    save_index,
    validate_index_structure,
)


@pytest.fixture
def sample_index():
    """Sample valid index structure"""
    return {
        "modules": {
            "lib/my_module.ex": {
                "functions": [
                    {"name": "my_func", "arity": 2, "type": "def"},
                    {"name": "private_func", "arity": 1, "type": "defp"},
                ]
            },
            "lib/other_module.ex": {
                "functions": [
                    {"name": "other_func", "arity": 0, "type": "def"},
                ]
            },
        },
        "metadata": {
            "version": "1.0",
            "timestamp": "2025-01-01T00:00:00Z",
        },
    }


@pytest.fixture
def temp_index_file(tmp_path, sample_index):
    """Create a temporary index file"""
    index_path = tmp_path / "test_index.json"
    with open(index_path, "w") as f:
        json.dump(sample_index, f)
    return index_path


class TestLoadIndex:
    """Tests for load_index function"""

    def test_load_valid_index(self, temp_index_file, sample_index):
        """Test loading a valid index file"""
        result = load_index(temp_index_file)
        assert result == sample_index

    def test_load_index_with_string_path(self, temp_index_file, sample_index):
        """Test loading with string path instead of Path"""
        result = load_index(str(temp_index_file))
        assert result == sample_index

    def test_load_nonexistent_file(self, tmp_path):
        """Test loading a file that doesn't exist"""
        nonexistent = tmp_path / "nonexistent.json"
        result = load_index(nonexistent)
        assert result is None

    def test_load_nonexistent_file_verbose(self, tmp_path, capsys):
        """Test loading nonexistent file with verbose=True"""
        nonexistent = tmp_path / "nonexistent.json"
        result = load_index(nonexistent, verbose=True)
        assert result is None
        captured = capsys.readouterr()
        assert "Warning: Index not found" in captured.err
        assert str(nonexistent) in captured.err

    def test_load_nonexistent_file_raise_on_error(self, tmp_path):
        """Test loading nonexistent file with raise_on_error=True"""
        nonexistent = tmp_path / "nonexistent.json"
        with pytest.raises(FileNotFoundError) as exc_info:
            load_index(nonexistent, raise_on_error=True)
        assert "Index file not found" in str(exc_info.value)

    def test_load_invalid_json(self, tmp_path):
        """Test loading file with invalid JSON"""
        invalid_json = tmp_path / "invalid.json"
        invalid_json.write_text("{invalid json content")
        result = load_index(invalid_json)
        assert result is None

    def test_load_invalid_json_verbose(self, tmp_path, capsys):
        """Test loading invalid JSON with verbose=True"""
        invalid_json = tmp_path / "invalid.json"
        invalid_json.write_text("{invalid json content")
        result = load_index(invalid_json, verbose=True)
        assert result is None
        captured = capsys.readouterr()
        assert "Warning: Could not parse index" in captured.err

    def test_load_invalid_json_raise_on_error(self, tmp_path):
        """Test loading invalid JSON with raise_on_error=True"""
        invalid_json = tmp_path / "invalid.json"
        invalid_json.write_text("{invalid json content")
        with pytest.raises(json.JSONDecodeError):
            load_index(invalid_json, raise_on_error=True)

    def test_load_io_error_verbose(self, tmp_path, capsys, monkeypatch):
        """Test handling IO errors with verbose=True"""
        index_path = tmp_path / "test.json"
        index_path.write_text("{}")

        # Mock the open function to raise IOError
        original_open = open

        def mock_open(*args, **kwargs):
            if str(index_path) in str(args[0]):
                raise OSError("Mocked IO error")
            return original_open(*args, **kwargs)

        monkeypatch.setattr("builtins.open", mock_open)

        result = load_index(index_path, verbose=True)
        assert result is None
        captured = capsys.readouterr()
        assert "Warning: Could not read index" in captured.err

    def test_load_io_error_raise_on_error(self, tmp_path, monkeypatch):
        """Test handling IO errors with raise_on_error=True"""
        index_path = tmp_path / "test.json"
        index_path.write_text("{}")

        # Mock the open function to raise IOError
        original_open = open

        def mock_open(*args, **kwargs):
            if str(index_path) in str(args[0]):
                raise OSError("Mocked IO error")
            return original_open(*args, **kwargs)

        monkeypatch.setattr("builtins.open", mock_open)

        with pytest.raises(IOError):
            load_index(index_path, raise_on_error=True)


class TestSaveIndex:
    """Tests for save_index function"""

    def test_save_index_basic(self, tmp_path, sample_index):
        """Test basic index saving"""
        output_path = tmp_path / "output.json"
        save_index(sample_index, output_path)

        assert output_path.exists()
        with open(output_path) as f:
            loaded = json.load(f)
        assert loaded == sample_index

    def test_save_index_with_string_path(self, tmp_path, sample_index):
        """Test saving with string path"""
        output_path = tmp_path / "output.json"
        save_index(sample_index, str(output_path))

        assert output_path.exists()
        with open(output_path) as f:
            loaded = json.load(f)
        assert loaded == sample_index

    def test_save_index_create_dirs(self, tmp_path, sample_index):
        """Test saving with automatic directory creation"""
        output_path = tmp_path / "subdir" / "nested" / "output.json"
        save_index(sample_index, output_path, create_dirs=True)

        assert output_path.exists()
        with open(output_path) as f:
            loaded = json.load(f)
        assert loaded == sample_index

    def test_save_index_no_create_dirs(self, tmp_path, sample_index):
        """Test saving without creating directories"""
        output_path = tmp_path / "subdir" / "output.json"
        with pytest.raises(FileNotFoundError):
            save_index(sample_index, output_path, create_dirs=False)

    def test_save_index_custom_indent(self, tmp_path, sample_index):
        """Test saving with custom indentation"""
        output_path = tmp_path / "output.json"
        save_index(sample_index, output_path, indent=4)

        content = output_path.read_text()
        # Check that indentation is 4 spaces (look for nested content)
        assert '    "modules"' in content

    def test_save_index_verbose(self, tmp_path, sample_index, capsys):
        """Test saving with verbose output"""
        output_path = tmp_path / "output.json"
        save_index(sample_index, output_path, verbose=True)

        captured = capsys.readouterr()
        assert "Index saved to:" in captured.out
        assert str(output_path) in captured.out

    def test_save_index_overwrite(self, tmp_path, sample_index):
        """Test overwriting an existing file"""
        output_path = tmp_path / "output.json"
        save_index({"old": "data"}, output_path)
        save_index(sample_index, output_path)

        with open(output_path) as f:
            loaded = json.load(f)
        assert loaded == sample_index


class TestValidateIndexStructure:
    """Tests for validate_index_structure function"""

    def test_validate_valid_index_default_keys(self, sample_index):
        """Test validating a valid index with default keys"""
        is_valid, error = validate_index_structure(sample_index)
        assert is_valid is True
        assert error is None

    def test_validate_valid_index_custom_keys(self):
        """Test validating with custom required keys"""
        index = {"custom_key": {}, "another_key": []}
        is_valid, error = validate_index_structure(
            index, required_keys=["custom_key", "another_key"]
        )
        assert is_valid is True
        assert error is None

    def test_validate_non_dict_input(self):
        """Test validating non-dictionary input"""
        is_valid, error = validate_index_structure([])
        assert is_valid is False
        assert error == "Index must be a dictionary"

    def test_validate_non_dict_input_string(self):
        """Test validating string input"""
        is_valid, error = validate_index_structure("not a dict")
        assert is_valid is False
        assert error == "Index must be a dictionary"

    def test_validate_missing_modules_key(self):
        """Test validating index missing 'modules' key"""
        index = {"metadata": {}}
        is_valid, error = validate_index_structure(index)
        assert is_valid is False
        assert error == "Missing required key: modules"

    def test_validate_missing_metadata_key(self):
        """Test validating index missing 'metadata' key"""
        index = {"modules": {}}
        is_valid, error = validate_index_structure(index)
        assert is_valid is False
        assert error == "Missing required key: metadata"

    def test_validate_missing_custom_key(self):
        """Test validating index missing custom required key"""
        index = {"modules": {}, "metadata": {}}
        is_valid, error = validate_index_structure(
            index, required_keys=["modules", "metadata", "custom"]
        )
        assert is_valid is False
        assert error == "Missing required key: custom"

    def test_validate_modules_not_dict(self):
        """Test validating when 'modules' is not a dictionary"""
        index = {"modules": [], "metadata": {}}
        is_valid, error = validate_index_structure(index)
        assert is_valid is False
        assert error == "'modules' must be a dictionary"

    def test_validate_metadata_not_dict(self):
        """Test validating when 'metadata' is not a dictionary"""
        index = {"modules": {}, "metadata": "string"}
        is_valid, error = validate_index_structure(index)
        assert is_valid is False
        assert error == "'metadata' must be a dictionary"

    def test_validate_empty_required_keys(self):
        """Test validating with empty required keys list"""
        index = {}
        is_valid, error = validate_index_structure(index, required_keys=[])
        assert is_valid is True
        assert error is None


class TestMergeIndexes:
    """Tests for merge_indexes function"""

    def test_merge_empty_input(self):
        """Test merging with no indexes"""
        result = merge_indexes()
        assert result == {}

    def test_merge_single_index(self, sample_index):
        """Test merging a single index"""
        result = merge_indexes(sample_index)
        assert result["modules"] == sample_index["modules"]
        assert result["metadata"] == sample_index["metadata"]

    def test_merge_two_indexes_last_wins(self):
        """Test merging two indexes with last_wins strategy"""
        index1 = {
            "modules": {"mod1": {"data": "value1"}},
            "metadata": {"version": "1.0"},
        }
        index2 = {
            "modules": {"mod2": {"data": "value2"}},
            "metadata": {"version": "2.0"},
        }

        result = merge_indexes(index1, index2, strategy="last_wins")

        assert "mod1" in result["modules"]
        assert "mod2" in result["modules"]
        assert result["metadata"]["version"] == "2.0"

    def test_merge_two_indexes_first_wins(self):
        """Test merging two indexes with first_wins strategy"""
        index1 = {
            "modules": {"mod1": {"data": "value1"}},
            "metadata": {"version": "1.0", "author": "first"},
        }
        index2 = {
            "modules": {"mod2": {"data": "value2"}},
            "metadata": {"version": "2.0", "timestamp": "later"},
        }

        result = merge_indexes(index1, index2, strategy="first_wins")

        assert "mod1" in result["modules"]
        assert "mod2" in result["modules"]
        # With first_wins, first index takes precedence for metadata
        assert result["metadata"]["version"] == "1.0"
        assert result["metadata"]["author"] == "first"

    def test_merge_overlapping_modules_last_wins(self):
        """Test merging indexes with overlapping module keys (last_wins)"""
        index1 = {
            "modules": {"shared": {"value": 1}},
            "metadata": {},
        }
        index2 = {
            "modules": {"shared": {"value": 2}},
            "metadata": {},
        }

        result = merge_indexes(index1, index2, strategy="last_wins")
        assert result["modules"]["shared"]["value"] == 2

    def test_merge_overlapping_modules_first_wins(self):
        """Test merging indexes with overlapping module keys (first_wins)"""
        index1 = {
            "modules": {"shared": {"value": 1}},
            "metadata": {},
        }
        index2 = {
            "modules": {"shared": {"value": 2}},
            "metadata": {},
        }

        result = merge_indexes(index1, index2, strategy="first_wins")
        assert result["modules"]["shared"]["value"] == 1

    def test_merge_invalid_strategy(self):
        """Test merging with invalid strategy"""
        index = {"modules": {}, "metadata": {}}
        with pytest.raises(ValueError) as exc_info:
            merge_indexes(index, strategy="invalid_strategy")
        assert "Unknown merge strategy" in str(exc_info.value)

    def test_merge_multiple_indexes(self):
        """Test merging three or more indexes"""
        index1 = {"modules": {"mod1": {}}, "metadata": {"key1": "val1"}}
        index2 = {"modules": {"mod2": {}}, "metadata": {"key2": "val2"}}
        index3 = {"modules": {"mod3": {}}, "metadata": {"key3": "val3"}}

        result = merge_indexes(index1, index2, index3, strategy="last_wins")

        assert "mod1" in result["modules"]
        assert "mod2" in result["modules"]
        assert "mod3" in result["modules"]
        assert len(result["metadata"]) == 3

    def test_merge_indexes_without_modules(self):
        """Test merging indexes that don't have modules key"""
        index1 = {"metadata": {"version": "1.0"}}
        index2 = {"metadata": {"version": "2.0"}}

        result = merge_indexes(index1, index2, strategy="last_wins")

        assert "modules" in result
        assert result["modules"] == {}
        assert result["metadata"]["version"] == "2.0"

    def test_merge_indexes_without_metadata(self):
        """Test merging indexes that don't have metadata key"""
        index1 = {"modules": {"mod1": {}}}
        index2 = {"modules": {"mod2": {}}}

        result = merge_indexes(index1, index2, strategy="last_wins")

        assert "mod1" in result["modules"]
        assert "mod2" in result["modules"]
        assert "metadata" in result
        assert result["metadata"] == {}


class TestGetIndexStats:
    """Tests for get_index_stats function"""

    def test_get_stats_empty_index(self):
        """Test getting stats from empty index"""
        stats = get_index_stats({})
        assert stats["total_modules"] == 0
        assert stats["total_functions"] == 0
        assert stats["public_functions"] == 0
        assert stats["private_functions"] == 0

    def test_get_stats_no_modules_key(self):
        """Test getting stats from index without modules key"""
        stats = get_index_stats({"metadata": {}})
        assert stats["total_modules"] == 0
        assert stats["total_functions"] == 0

    def test_get_stats_empty_modules(self):
        """Test getting stats from index with empty modules"""
        index = {"modules": {}}
        stats = get_index_stats(index)
        assert stats["total_modules"] == 0
        assert stats["total_functions"] == 0

    def test_get_stats_modules_without_functions(self):
        """Test getting stats from modules without functions"""
        index = {
            "modules": {
                "mod1": {},
                "mod2": {"other_key": "value"},
            }
        }
        stats = get_index_stats(index)
        assert stats["total_modules"] == 2
        assert stats["total_functions"] == 0

    def test_get_stats_with_functions(self, sample_index):
        """Test getting stats from index with functions"""
        stats = get_index_stats(sample_index)
        assert stats["total_modules"] == 2
        assert stats["total_functions"] == 3
        assert stats["public_functions"] == 2
        assert stats["private_functions"] == 1

    def test_get_stats_only_public_functions(self):
        """Test stats with only public functions"""
        index = {
            "modules": {
                "mod1": {
                    "functions": [
                        {"name": "func1", "type": "def"},
                        {"name": "func2", "type": "def"},
                    ]
                }
            }
        }
        stats = get_index_stats(index)
        assert stats["total_modules"] == 1
        assert stats["total_functions"] == 2
        assert stats["public_functions"] == 2
        assert stats["private_functions"] == 0

    def test_get_stats_only_private_functions(self):
        """Test stats with only private functions"""
        index = {
            "modules": {
                "mod1": {
                    "functions": [
                        {"name": "func1", "type": "defp"},
                        {"name": "func2", "type": "defp"},
                    ]
                }
            }
        }
        stats = get_index_stats(index)
        assert stats["total_modules"] == 1
        assert stats["total_functions"] == 2
        assert stats["public_functions"] == 0
        assert stats["private_functions"] == 2

    def test_get_stats_functions_without_type(self):
        """Test stats with functions missing type field"""
        index = {
            "modules": {
                "mod1": {
                    "functions": [
                        {"name": "func1"},
                        {"name": "func2", "type": "def"},
                    ]
                }
            }
        }
        stats = get_index_stats(index)
        assert stats["total_modules"] == 1
        assert stats["total_functions"] == 2
        assert stats["public_functions"] == 1
        assert stats["private_functions"] == 0

    def test_get_stats_mixed_function_types(self):
        """Test stats with various function types"""
        index = {
            "modules": {
                "mod1": {
                    "functions": [
                        {"name": "func1", "type": "def"},
                        {"name": "func2", "type": "defp"},
                        {"name": "func3", "type": "defmacro"},  # Should not be counted
                        {"name": "func4", "type": "def"},
                    ]
                }
            }
        }
        stats = get_index_stats(index)
        assert stats["total_functions"] == 4
        assert stats["public_functions"] == 2
        assert stats["private_functions"] == 1

    def test_get_stats_multiple_modules(self):
        """Test stats with multiple modules"""
        index = {
            "modules": {
                "mod1": {
                    "functions": [
                        {"name": "f1", "type": "def"},
                        {"name": "f2", "type": "defp"},
                    ]
                },
                "mod2": {
                    "functions": [
                        {"name": "f3", "type": "def"},
                    ]
                },
                "mod3": {
                    "functions": [
                        {"name": "f4", "type": "defp"},
                        {"name": "f5", "type": "defp"},
                    ]
                },
            }
        }
        stats = get_index_stats(index)
        assert stats["total_modules"] == 3
        assert stats["total_functions"] == 5
        assert stats["public_functions"] == 2
        assert stats["private_functions"] == 3


class TestMergeIndexesIncremental:
    """Tests for merge_indexes_incremental function"""

    def test_merge_incremental_basic(self):
        """Test basic incremental merge"""
        old_index = {
            "modules": {
                "Module1": {"file": "lib/module1.ex", "functions": []},
                "Module2": {"file": "lib/module2.ex", "functions": []},
            },
            "metadata": {"total_modules": 2, "total_functions": 0},
        }

        new_index = {
            "modules": {
                "Module3": {"file": "lib/module3.ex", "functions": []},
            },
            "metadata": {},
        }

        deleted_files = []

        result = merge_indexes_incremental(old_index, new_index, deleted_files)

        assert "Module1" in result["modules"]
        assert "Module2" in result["modules"]
        assert "Module3" in result["modules"]
        assert result["metadata"]["total_modules"] == 3

    def test_merge_incremental_with_deletions(self):
        """Test incremental merge with deleted files"""
        old_index = {
            "modules": {
                "Module1": {"file": "lib/module1.ex", "functions": []},
                "Module2": {"file": "lib/module2.ex", "functions": []},
                "Module3": {"file": "lib/module3.ex", "functions": []},
            },
            "metadata": {},
        }

        new_index = {"modules": {}, "metadata": {}}

        deleted_files = ["lib/module2.ex"]

        result = merge_indexes_incremental(old_index, new_index, deleted_files)

        assert "Module1" in result["modules"]
        assert "Module2" not in result["modules"]  # Deleted
        assert "Module3" in result["modules"]
        assert result["metadata"]["total_modules"] == 2

    def test_merge_incremental_update_existing(self):
        """Test incremental merge that updates existing modules"""
        old_index = {
            "modules": {
                "Module1": {
                    "file": "lib/module1.ex",
                    "functions": [{"name": "old_func", "type": "def"}],
                },
            },
            "metadata": {},
        }

        new_index = {
            "modules": {
                "Module1": {
                    "file": "lib/module1.ex",
                    "functions": [
                        {"name": "old_func", "type": "def"},
                        {"name": "new_func", "type": "def"},
                    ],
                },
            },
            "metadata": {},
        }

        deleted_files = []

        result = merge_indexes_incremental(old_index, new_index, deleted_files)

        assert len(result["modules"]["Module1"]["functions"]) == 2
        assert result["metadata"]["total_modules"] == 1

    def test_merge_incremental_empty_old_index(self):
        """Test incremental merge with empty old index (first run)"""
        old_index = {"modules": {}, "metadata": {}}

        new_index = {
            "modules": {
                "Module1": {"file": "lib/module1.ex", "functions": []},
            },
            "metadata": {},
        }

        deleted_files = []

        result = merge_indexes_incremental(old_index, new_index, deleted_files)

        assert "Module1" in result["modules"]
        assert result["metadata"]["total_modules"] == 1

    def test_merge_incremental_empty_new_index(self):
        """Test incremental merge with empty new index (no changes)"""
        old_index = {
            "modules": {
                "Module1": {"file": "lib/module1.ex", "functions": []},
            },
            "metadata": {},
        }

        new_index = {"modules": {}, "metadata": {}}

        deleted_files = []

        result = merge_indexes_incremental(old_index, new_index, deleted_files)

        assert "Module1" in result["modules"]
        assert result["metadata"]["total_modules"] == 1

    def test_merge_incremental_updates_function_counts(self):
        """Test that incremental merge updates function counts correctly"""
        old_index = {
            "modules": {
                "Module1": {
                    "file": "lib/module1.ex",
                    "functions": [{"name": "func1", "type": "def"}],
                },
            },
            "metadata": {},
        }

        new_index = {
            "modules": {
                "Module2": {
                    "file": "lib/module2.ex",
                    "functions": [
                        {"name": "func2", "type": "def"},
                        {"name": "func3", "type": "defp"},
                    ],
                },
            },
            "metadata": {},
        }

        deleted_files = []

        result = merge_indexes_incremental(old_index, new_index, deleted_files)

        assert result["metadata"]["total_modules"] == 2
        assert result["metadata"]["total_functions"] == 3
        assert result["metadata"]["public_functions"] == 2
        assert result["metadata"]["private_functions"] == 1

    def test_merge_incremental_delete_multiple_files(self):
        """Test deleting multiple files at once"""
        old_index = {
            "modules": {
                "Module1": {"file": "lib/module1.ex", "functions": []},
                "Module2": {"file": "lib/module2.ex", "functions": []},
                "Module3": {"file": "lib/module3.ex", "functions": []},
                "Module4": {"file": "lib/module4.ex", "functions": []},
            },
            "metadata": {},
        }

        new_index = {"modules": {}, "metadata": {}}

        deleted_files = ["lib/module1.ex", "lib/module3.ex"]

        result = merge_indexes_incremental(old_index, new_index, deleted_files)

        assert "Module1" not in result["modules"]
        assert "Module2" in result["modules"]
        assert "Module3" not in result["modules"]
        assert "Module4" in result["modules"]
        assert result["metadata"]["total_modules"] == 2

    def test_merge_incremental_metadata_priority(self):
        """Test that new_index metadata takes priority"""
        old_index = {
            "modules": {},
            "metadata": {"indexed_at": "2025-01-01", "repo_path": "/old/path"},
        }

        new_index = {
            "modules": {},
            "metadata": {"indexed_at": "2025-01-02"},
        }

        deleted_files = []

        result = merge_indexes_incremental(old_index, new_index, deleted_files)

        # New index metadata should override old
        assert result["metadata"]["indexed_at"] == "2025-01-02"
        # But counts should be updated regardless
        assert "total_modules" in result["metadata"]

    def test_merge_incremental_complex_scenario(self):
        """Test a complex scenario with additions, updates, and deletions"""
        old_index = {
            "modules": {
                "Unchanged": {
                    "file": "lib/unchanged.ex",
                    "functions": [{"name": "f1", "type": "def"}],
                },
                "ToBeUpdated": {
                    "file": "lib/updated.ex",
                    "functions": [{"name": "f2", "type": "def"}],
                },
                "ToBeDeleted": {
                    "file": "lib/deleted.ex",
                    "functions": [{"name": "f3", "type": "def"}],
                },
            },
            "metadata": {},
        }

        new_index = {
            "modules": {
                "ToBeUpdated": {
                    "file": "lib/updated.ex",
                    "functions": [
                        {"name": "f2", "type": "def"},
                        {"name": "f4", "type": "defp"},
                    ],
                },
                "NewModule": {
                    "file": "lib/new.ex",
                    "functions": [{"name": "f5", "type": "def"}],
                },
            },
            "metadata": {},
        }

        deleted_files = ["lib/deleted.ex"]

        result = merge_indexes_incremental(old_index, new_index, deleted_files)

        # Unchanged should remain
        assert "Unchanged" in result["modules"]
        assert len(result["modules"]["Unchanged"]["functions"]) == 1

        # ToBeUpdated should have new functions
        assert "ToBeUpdated" in result["modules"]
        assert len(result["modules"]["ToBeUpdated"]["functions"]) == 2

        # ToBeDeleted should be removed
        assert "ToBeDeleted" not in result["modules"]

        # NewModule should be added
        assert "NewModule" in result["modules"]

        # Check stats
        assert result["metadata"]["total_modules"] == 3
        assert result["metadata"]["total_functions"] == 4
        assert result["metadata"]["public_functions"] == 3
        assert result["metadata"]["private_functions"] == 1
