"""
Author: Cursor(Auto)

Comprehensive tests for LineMapper.

Tests all methods and error paths with proper mocking to achieve high coverage
while maintaining loose coupling to implementation details.
"""

import subprocess

import pytest

from cicada.pr_indexer.line_mapper import LineMapper
from tests.mocks.git_responses import (
    create_git_show_response,
)
from tests.mocks.subprocess_mocks import MockCompletedProcess, MockSubprocessRunner


class TestLineMapperInit:
    """Test LineMapper initialization."""

    def test_init_with_path(self, tmp_path):
        """Test initialization with Path object."""
        mapper = LineMapper(tmp_path)

        assert mapper.repo_path == tmp_path
        assert mapper.runner is not None

    def test_init_with_string_path(self, tmp_path):
        """Test initialization with string path."""
        mapper = LineMapper(str(tmp_path))

        assert mapper.repo_path == str(tmp_path)
        assert mapper.runner is not None


class TestMapAllCommentLines:
    """Test batch comment line mapping."""

    def test_map_all_comment_lines_success(self, tmp_path, capsys):
        """Test successful line mapping for all comments."""
        mock_runner = MockSubprocessRunner()

        # Mock file existence check
        mock_runner.add_git_response(
            command=["ls-files", "test.py"],
            response=MockCompletedProcess(returncode=0, stdout="test.py"),
        )

        # Mock git show for HEAD
        mock_runner.add_git_response(
            command=["show", "HEAD:test.py"],
            response=MockCompletedProcess(
                returncode=0,
                stdout=create_git_show_response(
                    _ref="HEAD",
                    file_path="test.py",
                    content=[
                        "def hello():",
                        "    print('Hello')",
                        "",
                        "def world():",
                        "    print('World')",
                    ],
                ),
            ),
        )

        # Mock git show for commit
        mock_runner.add_git_response(
            command=["show", "abc123:test.py"],
            response=MockCompletedProcess(
                returncode=0,
                stdout=create_git_show_response(
                    _ref="abc123",
                    file_path="test.py",
                    content=[
                        "def hello():",
                        "    print('Hello')",
                        "",
                        "def world():",
                        "    print('World')",
                    ],
                ),
            ),
        )

        mapper = LineMapper(tmp_path)
        mapper.runner = mock_runner

        prs = [
            {
                "number": 1,
                "comments": [
                    {
                        "original_line": 2,
                        "commit_sha": "abc123",
                        "path": "test.py",
                        "line": None,  # Will be set by mapping
                    }
                ],
            }
        ]

        mapper.map_all_comment_lines(prs)

        # Check that line was mapped
        assert prs[0]["comments"][0]["line"] == 2

        # Check output
        captured = capsys.readouterr()
        assert "Mapped 1 comments" in captured.out

    def test_map_all_comment_lines_empty_prs(self, tmp_path, capsys):
        """Test line mapping with empty PR list."""
        mapper = LineMapper(tmp_path)
        mapper.runner = MockSubprocessRunner()

        mapper.map_all_comment_lines([])

        captured = capsys.readouterr()
        assert "Mapping comment lines to current file state" in captured.out
        assert "Mapped 0 comments" not in captured.out  # Should return early

    def test_map_all_comment_lines_no_comments(self, tmp_path, capsys):
        """Test line mapping with PRs that have no comments."""
        mapper = LineMapper(tmp_path)
        mapper.runner = MockSubprocessRunner()

        prs = [{"number": 1, "comments": []}, {"number": 2, "comments": []}]

        mapper.map_all_comment_lines(prs)

        captured = capsys.readouterr()
        assert "Mapping comment lines to current file state" in captured.out
        assert "Mapped 0 comments" not in captured.out  # Should return early

    def test_map_all_comment_lines_partial_mapping(self, tmp_path, capsys):
        """Test line mapping with partial success."""
        mock_runner = MockSubprocessRunner()

        # Mock file existence for first file
        mock_runner.add_git_response(
            command=["ls-files", "existing.py"],
            response=MockCompletedProcess(returncode=0, stdout="existing.py"),
        )

        # Mock file existence for second file (not found)
        mock_runner.add_git_response(
            command=["ls-files", "missing.py"],
            response=MockCompletedProcess(returncode=0, stdout=""),
        )

        # Mock git show for existing file
        mock_runner.add_git_response(
            command=["show", "HEAD:existing.py"],
            response=MockCompletedProcess(
                returncode=0,
                stdout=create_git_show_response(
                    _ref="HEAD",
                    file_path="existing.py",
                    content=["line1", "line2", "line3"],
                ),
            ),
        )

        # Mock git show for commit
        mock_runner.add_git_response(
            command=["show", "abc123:existing.py"],
            response=MockCompletedProcess(
                returncode=0,
                stdout=create_git_show_response(
                    _ref="abc123",
                    file_path="existing.py",
                    content=["line1", "line2", "line3"],
                ),
            ),
        )

        mapper = LineMapper(tmp_path)
        mapper.runner = mock_runner

        prs = [
            {
                "number": 1,
                "comments": [
                    {
                        "original_line": 2,
                        "commit_sha": "abc123",
                        "path": "existing.py",
                        "line": None,
                    },
                    {
                        "original_line": 1,
                        "commit_sha": "def456",
                        "path": "missing.py",
                        "line": None,
                    },
                ],
            }
        ]

        mapper.map_all_comment_lines(prs)

        # First comment should be mapped, second should not
        assert prs[0]["comments"][0]["line"] == 2
        assert prs[0]["comments"][1]["line"] is None

        captured = capsys.readouterr()
        assert "Mapped 1 comments, 1 unmappable" in captured.out

    def test_map_all_comment_lines_keyboard_interrupt(self, tmp_path, capsys):
        """Test line mapping with keyboard interrupt."""
        mock_runner = MockSubprocessRunner()

        # Mock file existence
        mock_runner.add_git_response(
            command=["ls-files", "test.py"],
            response=MockCompletedProcess(returncode=0, stdout="test.py"),
        )

        # Mock git show to raise KeyboardInterrupt
        def mock_run_git_command(*_args, **_kwargs):
            raise KeyboardInterrupt()

        mapper = LineMapper(tmp_path)
        mapper.runner = MockSubprocessRunner()
        mapper.runner.run_git_command = mock_run_git_command

        prs = [
            {
                "number": 1,
                "comments": [
                    {
                        "original_line": 2,
                        "commit_sha": "abc123",
                        "path": "test.py",
                        "line": None,
                    }
                ],
            }
        ]

        with pytest.raises(KeyboardInterrupt):
            mapper.map_all_comment_lines(prs)

        captured = capsys.readouterr()
        assert "Line mapping interrupted" in captured.out

    def test_map_all_comment_lines_missing_fields(self, tmp_path, capsys):
        """Test line mapping with missing comment fields."""
        mapper = LineMapper(tmp_path)
        mapper.runner = MockSubprocessRunner()

        prs = [
            {
                "number": 1,
                "comments": [
                    {
                        "original_line": None,  # Missing
                        "commit_sha": "abc123",
                        "path": "test.py",
                        "line": None,
                    },
                    {
                        "original_line": 2,
                        "commit_sha": None,  # Missing
                        "path": "test.py",
                        "line": None,
                    },
                    {
                        "original_line": 2,
                        "commit_sha": "abc123",
                        "path": None,  # Missing
                        "line": None,
                    },
                ],
            }
        ]

        mapper.map_all_comment_lines(prs)

        # All comments should have line set to None
        for comment in prs[0]["comments"]:
            assert comment["line"] is None

        captured = capsys.readouterr()
        assert "Mapped 0 comments, 3 unmappable" in captured.out


