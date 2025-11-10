"""
Comprehensive tests for cicada/utils/hash_utils.py
"""

import json

import pytest

from cicada.utils.hash_utils import (
    compute_file_hash,
    compute_hashes_for_files,
    detect_file_changes,
    load_file_hashes,
    save_file_hashes,
)


@pytest.fixture
def sample_file(tmp_path):
    """Create a sample text file for testing"""
    file_path = tmp_path / "sample.txt"
    file_path.write_text("Hello, world!\n")
    return file_path


@pytest.fixture
def sample_files(tmp_path):
    """Create multiple sample files for testing"""
    files = []
    for i in range(3):
        file_path = tmp_path / f"file{i}.ex"
        file_path.write_text(f"defmodule File{i} do\nend\n")
        files.append(file_path)
    return files


@pytest.fixture
def cicada_dir_with_hashes(tmp_path):
    """Create a .cicada directory with hashes.json"""
    cicada_dir = tmp_path / ".cicada"
    cicada_dir.mkdir()

    hashes_data = {
        "version": "1.0",
        "hashes": {
            "lib/file1.ex": "abc123",
            "lib/file2.ex": "def456",
        },
        "last_updated": "2025-01-01T00:00:00Z",
    }

    hashes_path = cicada_dir / "hashes.json"
    with open(hashes_path, "w") as f:
        json.dump(hashes_data, f)

    return cicada_dir


class TestComputeFileHash:
    """Tests for compute_file_hash function"""

    def test_compute_hash_basic(self, sample_file):
        """Test basic hash computation"""
        hash_result = compute_file_hash(str(sample_file))
        assert isinstance(hash_result, str)
        assert len(hash_result) == 32  # MD5 hash is 32 hex characters

    def test_compute_hash_deterministic(self, sample_file):
        """Test that hashing the same file produces the same hash"""
        hash1 = compute_file_hash(str(sample_file))
        hash2 = compute_file_hash(str(sample_file))
        assert hash1 == hash2

    def test_compute_hash_different_content(self, tmp_path):
        """Test that different content produces different hashes"""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("content1")
        file2.write_text("content2")

        hash1 = compute_file_hash(str(file1))
        hash2 = compute_file_hash(str(file2))
        assert hash1 != hash2

    def test_compute_hash_modified_file(self, sample_file):
        """Test that modifying a file changes its hash"""
        hash_before = compute_file_hash(str(sample_file))

        # Modify the file
        sample_file.write_text("Modified content\n")

        hash_after = compute_file_hash(str(sample_file))
        assert hash_before != hash_after

    def test_compute_hash_empty_file(self, tmp_path):
        """Test hashing an empty file"""
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("")

        hash_result = compute_file_hash(str(empty_file))
        assert isinstance(hash_result, str)
        assert len(hash_result) == 32

    def test_compute_hash_large_file(self, tmp_path):
        """Test hashing a large file (tests chunked reading)"""
        large_file = tmp_path / "large.txt"
        # Create a file larger than 4096 bytes (chunk size)
        large_file.write_text("x" * 10000)

        hash_result = compute_file_hash(str(large_file))
        assert isinstance(hash_result, str)
        assert len(hash_result) == 32

    def test_compute_hash_binary_file(self, tmp_path):
        """Test hashing a binary file"""
        binary_file = tmp_path / "binary.bin"
        binary_file.write_bytes(b"\x00\x01\x02\x03\x04")

        hash_result = compute_file_hash(str(binary_file))
        assert isinstance(hash_result, str)
        assert len(hash_result) == 32

    def test_compute_hash_nonexistent_file(self, tmp_path):
        """Test hashing a file that doesn't exist"""
        nonexistent = tmp_path / "nonexistent.txt"
        with pytest.raises(FileNotFoundError):
            compute_file_hash(str(nonexistent))

    def test_compute_hash_read_error(self, tmp_path):
        """Test handling of read errors"""
        import unittest.mock as mock

        file = tmp_path / "test.txt"
        file.write_text("content")

        # Mock open to raise an IOError
        with mock.patch("builtins.open", side_effect=IOError("Permission denied")):
            with pytest.raises(OSError, match="Error reading file"):
                compute_file_hash(str(file))


