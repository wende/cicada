"""
Tests for install.py summary output functionality
"""

import pytest
from pathlib import Path
from cicada.install import is_gitignored, print_setup_summary
import sys
from io import StringIO


class TestIsGitignored:
    """Tests for is_gitignored function"""

    def test_returns_true_if_pattern_in_gitignore(self, tmp_path):
        """Test returns True if pattern is in .gitignore"""
        gitignore_path = tmp_path / ".gitignore"
        gitignore_path.write_text("node_modules/\n.cicada/\n*.log\n")

        assert is_gitignored(tmp_path, ".cicada/") is True
        assert is_gitignored(tmp_path, ".cicada") is True

    def test_returns_false_if_pattern_not_in_gitignore(self, tmp_path):
        """Test returns False if pattern is not in .gitignore"""
        gitignore_path = tmp_path / ".gitignore"
        gitignore_path.write_text("node_modules/\n*.log\n")

        assert is_gitignored(tmp_path, ".cicada/") is False
        assert is_gitignored(tmp_path, ".mcp.json") is False

    def test_returns_false_if_gitignore_does_not_exist(self, tmp_path):
        """Test returns False if .gitignore doesn't exist"""
        assert is_gitignored(tmp_path, ".cicada/") is False

    def test_handles_pattern_with_slash_prefix(self, tmp_path):
        """Test handles patterns with leading slash"""
        gitignore_path = tmp_path / ".gitignore"
        gitignore_path.write_text("/.cicada/\n")

        assert is_gitignored(tmp_path, ".cicada/") is True
        assert is_gitignored(tmp_path, "/.cicada/") is True

    def test_handles_pattern_without_slash_suffix(self, tmp_path):
        """Test handles patterns without trailing slash"""
        gitignore_path = tmp_path / ".gitignore"
        gitignore_path.write_text(".cicada\n")

        assert is_gitignored(tmp_path, ".cicada/") is True
        assert is_gitignored(tmp_path, ".cicada") is True


