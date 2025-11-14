"""Tests for cicada/editor_specs.py module"""

from pathlib import Path

import pytest

from cicada.editor_specs import (
    CLI_EDITOR_NAMES,
    CLI_EDITOR_SPECS,
    EDITOR_PROMPT_OPTIONS,
    EDITOR_SPEC_BY_NAME,
    EDITOR_SPECS,
    EditorSpec,
    EditorType,
    get_editor_specs,
)


class TestEditorSpec:
    """Tests for EditorSpec dataclass"""

    def test_editor_spec_creation(self):
        """Should create EditorSpec with all required fields"""
        spec = EditorSpec(
            name="claude",
            cli_help="Test help",
            cli_description="Test description",
            prompt_label="Test label",
            config_relpath=Path(".mcp.json"),
            config_key="mcpServers",
            needs_dir=False,
        )
        assert spec.name == "claude"
        assert spec.cli_help == "Test help"
        assert spec.cli_description == "Test description"
        assert spec.prompt_label == "Test label"
        assert spec.config_relpath == Path(".mcp.json")
        assert spec.config_key == "mcpServers"
        assert spec.needs_dir is False
        assert spec.cli_available is True

    def test_editor_spec_with_cli_available_false(self):
        """Should create EditorSpec with cli_available=False"""
        spec = EditorSpec(
            name="opencode",
            cli_help="Test help",
            cli_description="Test description",
            prompt_label="Test label",
            config_relpath=Path(".opencode.json"),
            config_key="mcpServers",
            needs_dir=False,
            cli_available=False,
        )
        assert spec.cli_available is False

    def test_editor_spec_frozen(self):
        """Should be frozen (immutable)"""
        spec = EditorSpec(
            name="claude",
            cli_help="Test help",
            cli_description="Test description",
            prompt_label="Test label",
            config_relpath=Path(".mcp.json"),
            config_key="mcpServers",
            needs_dir=False,
        )
        with pytest.raises(AttributeError):
            spec.name = "cursor"  # type: ignore


class TestEditorSpecs:
    """Tests for EDITOR_SPECS tuple"""

    def test_editor_specs_contains_all_editors(self):
        """Should contain specs for all supported editors"""
        editor_names = {spec.name for spec in EDITOR_SPECS}
        expected_names = {"claude", "cursor", "vs", "gemini", "codex", "opencode"}
        assert editor_names == expected_names

    def test_editor_specs_immutable(self):
        """Should be immutable tuple"""
        assert isinstance(EDITOR_SPECS, tuple)
        with pytest.raises(TypeError):
            EDITOR_SPECS[0] = EditorSpec(  # type: ignore
                name="test",
                cli_help="Test",
                cli_description="Test",
                prompt_label="Test",
                config_relpath=Path(".test"),
                config_key="test",
                needs_dir=False,
            )

    def test_claude_spec(self):
        """Should have correct Claude spec"""
        claude_spec = next(s for s in EDITOR_SPECS if s.name == "claude")
        assert claude_spec.cli_help == "Setup Cicada for Claude Code editor"
        assert claude_spec.config_relpath == Path(".mcp.json")
        assert claude_spec.config_key == "mcpServers"
        assert claude_spec.needs_dir is False
        assert claude_spec.cli_available is True

    def test_cursor_spec(self):
        """Should have correct Cursor spec"""
        cursor_spec = next(s for s in EDITOR_SPECS if s.name == "cursor")
        assert cursor_spec.cli_help == "Setup Cicada for Cursor editor"
        assert cursor_spec.config_relpath == Path(".cursor") / "mcp.json"
        assert cursor_spec.config_key == "mcpServers"
        assert cursor_spec.needs_dir is True
        assert cursor_spec.cli_available is True

    def test_vs_spec(self):
        """Should have correct VS Code spec"""
        vs_spec = next(s for s in EDITOR_SPECS if s.name == "vs")
        assert vs_spec.cli_help == "Setup Cicada for VS Code editor"
        assert vs_spec.config_relpath == Path(".vscode") / "settings.json"
        assert vs_spec.config_key == "mcp.servers"
        assert vs_spec.needs_dir is True
        assert vs_spec.cli_available is True

    def test_gemini_spec(self):
        """Should have correct Gemini spec"""
        gemini_spec = next(s for s in EDITOR_SPECS if s.name == "gemini")
        assert gemini_spec.cli_help == "Setup Cicada for Gemini CLI"
        assert gemini_spec.config_relpath == Path(".gemini") / "mcp.json"
        assert gemini_spec.config_key == "mcpServers"
        assert gemini_spec.needs_dir is True
        assert gemini_spec.cli_available is True

    def test_codex_spec(self):
        """Should have correct Codex spec"""
        codex_spec = next(s for s in EDITOR_SPECS if s.name == "codex")
        assert codex_spec.cli_help == "Setup Cicada for Codex editor"
        assert codex_spec.config_relpath == Path(".codex") / "mcp.json"
        assert codex_spec.config_key == "mcpServers"
        assert codex_spec.needs_dir is True
        assert codex_spec.cli_available is True

    def test_opencode_spec(self):
        """Should have correct OpenCode spec"""
        opencode_spec = next(s for s in EDITOR_SPECS if s.name == "opencode")
        assert opencode_spec.cli_help == "Setup Cicada for OpenCode"
        assert opencode_spec.config_relpath == Path(".mcp.json")
        assert opencode_spec.config_key == "mcpServers"
        assert opencode_spec.needs_dir is False
        assert opencode_spec.cli_available is False