class TestMapLineToCurrentSuccess:
    """Test successful line mapping scenarios."""

    def test_map_line_to_current_exact_match(self, tmp_path):
        """Test line mapping with exact match."""
        mock_runner = MockSubprocessRunner()

        # Mock file existence
        mock_runner.add_git_response(
            command=["ls-files", "test.py"],
            response=MockCompletedProcess(returncode=0, stdout="test.py"),
        )

        # Mock git show for HEAD
        mock_runner.add_git_response(
            command=["show", "HEAD:test.py"],
            response=MockCompletedProcess(
                returncode=0,
                stdout=create_git_show_response(
                    _ref="HEAD",
                    file_path="test.py",
                    content=["line1", "line2", "line3"],
                ),
            ),
        )

        # Mock git show for commit
        mock_runner.add_git_response(
            command=["show", "abc123:test.py"],
            response=MockCompletedProcess(
                returncode=0,
                stdout=create_git_show_response(
                    _ref="abc123",
                    file_path="test.py",
                    content=["line1", "line2", "line3"],
                ),
            ),
        )

        mapper = LineMapper(tmp_path)
        mapper.runner = mock_runner

        result = mapper.map_line_to_current("test.py", 2, "abc123")

        assert result == 2

    def test_map_line_to_current_nearby_match(self, tmp_path):
        """Test line mapping with nearby match."""
        mock_runner = MockSubprocessRunner()

        # Mock file existence
        mock_runner.add_git_response(
            command=["ls-files", "test.py"],
            response=MockCompletedProcess(returncode=0, stdout="test.py"),
        )

        # Mock git show for HEAD (line moved down by 1)
        mock_runner.add_git_response(
            command=["show", "HEAD:test.py"],
            response=MockCompletedProcess(
                returncode=0,
                stdout=create_git_show_response(
                    _ref="HEAD",
                    file_path="test.py",
                    content=["line1", "new_line", "line2", "line3"],
                ),
            ),
        )

        # Mock git show for commit
        mock_runner.add_git_response(
            command=["show", "abc123:test.py"],
            response=MockCompletedProcess(
                returncode=0,
                stdout=create_git_show_response(
                    _ref="abc123",
                    file_path="test.py",
                    content=["line1", "line2", "line3"],
                ),
            ),
        )

        mapper = LineMapper(tmp_path)
        mapper.runner = mock_runner

        result = mapper.map_line_to_current("test.py", 2, "abc123")

        assert result == 3  # line2 moved from position 2 to 3

    def test_map_line_to_current_with_offset(self, tmp_path):
        """Test line mapping with larger offset."""
        mock_runner = MockSubprocessRunner()

        # Mock file existence
        mock_runner.add_git_response(
            command=["ls-files", "test.py"],
            response=MockCompletedProcess(returncode=0, stdout="test.py"),
        )

        # Mock git show for HEAD (line moved down by 5)
        head_content = ["line1"] + [f"new_line_{i}" for i in range(5)] + ["line2", "line3"]
        mock_runner.add_git_response(
            command=["show", "HEAD:test.py"],
            response=MockCompletedProcess(
                returncode=0,
                stdout=create_git_show_response(
                    _ref="HEAD", file_path="test.py", content=head_content
                ),
            ),
        )

        # Mock git show for commit
        mock_runner.add_git_response(
            command=["show", "abc123:test.py"],
            response=MockCompletedProcess(
                returncode=0,
                stdout=create_git_show_response(
                    _ref="abc123",
                    file_path="test.py",
                    content=["line1", "line2", "line3"],
                ),
            ),
        )

        mapper = LineMapper(tmp_path)
        mapper.runner = mock_runner

        result = mapper.map_line_to_current("test.py", 2, "abc123")

        assert result == 7  # line2 moved from position 2 to 7