class TestPrintSetupSummary:
    """Tests for print_setup_summary function"""

    def test_prints_summary_with_gitignored_files(self, tmp_path, capsys):
        """Test prints summary when files are gitignored"""
        # Setup repo
        gitignore_path = tmp_path / ".gitignore"
        gitignore_path.write_text(".cicada/\n.mcp.json\n")

        cicada_dir = tmp_path / ".cicada"
        cicada_dir.mkdir()
        index_path = cicada_dir / "index.json"
        index_path.write_text("{}")

        mcp_json = tmp_path / ".mcp.json"
        mcp_json.write_text("{}")

        # Call function
        print_setup_summary(tmp_path, index_path)

        # Check output
        captured = capsys.readouterr()
        assert "Files created/modified:" in captured.out
        assert ".cicada/" in captured.out
        assert ".mcp.json" in captured.out
        assert "✓ gitignored" in captured.out
        # Should not show warning since both are gitignored
        assert "⚠️" not in captured.out
        assert "printf" not in captured.out  # No command should be shown

    def test_shows_warning_if_mcp_json_not_gitignored(self, tmp_path, capsys):
        """Test shows warning when .mcp.json is not gitignored"""
        # Setup repo without .mcp.json in gitignore
        gitignore_path = tmp_path / ".gitignore"
        gitignore_path.write_text(".cicada/\n")

        cicada_dir = tmp_path / ".cicada"
        cicada_dir.mkdir()
        index_path = cicada_dir / "index.json"
        index_path.write_text("{}")

        mcp_json = tmp_path / ".mcp.json"
        mcp_json.write_text("{}")

        # Call function
        print_setup_summary(tmp_path, index_path)

        # Check output
        captured = capsys.readouterr()
        assert "⚠️" in captured.out
        assert "Warning: The following should be in .gitignore:" in captured.out
        assert ".mcp.json" in captured.out
        assert "local configuration" in captured.out
        assert "printf" in captured.out  # Command should be shown

    def test_handles_missing_gitignore(self, tmp_path, capsys):
        """Test handles case when .gitignore doesn't exist"""
        cicada_dir = tmp_path / ".cicada"
        cicada_dir.mkdir()
        index_path = cicada_dir / "index.json"
        index_path.write_text("{}")

        mcp_json = tmp_path / ".mcp.json"
        mcp_json.write_text("{}")

        # Call function (should not crash)
        print_setup_summary(tmp_path, index_path)

        # Check output
        captured = capsys.readouterr()
        assert "Files created/modified:" in captured.out
        assert "✗ not gitignored" in captured.out
        assert "⚠️" in captured.out
        assert ".cicada/" in captured.out
        assert ".mcp.json" in captured.out
        assert "printf" in captured.out  # Command should be shown

    def test_only_shows_existing_files(self, tmp_path, capsys):
        """Test only shows files that actually exist"""
        # Create only .cicada directory
        cicada_dir = tmp_path / ".cicada"
        cicada_dir.mkdir()
        index_path = cicada_dir / "index.json"
        index_path.write_text("{}")

        gitignore_path = tmp_path / ".gitignore"
        gitignore_path.write_text(".cicada/\n")

        # Call function
        print_setup_summary(tmp_path, index_path)

        # Check output
        captured = capsys.readouterr()
        assert ".cicada/" in captured.out
        # .mcp.json shouldn't appear in the file list if it doesn't exist
        lines = captured.out.split("\n")
        file_list_lines = [
            line
            for line in lines
            if "MCP server configuration" in line or "Cicada index directory" in line
        ]
        # Only .cicada/ should be in the file list
        assert len(file_list_lines) == 1
        assert "Cicada index directory" in file_list_lines[0]
        # But warning should appear for .mcp.json
        assert "⚠️" in captured.out
        assert ".mcp.json" in captured.out

    def test_shows_warning_for_cicada_if_not_gitignored(self, tmp_path, capsys):
        """Test shows warning when .cicada/ is not gitignored"""
        # Setup repo without .cicada/ in gitignore
        gitignore_path = tmp_path / ".gitignore"
        gitignore_path.write_text(".mcp.json\n")

        cicada_dir = tmp_path / ".cicada"
        cicada_dir.mkdir()
        index_path = cicada_dir / "index.json"
        index_path.write_text("{}")

        mcp_json = tmp_path / ".mcp.json"
        mcp_json.write_text("{}")

        # Call function
        print_setup_summary(tmp_path, index_path)

        # Check output
        captured = capsys.readouterr()
        assert "⚠️" in captured.out
        assert "Warning: The following should be in .gitignore:" in captured.out
        assert ".cicada/" in captured.out
        assert "build artifacts and cache" in captured.out
        assert "printf" in captured.out  # Command should be shown

    def test_shows_warning_for_both_if_neither_gitignored(self, tmp_path, capsys):
        """Test shows warning for both files when neither is gitignored"""
        # Setup repo without either in gitignore
        gitignore_path = tmp_path / ".gitignore"
        gitignore_path.write_text("node_modules/\n")

        cicada_dir = tmp_path / ".cicada"
        cicada_dir.mkdir()
        index_path = cicada_dir / "index.json"
        index_path.write_text("{}")

        mcp_json = tmp_path / ".mcp.json"
        mcp_json.write_text("{}")

        # Call function
        print_setup_summary(tmp_path, index_path)

        # Check output
        captured = capsys.readouterr()
        assert "⚠️" in captured.out
        assert "Warning: The following should be in .gitignore:" in captured.out
        assert ".cicada/" in captured.out
        assert ".mcp.json" in captured.out
        assert "build artifacts and cache" in captured.out
        assert "local configuration" in captured.out
        assert "printf" in captured.out
        # Both should be in the command
        assert ".cicada/" in captured.out
        assert ".mcp.json" in captured.out

    def test_command_format_is_correct(self, tmp_path, capsys):
        """Test that the echo command is properly formatted"""
        # Setup repo without files in gitignore
        gitignore_path = tmp_path / ".gitignore"
        gitignore_path.write_text("node_modules/\n")

        cicada_dir = tmp_path / ".cicada"
        cicada_dir.mkdir()
        index_path = cicada_dir / "index.json"
        index_path.write_text("{}")

        mcp_json = tmp_path / ".mcp.json"
        mcp_json.write_text("{}")

        # Call function
        print_setup_summary(tmp_path, index_path)

        # Check output
        captured = capsys.readouterr()
        # Command should be present and properly formatted
        assert "printf" in captured.out
        assert ">> .gitignore" in captured.out
        # Check that it contains both items separated by \n
        lines = captured.out.split("\n")
        command_lines = [line for line in lines if "printf" in line]
        assert len(command_lines) == 1
        command = command_lines[0]
        assert ".cicada/" in command
        assert ".mcp.json" in command
