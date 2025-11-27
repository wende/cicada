"""
Comprehensive tests for cicada/status.py
"""

import json
from datetime import datetime
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from cicada.status import (
    _determine_tier,
    check_repository,
    find_agent_files,
    find_mcp_files,
    get_index_info,
    get_pr_index_info,
)


class TestGetIndexInfo:
    """Tests for get_index_info function"""

    def test_index_does_not_exist(self, tmp_path, mock_home_dir):
        """Should return exists=False when index doesn't exist"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        info = get_index_info(repo_path)

        assert info["exists"] is False
        assert info["date"] is None
        assert info["tier"] is None
        assert info["extraction_method"] is None
        assert info["expansion_method"] is None
        assert info["file_size"] is None

    def test_index_exists_no_config(self, tmp_path, mock_home_dir):
        """Should return basic info when index exists but no config"""
        from cicada.utils.storage import create_storage_dir, get_index_path

        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Create storage dir and index file
        create_storage_dir(repo_path)
        index_path = get_index_path(repo_path)
        index_data = {"modules": {}, "metadata": {}}

        with open(index_path, "w") as f:
            json.dump(index_data, f)

        info = get_index_info(repo_path)

        assert info["exists"] is True
        assert info["path"] == str(index_path)
        assert info["date"] is not None
        assert info["file_size"] is not None
        assert info["file_size"] > 0
        assert info["tier"] is None
        assert info["extraction_method"] is None
        assert info["expansion_method"] is None

    def test_index_exists_with_config(self, tmp_path, mock_home_dir):
        """Should return full info when index and config exist"""
        from cicada.utils.storage import (
            create_storage_dir,
            get_config_path,
            get_index_path,
        )

        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Create storage dir
        create_storage_dir(repo_path)

        # Create index file
        index_path = get_index_path(repo_path)
        index_data = {"modules": {}, "metadata": {}}
        with open(index_path, "w") as f:
            json.dump(index_data, f)

        # Create config file with tier info
        config_path = get_config_path(repo_path)
        config_data = {
            "keyword_extraction": {"method": "bert_small"},
            "keyword_expansion": {"method": "glove"},
        }
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        info = get_index_info(repo_path)

        assert info["exists"] is True
        assert info["date"] is not None
        assert info["file_size"] is not None
        assert info["tier"] == "regular"
        assert info["extraction_method"] == "bert_small"
        assert info["expansion_method"] == "glove"

    def test_index_with_invalid_config(self, tmp_path, mock_home_dir):
        """Should handle invalid config gracefully"""
        from cicada.utils.storage import (
            create_storage_dir,
            get_config_path,
            get_index_path,
        )

        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Create storage dir and index
        create_storage_dir(repo_path)
        index_path = get_index_path(repo_path)
        with open(index_path, "w") as f:
            json.dump({"modules": {}}, f)

        # Create invalid config file
        config_path = get_config_path(repo_path)
        with open(config_path, "w") as f:
            f.write("invalid: yaml: content: [")

        info = get_index_info(repo_path)

        assert info["exists"] is True
        assert info["tier"] is None
        assert info["extraction_method"] is None
        assert info["expansion_method"] is None

    def test_index_with_partial_config(self, tmp_path, mock_home_dir):
        """Should handle config with only one method specified"""
        from cicada.utils.storage import (
            create_storage_dir,
            get_config_path,
            get_index_path,
        )

        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Create storage dir and index
        create_storage_dir(repo_path)
        index_path = get_index_path(repo_path)
        with open(index_path, "w") as f:
            json.dump({"modules": {}}, f)

        # Create config with only extraction method
        config_path = get_config_path(repo_path)
        config_data = {
            "keyword_extraction": {"method": "bert_small"},
            # Missing expansion method
        }
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        info = get_index_info(repo_path)

        assert info["exists"] is True
        assert info["extraction_method"] == "bert_small"
        assert info["expansion_method"] is None
        assert info["tier"] is None  # Can't determine tier without both methods


class TestGetPrIndexInfo:
    """Tests for get_pr_index_info function"""

    def test_pr_index_does_not_exist(self, tmp_path, mock_home_dir):
        """Should return exists=False when PR index doesn't exist"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        info = get_pr_index_info(repo_path)

        assert info["exists"] is False
        assert info["date"] is None
        assert info["file_size"] is None

    def test_pr_index_exists(self, tmp_path, mock_home_dir):
        """Should return info when PR index exists"""
        from cicada.utils.storage import create_storage_dir, get_pr_index_path

        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Create storage dir and PR index
        create_storage_dir(repo_path)
        pr_index_path = get_pr_index_path(repo_path)
        pr_data = {"prs": []}

        with open(pr_index_path, "w") as f:
            json.dump(pr_data, f)

        info = get_pr_index_info(repo_path)

        assert info["exists"] is True
        assert info["path"] == str(pr_index_path)
        assert info["date"] is not None
        assert info["file_size"] is not None
        assert info["file_size"] > 0


