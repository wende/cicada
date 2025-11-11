"""Tests for find_dead_code CLI functionality.

Author: Cursor(Auto)
"""

import json
from unittest.mock import patch

import pytest

from cicada.dead_code.finder import (
    filter_by_confidence,
    format_json,
    format_markdown,
    main,
)


@pytest.fixture
def empty_results():
    """Results with no candidates."""
    return {
        "summary": {
            "total_public_functions": 10,
            "analyzed": 8,
            "skipped_impl": 2,
            "skipped_files": 0,
            "total_candidates": 0,
        },
        "candidates": {"high": [], "medium": [], "low": []},
    }


@pytest.fixture
def results_with_high_only():
    """Results with only high confidence candidates."""
    return {
        "summary": {
            "total_public_functions": 10,
            "analyzed": 8,
            "skipped_impl": 2,
            "skipped_files": 0,
            "total_candidates": 2,
        },
        "candidates": {
            "high": [
                {
                    "module": "MyApp.UserService",
                    "function": "get_user",
                    "arity": 1,
                    "line": 10,
                    "file": "lib/my_app/user_service.ex",
                    "reason": "Zero usage found",
                },
                {
                    "module": "MyApp.UserService",
                    "function": "delete_user",
                    "arity": 1,
                    "line": 20,
                    "file": "lib/my_app/user_service.ex",
                    "reason": "Zero usage found",
                },
            ],
            "medium": [],
            "low": [],
        },
    }


@pytest.fixture
def results_with_medium():
    """Results with medium confidence candidates."""
    return {
        "summary": {
            "total_public_functions": 10,
            "analyzed": 8,
            "skipped_impl": 2,
            "skipped_files": 0,
            "total_candidates": 1,
        },
        "candidates": {
            "high": [],
            "medium": [
                {
                    "module": "MyApp.GenServer",
                    "function": "extra_func",
                    "arity": 0,
                    "line": 30,
                    "file": "lib/my_app/gen_server.ex",
                    "reason": "Zero usage, but has behaviours/uses",
                    "behaviours": ["GenServer"],
                    "uses": ["GenServer"],
                }
            ],
            "low": [],
        },
    }


@pytest.fixture
def results_with_low():
    """Results with low confidence candidates."""
    return {
        "summary": {
            "total_public_functions": 10,
            "analyzed": 8,
            "skipped_impl": 2,
            "skipped_files": 0,
            "total_candidates": 1,
        },
        "candidates": {
            "high": [],
            "medium": [],
            "low": [
                {
                    "module": "MyApp.Handler",
                    "function": "handle",
                    "arity": 1,
                    "line": 10,
                    "file": "lib/my_app/handler.ex",
                    "reason": "Zero usage, but module used as value",
                    "mentioned_in": [
                        {
                            "module": "MyApp.Router",
                            "file": "lib/my_app/router.ex",
                        }
                    ],
                }
            ],
        },
    }


@pytest.fixture
def results_with_all_levels():
    """Results with all confidence levels."""
    return {
        "summary": {
            "total_public_functions": 10,
            "analyzed": 8,
            "skipped_impl": 2,
            "skipped_files": 1,
            "total_candidates": 5,
        },
        "candidates": {
            "high": [
                {
                    "module": "MyApp.UserService",
                    "function": "get_user",
                    "arity": 1,
                    "line": 10,
                    "file": "lib/my_app/user_service.ex",
                    "reason": "Zero usage found",
                },
                {
                    "module": "MyApp.AccountService",
                    "function": "create",
                    "arity": 1,
                    "line": 5,
                    "file": "lib/my_app/account_service.ex",
                    "reason": "Zero usage found",
                },
            ],
            "medium": [
                {
                    "module": "MyApp.GenServer",
                    "function": "extra_func",
                    "arity": 0,
                    "line": 30,
                    "file": "lib/my_app/gen_server.ex",
                    "reason": "Zero usage, but has behaviours/uses",
                    "behaviours": ["GenServer"],
                    "uses": [],
                },
                {
                    "module": "MyApp.Controller",
                    "function": "unused_action",
                    "arity": 2,
                    "line": 15,
                    "file": "lib/my_app/controller.ex",
                    "reason": "Zero usage, but has behaviours/uses",
                    "behaviours": [],
                    "uses": ["Phoenix.Controller"],
                },
            ],
            "low": [
                {
                    "module": "MyApp.Handler",
                    "function": "handle",
                    "arity": 1,
                    "line": 10,
                    "file": "lib/my_app/handler.ex",
                    "reason": "Zero usage, but module used as value",
                    "mentioned_in": [
                        {
                            "module": "MyApp.Router",
                            "file": "lib/my_app/router.ex",
                        }
                    ],
                }
            ],
        },
    }


# Tests for format_markdown