class TestMapLineToCurrentFailure:
    """Test line mapping failure scenarios."""

    def test_map_line_to_current_file_missing(self, tmp_path):
        """Test line mapping when file is missing."""
        mock_runner = MockSubprocessRunner()

        # Mock file not found
        mock_runner.add_git_response(
            command=["ls-files", "missing.py"],
            response=MockCompletedProcess(returncode=0, stdout=""),
        )

        mapper = LineMapper(tmp_path)
        mapper.runner = mock_runner

        result = mapper.map_line_to_current("missing.py", 2, "abc123")

        assert result is None

    def test_map_line_to_current_line_deleted(self, tmp_path):
        """Test line mapping when line was deleted."""
        mock_runner = MockSubprocessRunner()

        # Mock file existence
        mock_runner.add_git_response(
            command=["ls-files", "test.py"],
            response=MockCompletedProcess(returncode=0, stdout="test.py"),
        )

        # Mock git show for HEAD (line deleted)
        mock_runner.add_git_response(
            command=["show", "HEAD:test.py"],
            response=MockCompletedProcess(
                returncode=0,
                stdout=create_git_show_response(
                    _ref="HEAD",
                    file_path="test.py",
                    content=["line1", "line3"],  # line2 deleted
                ),
            ),
        )

        # Mock git show for commit
        mock_runner.add_git_response(
            command=["show", "abc123:test.py"],
            response=MockCompletedProcess(
                returncode=0,
                stdout=create_git_show_response(
                    _ref="abc123",
                    file_path="test.py",
                    content=["line1", "line2", "line3"],
                ),
            ),
        )

        mapper = LineMapper(tmp_path)
        mapper.runner = mock_runner

        result = mapper.map_line_to_current("test.py", 2, "abc123")

        assert result is None

    def test_map_line_to_current_empty_line(self, tmp_path):
        """Test line mapping with empty line."""
        mock_runner = MockSubprocessRunner()

        # Mock file existence
        mock_runner.add_git_response(
            command=["ls-files", "test.py"],
            response=MockCompletedProcess(returncode=0, stdout="test.py"),
        )

        # Mock git show for HEAD
        mock_runner.add_git_response(
            command=["show", "HEAD:test.py"],
            response=MockCompletedProcess(
                returncode=0,
                stdout=create_git_show_response(
                    _ref="HEAD", file_path="test.py", content=["line1", "", "line3"]
                ),
            ),
        )

        # Mock git show for commit (empty line at position 2)
        mock_runner.add_git_response(
            command=["show", "abc123:test.py"],
            response=MockCompletedProcess(
                returncode=0,
                stdout=create_git_show_response(
                    _ref="abc123", file_path="test.py", content=["line1", "", "line3"]
                ),
            ),
        )

        mapper = LineMapper(tmp_path)
        mapper.runner = mock_runner

        result = mapper.map_line_to_current("test.py", 2, "abc123")

        assert result is None  # Empty lines can't be tracked

    def test_map_line_to_current_invalid_line_number(self, tmp_path):
        """Test line mapping with invalid line number."""
        mock_runner = MockSubprocessRunner()

        # Mock file existence
        mock_runner.add_git_response(
            command=["ls-files", "test.py"],
            response=MockCompletedProcess(returncode=0, stdout="test.py"),
        )

        # Mock git show for HEAD
        mock_runner.add_git_response(
            command=["show", "HEAD:test.py"],
            response=MockCompletedProcess(
                returncode=0,
                stdout=create_git_show_response(
                    _ref="HEAD", file_path="test.py", content=["line1", "line2"]
                ),
            ),
        )

        # Mock git show for commit (only 2 lines, asking for line 5)
        mock_runner.add_git_response(
            command=["show", "abc123:test.py"],
            response=MockCompletedProcess(
                returncode=0,
                stdout=create_git_show_response(
                    _ref="abc123", file_path="test.py", content=["line1", "line2"]
                ),
            ),
        )

        mapper = LineMapper(tmp_path)
        mapper.runner = mock_runner

        result = mapper.map_line_to_current("test.py", 5, "abc123")

        assert result is None  # Line 5 doesn't exist

    def test_map_line_to_current_missing_parameters(self, tmp_path):
        """Test line mapping with missing parameters."""
        mapper = LineMapper(tmp_path)
        mapper.runner = MockSubprocessRunner()

        # Test with None values
        assert mapper.map_line_to_current(None, 2, "abc123") is None
        assert mapper.map_line_to_current("test.py", None, "abc123") is None
        assert mapper.map_line_to_current("test.py", 2, None) is None
        assert mapper.map_line_to_current("", 2, "abc123") is None
        assert mapper.map_line_to_current("test.py", 0, "abc123") is None

    def test_map_line_to_current_subprocess_error(self, tmp_path):
        """Test line mapping with subprocess error."""
        mock_runner = MockSubprocessRunner()

        # Mock file existence
        mock_runner.add_git_response(
            command=["ls-files", "test.py"],
            response=MockCompletedProcess(returncode=0, stdout="test.py"),
        )

        # Mock git show to raise exception
        def mock_run_git_command(*_args, **_kwargs):
            raise subprocess.CalledProcessError(1, "git", "Error")

        mapper = LineMapper(tmp_path)
        mapper.runner = MockSubprocessRunner()
        mapper.runner.run_git_command = mock_run_git_command

        result = mapper.map_line_to_current("test.py", 2, "abc123")

        assert result is None


