"""Tests for CLAUDE.md update functionality."""

import re
from pathlib import Path

import pytest

from cicada.setup import update_claude_md


@pytest.fixture
def mock_repo(tmp_path):
    """Create a temporary repository directory."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    # Create mix.exs to mark as Elixir project
    (repo_path / "mix.exs").write_text("defmodule Test.MixProject do\nend\n")
    return repo_path


def test_update_claude_md_creates_new_section(mock_repo):
    """Test that update_claude_md adds cicada instructions to a new CLAUDE.md."""
    claude_md = mock_repo / "CLAUDE.md"
    claude_md.write_text("# Project Instructions\n\nSome existing content.\n")

    update_claude_md(mock_repo)

    content = claude_md.read_text()
    assert "<cicada>" in content
    assert "</cicada>" in content
    assert "ALWAYS use cicada-mcp tools for Elixir and Python code searches" in content
    assert "mcp__cicada__search_module" in content
    assert "mcp__cicada__search_function" in content


def test_update_claude_md_replaces_existing_section(mock_repo):
    """Test that update_claude_md replaces existing <cicada> tags."""
    claude_md = mock_repo / "CLAUDE.md"
    initial_content = """# Project Instructions

<cicada>
Old cicada instructions that should be replaced.
</cicada>

Some other content.
"""
    claude_md.write_text(initial_content)

    update_claude_md(mock_repo)

    content = claude_md.read_text()
    assert "<cicada>" in content
    assert "</cicada>" in content
    assert "Old cicada instructions" not in content
    assert "ALWAYS use cicada-mcp tools for Elixir and Python code searches" in content


def test_update_claude_md_appends_tags_even_if_cicada_mentioned(mock_repo):
    """Test that update_claude_md appends <cicada> tags even if 'cicada' is mentioned without tags."""
    claude_md = mock_repo / "CLAUDE.md"
    initial_content = "# Project Instructions\n\nPlease use cicada for searches.\n"
    claude_md.write_text(initial_content)

    update_claude_md(mock_repo)

    # <cicada> tags should be appended
    content = claude_md.read_text()
    assert initial_content in content
    assert "<cicada>" in content
    assert "</cicada>" in content


def test_update_claude_md_skips_if_no_claude_md(mock_repo):
    """Test that update_claude_md fails silently if CLAUDE.md doesn't exist."""
    # Don't create CLAUDE.md
    update_claude_md(mock_repo)  # Should not raise an exception


def test_update_claude_md_includes_all_tools(mock_repo):
    """Test that all cicada tools are included in the updated CLAUDE.md."""
    claude_md = mock_repo / "CLAUDE.md"
    claude_md.write_text("# Project Instructions\n")

    update_claude_md(mock_repo)

    content = claude_md.read_text()

    # Check for key tools
    expected_tools = [
        "mcp__cicada__query",
        "mcp__cicada__search_module",
        "mcp__cicada__search_function",
        "mcp__cicada__git_history",
        "mcp__cicada__find_dead_code",
        "mcp__cicada__expand_result",
        "mcp__cicada__query_jq",
    ]

    for tool in expected_tools:
        assert tool in content, f"Expected tool {tool} not found in CLAUDE.md"


def test_update_claude_md_preserves_existing_content(mock_repo):
    """Test that update_claude_md preserves other content in CLAUDE.md."""
    claude_md = mock_repo / "CLAUDE.md"
    initial_content = """# Project Instructions

Some important project-specific instructions.

## Code Style

Follow these rules...
"""
    claude_md.write_text(initial_content)

    update_claude_md(mock_repo)

    content = claude_md.read_text()
    assert "Some important project-specific instructions" in content
    assert "## Code Style" in content
    assert "Follow these rules..." in content
    assert "<cicada>" in content


def test_update_claude_md_handles_multiline_tags(mock_repo):
    """Test that update_claude_md correctly handles multiline <cicada> tags."""
    claude_md = mock_repo / "CLAUDE.md"
    initial_content = """# Project

<cicada>
Line 1 of old instructions.
Line 2 of old instructions.
Line 3 of old instructions.
</cicada>

More content.
"""
    claude_md.write_text(initial_content)

    update_claude_md(mock_repo)

    content = claude_md.read_text()
    # Count <cicada> and </cicada> tags
    assert content.count("<cicada>") == 1
    assert content.count("</cicada>") == 1
    assert "Line 1 of old instructions" not in content
    assert "ALWAYS use cicada-mcp tools" in content


def test_update_claude_md_adds_newline_if_missing(mock_repo):
    """Test that update_claude_md adds a newline before appending if file doesn't end with one."""
    claude_md = mock_repo / "CLAUDE.md"
    initial_content = "# Project Instructions\n\nNo trailing newline"
    claude_md.write_text(initial_content)

    update_claude_md(mock_repo)

    content = claude_md.read_text()
    # Check that the cicada section is properly separated
    lines = content.split("\n")
    # Should have: initial content, empty line, <cicada> section
    assert any("<cicada>" in line for line in lines)


def test_creates_agents_md_for_gemini(mock_repo):
    """Test that update_claude_md updates AGENTS.md for Gemini editor."""
    agents_md = mock_repo / "AGENTS.md"
    agents_md.write_text("# AI Agent Instructions\n\nSome existing content.\n")

    # Call update_claude_md with gemini editor
    update_claude_md(mock_repo, editor="gemini")

    # AGENTS.md should be updated
    assert agents_md.exists()
    content = agents_md.read_text()

    # Should contain cicada instructions
    assert "<cicada>" in content
    assert "</cicada>" in content
    assert "ALWAYS use cicada-mcp tools for Elixir and Python code searches" in content
    assert "mcp__cicada__search_module" in content
    assert "mcp__cicada__search_function" in content


def test_creates_agents_md_for_codex(mock_repo):
    """Test that update_claude_md updates AGENTS.md for Codex editor."""
    agents_md = mock_repo / "AGENTS.md"
    agents_md.write_text("# AI Agent Instructions\n\nSome existing content.\n")

    # Call update_claude_md with codex editor
    update_claude_md(mock_repo, editor="codex")

    # AGENTS.md should be updated
    assert agents_md.exists()
    content = agents_md.read_text()

    # Should contain cicada instructions
    assert "<cicada>" in content
    assert "</cicada>" in content
    assert "ALWAYS use cicada-mcp tools for Elixir and Python code searches" in content
    assert "mcp__cicada__search_module" in content
    assert "mcp__cicada__search_function" in content
