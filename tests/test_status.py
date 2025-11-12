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

        mcp_file = gemini_dir / "mcp.json"
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
        # Should have 3/4 components: Index, PR Index, MCP files (no agent files)
        assert "Summary: 3/4 components configured" in captured.out

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