def test_format_markdown_empty_results(empty_results):
    """Test markdown formatting with no candidates."""
    output = format_markdown(empty_results)

    assert "# Dead Code Analysis" in output
    assert "Analyzed 8 public functions" in output
    assert "skipped 2 with @impl" in output
    assert "0 in test/script files" in output
    assert "**0 potentially unused functions**" in output
    assert "*No dead code candidates found!*" in output


def test_format_markdown_high_confidence_single(results_with_high_only):
    """Test markdown with high confidence - plural vs singular."""
    # Modify to have single function
    results_with_high_only["candidates"]["high"] = [results_with_high_only["candidates"]["high"][0]]
    results_with_high_only["summary"]["total_candidates"] = 1

    output = format_markdown(results_with_high_only)

    assert "HIGH CONFIDENCE (1 function)" in output
    assert "HIGH CONFIDENCE (1 functions)" not in output


def test_format_markdown_high_confidence_plural(results_with_high_only):
    """Test markdown with high confidence - plural."""
    output = format_markdown(results_with_high_only)

    assert "HIGH CONFIDENCE (2 functions)" in output
    assert "Functions with zero usage in codebase" in output
    assert "### MyApp.UserService" in output
    assert "lib/my_app/user_service.ex" in output
    assert "`get_user/1` :10" in output
    assert "`delete_user/1` :20" in output


def test_format_markdown_medium_confidence(results_with_medium):
    """Test markdown with medium confidence."""
    output = format_markdown(results_with_medium)

    assert "MEDIUM CONFIDENCE (1 function)" in output
    assert "possible callbacks" in output
    assert "### MyApp.GenServer" in output
    assert "**Behaviours:** GenServer" in output
    assert "**Uses:** GenServer" in output
    assert "`extra_func/0` :30" in output


def test_format_markdown_low_confidence(results_with_low):
    """Test markdown with low confidence."""
    output = format_markdown(results_with_low)

    assert "LOW CONFIDENCE (1 function)" in output
    assert "possible dynamic calls" in output
    assert "### MyApp.Handler" in output
    assert "**Module mentioned as value in:**" in output
    assert "- MyApp.Router (lib/my_app/router.ex)" in output
    assert "`handle/1` :10" in output


def test_format_markdown_all_levels(results_with_all_levels):
    """Test markdown with all confidence levels."""
    output = format_markdown(results_with_all_levels)

    # Check all sections present
    assert "HIGH CONFIDENCE (2 functions)" in output
    assert "MEDIUM CONFIDENCE (2 functions)" in output
    assert "LOW CONFIDENCE (1 function)" in output

    # Check grouping by module
    assert "### MyApp.UserService" in output
    assert "### MyApp.AccountService" in output
    assert "### MyApp.GenServer" in output
    assert "### MyApp.Controller" in output
    assert "### MyApp.Handler" in output


def test_format_markdown_header_centering():
    """Test that confidence headers are properly formatted."""
    results = {
        "summary": {
            "total_public_functions": 10,
            "analyzed": 8,
            "skipped_impl": 2,
            "skipped_files": 0,
            "total_candidates": 1,
        },
        "candidates": {
            "high": [
                {
                    "module": "MyApp.Test",
                    "function": "test",
                    "arity": 0,
                    "line": 1,
                    "file": "lib/test.ex",
                    "reason": "test",
                }
            ],
            "medium": [],
            "low": [],
        },
    }

    output = format_markdown(results)

    # Check that header has equal signs and label
    assert "═" in output
    assert "HIGH CONFIDENCE" in output


def test_format_markdown_medium_with_only_behaviours():
    """Test medium confidence with only behaviours (no uses)."""
    results = {
        "summary": {
            "total_public_functions": 1,
            "analyzed": 1,
            "skipped_impl": 0,
            "skipped_files": 0,
            "total_candidates": 1,
        },
        "candidates": {
            "high": [],
            "medium": [
                {
                    "module": "MyApp.GenServer",
                    "function": "func",
                    "arity": 0,
                    "line": 10,
                    "file": "lib/gen_server.ex",
                    "reason": "test",
                    "behaviours": ["GenServer"],
                    "uses": [],
                }
            ],
            "low": [],
        },
    }

    output = format_markdown(results)

    assert "**Behaviours:** GenServer" in output
    assert "**Uses:**" not in output


def test_format_markdown_medium_with_only_uses():
    """Test medium confidence with only uses (no behaviours)."""
    results = {
        "summary": {
            "total_public_functions": 1,
            "analyzed": 1,
            "skipped_impl": 0,
            "skipped_files": 0,
            "total_candidates": 1,
        },
        "candidates": {
            "high": [],
            "medium": [
                {
                    "module": "MyApp.Controller",
                    "function": "func",
                    "arity": 0,
                    "line": 10,
                    "file": "lib/controller.ex",
                    "reason": "test",
                    "behaviours": [],
                    "uses": ["Phoenix.Controller"],
                }
            ],
            "low": [],
        },
    }

    output = format_markdown(results)

    assert "**Uses:** Phoenix.Controller" in output
    assert "**Behaviours:**" not in output


