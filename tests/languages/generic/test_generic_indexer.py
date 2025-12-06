"""Tests for the generic file indexer."""

import json
import tempfile
from pathlib import Path

import pytest

from cicada.languages.generic import GenericFileIndexer


class TestGenericFileIndexer:
    """Tests for GenericFileIndexer."""

    def test_indexer_basic(self):
        """Test basic indexing of text files."""
        indexer = GenericFileIndexer()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a simple markdown file
            readme = Path(tmpdir) / "README.md"
            readme.write_text("# Test Project\n\nThis is a test project for authentication.")

            output_path = Path(tmpdir) / "index.json"
            result = indexer.index_repository(tmpdir, output_path)

            assert result["success"] is True
            assert result["modules_count"] == 1
            assert result["functions_count"] == 0  # Generic files have no functions

            with open(output_path) as f:
                data = json.load(f)

            assert "README.md" in data["modules"]
            assert data["modules"]["README.md"]["file"] == "README.md"
            assert data["modules"]["README.md"]["functions"] == []

    def test_indexer_keyword_extraction(self):
        """Test that keywords are extracted from file content."""
        indexer = GenericFileIndexer()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file with distinct keywords
            readme = Path(tmpdir) / "README.md"
            readme.write_text(
                """# Authentication System

This module provides authentication and authorization
for users. It handles login, logout, and session management.

## Installation

Install the authentication package using pip.
"""
            )

            output_path = Path(tmpdir) / "index.json"
            result = indexer.index_repository(tmpdir, output_path)

            assert result["success"] is True

            with open(output_path) as f:
                data = json.load(f)

            module = data["modules"]["README.md"]
            assert "keywords" in module

            keywords = module["keywords"]
            # Should extract authentication-related keywords
            assert "authentication" in keywords or "auth" in keywords

    def test_indexer_excludes_language_files(self):
        """Test that language-specific files are excluded."""
        indexer = GenericFileIndexer(excluded_extensions={".py", ".ex"})

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create various files
            Path(tmpdir, "README.md").write_text("# Readme")
            Path(tmpdir, "main.py").write_text("print('hello')")
            Path(tmpdir, "lib.ex").write_text("defmodule Lib do end")
            Path(tmpdir, "config.json").write_text('{"key": "value"}')

            output_path = Path(tmpdir) / "index.json"
            result = indexer.index_repository(tmpdir, output_path)

            assert result["success"] is True

            with open(output_path) as f:
                data = json.load(f)

            modules = data["modules"]
            # Should include markdown and json
            assert "README.md" in modules
            assert "config.json" in modules
            # Should exclude Python and Elixir
            assert "main.py" not in modules
            assert "lib.ex" not in modules

    def test_indexer_respects_gitignore(self):
        """Test that gitignored files are not indexed."""
        indexer = GenericFileIndexer()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create .gitignore
            gitignore = Path(tmpdir) / ".gitignore"
            gitignore.write_text("*.log\nbuild/\n")

            # Create various files
            Path(tmpdir, "README.md").write_text("# Readme")
            Path(tmpdir, "debug.log").write_text("some logs")
            build_dir = Path(tmpdir) / "build"
            build_dir.mkdir()
            Path(build_dir, "output.txt").write_text("build output")

            output_path = Path(tmpdir) / "index.json"
            result = indexer.index_repository(tmpdir, output_path)

            assert result["success"] is True

            with open(output_path) as f:
                data = json.load(f)

            modules = data["modules"]
            # Should include README
            assert "README.md" in modules
            # Should exclude gitignored files
            assert "debug.log" not in modules
            assert "build/output.txt" not in modules

    def test_indexer_skips_binary_files(self):
        """Test that binary files are not indexed.

        Covers both null-byte detection and mimetype-based detection.
        """
        indexer = GenericFileIndexer()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a text file
            Path(tmpdir, "readme.txt").write_text("Hello world")

            # Create a binary file (with null bytes) to exercise null-byte heuristic
            binary_file = Path(tmpdir, "image.dat")
            binary_file.write_bytes(b"\x00\x01\x02\x03\x04\x05")

            # Create a PNG file to exercise mimetype-based detection
            png_file = Path(tmpdir, "picture.png")
            png_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\x0dIHDR")

            output_path = Path(tmpdir) / "index.json"
            result = indexer.index_repository(tmpdir, output_path)

            assert result["success"] is True

            with open(output_path) as f:
                data = json.load(f)

            modules = data["modules"]
            # Should include text file
            assert "readme.txt" in modules
            # Should exclude binary files (both by null-byte and mimetype detection)
            assert "image.dat" not in modules
            assert "picture.png" not in modules

    def test_indexer_skips_excluded_directories(self):
        """Test that excluded directories like .git are not indexed."""
        indexer = GenericFileIndexer()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create normal file
            Path(tmpdir, "README.md").write_text("# Readme")

            # Create files in excluded directories
            git_dir = Path(tmpdir) / ".git"
            git_dir.mkdir()
            Path(git_dir, "config").write_text("git config")

            node_modules = Path(tmpdir) / "node_modules"
            node_modules.mkdir()
            Path(node_modules, "package.json").write_text('{"name": "dep"}')

            output_path = Path(tmpdir) / "index.json"
            result = indexer.index_repository(tmpdir, output_path)

            assert result["success"] is True

            with open(output_path) as f:
                data = json.load(f)

            modules = data["modules"]
            # Should include README
            assert "README.md" in modules
            # Should exclude files in .git and node_modules
            assert ".git/config" not in modules
            assert "node_modules/package.json" not in modules

    def test_indexer_empty_repo(self):
        """Test indexing an empty repository."""
        indexer = GenericFileIndexer()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "index.json"
            result = indexer.index_repository(tmpdir, output_path)

            assert result["success"] is True
            assert result["modules_count"] == 0
            assert result["files_indexed"] == 0

    def test_indexer_no_changes_fast_path(self):
        """Test incremental indexing fast path when no changes are detected."""
        indexer = GenericFileIndexer()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a repository with at least one file
            repo_root = Path(tmpdir)
            (repo_root / "README.md").write_text("# Initial content")

            # Put output in a subdirectory to avoid it being indexed
            output_dir = repo_root / ".cicada"
            output_dir.mkdir()
            output_path = output_dir / "index.json"

            # Initial indexing
            first_result = indexer.index_repository(repo_root, output_path)
            assert first_result["success"] is True
            assert first_result["modules_count"] == 1
            assert first_result["files_indexed"] == 1

            # Second run without any changes should hit the "no changes detected" fast path
            second_result = indexer.index_repository(repo_root, output_path)
            assert second_result["success"] is True
            # Fast-path incremental run should be skipped and not re-index any files
            assert second_result.get("skipped") is True
            assert second_result["files_indexed"] == 0

    def test_indexer_nested_directories(self):
        """Test that files in nested directories are indexed."""
        indexer = GenericFileIndexer()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create nested directory structure
            docs_dir = Path(tmpdir) / "docs" / "api"
            docs_dir.mkdir(parents=True)
            Path(docs_dir, "endpoints.md").write_text("# API Endpoints")

            output_path = Path(tmpdir) / "index.json"
            result = indexer.index_repository(tmpdir, output_path)

            assert result["success"] is True

            with open(output_path) as f:
                data = json.load(f)

            # Check nested file is indexed with relative path
            assert "docs/api/endpoints.md" in data["modules"]

    def test_indexer_verbose_output(self, capsys):
        """Test verbose output during indexing."""
        indexer = GenericFileIndexer(verbose=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "README.md").write_text("# Test")

            output_path = Path(tmpdir) / "index.json"
            indexer.index_repository(tmpdir, output_path, verbose=True)

            captured = capsys.readouterr()
            assert "Indexing generic files" in captured.out
            assert "Found" in captured.out

    def test_merge_into_existing_index(self):
        """Test merging generic files into an existing index."""
        indexer = GenericFileIndexer()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create an existing index with a Python module
            existing_index = {
                "modules": {
                    "MyModule": {
                        "file": "mymodule.py",
                        "line": 1,
                        "functions": [{"name": "hello", "arity": 0}],
                    }
                },
                "metadata": {"language": "python", "total_modules": 1},
            }

            index_path = Path(tmpdir) / "index.json"
            with open(index_path, "w") as f:
                json.dump(existing_index, f)

            # Create a markdown file
            Path(tmpdir, "README.md").write_text("# Project Documentation")

            # Merge generic files
            result = indexer.merge_into_existing_index(
                existing_index_path=index_path,
                repo_path=Path(tmpdir),
                verbose=False,
            )

            assert result["success"] is True

            # Load merged index
            with open(index_path) as f:
                merged = json.load(f)

            # Should have both the Python module and the markdown file
            assert "MyModule" in merged["modules"]
            assert "README.md" in merged["modules"]
            # Python module should be unchanged
            assert merged["modules"]["MyModule"]["functions"][0]["name"] == "hello"

    def test_merge_into_existing_index_with_deletions(self):
        """Test merging generic files with deleted file handling."""
        indexer = GenericFileIndexer(excluded_extensions={".py"})

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a subdirectory for storage to avoid it being indexed
            storage_dir = Path(tmpdir) / ".cicada"
            storage_dir.mkdir()

            # First, do an initial index with README.md present
            Path(tmpdir, "README.md").write_text("# Test")

            initial_index = {
                "modules": {
                    "README.md": {
                        "file": "README.md",
                        "line": 1,
                        "functions": [],
                    },
                },
                "metadata": {"language": "generic", "total_modules": 1},
            }

            index_path = storage_dir / "index.json"
            with open(index_path, "w") as f:
                json.dump(initial_index, f)

            # Initialize the hashes file by doing a merge (this creates the hashes file)
            result1 = indexer.merge_into_existing_index(
                existing_index_path=index_path,
                repo_path=Path(tmpdir),
                verbose=False,
            )
            assert result1["success"] is True

            # Now delete README.md from disk
            Path(tmpdir, "README.md").unlink()

            # Merge again - should detect deletion and remove README.md from index
            result2 = indexer.merge_into_existing_index(
                existing_index_path=index_path,
                repo_path=Path(tmpdir),
                verbose=False,
            )

            assert result2["success"] is True

            # Load merged index
            with open(index_path) as f:
                merged = json.load(f)

            # Deleted generic file should be removed from the index
            assert "README.md" not in merged["modules"]

    def test_incremental_indexing(self):
        """Test incremental indexing only processes changed files."""
        indexer = GenericFileIndexer()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Put output in a subdirectory to avoid it being indexed as a text file
            output_dir = Path(tmpdir) / ".cicada"
            output_dir.mkdir()
            output_path = output_dir / "index.json"

            # Create initial files
            Path(tmpdir, "file1.md").write_text("# File 1")
            Path(tmpdir, "file2.md").write_text("# File 2")

            # First index
            result1 = indexer.index_repository(tmpdir, output_path)
            assert result1["success"] is True
            assert result1["files_indexed"] == 2

            # Verify both files are in the index
            with open(output_path) as f:
                data = json.load(f)
            assert "file1.md" in data["modules"]
            assert "file2.md" in data["modules"]
            # The index.json should not be indexed since it's in .cicada/
            assert ".cicada/index.json" not in data["modules"]

            # Second run without any changes should be a no-op
            result2 = indexer.index_repository(tmpdir, output_path)
            assert result2["success"] is True
            assert result2["files_indexed"] == 0
            assert result2.get("skipped") is True

            # Modify one file and run again; only that file should be re-indexed
            Path(tmpdir, "file1.md").write_text("# File 1 - updated")
            result3 = indexer.index_repository(tmpdir, output_path)
            assert result3["success"] is True
            assert result3["files_indexed"] == 1
            assert result3.get("skipped") is not True

            # Delete the other file and run again
            Path(tmpdir, "file2.md").unlink()
            result4 = indexer.index_repository(tmpdir, output_path)
            assert result4["success"] is True

            # Verify deletion is reflected in the index
            with open(output_path) as f:
                data = json.load(f)
            assert "file1.md" in data["modules"]
            assert "file2.md" not in data["modules"]

    def test_get_language_name(self):
        """Test get_language_name returns 'generic'."""
        indexer = GenericFileIndexer()
        assert indexer.get_language_name() == "generic"

    def test_is_text_file_for_common_types(self):
        """Test _is_text_file correctly identifies text files."""
        indexer = GenericFileIndexer()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create text files
            md_file = Path(tmpdir, "readme.md")
            md_file.write_text("# Readme")

            json_file = Path(tmpdir, "config.json")
            json_file.write_text('{"key": "value"}')

            txt_file = Path(tmpdir, "notes.txt")
            txt_file.write_text("Some notes")

            # All should be detected as text
            assert indexer._is_text_file(md_file) is True
            assert indexer._is_text_file(json_file) is True
            assert indexer._is_text_file(txt_file) is True

    def test_load_gitignore_with_comments(self):
        """Test that gitignore comments are handled correctly."""
        indexer = GenericFileIndexer()

        with tempfile.TemporaryDirectory() as tmpdir:
            gitignore = Path(tmpdir) / ".gitignore"
            gitignore.write_text(
                """# Comment line
*.log
# Another comment
build/
"""
            )

            spec = indexer._load_gitignore(Path(tmpdir))

            # Should match patterns but not comments
            assert spec.match_file("debug.log")
            assert spec.match_file("build/output.txt")
            # Comments should not be patterns
            assert not spec.match_file("# Comment line")


class TestGenericFileIndexerSkipLargeFiles:
    """Tests for large file handling."""

    def test_skips_files_over_line_limit(self):
        """Test that files over MAX_LINES are skipped."""
        indexer = GenericFileIndexer()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file with more than MAX_LINES
            large_file = Path(tmpdir, "large.txt")
            # Write 10001 lines (just over the limit)
            large_file.write_text("\n".join(["line"] * 10001))

            # Create a normal file
            normal_file = Path(tmpdir, "normal.txt")
            normal_file.write_text("Just a few lines\nof text")

            output_path = Path(tmpdir) / "index.json"
            result = indexer.index_repository(tmpdir, output_path, verbose=False)

            assert result["success"] is True

            with open(output_path) as f:
                data = json.load(f)

            # Normal file should be indexed
            assert "normal.txt" in data["modules"]
            # Large file should be skipped
            assert "large.txt" not in data["modules"]