class TestFindAgentFiles:
    """Tests for find_agent_files function"""

    def test_no_agent_files(self, tmp_path):
        """Should return empty when no agent files exist"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        result = find_agent_files(repo_path)

        assert result["total_found"] == 0
        assert result["agents"] == []

    def test_finds_claude_agent_with_cicada(self, tmp_path):
        """Should find Claude Code agent files with cicada"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Create Claude agent file with cicada reference
        agent_dir = repo_path / ".claude" / "agents"
        agent_dir.mkdir(parents=True)

        agent_file = agent_dir / "my_agent.json"
        agent_data = {"name": "test", "tools": ["cicada"]}
        with open(agent_file, "w") as f:
            json.dump(agent_data, f)

        result = find_agent_files(repo_path)

        assert result["total_found"] == 1
        assert len(result["agents"]) == 1
        assert result["agents"][0]["description"] == "Claude Code agents"
        assert result["agents"][0]["relative_path"] == ".claude/agents/my_agent.json"

    def test_finds_cursor_agent_with_cicada(self, tmp_path):
        """Should find Cursor agent files with cicada"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Create Cursor agent file
        agent_dir = repo_path / ".cursor" / "agents"
        agent_dir.mkdir(parents=True)

        agent_file = agent_dir / "cursor_agent.json"
        agent_data = {"config": {"mcp": "CICADA-MCP"}}
        with open(agent_file, "w") as f:
            json.dump(agent_data, f)

        result = find_agent_files(repo_path)

        assert result["total_found"] == 1
        assert result["agents"][0]["description"] == "Cursor agents"

    def test_ignores_agent_without_cicada(self, tmp_path):
        """Should ignore agent files without cicada references"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Create agent file without cicada
        agent_dir = repo_path / ".claude" / "agents"
        agent_dir.mkdir(parents=True)

        agent_file = agent_dir / "other_agent.json"
        agent_data = {"name": "test", "tools": ["other"]}
        with open(agent_file, "w") as f:
            json.dump(agent_data, f)

        result = find_agent_files(repo_path)

        assert result["total_found"] == 0

    def test_finds_multiple_agents_across_editors(self, tmp_path):
        """Should find agent files across multiple editor directories"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Create agents in different directories
        for editor in [".claude", ".cursor", ".vscode"]:
            agent_dir = repo_path / editor / "agents"
            agent_dir.mkdir(parents=True)

            agent_file = agent_dir / f"{editor}_agent.json"
            agent_data = {"cicada": True}
            with open(agent_file, "w") as f:
                json.dump(agent_data, f)

        result = find_agent_files(repo_path)

        assert result["total_found"] == 3

    def test_handles_invalid_json_gracefully(self, tmp_path):
        """Should handle invalid JSON files gracefully"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Create invalid JSON file
        agent_dir = repo_path / ".claude" / "agents"
        agent_dir.mkdir(parents=True)

        agent_file = agent_dir / "invalid.json"
        with open(agent_file, "w") as f:
            f.write("invalid json {")

        result = find_agent_files(repo_path)

        assert result["total_found"] == 0

    def test_handles_read_error_gracefully(self, tmp_path):
        """Should handle file read errors gracefully"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        agent_dir = repo_path / ".claude" / "agents"
        agent_dir.mkdir(parents=True)

        agent_file = agent_dir / "agent.json"
        agent_data = {"cicada": True}
        with open(agent_file, "w") as f:
            json.dump(agent_data, f)

        # Mock open to raise an error
        original_open = open

        def mock_open(*args, **kwargs):
            if "agent.json" in str(args[0]):
                raise OSError("Permission denied")
            return original_open(*args, **kwargs)

        with patch("builtins.open", side_effect=mock_open):
            result = find_agent_files(repo_path)

        assert result["total_found"] == 0

    def test_finds_claude_md_with_cicada(self, tmp_path):
        """Should find CLAUDE.md when it mentions cicada"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Create CLAUDE.md with cicada reference
        claude_md = repo_path / "CLAUDE.md"
        claude_md.write_text("# Instructions\n\nUse cicada-mcp for code searches.")

        result = find_agent_files(repo_path)

        assert result["total_found"] == 1
        assert result["agents"][0]["description"] == "Claude Code instructions"
        assert result["agents"][0]["relative_path"] == "CLAUDE.md"

    def test_finds_agents_md_with_cicada(self, tmp_path):
        """Should find AGENTS.md when it mentions cicada"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Create AGENTS.md with cicada reference
        agents_md = repo_path / "AGENTS.md"
        agents_md.write_text("# Agent Guidelines\n\nCICADA tools are required.")

        result = find_agent_files(repo_path)

        assert result["total_found"] == 1
        assert result["agents"][0]["description"] == "Agent instructions"
        assert result["agents"][0]["relative_path"] == "AGENTS.md"

    def test_ignores_claude_md_without_cicada(self, tmp_path):
        """Should ignore CLAUDE.md without cicada references"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Create CLAUDE.md without cicada reference
        claude_md = repo_path / "CLAUDE.md"
        claude_md.write_text("# Instructions\n\nSome other instructions.")

        result = find_agent_files(repo_path)

        assert result["total_found"] == 0

    def test_finds_both_md_and_json_agents(self, tmp_path):
        """Should find both markdown files and JSON agent files"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Create CLAUDE.md with cicada
        claude_md = repo_path / "CLAUDE.md"
        claude_md.write_text("Use cicada for searches.")

        # Create agent JSON file with cicada
        agent_dir = repo_path / ".claude" / "agents"
        agent_dir.mkdir(parents=True)
        agent_file = agent_dir / "my_agent.json"
        with open(agent_file, "w") as f:
            json.dump({"tools": ["cicada"]}, f)

        result = find_agent_files(repo_path)

        assert result["total_found"] == 2
        descriptions = [a["description"] for a in result["agents"]]
        assert "Claude Code instructions" in descriptions
        assert "Claude Code agents" in descriptions


class TestFindMcpFiles:
    """Tests for find_mcp_files function"""

    def test_no_mcp_files(self, tmp_path):
        """Should return empty when no MCP files exist"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        result = find_mcp_files(repo_path)

        assert result["total_found"] == 0
        assert result["files"] == []

    def test_finds_claude_code_mcp(self, tmp_path):
        """Should find Claude Code .mcp.json file"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        mcp_file = repo_path / ".mcp.json"
        mcp_data = {"mcpServers": {"cicada": {"command": "uvx"}}}
        with open(mcp_file, "w") as f:
            json.dump(mcp_data, f)

        result = find_mcp_files(repo_path)

        assert result["total_found"] == 1
        assert result["files"][0]["editor"] == "Claude Code"
        assert result["files"][0]["has_cicada"] is True
        assert result["files"][0]["relative_path"] == ".mcp.json"

    def test_finds_cursor_mcp(self, tmp_path):
        """Should find Cursor MCP config"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        cursor_dir = repo_path / ".cursor"
        cursor_dir.mkdir()

        mcp_file = cursor_dir / "mcp.json"
        mcp_data = {"mcpServers": {"cicada": {}}}
        with open(mcp_file, "w") as f:
            json.dump(mcp_data, f)

        result = find_mcp_files(repo_path)

        assert result["total_found"] == 1
        assert result["files"][0]["editor"] == "Cursor"
        assert result["files"][0]["has_cicada"] is True

    def test_finds_vscode_settings(self, tmp_path):
        """Should find VS Code settings.json"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        vscode_dir = repo_path / ".vscode"
        vscode_dir.mkdir()

        settings_file = vscode_dir / "settings.json"
        settings_data = {"mcpServers": {"cicada": {}}}
        with open(settings_file, "w") as f:
            json.dump(settings_data, f)

        result = find_mcp_files(repo_path)

        assert result["total_found"] == 1
        assert result["files"][0]["editor"] == "VS Code"

    def test_finds_gemini_mcp(self, tmp_path):
        """Should find Gemini CLI MCP config"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        gemini_dir = repo_path / ".gemini"
        gemini_dir.mkdir()

        mcp_file = gemini_dir / "settings.json"
        mcp_data = {"mcpServers": {"Cicada": {}}}
        with open(mcp_file, "w") as f:
            json.dump(mcp_data, f)

        result = find_mcp_files(repo_path)

        assert result["total_found"] == 1
        assert result["files"][0]["editor"] == "Gemini CLI"
        assert result["files"][0]["has_cicada"] is True

    def test_finds_codex_mcp(self, tmp_path):
        """Should find Codex MCP config"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        codex_dir = repo_path / ".codex"
        codex_dir.mkdir()

        mcp_file = codex_dir / "mcp.json"
        with open(mcp_file, "w") as f:
            json.dump({}, f)

        result = find_mcp_files(repo_path)

        assert result["total_found"] == 1
        assert result["files"][0]["editor"] == "Codex"
        assert result["files"][0]["has_cicada"] is False

    def test_finds_opencode_config(self, tmp_path):
        """Should find OpenCode config"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        config_file = repo_path / ".opencode.json"
        with open(config_file, "w") as f:
            json.dump({"mcp": "cicada"}, f)

        result = find_mcp_files(repo_path)

        assert result["total_found"] == 1
        assert result["files"][0]["editor"] == "OpenCode"
        assert result["files"][0]["has_cicada"] is True

    def test_detects_cicada_case_insensitive(self, tmp_path):
        """Should detect cicada references case-insensitively"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        mcp_file = repo_path / ".mcp.json"
        with open(mcp_file, "w") as f:
            f.write('{"servers": {"CICADA": {}}}')

        result = find_mcp_files(repo_path)

        assert result["files"][0]["has_cicada"] is True

    def test_finds_multiple_mcp_files(self, tmp_path):
        """Should find multiple MCP config files"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Create multiple MCP files
        mcp_file = repo_path / ".mcp.json"
        with open(mcp_file, "w") as f:
            json.dump({"cicada": True}, f)

        cursor_dir = repo_path / ".cursor"
        cursor_dir.mkdir()
        cursor_mcp = cursor_dir / "mcp.json"
        with open(cursor_mcp, "w") as f:
            json.dump({"cicada": True}, f)

        result = find_mcp_files(repo_path)

        assert result["total_found"] == 2

    def test_handles_read_error_gracefully(self, tmp_path):
        """Should handle file read errors gracefully"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        mcp_file = repo_path / ".mcp.json"
        with open(mcp_file, "w") as f:
            json.dump({}, f)

        # Mock open to raise an error
        original_open = open

        def mock_open(*args, **kwargs):
            if ".mcp.json" in str(args[0]):
                raise OSError("Permission denied")
            return original_open(*args, **kwargs)

        with patch("builtins.open", side_effect=mock_open):
            result = find_mcp_files(repo_path)

        # File exists but has_cicada should be False due to read error
        assert result["total_found"] == 1
        assert result["files"][0]["has_cicada"] is False


class TestDetermineTier:
    """Tests for _determine_tier function"""

    def test_fast_tier(self):
        """Should identify fast tier correctly"""
        tier = _determine_tier("regular", "lemmi")
        assert tier == "fast"

    def test_regular_tier(self):
        """Should identify regular tier correctly"""
        tier = _determine_tier("bert_small", "glove")
        assert tier == "regular"

    def test_max_tier(self):
        """Should identify max tier correctly"""
        tier = _determine_tier("bert_large", "fasttext")
        assert tier == "max"

    def test_unknown_combination(self):
        """Should return descriptive string for unknown combinations"""
        tier = _determine_tier("custom_method", "other_method")
        assert tier == "custom_method/other_method"

    def test_partial_match_not_tier(self):
        """Should not match tiers with partial method matches"""
        tier = _determine_tier("regular", "glove")
        assert tier == "regular/glove"

        tier = _determine_tier("bert_small", "lemmi")
        assert tier == "bert_small/lemmi"


class TestCheckRepository:
    """Tests for check_repository function"""

    def test_basic_output(self, tmp_path, mock_home_dir, capsys):
        """Should display basic status information"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        check_repository(repo_path)

        captured = capsys.readouterr()
        assert "Cicada Status" in captured.out
        assert "Repository:" in captured.out
        assert "INDEX STATUS" in captured.out
        assert "PR INDEX STATUS" in captured.out
        assert "AGENT FILES" in captured.out
        assert "MCP CONFIGURATION FILES" in captured.out
        assert "Summary:" in captured.out

    def test_no_index_output(self, tmp_path, mock_home_dir, capsys):
        """Should show 'No index found' when index doesn't exist"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        check_repository(repo_path)

        captured = capsys.readouterr()
        assert "✗ No index found" in captured.out

    def test_with_index_output(self, tmp_path, mock_home_dir, capsys):
        """Should display index information when it exists"""
        from cicada.utils.storage import (
            create_storage_dir,
            get_config_path,
            get_index_path,
        )

        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Create storage, index, and config
        create_storage_dir(repo_path)

        index_path = get_index_path(repo_path)
        with open(index_path, "w") as f:
            json.dump({"modules": {}}, f)

        config_path = get_config_path(repo_path)
        config_data = {
            "keyword_extraction": {"method": "bert_large"},
            "keyword_expansion": {"method": "fasttext"},
        }
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        check_repository(repo_path)

        captured = capsys.readouterr()
        assert "✓ Index exists:" in captured.out
        assert "Built:" in captured.out
        assert "Size:" in captured.out
        assert "Tier: max" in captured.out
        assert "Extraction: bert_large" in captured.out
        assert "Expansion: fasttext" in captured.out

    def test_with_pr_index_output(self, tmp_path, mock_home_dir, capsys):
        """Should display PR index information when it exists"""
        from cicada.utils.storage import create_storage_dir, get_pr_index_path

        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Create storage and PR index
        create_storage_dir(repo_path)
        pr_index_path = get_pr_index_path(repo_path)
        with open(pr_index_path, "w") as f:
            json.dump({"prs": []}, f)

        check_repository(repo_path)

        captured = capsys.readouterr()
        assert "✓ PR index exists:" in captured.out

    def test_with_agent_files_output(self, tmp_path, mock_home_dir, capsys):
        """Should display agent file information"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Create agent file
        agent_dir = repo_path / ".claude" / "agents"
        agent_dir.mkdir(parents=True)
        agent_file = agent_dir / "test.json"
        with open(agent_file, "w") as f:
            json.dump({"cicada": True}, f)

        check_repository(repo_path)

        captured = capsys.readouterr()
        assert "✓ Found 1 agent file(s) with cicada:" in captured.out
        assert ".claude/agents/test.json" in captured.out

    def test_with_mcp_files_output(self, tmp_path, mock_home_dir, capsys):
        """Should display MCP file information"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Create MCP file
        mcp_file = repo_path / ".mcp.json"
        with open(mcp_file, "w") as f:
            json.dump({"cicada": True}, f)

        check_repository(repo_path)

        captured = capsys.readouterr()
        assert "✓ Found 1 MCP config file(s):" in captured.out
        assert "(Claude Code)" in captured.out
        assert "(with cicada)" in captured.out

    def test_summary_counts(self, tmp_path, mock_home_dir, capsys):
        """Should display correct summary counts"""
        from cicada.utils.storage import (
            create_storage_dir,
            get_index_path,
            get_pr_index_path,
        )

        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Create index and PR index
        create_storage_dir(repo_path)

        index_path = get_index_path(repo_path)
        with open(index_path, "w") as f:
            json.dump({"modules": {}}, f)

        pr_index_path = get_pr_index_path(repo_path)
        with open(pr_index_path, "w") as f:
            json.dump({"prs": []}, f)

        # Create MCP file
        mcp_file = repo_path / ".mcp.json"
        with open(mcp_file, "w") as f:
            json.dump({"cicada": True}, f)

        check_repository(repo_path)

        captured = capsys.readouterr()
        # Should have 3/5 components: Index, PR Index, MCP files (no agent files, no links)
        assert "Summary: 3/5 components configured" in captured.out

    def test_resolves_repo_path(self, tmp_path, mock_home_dir, capsys):
        """Should resolve repository path"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Pass relative-like path (though still absolute in test)
        check_repository(repo_path)

        captured = capsys.readouterr()
        # Path should be resolved and displayed
        assert str(repo_path.resolve()) in captured.out

    def test_displays_config_dir(self, tmp_path, mock_home_dir, capsys):
        """Should display config dir when get_storage_dir succeeds"""
        from cicada.utils.storage import create_storage_dir

        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Create storage dir so it can be displayed
        create_storage_dir(repo_path)

        check_repository(repo_path)

        captured = capsys.readouterr()
        assert "Cicada Status" in captured.out
        assert "Config Dir:" in captured.out

    def test_handles_storage_dir_exception(self, tmp_path, mock_home_dir, capsys):
        """Should handle get_storage_dir exception gracefully (lines 296-297)"""
        from cicada.utils.storage import create_storage_dir, get_index_path
        from cicada.utils import storage as storage_module

        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        create_storage_dir(repo_path)
        index_path = get_index_path(repo_path)
        index_path.write_text('{"modules": {}}')

        # Store the original function
        original_get_storage_dir = storage_module.get_storage_dir

        # Track call count - the first call is inside check_repository's try block
        call_count = {"count": 0}

        def selective_raiser(*args, **kwargs):
            call_count["count"] += 1
            # Fail on the FIRST call (the try block in check_repository at line 294)
            if call_count["count"] == 1:
                raise Exception("Storage error")
            return original_get_storage_dir(*args, **kwargs)

        with patch.object(storage_module, "get_storage_dir", selective_raiser):
            check_repository(repo_path)

        captured = capsys.readouterr()
        assert "Cicada Status" in captured.out
        # Exception was caught - no crash and "Config Dir:" was not printed
        assert "Config Dir:" not in captured.out


