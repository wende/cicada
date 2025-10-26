"""Tests for CLAUDE.md update functionality in install.py"""

import os
import tempfile
from pathlib import Path

import pytest

from cicada.install import update_claude_md


def test_update_claude_md_when_file_exists():
    """Test that update_claude_md adds instruction when CLAUDE.md exists"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        claude_md_path = repo_path / "CLAUDE.md"

        # Create a basic CLAUDE.md
        claude_md_path.write_text("# Project Instructions\n\n- Some instruction\n")

        # Update it
        update_claude_md(repo_path)

        # Check that the instruction was added
        content = claude_md_path.read_text()
        assert "cicada-mcp" in content
        assert "ALWAYS use cicada-mcp tools" in content
        assert "# Project Instructions" in content  # Original content preserved


def test_update_claude_md_when_file_does_not_exist():
    """Test that update_claude_md fails silently when CLAUDE.md doesn't exist"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        claude_md_path = repo_path / "CLAUDE.md"

        # Don't create CLAUDE.md
        assert not claude_md_path.exists()

        # Update should not create the file
        update_claude_md(repo_path)

        # File should still not exist
        assert not claude_md_path.exists()


def test_update_claude_md_when_already_updated():
    """Test that update_claude_md doesn't duplicate instruction if already present"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        claude_md_path = repo_path / "CLAUDE.md"

        # Create CLAUDE.md with existing cicada-mcp instruction
        original_content = (
            "# Project Instructions\n\n"
            "- When searching through the Elixir codebase, use the cicada-mcp MCP server\n"
        )
        claude_md_path.write_text(original_content)

        # Update it
        update_claude_md(repo_path)

        # Check that instruction wasn't duplicated
        content = claude_md_path.read_text()
        assert content == original_content
        assert content.count("cicada-mcp") == 1


def test_update_claude_md_adds_newline_if_needed():
    """Test that update_claude_md adds newline before instruction if file doesn't end with one"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        claude_md_path = repo_path / "CLAUDE.md"

        # Create CLAUDE.md without trailing newline
        claude_md_path.write_text("# Project Instructions\n\n- Some instruction")

        # Update it
        update_claude_md(repo_path)

        # Check that newlines were added properly
        content = claude_md_path.read_text()
        lines = content.split("\n")

        # Should have proper spacing
        assert "cicada-mcp" in content
        # Check there's at least one blank line before the instruction
        assert "" in lines


def test_update_claude_md_handles_empty_file():
    """Test that update_claude_md handles empty CLAUDE.md file"""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        claude_md_path = repo_path / "CLAUDE.md"

        # Create empty CLAUDE.md
        claude_md_path.write_text("")

        # Update it
        update_claude_md(repo_path)

        # Check that instruction was added
        content = claude_md_path.read_text()
        assert "cicada-mcp" in content
        assert content.startswith("\n")  # Should start with newline