class TestEditorSpecByName:
    """Tests for EDITOR_SPEC_BY_NAME dictionary"""

    def test_editor_spec_by_name_mapping(self):
        """Should map all editor names to their specs"""
        assert len(EDITOR_SPEC_BY_NAME) == len(EDITOR_SPECS)
        for spec in EDITOR_SPECS:
            assert EDITOR_SPEC_BY_NAME[spec.name] == spec

    def test_editor_spec_by_name_access(self):
        """Should allow direct access by editor name"""
        assert EDITOR_SPEC_BY_NAME["claude"].name == "claude"
        assert EDITOR_SPEC_BY_NAME["cursor"].name == "cursor"
        assert EDITOR_SPEC_BY_NAME["vs"].name == "vs"
        assert EDITOR_SPEC_BY_NAME["gemini"].name == "gemini"
        assert EDITOR_SPEC_BY_NAME["codex"].name == "codex"
        assert EDITOR_SPEC_BY_NAME["opencode"].name == "opencode"


class TestCliEditorSpecs:
    """Tests for CLI_EDITOR_SPECS tuple"""

    def test_cli_editor_specs_excludes_non_cli(self):
        """Should exclude editors with cli_available=False"""
        cli_names = {spec.name for spec in CLI_EDITOR_SPECS}
        assert "opencode" not in cli_names
        assert len(CLI_EDITOR_SPECS) == len(EDITOR_SPECS) - 1

    def test_cli_editor_specs_includes_available(self):
        """Should include all CLI-available editors"""
        cli_names = {spec.name for spec in CLI_EDITOR_SPECS}
        expected_cli_names = {"claude", "cursor", "vs", "gemini", "codex"}
        assert cli_names == expected_cli_names


class TestCliEditorNames:
    """Tests for CLI_EDITOR_NAMES tuple"""

    def test_cli_editor_names_correct(self):
        """Should contain names of all CLI-available editors"""
        assert set(CLI_EDITOR_NAMES) == {"claude", "cursor", "vs", "gemini", "codex"}
        assert len(CLI_EDITOR_NAMES) == 5

    def test_cli_editor_names_order_preserved(self):
        """Should preserve order from CLI_EDITOR_SPECS"""
        expected_names = [spec.name for spec in CLI_EDITOR_SPECS]
        assert list(CLI_EDITOR_NAMES) == expected_names


class TestEditorPromptOptions:
    """Tests for EDITOR_PROMPT_OPTIONS list"""

    def test_editor_prompt_options_correct(self):
        """Should contain prompt labels for CLI-available editors"""
        expected_labels = [spec.prompt_label for spec in CLI_EDITOR_SPECS]
        assert EDITOR_PROMPT_OPTIONS == expected_labels

    def test_editor_prompt_options_excludes_non_cli(self):
        """Should not include opencode prompt label"""
        opencode_label = next(s.prompt_label for s in EDITOR_SPECS if s.name == "opencode")
        assert opencode_label not in EDITOR_PROMPT_OPTIONS


class TestGetEditorSpecs:
    """Tests for get_editor_specs function"""

    def test_get_editor_specs_single_editor(self):
        """Should return specs for a single editor"""
        specs = get_editor_specs(["claude"])
        assert len(specs) == 1
        assert specs[0].name == "claude"

    def test_get_editor_specs_multiple_editors(self):
        """Should return specs for multiple editors"""
        specs = get_editor_specs(["claude", "cursor", "vs"])
        assert len(specs) == 3
        assert specs[0].name == "claude"
        assert specs[1].name == "cursor"
        assert specs[2].name == "vs"

    def test_get_editor_specs_preserves_order(self):
        """Should preserve the order of input names"""
        specs = get_editor_specs(["vs", "claude", "cursor"])
        assert [s.name for s in specs] == ["vs", "claude", "cursor"]

    def test_get_editor_specs_empty_list(self):
        """Should return empty list for empty input"""
        specs = get_editor_specs([])
        assert specs == []

    def test_get_editor_specs_all_editors(self):
        """Should work with all editor names"""
        all_names: list[EditorType] = ["claude", "cursor", "vs", "gemini", "codex", "opencode"]
        specs = get_editor_specs(all_names)
        assert len(specs) == 6
        assert [s.name for s in specs] == all_names
