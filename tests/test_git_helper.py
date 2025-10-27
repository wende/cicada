"""
Unit tests for the git_helper module.
"""

import pytest
from pathlib import Path
from cicada.git_helper import GitHelper
import git


def test_git_helper_initialization():
    """Test that GitHelper can be initialized with the current repo."""
    print("Testing GitHelper initialization...")

    # Initialize with current directory (cicada repo)
    helper = GitHelper(".")

    assert helper.repo is not None, "Git repo not initialized"
    assert helper.repo_path == Path("."), "Repo path not set correctly"

    print("  ✓ GitHelper initialized successfully")


def test_git_helper_invalid_repo():
    """Test that GitHelper raises error for non-git directory."""
    print("\nTesting invalid repo error...")

    # Try to initialize with /tmp which is likely not a git repo
    with pytest.raises(git.InvalidGitRepositoryError):
        _ = GitHelper("/tmp")

    print("  ✓ Invalid repo error raised correctly")


def test_get_recent_commits():
    """Test retrieving recent commits from the repo."""
    print("\nTesting recent commits retrieval...")

    helper = GitHelper(".")
    commits = helper.get_recent_commits(max_count=5)

    assert len(commits) > 0, "No commits found"
    assert len(commits) <= 5, "More commits than max_count returned"

    # Check first commit structure
    first_commit = commits[0]
    assert "sha" in first_commit, "Commit missing 'sha'"
    assert "full_sha" in first_commit, "Commit missing 'full_sha'"
    assert "author" in first_commit, "Commit missing 'author'"
    assert "date" in first_commit, "Commit missing 'date'"
    assert "message" in first_commit, "Commit missing 'message'"
    assert "files_changed" in first_commit, "Commit missing 'files_changed'"

    # Verify SHA is 8 chars
    assert len(first_commit["sha"]) == 8, "SHA should be 8 characters"

    # Verify full SHA is longer
    assert len(first_commit["full_sha"]) > 8, "Full SHA should be longer than 8 chars"

    print(f"  ✓ Found {len(commits)} recent commit(s)")
    print(f"  ✓ Latest commit: {first_commit['sha']} - {first_commit['message'][:50]}")


def test_get_file_history():
    """Test retrieving commit history for a specific file."""
    print("\nTesting file history retrieval...")

    helper = GitHelper(".")

    # Test with README.md which should exist in the repo
    commits = helper.get_file_history("README.md", max_commits=5)

    assert len(commits) > 0, "No commits found for README.md"
    assert len(commits) <= 5, "More commits than max_count returned"

    # Check commit structure
    first_commit = commits[0]
    assert "sha" in first_commit
    assert "full_sha" in first_commit
    assert "author" in first_commit
    assert "author_email" in first_commit
    assert "date" in first_commit
    assert "message" in first_commit
    assert "summary" in first_commit

    print(f"  ✓ Found {len(commits)} commit(s) for README.md")
    print(f"  ✓ Most recent: {first_commit['summary'][:50]}")


def test_get_file_history_nonexistent():
    """Test file history for non-existent file returns empty list."""
    print("\nTesting file history for non-existent file...")

    helper = GitHelper(".")

    # Test with a file that shouldn't exist
    commits = helper.get_file_history("nonexistent_file.txt", max_commits=5)

    assert len(commits) == 0, "Should return empty list for non-existent file"

    print("  ✓ Non-existent file handled correctly")


def test_get_function_history():
    """Test retrieving function-specific commit history."""
    print("\nTesting function history retrieval...")

    helper = GitHelper(".")

    # Test with a known function in the git_helper.py file itself
    commits = helper.get_function_history(
        "cicada/git_helper.py",
        "get_file_history",
        28,  # Approximate line number
        max_commits=3,
    )

    # Should return at least the initial commit of git_helper.py
    assert isinstance(commits, list), "Should return a list"

    # Check that commits have relevance field
    if commits:
        for commit in commits:
            assert (
                "relevance" in commit
            ), "Function history commits should have 'relevance' field"
            assert commit["relevance"] in [
                "mentioned",
                "file_change",
            ], "Invalid relevance value"

        print(f"  ✓ Found {len(commits)} relevant commit(s)")

        # Count how many are 'mentioned' vs 'file_change'
        mentioned = sum(1 for c in commits if c["relevance"] == "mentioned")
        file_changed = sum(1 for c in commits if c["relevance"] == "file_change")
        print(f"  ✓ Mentioned: {mentioned}, File changed: {file_changed}")
    else:
        print("  ✓ No commits found (file may be new)")