# Tests for format_json


def test_format_json_basic(results_with_high_only):
    """Test JSON formatting."""
    output = format_json(results_with_high_only)

    # Should be valid JSON
    parsed = json.loads(output)

    assert parsed == results_with_high_only
    assert "summary" in parsed
    assert "candidates" in parsed


def test_format_json_indented(results_with_high_only):
    """Test that JSON is indented."""
    output = format_json(results_with_high_only)

    # Should have indentation (2 spaces)
    assert "  " in output
    assert "\n" in output


# Tests for filter_by_confidence


def test_filter_by_confidence_low_shows_all(results_with_all_levels):
    """Test that low confidence filter shows all levels."""
    filtered = filter_by_confidence(results_with_all_levels, "low")

    assert len(filtered["candidates"]["high"]) == 2
    assert len(filtered["candidates"]["medium"]) == 2
    assert len(filtered["candidates"]["low"]) == 1
    assert filtered["summary"]["total_candidates"] == 5


def test_filter_by_confidence_medium_shows_high_and_medium(results_with_all_levels):
    """Test that medium confidence filter shows high and medium only."""
    filtered = filter_by_confidence(results_with_all_levels, "medium")

    assert len(filtered["candidates"]["high"]) == 2
    assert len(filtered["candidates"]["medium"]) == 2
    assert len(filtered["candidates"]["low"]) == 0
    assert filtered["summary"]["total_candidates"] == 4


def test_filter_by_confidence_high_shows_only_high(results_with_all_levels):
    """Test that high confidence filter shows only high."""
    filtered = filter_by_confidence(results_with_all_levels, "high")

    assert len(filtered["candidates"]["high"]) == 2
    assert len(filtered["candidates"]["medium"]) == 0
    assert len(filtered["candidates"]["low"]) == 0
    assert filtered["summary"]["total_candidates"] == 2


def test_filter_by_confidence_modifies_in_place(results_with_all_levels):
    """Test that filter modifies the results dict."""
    original_id = id(results_with_all_levels)
    filtered = filter_by_confidence(results_with_all_levels, "high")

    # Returns the same object
    assert id(filtered) == original_id


def test_filter_by_confidence_with_empty_results(empty_results):
    """Test filtering empty results."""
    filtered = filter_by_confidence(empty_results, "high")

    assert filtered["summary"]["total_candidates"] == 0
    assert len(filtered["candidates"]["high"]) == 0
    assert len(filtered["candidates"]["medium"]) == 0
    assert len(filtered["candidates"]["low"]) == 0


# Tests for main() CLI