class TestLoadFileHashes:
    """Tests for load_file_hashes function"""

    def test_load_existing_hashes(self, cicada_dir_with_hashes):
        """Test loading existing hashes.json"""
        hashes = load_file_hashes(str(cicada_dir_with_hashes))

        assert isinstance(hashes, dict)
        assert "lib/file1.ex" in hashes
        assert "lib/file2.ex" in hashes
        assert hashes["lib/file1.ex"] == "abc123"
        assert hashes["lib/file2.ex"] == "def456"

    def test_load_nonexistent_hashes(self, tmp_path):
        """Test loading when hashes.json doesn't exist"""
        hashes = load_file_hashes(str(tmp_path))
        assert hashes == {}

    def test_load_invalid_json(self, tmp_path):
        """Test loading when hashes.json contains invalid JSON"""
        cicada_dir = tmp_path / ".cicada"
        cicada_dir.mkdir()
        hashes_path = cicada_dir / "hashes.json"
        hashes_path.write_text("{invalid json")

        hashes = load_file_hashes(str(cicada_dir))
        assert hashes == {}

    def test_load_missing_hashes_key(self, tmp_path):
        """Test loading when hashes.json is missing 'hashes' key"""
        cicada_dir = tmp_path / ".cicada"
        cicada_dir.mkdir()
        hashes_path = cicada_dir / "hashes.json"
        hashes_path.write_text('{"version": "1.0"}')

        hashes = load_file_hashes(str(cicada_dir))
        assert hashes == {}

    def test_load_empty_hashes(self, tmp_path):
        """Test loading when hashes.json has empty hashes"""
        cicada_dir = tmp_path / ".cicada"
        cicada_dir.mkdir()
        hashes_data = {"version": "1.0", "hashes": {}}
        hashes_path = cicada_dir / "hashes.json"
        with open(hashes_path, "w") as f:
            json.dump(hashes_data, f)

        hashes = load_file_hashes(str(cicada_dir))
        assert hashes == {}


class TestSaveFileHashes:
    """Tests for save_file_hashes function"""

    def test_save_hashes_basic(self, tmp_path):
        """Test basic hash saving"""
        cicada_dir = tmp_path / ".cicada"
        hashes = {
            "lib/file1.ex": "hash1",
            "lib/file2.ex": "hash2",
        }

        save_file_hashes(str(cicada_dir), hashes)

        hashes_path = cicada_dir / "hashes.json"
        assert hashes_path.exists()

        with open(hashes_path) as f:
            data = json.load(f)

        assert data["version"] == "1.0"
        assert data["hashes"] == hashes
        assert "last_updated" in data

    def test_save_hashes_creates_directory(self, tmp_path):
        """Test that save_file_hashes creates .cicada directory if needed"""
        cicada_dir = tmp_path / ".cicada"
        assert not cicada_dir.exists()

        save_file_hashes(str(cicada_dir), {"file.ex": "hash"})

        assert cicada_dir.exists()
        assert (cicada_dir / "hashes.json").exists()

    def test_save_empty_hashes(self, tmp_path):
        """Test saving empty hashes dictionary"""
        cicada_dir = tmp_path / ".cicada"
        save_file_hashes(str(cicada_dir), {})

        hashes_path = cicada_dir / "hashes.json"
        assert hashes_path.exists()

        with open(hashes_path) as f:
            data = json.load(f)

        assert data["hashes"] == {}

    def test_save_hashes_overwrite(self, cicada_dir_with_hashes):
        """Test overwriting existing hashes.json"""
        new_hashes = {"new/file.ex": "newhash"}
        save_file_hashes(str(cicada_dir_with_hashes), new_hashes)

        hashes_path = cicada_dir_with_hashes / "hashes.json"
        with open(hashes_path) as f:
            data = json.load(f)

        assert data["hashes"] == new_hashes

    def test_save_hashes_write_error(self, tmp_path, capsys):
        """Test handling of write errors"""
        import unittest.mock as mock

        cicada_dir = tmp_path / ".cicada"
        hashes = {"file.ex": "hash"}

        # Mock open to raise an OSError
        with mock.patch("builtins.open", side_effect=OSError("Permission denied")):
            # Should not raise, but print warning
            save_file_hashes(str(cicada_dir), hashes)

        captured = capsys.readouterr()
        assert "Warning" in captured.out
        assert "Could not save" in captured.out