class TestFileExists:
    """Test file existence checking."""

    def test_file_exists_true(self, tmp_path):
        """Test file existence check when file exists."""
        mock_runner = MockSubprocessRunner()
        mock_runner.add_git_response(
            command=["ls-files", "test.py"],
            response=MockCompletedProcess(returncode=0, stdout="test.py"),
        )

        mapper = LineMapper(tmp_path)
        mapper.runner = mock_runner

        result = mapper._file_exists("test.py")

        assert result is True

    def test_file_exists_false(self, tmp_path):
        """Test file existence check when file doesn't exist."""
        mock_runner = MockSubprocessRunner()
        mock_runner.add_git_response(
            command=["ls-files", "missing.py"],
            response=MockCompletedProcess(returncode=0, stdout=""),
        )

        mapper = LineMapper(tmp_path)
        mapper.runner = mock_runner

        result = mapper._file_exists("missing.py")

        assert result is False

    def test_file_exists_subprocess_error(self, tmp_path):
        """Test file existence check with subprocess error."""
        mock_runner = MockSubprocessRunner()
        mock_runner.add_git_response(
            command=["ls-files", "test.py"],
            response=MockCompletedProcess(returncode=1, stderr="Error"),
        )

        mapper = LineMapper(tmp_path)
        mapper.runner = mock_runner

        result = mapper._file_exists("test.py")

        assert result is False