class TestExceptionPaths:
    """Tests for exception handling paths"""

    def test_index_stat_oserror(self, tmp_path, mock_home_dir):
        """Should handle OSError when getting index file stats (lines 52-53)"""
        from cicada.utils.storage import create_storage_dir, get_index_path
        from datetime import datetime

        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        create_storage_dir(repo_path)
        index_path = get_index_path(repo_path)
        index_path.write_text('{"modules": {}}')

        # Mock datetime.fromtimestamp to raise ValueError
        with patch("cicada.status.datetime") as mock_dt:
            mock_dt.fromtimestamp.side_effect = ValueError("Invalid timestamp")
            info = get_index_info(repo_path)

        # Should have exists=True but gracefully handle the error
        assert info["exists"] is True

    def test_pr_index_stat_valueerror(self, tmp_path, mock_home_dir):
        """Should handle ValueError when getting PR index file stats (lines 103-104)"""
        from cicada.utils.storage import create_storage_dir, get_pr_index_path

        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        create_storage_dir(repo_path)
        pr_index_path = get_pr_index_path(repo_path)
        pr_index_path.write_text('{"prs": []}')

        # Mock datetime.fromtimestamp to raise ValueError
        with patch("cicada.status.datetime") as mock_dt:
            mock_dt.fromtimestamp.side_effect = ValueError("Invalid timestamp")
            info = get_pr_index_info(repo_path)

        assert info["exists"] is True

    def test_markdown_file_read_oserror(self, tmp_path):
        """Should handle OSError when reading markdown files (lines 166-167)"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        claude_md = repo_path / "CLAUDE.md"
        claude_md.write_text("cicada content")

        # Directly test the exception handling by mocking open at the cicada.status module level
        with patch("cicada.status.open", side_effect=OSError("Cannot read")):
            result = find_agent_files(repo_path)

        # Should gracefully handle the error
        assert result["total_found"] == 0

    def test_check_repository_no_date_display(self, tmp_path, mock_home_dir, capsys):
        """Should skip date display when date is None (branch 307->309)"""
        from cicada.utils.storage import create_storage_dir, get_index_path

        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        create_storage_dir(repo_path)
        index_path = get_index_path(repo_path)
        index_path.write_text('{"modules": {}}')

        with patch("cicada.status.get_index_info") as mock_info:
            mock_info.return_value = {
                "exists": True,
                "path": str(index_path),
                "date": None,  # No date
                "file_size": None,  # No size
                "tier": None,
                "extraction_method": None,
                "expansion_method": None,
            }
            check_repository(repo_path)

        captured = capsys.readouterr()
        assert "✓ Index exists:" in captured.out
        assert "Built:" not in captured.out
        assert "Size:" not in captured.out

    def test_check_repository_pr_index_no_date(self, tmp_path, mock_home_dir, capsys):
        """Should skip PR index date display when date is None (branch 328->330)"""
        from cicada.utils.storage import create_storage_dir, get_pr_index_path

        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        create_storage_dir(repo_path)
        pr_path = get_pr_index_path(repo_path)
        pr_path.write_text('{"prs": []}')

        with patch("cicada.status.get_pr_index_info") as mock_info:
            mock_info.return_value = {
                "exists": True,
                "path": str(pr_path),
                "date": None,
                "file_size": None,
            }
            check_repository(repo_path)

        captured = capsys.readouterr()
        assert "✓ PR index exists:" in captured.out
        assert captured.out.count("Built:") == 0  # No "Built:" for PR index

class TestCheckRepositoryLinkStatus:
    """Tests for link status section of check_repository"""

    @pytest.fixture
    def setup_repos(self, tmp_path, mock_home_dir):
        """Setup source and target repositories for link tests"""
        from cicada.utils.storage import create_storage_dir, get_index_path

        source_repo = tmp_path / "source_repo"
        source_repo.mkdir()
        target_repo = tmp_path / "target_repo"
        target_repo.mkdir()

        # Create storage dir and index for source repo (required for linking)
        create_storage_dir(source_repo)
        index_path = get_index_path(source_repo)
        with open(index_path, "w") as f:
            json.dump({"modules": {}, "metadata": {}}, f)

        return source_repo, target_repo

    def test_displays_forward_link(self, setup_repos, capsys):
        """Should display forward link info when repo is linked to source"""
        from cicada.utils.storage import create_link

        source_repo, target_repo = setup_repos

        # Create forward link from target to source
        create_link(target_repo, source_repo)

        check_repository(target_repo)

        captured = capsys.readouterr()
        assert "LINK STATUS" in captured.out
        assert f"This repo links to: {source_repo}" in captured.out
        assert "Linked at:" in captured.out

    def test_displays_no_forward_link(self, tmp_path, mock_home_dir, capsys):
        """Should display message when repo is not linked to any source"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        check_repository(repo_path)

        captured = capsys.readouterr()
        assert "LINK STATUS" in captured.out
        assert "This repo is not linked to any source repository" in captured.out

    def test_displays_valid_reverse_links(self, setup_repos, capsys):
        """Should display valid reverse links when other repos link to this one"""
        from cicada.utils.storage import create_link

        source_repo, target_repo = setup_repos

        # Create link from target to source (target links to source)
        create_link(target_repo, source_repo)

        # Now check the source repo - it should show target as a reverse link
        check_repository(source_repo)

        captured = capsys.readouterr()
        assert "LINK STATUS" in captured.out
        assert "Repositories linking to this (1 valid)" in captured.out
        assert str(target_repo) in captured.out

    def test_displays_no_reverse_links(self, tmp_path, mock_home_dir, capsys):
        """Should display message when no other repos link to this one"""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        check_repository(repo_path)

        captured = capsys.readouterr()
        assert "LINK STATUS" in captured.out
        assert "No other repositories link to this repo" in captured.out

    def test_displays_stale_reverse_links(self, setup_repos, capsys):
        """Should display stale reverse links when target has removed its link"""
        import shutil

        from cicada.utils.storage import create_link, get_storage_dir

        source_repo, target_repo = setup_repos

        # Create link from target to source
        create_link(target_repo, source_repo)

        # Remove target's storage (simulates deleted repo)
        target_storage = get_storage_dir(target_repo)
        shutil.rmtree(target_storage)

        # Now check source repo - should show stale reverse link
        check_repository(source_repo)

        captured = capsys.readouterr()
        assert "LINK STATUS" in captured.out
        assert "Stale reverse links (1)" in captured.out
        assert "does not exist" in captured.out

    def test_summary_with_links(self, setup_repos, capsys):
        """Should show Links component as configured when links exist"""
        from cicada.utils.storage import create_link

        source_repo, target_repo = setup_repos

        # Create link from target to source
        create_link(target_repo, source_repo)

        # Check target repo (has forward link)
        check_repository(target_repo)

        captured = capsys.readouterr()
        # Summary should show 2/5 components (Index + Links)
        assert "2/5 components configured" in captured.out
        # Link section should show forward link
        assert "This repo links to:" in captured.out