class TestDetectFileChanges:
    """Tests for detect_file_changes function"""

    def test_detect_new_files(self, tmp_path):
        """Test detecting new files"""
        # Create test files
        file1 = tmp_path / "file1.ex"
        file2 = tmp_path / "file2.ex"
        file1.write_text("content 1")
        file2.write_text("content 2")

        # Compute hashes for existing files
        old_hash1 = compute_file_hash(str(file1))
        old_hash2 = compute_file_hash(str(file2))

        current_files = ["file1.ex", "file2.ex", "file3.ex"]
        old_hashes = {
            "file1.ex": old_hash1,
            "file2.ex": old_hash2,
        }

        new_files, modified_files, deleted_files = detect_file_changes(
            current_files, old_hashes, str(tmp_path)
        )

        assert "file3.ex" in new_files
        assert len(new_files) == 1
        assert len(modified_files) == 0
        assert len(deleted_files) == 0

    def test_detect_deleted_files(self, tmp_path):
        """Test detecting deleted files"""
        # Create test file
        file1 = tmp_path / "file1.ex"
        file1.write_text("content 1")

        # Compute hash for existing file
        old_hash1 = compute_file_hash(str(file1))

        current_files = ["file1.ex"]
        old_hashes = {
            "file1.ex": old_hash1,
            "file2.ex": "hash2",
            "file3.ex": "hash3",
        }

        new_files, modified_files, deleted_files = detect_file_changes(
            current_files, old_hashes, str(tmp_path)
        )

        assert len(new_files) == 0
        assert len(modified_files) == 0
        assert "file2.ex" in deleted_files
        assert "file3.ex" in deleted_files
        assert len(deleted_files) == 2

    def test_detect_modified_files(self, tmp_path):
        """Test detecting modified files"""
        # Create test files
        file1 = tmp_path / "file1.ex"
        file2 = tmp_path / "file2.ex"
        file1.write_text("original content 1")
        file2.write_text("original content 2")

        # Old hashes
        old_hash1 = compute_file_hash(str(file1))
        old_hash2 = compute_file_hash(str(file2))
        old_hashes = {
            "file1.ex": old_hash1,
            "file2.ex": old_hash2,
        }

        # Modify file1
        file1.write_text("modified content 1")

        current_files = ["file1.ex", "file2.ex"]
        new_files, modified_files, deleted_files = detect_file_changes(
            current_files, old_hashes, str(tmp_path)
        )

        assert "file1.ex" in modified_files
        assert len(modified_files) == 1
        assert len(new_files) == 0
        assert len(deleted_files) == 0

    def test_detect_no_changes(self, tmp_path):
        """Test when no files have changed"""
        # Create test files
        file1 = tmp_path / "file1.ex"
        file1.write_text("content 1")

        old_hash1 = compute_file_hash(str(file1))
        old_hashes = {"file1.ex": old_hash1}

        current_files = ["file1.ex"]
        new_files, modified_files, deleted_files = detect_file_changes(
            current_files, old_hashes, str(tmp_path)
        )

        assert len(new_files) == 0
        assert len(modified_files) == 0
        assert len(deleted_files) == 0

    def test_detect_mixed_changes(self, tmp_path):
        """Test detecting a mix of new, modified, and deleted files"""
        # Create test files
        file1 = tmp_path / "file1.ex"
        file2 = tmp_path / "file2.ex"
        file3 = tmp_path / "file3.ex"

        file1.write_text("content 1")
        file2.write_text("original content 2")

        old_hash1 = compute_file_hash(str(file1))
        old_hash2 = compute_file_hash(str(file2))

        old_hashes = {
            "file1.ex": old_hash1,  # Unchanged
            "file2.ex": old_hash2,  # Will be modified
            "file4.ex": "hash4",  # Deleted
        }

        # Modify file2, create file3
        file2.write_text("modified content 2")
        file3.write_text("new file")

        current_files = ["file1.ex", "file2.ex", "file3.ex"]
        new_files, modified_files, deleted_files = detect_file_changes(
            current_files, old_hashes, str(tmp_path)
        )

        assert "file3.ex" in new_files
        assert "file2.ex" in modified_files
        assert "file4.ex" in deleted_files
        assert len(new_files) == 1
        assert len(modified_files) == 1
        assert len(deleted_files) == 1

    def test_detect_changes_empty_old_hashes(self, tmp_path):
        """Test detecting changes when old_hashes is empty (first run)"""
        file1 = tmp_path / "file1.ex"
        file1.write_text("content 1")

        current_files = ["file1.ex"]
        new_files, modified_files, deleted_files = detect_file_changes(
            current_files, {}, str(tmp_path)
        )

        assert "file1.ex" in new_files
        assert len(new_files) == 1
        assert len(modified_files) == 0
        assert len(deleted_files) == 0

    def test_detect_changes_file_hash_error(self, tmp_path, capsys):
        """Test handling of file hash errors during change detection"""
        import unittest.mock as mock

        file1 = tmp_path / "file1.ex"
        file1.write_text("content 1")

        old_hash1 = compute_file_hash(str(file1))
        old_hashes = {"file1.ex": old_hash1}
        current_files = ["file1.ex"]

        # Mock compute_file_hash to raise an error
        with mock.patch(
            "cicada.utils.hash_utils.compute_file_hash", side_effect=OSError("Read error")
        ):
            new_files, modified_files, deleted_files = detect_file_changes(
                current_files, old_hashes, str(tmp_path)
            )

        # File should be treated as deleted due to hash error
        assert "file1.ex" in deleted_files
        captured = capsys.readouterr()
        assert "Warning" in captured.out