def test_search_commits():
    """Test searching commits by message."""
    print("\nTesting commit message search...")

    helper = GitHelper(".")

    # Get recent commits to find a word that's actually in them
    recent = helper.get_recent_commits(max_count=10)

    # Search for a word from the most recent commit
    search_term = None
    if recent:
        # Extract a meaningful word from the first commit message
        words = recent[0]["message"].lower().split()
        # Find a word that's at least 4 characters
        for word in words:
            clean_word = "".join(c for c in word if c.isalpha())
            if len(clean_word) >= 4:
                search_term = clean_word
                break

    if not search_term:
        search_term = "update"  # Fallback

    commits = helper.search_commits(search_term, max_results=3)

    # Verify results structure
    assert isinstance(commits, list), "Should return a list"
    assert len(commits) <= 3, "Should respect max_results"

    # Verify commit structure
    for commit in commits:
        assert "sha" in commit, "Commit should have 'sha'"
        assert "author" in commit, "Commit should have 'author'"
        assert "date" in commit, "Commit should have 'date'"
        assert "message" in commit, "Commit should have 'message'"

    if commits:
        print(f"  ✓ Found {len(commits)} commit(s) with search term '{search_term}'")
    else:
        print(f"  ✓ Search working (no matches for '{search_term}')")


def test_get_commit_details():
    """Test retrieving detailed information about a specific commit."""
    print("\nTesting commit details retrieval...")

    helper = GitHelper(".")

    # Get a recent commit first
    recent_commits = helper.get_recent_commits(max_count=1)
    assert len(recent_commits) > 0, "Need at least one commit"

    commit_sha = recent_commits[0]["full_sha"]

    # Get details for that commit
    details = helper.get_commit_details(commit_sha)

    assert details is not None, "Should return commit details"
    assert details["full_sha"] == commit_sha, "SHA should match"
    assert "files_changed" in details, "Should include files_changed"
    assert "insertions" in details, "Should include insertions"
    assert "deletions" in details, "Should include deletions"
    assert isinstance(details["files_changed"], list), "files_changed should be a list"

    print(f"  ✓ Retrieved details for commit {details['sha']}")
    print(f"  ✓ Files changed: {len(details['files_changed'])}")
    print(f"  ✓ +{details['insertions']} -{details['deletions']}")


def test_get_commit_details_short_sha():
    """Test that commit details work with short SHA."""
    print("\nTesting commit details with short SHA...")

    helper = GitHelper(".")

    # Get a recent commit
    recent_commits = helper.get_recent_commits(max_count=1)
    short_sha = recent_commits[0]["sha"]

    # Get details using short SHA
    details = helper.get_commit_details(short_sha)

    assert details is not None, "Should return commit details with short SHA"
    assert details["sha"] == short_sha, "SHA should match"

    print(f"  ✓ Short SHA lookup working: {short_sha}")


def test_get_commit_details_invalid():
    """Test that invalid commit SHA returns None."""
    print("\nTesting invalid commit SHA...")

    helper = GitHelper(".")

    # Try to get details for an invalid SHA
    details = helper.get_commit_details("invalid_sha_12345")

    assert details is None, "Should return None for invalid SHA"

    print("  ✓ Invalid SHA handled correctly")


def test_date_format():
    """Test that dates are in ISO format."""
    print("\nTesting date format...")

    helper = GitHelper(".")
    commits = helper.get_recent_commits(max_count=1)

    assert len(commits) > 0, "Need at least one commit"

    date_str = commits[0]["date"]

    # Verify it's in ISO format (contains 'T' separator and timezone)
    assert "T" in date_str, "Date should be in ISO format with 'T' separator"
    assert (
        "+" in date_str or "-" in date_str or date_str.endswith("Z")
    ), "Date should include timezone information"

    print(f"  ✓ Date format is correct: {date_str}")


def test_multiple_file_history():
    """Test that we can get history for multiple files."""
    print("\nTesting multiple file histories...")

    helper = GitHelper(".")

    test_files = ["README.md", "pyproject.toml", "cicada/mcp_server.py"]
    results = {}

    for file_path in test_files:
        commits = helper.get_file_history(file_path, max_commits=2)
        results[file_path] = len(commits)

    # At least one file should have commits
    assert sum(results.values()) > 0, "Should find commits for at least one file"

    for file_path, count in results.items():
        print(f"  ✓ {file_path}: {count} commit(s)")


if __name__ == "__main__":
    print("Running git_helper tests...\n")

    try:
        test_git_helper_initialization()
        test_git_helper_invalid_repo()
        test_get_recent_commits()
        test_get_file_history()
        test_get_file_history_nonexistent()
        test_get_function_history()
        test_search_commits()
        test_get_commit_details()
        test_get_commit_details_short_sha()
        test_get_commit_details_invalid()
        test_date_format()
        test_multiple_file_history()

        print("\n" + "=" * 50)
        print("All git_helper tests passed!")
        print("=" * 50)

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()
        exit(1)
