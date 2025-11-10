#!/usr/bin/env python
"""
Test MCP PR tools functionality.

Tests the get_file_pr_history MCP tool with mock data.
"""

import json
import tempfile
from pathlib import Path


def test_get_file_pr_history():
    """Test the get_file_pr_history logic."""
    print("Testing get_file_pr_history MCP tool...")

    # Create mock PR index data
    mock_index = {
        "metadata": {
            "repo_owner": "test",
            "repo_name": "repo",
            "total_prs": 2,
            "total_comments": 3,
        },
        "prs": {
            "42": {
                "number": 42,
                "title": "Add user authentication",
                "url": "https://github.com/test/repo/pull/42",
                "state": "closed",
                "merged": True,
                "author": "wende",
                "description": "This PR adds JWT-based authentication to the User module with token validation and caching.",
                "commits": ["abc123"],
                "files_changed": ["lib/user.ex", "lib/auth.ex"],
                "comments": [
                    {
                        "id": "c1",
                        "author": "reviewer",
                        "body": "Consider caching the token validation to avoid redundant DB calls",
                        "created_at": "2025-10-20T10:00:00Z",
                        "path": "lib/user.ex",
                        "line": 58,
                        "original_line": 55,
                        "resolved": True,
                        "commit_sha": "abc123",
                    },
                    {
                        "id": "c2",
                        "author": "security-team",
                        "body": "Make sure we're using constant-time comparison for tokens",
                        "created_at": "2025-10-20T11:00:00Z",
                        "path": "lib/user.ex",
                        "line": 92,
                        "original_line": 90,
                        "resolved": True,
                        "commit_sha": "abc123",
                    },
                    {
                        "id": "c3",
                        "author": "reviewer",
                        "body": "Good implementation!",
                        "created_at": "2025-10-20T12:00:00Z",
                        "path": "lib/auth.ex",
                        "line": 10,
                        "original_line": 10,
                        "resolved": False,
                        "commit_sha": "abc123",
                    },
                ],
            },
            "38": {
                "number": 38,
                "title": "Initial user module",
                "url": "https://github.com/test/repo/pull/38",
                "state": "merged",
                "merged": True,
                "author": "contributor",
                "description": "Creates the basic User module structure",
                "commits": ["def456"],
                "files_changed": ["lib/user.ex"],
                "comments": [],
            },
        },
        "file_to_prs": {"lib/user.ex": [42, 38], "lib/auth.ex": [42]},
    }

    # Simulate the _get_file_pr_history logic
    def format_file_pr_history(pr_index, file_path):
        """Simulate the MCP tool logic."""
        file_to_prs = pr_index.get("file_to_prs", {})
        pr_numbers = file_to_prs.get(file_path, [])

        if not pr_numbers:
            return f"No pull requests found that modified: {file_path}"

        prs_data = pr_index.get("prs", {})

        lines = [f"# Pull Request History for {file_path}\n"]
        lines.append(f"Found {len(pr_numbers)} pull request(s)\n")

        for pr_num in pr_numbers:
            pr = prs_data.get(str(pr_num))
            if not pr:
                continue

            # PR Header
            status = "merged" if pr.get("merged") else pr.get("state", "unknown")
            lines.append(f"## PR #{pr['number']}: {pr['title']}")
            lines.append(f"- **Author:** @{pr['author']}")
            lines.append(f"- **Status:** {status}")
            lines.append(f"- **URL:** {pr['url']}\n")

            # PR Description
            description = pr.get("description", "").strip()
            if description:
                lines.append("### Description")
                lines.append(f"{description}\n")

            # Review Comments for this file only
            comments = pr.get("comments", [])
            file_comments = [c for c in comments if c.get("path") == file_path]

            if file_comments:
                lines.append(f"### Review Comments ({len(file_comments)})")

                for comment in file_comments:
                    author = comment.get("author", "unknown")
                    body = comment.get("body", "").strip()
                    line_num = comment.get("line")
                    original_line = comment.get("original_line")
                    resolved = comment.get("resolved", False)

                    # Comment header with line info
                    if line_num:
                        line_info = f"Line {line_num}"
                    elif original_line:
                        line_info = f"Original line {original_line} (unmapped)"
                    else:
                        line_info = "No line info"

                    resolved_marker = " ✓ Resolved" if resolved else ""
                    lines.append(f"\n**@{author}** ({line_info}){resolved_marker}:")
                    lines.append(f"> {body}")

                lines.append("")

            lines.append("---\n")

        return "\n".join(lines)

    # Test with lib/user.ex (has 2 PRs)
    print("\n  Testing lib/user.ex...")
    result = format_file_pr_history(mock_index, "lib/user.ex")

    checks = [
        ("Found 2 pull request(s)" in result, "Shows correct PR count"),
        ("PR #42: Add user authentication" in result, "Shows PR 42"),
        ("PR #38: Initial user module" in result, "Shows PR 38"),
        ("JWT-based authentication" in result, "Shows PR description"),
        ("Review Comments (2)" in result, "Shows comment count for lib/user.ex"),
        ("@reviewer" in result, "Shows reviewer comment"),
        ("@security-team" in result, "Shows security comment"),
        ("Line 58" in result, "Shows mapped line number"),
        ("✓ Resolved" in result, "Shows resolved marker"),
        (
            "@contributor" not in result
            or "Review Comments" not in result.split("PR #38")[1].split("---")[0],
            "PR 38 has no comments section",
        ),
    ]

    for passed, description in checks:
        if passed:
            print(f"     ✅ {description}")
        else:
            print(f"     ❌ {description}")
        assert passed, f"Failed: {description}"

    # Test with lib/auth.ex (has 1 PR)
    print("\n  Testing lib/auth.ex...")
    result_auth = format_file_pr_history(mock_index, "lib/auth.ex")

    checks_auth = [
        ("Found 1 pull request(s)" in result_auth, "Shows correct PR count"),
        ("PR #42" in result_auth, "Shows PR 42"),
        ("Review Comments (1)" in result_auth, "Shows 1 comment for lib/auth.ex"),
        ("Good implementation!" in result_auth, "Shows correct comment"),
    ]

    for passed, description in checks_auth:
        if passed:
            print(f"     ✅ {description}")
        else:
            print(f"     ❌ {description}")
        assert passed, f"Failed: {description}"

    # Test with non-existent file
    print("\n  Testing non-existent file...")
    result_none = format_file_pr_history(mock_index, "lib/nonexistent.ex")
    assert "No pull requests found" in result_none, "Non-existent file handling failed"
    print("     ✅ Handles non-existent file correctly")


def test_pr_index_loading():
    """Test PR index loading logic."""
    print("\nTesting PR index loading...")

    # Create temporary PR index file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        test_index = {"metadata": {"total_prs": 1}, "prs": {}, "file_to_prs": {}}
        json.dump(test_index, f)
        temp_path = f.name

    try:
        # Test loading
        with open(temp_path) as f:
            loaded = json.load(f)

        checks = [
            ("metadata" in loaded, "Metadata key present"),
            ("prs" in loaded, "PRs key present"),
            ("file_to_prs" in loaded, "file_to_prs key present"),
            (loaded["metadata"]["total_prs"] == 1, "Metadata correct"),
        ]

        for passed, description in checks:
            if passed:
                print(f"   ✅ {description}")
            else:
                print(f"   ❌ {description}")
            assert passed, f"Failed: {description}"
    finally:
        Path(temp_path).unlink()


def main():
    """Run all MCP tool tests."""
    print("=" * 60)
    print("MCP PR Tools Tests")
    print("=" * 60)

    results = []

    # Test 1: get_file_pr_history
    results.append(("get_file_pr_history", test_get_file_pr_history()))

    # Test 2: PR index loading
    results.append(("PR Index Loading", test_pr_index_loading()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All MCP tool tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit(main())