class TestGetFileLines:
    """Test file content retrieval."""

    def test_get_file_lines_success_head(self, tmp_path):
        """Test successful file content retrieval for HEAD."""
        mock_runner = MockSubprocessRunner()
        mock_runner.add_git_response(
            command=["show", "HEAD:test.py"],
            response=MockCompletedProcess(
                returncode=0,
                stdout=create_git_show_response(
                    _ref="HEAD",
                    file_path="test.py",
                    content=["line1", "line2", "line3"],
                ),
            ),
        )

        mapper = LineMapper(tmp_path)
        mapper.runner = mock_runner

        result = mapper._get_file_lines("HEAD", "test.py")

        assert result == ["line1", "line2", "line3"]

    def test_get_file_lines_success_commit_sha(self, tmp_path):
        """Test successful file content retrieval for commit SHA."""
        mock_runner = MockSubprocessRunner()
        mock_runner.add_git_response(
            command=["show", "abc123:test.py"],
            response=MockCompletedProcess(
                returncode=0,
                stdout=create_git_show_response(
                    _ref="abc123", file_path="test.py", content=["line1", "line2"]
                ),
            ),
        )

        mapper = LineMapper(tmp_path)
        mapper.runner = mock_runner

        result = mapper._get_file_lines("abc123", "test.py")

        assert result == ["line1", "line2"]

    def test_get_file_lines_file_not_found(self, tmp_path):
        """Test file content retrieval when file doesn't exist."""
        mock_runner = MockSubprocessRunner()
        mock_runner.add_git_response(
            command=["show", "HEAD:missing.py"],
            response=MockCompletedProcess(
                returncode=1, stderr="fatal: path 'missing.py' does not exist"
            ),
        )

        mapper = LineMapper(tmp_path)
        mapper.runner = mock_runner

        result = mapper._get_file_lines("HEAD", "missing.py")

        assert result is None

    def test_get_file_lines_subprocess_error(self, tmp_path):
        """Test file content retrieval with subprocess error."""
        mock_runner = MockSubprocessRunner()
        mock_runner.add_git_response(
            command=["show", "HEAD:test.py"],
            response=MockCompletedProcess(returncode=1, stderr="Error"),
        )

        mapper = LineMapper(tmp_path)
        mapper.runner = mock_runner

        result = mapper._get_file_lines("HEAD", "test.py")

        assert result is None

    def test_get_file_lines_empty_file(self, tmp_path):
        """Test file content retrieval for empty file."""
        mock_runner = MockSubprocessRunner()
        mock_runner.add_git_response(
            command=["show", "HEAD:empty.py"],
            response=MockCompletedProcess(returncode=0, stdout=""),
        )

        mapper = LineMapper(tmp_path)
        mapper.runner = mock_runner

        result = mapper._get_file_lines("HEAD", "empty.py")

        assert result == [""]  # Single empty string for empty file


