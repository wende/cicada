"""
Test for the git blame cache fix.

This test ensures that git blame correctly handles the case where
consecutive lines come from the same commit, and git only outputs
full metadata once (with subsequent lines just having the SHA).
"""

from pathlib import Path

import pytest

from cicada.git_helper import GitHelper


@pytest.fixture
def git_helper():
    """Fixture to create a GitHelper instance for the current repo."""
    repo_path = Path.cwd()
    return GitHelper(str(repo_path))


def test_blame_with_repeated_commits(git_helper):
    """
    Test that blame correctly handles consecutive lines from same commit.

    When git blame encounters consecutive lines from the same commit,
    it outputs full metadata (author, email, date) only for the first line,
    and subsequent lines only have the commit SHA. The code must cache
    and reuse the metadata.
    """
    # Test file selection rationale:
    # - Using cicada/git_helper.py (stable core file in this repo)
    # - Lines 15-25 span the imports section, which typically has multiple
    #   consecutive lines from the same commit (when imports are added together)
    # - This creates the exact scenario we're testing: git blame returns full
    #   metadata for line 15, then just SHA references for lines 16-25
    # - If this file changes significantly, the test will still pass as long as
    #   any blame data is returned (we verify structure, not specific content)
    file_path = "cicada/git_helper.py"
    start_line = 15
    end_line = 25

    blame_groups = git_helper.get_function_history(file_path, start_line, end_line)

    # Should successfully return blame information
    assert isinstance(blame_groups, list)
    assert len(blame_groups) > 0, "Should find at least one blame group"

    # Verify all groups have required fields
    for group in blame_groups:
        assert "author" in group, "Each group must have author"
        assert "author_email" in group, "Each group must have author_email"
        assert "sha" in group, "Each group must have SHA"
        assert "date" in group, "Each group must have date"
        assert "line_start" in group
        assert "line_end" in group
        assert "line_count" in group
        assert "lines" in group

        # Verify line count matches actual lines
        assert group["line_count"] == len(group["lines"])

        # Verify each line has required fields
        for line in group["lines"]:
            assert "number" in line
            assert "content" in line


def test_blame_single_commit_multiple_lines(git_helper):
    """
    Test that a single commit appearing multiple times is handled correctly.

    This specifically tests the cache mechanism that stores commit metadata
    and reuses it when the same commit SHA appears again.
    """
    # Find any file with multiple lines likely from same commit
    file_path = "README.md"
    start_line = 1
    end_line = 5

    blame_groups = git_helper.get_function_history(file_path, start_line, end_line)

    # Should not fail with KeyError
    assert isinstance(blame_groups, list)

    # If we got results, verify they're valid
    if blame_groups:
        for group in blame_groups:
            # All required fields must be present
            required_fields = ["author", "author_email", "sha", "date", "lines"]
            for field in required_fields:
                assert field in group, f"Missing required field: {field}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