def test_main_missing_index_file(tmp_path, capsys):
    """Test main with missing index file."""
    index_path = tmp_path / "nonexistent.json"

    with (
        patch("sys.argv", ["cicada-find-dead-code"]),
        patch("cicada.dead_code.finder.get_index_path", return_value=index_path),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "Error: Index file not found" in captured.err
    assert "Run 'cicada index' first" in captured.err


def test_main_invalid_index_file(tmp_path, capsys):
    """Test main with invalid JSON in index file."""
    index_path = tmp_path / "invalid.json"
    index_path.write_text("{ invalid json }")

    with (
        patch("sys.argv", ["cicada-find-dead-code"]),
        patch("cicada.dead_code.finder.get_index_path", return_value=index_path),
        pytest.raises(SystemExit) as exc,
    ):
        main()

    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "Error loading index" in captured.err


def test_main_with_valid_index_markdown(tmp_path, capsys):
    """Test main with valid index and markdown output."""
    # Create valid index file
    index_path = tmp_path / "index.json"
    index_data = {
        "modules": {
            "MyApp.Test": {
                "file": "lib/test.ex",
                "functions": [
                    {
                        "name": "unused",
                        "arity": 0,
                        "type": "def",
                        "line": 10,
                        "impl": False,
                    }
                ],
                "aliases": {},
                "imports": [],
                "requires": [],
                "uses": [],
                "behaviours": [],
                "value_mentions": [],
                "calls": [],
            }
        }
    }
    index_path.write_text(json.dumps(index_data))

    with (
        patch("sys.argv", ["cicada-find-dead-code"]),
        patch("cicada.dead_code.finder.get_index_path", return_value=index_path),
    ):
        main()

    captured = capsys.readouterr()
    assert "# Dead Code Analysis" in captured.out
    assert "HIGH CONFIDENCE" in captured.out


def test_main_with_json_format(tmp_path, capsys):
    """Test main with JSON output format."""
    index_path = tmp_path / "index.json"
    index_data = {
        "modules": {
            "MyApp.Test": {
                "file": "lib/test.ex",
                "functions": [
                    {
                        "name": "unused",
                        "arity": 0,
                        "type": "def",
                        "line": 10,
                        "impl": False,
                    }
                ],
                "aliases": {},
                "imports": [],
                "requires": [],
                "uses": [],
                "behaviours": [],
                "value_mentions": [],
                "calls": [],
            }
        }
    }
    index_path.write_text(json.dumps(index_data))

    with (
        patch("sys.argv", ["cicada-find-dead-code", "--format", "json"]),
        patch("cicada.dead_code.finder.get_index_path", return_value=index_path),
    ):
        main()

    captured = capsys.readouterr()
    # Should be valid JSON
    result = json.loads(captured.out)
    assert "summary" in result
    assert "candidates" in result


def test_main_with_min_confidence_high(tmp_path, capsys):
    """Test main with high confidence filter."""
    index_path = tmp_path / "index.json"
    index_data = {
        "modules": {
            "MyApp.GenServer": {
                "file": "lib/gen_server.ex",
                "functions": [
                    {
                        "name": "unused",
                        "arity": 0,
                        "type": "def",
                        "line": 10,
                        "impl": False,
                    }
                ],
                "aliases": {},
                "imports": [],
                "requires": [],
                "uses": ["GenServer"],
                "behaviours": ["GenServer"],
                "value_mentions": [],
                "calls": [],
            }
        }
    }
    index_path.write_text(json.dumps(index_data))

    with (
        patch("sys.argv", ["cicada-find-dead-code", "--min-confidence", "high"]),
        patch("cicada.dead_code.finder.get_index_path", return_value=index_path),
    ):
        main()

    captured = capsys.readouterr()
    # Should not show medium confidence results
    assert "HIGH CONFIDENCE" not in captured.out
    assert "MEDIUM CONFIDENCE" not in captured.out
    assert "*No dead code candidates found!*" in captured.out


def test_main_with_min_confidence_medium(tmp_path, capsys):
    """Test main with medium confidence filter."""
    index_path = tmp_path / "index.json"
    index_data = {
        "modules": {
            "MyApp.GenServer": {
                "file": "lib/gen_server.ex",
                "functions": [
                    {
                        "name": "unused",
                        "arity": 0,
                        "type": "def",
                        "line": 10,
                        "impl": False,
                    }
                ],
                "aliases": {},
                "imports": [],
                "requires": [],
                "uses": ["GenServer"],
                "behaviours": ["GenServer"],
                "value_mentions": [],
                "calls": [],
            }
        }
    }
    index_path.write_text(json.dumps(index_data))

    with (
        patch("sys.argv", ["cicada-find-dead-code", "--min-confidence", "medium"]),
        patch("cicada.dead_code.finder.get_index_path", return_value=index_path),
    ):
        main()

    captured = capsys.readouterr()
    # Should show medium confidence results
    assert "MEDIUM CONFIDENCE" in captured.out


def test_main_with_min_confidence_low(tmp_path, capsys):
    """Test main with low confidence filter (shows all)."""
    index_path = tmp_path / "index.json"
    index_data = {
        "modules": {
            "MyApp.Handler": {
                "file": "lib/handler.ex",
                "functions": [
                    {
                        "name": "unused",
                        "arity": 0,
                        "type": "def",
                        "line": 10,
                        "impl": False,
                    }
                ],
                "aliases": {},
                "imports": [],
                "requires": [],
                "uses": [],
                "behaviours": [],
                "value_mentions": [],
                "calls": [],
            },
            "MyApp.Router": {
                "file": "lib/router.ex",
                "functions": [],
                "aliases": {},
                "imports": [],
                "requires": [],
                "uses": [],
                "behaviours": [],
                "value_mentions": ["MyApp.Handler"],
                "calls": [],
            },
        }
    }
    index_path.write_text(json.dumps(index_data))

    with (
        patch("sys.argv", ["cicada-find-dead-code", "--min-confidence", "low"]),
        patch("cicada.dead_code.finder.get_index_path", return_value=index_path),
    ):
        main()

    captured = capsys.readouterr()
    # Should show low confidence results
    assert "LOW CONFIDENCE" in captured.out


def test_main_default_index_path(tmp_path, capsys):
    """Test that main uses centralized storage path."""
    # Create index in centralized location
    index_path = tmp_path / "index.json"
    index_data = {"modules": {}}
    index_path.write_text(json.dumps(index_data))

    with (
        patch("sys.argv", ["cicada-find-dead-code"]),
        patch("cicada.dead_code.finder.get_index_path", return_value=index_path),
    ):
        main()

    captured = capsys.readouterr()
    assert "# Dead Code Analysis" in captured.out