class TestComputeHashesForFiles:
    """Tests for compute_hashes_for_files function"""

    def test_compute_hashes_single_file(self, tmp_path):
        """Test computing hash for a single file"""
        file1 = tmp_path / "file1.ex"
        file1.write_text("content 1")

        hashes = compute_hashes_for_files(["file1.ex"], str(tmp_path))

        assert "file1.ex" in hashes
        assert isinstance(hashes["file1.ex"], str)
        assert len(hashes["file1.ex"]) == 32

    def test_compute_hashes_multiple_files(self, sample_files):
        """Test computing hashes for multiple files"""
        tmp_path = sample_files[0].parent
        relative_files = [f.name for f in sample_files]

        hashes = compute_hashes_for_files(relative_files, str(tmp_path))

        assert len(hashes) == 3
        for file in relative_files:
            assert file in hashes
            assert len(hashes[file]) == 32

    def test_compute_hashes_empty_list(self, tmp_path):
        """Test computing hashes for empty file list"""
        hashes = compute_hashes_for_files([], str(tmp_path))
        assert hashes == {}

    def test_compute_hashes_nonexistent_file(self, tmp_path, capsys):
        """Test computing hashes when a file doesn't exist"""
        hashes = compute_hashes_for_files(["nonexistent.ex"], str(tmp_path))

        # Should return empty dict for the nonexistent file
        # and print a warning
        assert "nonexistent.ex" not in hashes
        captured = capsys.readouterr()
        assert "Warning" in captured.out

    def test_compute_hashes_nested_paths(self, tmp_path):
        """Test computing hashes for files in nested directories"""
        nested_dir = tmp_path / "lib" / "subdir"
        nested_dir.mkdir(parents=True)
        file1 = nested_dir / "file1.ex"
        file1.write_text("content 1")

        relative_path = "lib/subdir/file1.ex"
        hashes = compute_hashes_for_files([relative_path], str(tmp_path))

        assert relative_path in hashes
        assert len(hashes[relative_path]) == 32