class TestFindMatchingLine:
    """Test line matching algorithm."""

    def test_find_matching_line_exact_position(self, tmp_path):
        """Test line matching at exact position."""
        mapper = LineMapper(tmp_path)

        current_lines = ["line1", "line2", "line3"]
        result = mapper._find_matching_line(current_lines, "line2", 2)

        assert result == 2

    def test_find_matching_line_moved_up(self, tmp_path):
        """Test line matching when line moved up."""
        mapper = LineMapper(tmp_path)

        current_lines = ["line1", "line2", "line3", "line4"]
        result = mapper._find_matching_line(
            current_lines, "line3", 4
        )  # Looking for line3 at position 4

        assert result == 3  # Found at position 3

    def test_find_matching_line_moved_down(self, tmp_path):
        """Test line matching when line moved down."""
        mapper = LineMapper(tmp_path)

        current_lines = ["line1", "line2", "line3", "line4"]
        result = mapper._find_matching_line(
            current_lines, "line2", 1
        )  # Looking for line2 at position 1

        assert result == 2  # Found at position 2

    def test_find_matching_line_at_boundary(self, tmp_path):
        """Test line matching at search boundary."""
        mapper = LineMapper(tmp_path)

        current_lines = ["line1", "line2", "line3", "line4", "line5"]
        result = mapper._find_matching_line(
            current_lines, "line5", 1, search_range=5
        )  # Within range

        assert result == 5

    def test_find_matching_line_not_found(self, tmp_path):
        """Test line matching when line not found."""
        mapper = LineMapper(tmp_path)

        current_lines = ["line1", "line2", "line3"]
        result = mapper._find_matching_line(current_lines, "missing_line", 2)

        assert result is None

    def test_find_matching_line_empty_content(self, tmp_path):
        """Test line matching with empty content."""
        mapper = LineMapper(tmp_path)

        current_lines = ["line1", "", "line3"]
        result = mapper._find_matching_line(current_lines, "", 2)

        assert result == 2

    def test_find_matching_line_custom_range(self, tmp_path):
        """Test line matching with custom search range."""
        mapper = LineMapper(tmp_path)

        current_lines = ["line1", "line2", "line3", "line4", "line5", "line6"]
        # Line is 5 positions away, within search range of 5
        result = mapper._find_matching_line(current_lines, "line6", 1, search_range=5)

        assert result == 6  # Found within range

    def test_find_matching_line_outside_bounds(self, tmp_path):
        """Test line matching when original line is outside current file bounds."""
        mapper = LineMapper(tmp_path)

        current_lines = ["line1", "line2"]
        result = mapper._find_matching_line(
            current_lines, "line3", 5
        )  # Looking for line3 at position 5

        assert result is None  # Position 5 doesn't exist

    def test_find_matching_line_whitespace_differences(self, tmp_path):
        """Test line matching with whitespace differences."""
        mapper = LineMapper(tmp_path)

        current_lines = ["line1", "  line2  ", "line3"]  # line2 has extra whitespace
        result = mapper._find_matching_line(current_lines, "line2", 2)  # Looking for "line2"

        assert result == 2  # Will match because we strip whitespace in comparison

    def test_find_matching_line_multiple_matches(self, tmp_path):
        """Test line matching when multiple lines match (should return first)."""
        mapper = LineMapper(tmp_path)

        current_lines = ["line1", "duplicate", "line3", "duplicate"]
        result = mapper._find_matching_line(
            current_lines, "duplicate", 4
        )  # Looking for "duplicate" at position 4

        assert result == 2  # Should return first match (position 2)
