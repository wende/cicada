"""Centralized editor metadata used across CLI, setup, and cleanup flows."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

EditorType = Literal["claude", "cursor", "vs", "gemini", "codex", "opencode"]


@dataclass(frozen=True, slots=True)
class EditorSpec:
    """Describes editor-specific configuration and CLI metadata."""

    name: EditorType
    cli_help: str
    cli_description: str
    prompt_label: str
    config_relpath: Path
    config_key: str
    needs_dir: bool
    cli_available: bool = True  # Some specs (e.g., opencode) are not exposed as subcommands.


EDITOR_SPECS: tuple[EditorSpec, ...] = (
    EditorSpec(
        name="claude",
        cli_help="Setup Cicada for Claude Code editor",
        cli_description="One-command setup for Claude Code with keyword extraction",
        prompt_label="Claude Code (Claude AI assistant)",
        config_relpath=Path(".mcp.json"),
        config_key="mcpServers",
        needs_dir=False,
    ),
    EditorSpec(
        name="cursor",
        cli_help="Setup Cicada for Cursor editor",
        cli_description="One-command setup for Cursor with keyword extraction",
        prompt_label="Cursor (AI-powered code editor)",
        config_relpath=Path(".cursor") / "mcp.json",
        config_key="mcpServers",
        needs_dir=True,
    ),
    EditorSpec(
        name="vs",
        cli_help="Setup Cicada for VS Code editor",
        cli_description="One-command setup for VS Code with keyword extraction",
        prompt_label="VS Code (Visual Studio Code)",
        config_relpath=Path(".vscode") / "settings.json",
        config_key="mcp.servers",
        needs_dir=True,
    ),
    EditorSpec(
        name="gemini",
        cli_help="Setup Cicada for Gemini CLI",
        cli_description="One-command setup for Gemini CLI with keyword extraction",
        prompt_label="Gemini CLI (Google Gemini command line interface)",
        config_relpath=Path(".gemini") / "settings.json",
        config_key="mcpServers",
        needs_dir=True,
    ),
    EditorSpec(
        name="codex",
        cli_help="Setup Cicada for Codex editor",
        cli_description="One-command setup for Codex with keyword extraction",
        prompt_label="Codex (AI code editor)",
        config_relpath=Path(".codex") / "mcp.json",
        config_key="mcpServers",
        needs_dir=True,
    ),
    EditorSpec(
        name="opencode",
        cli_help="Setup Cicada for OpenCode",
        cli_description="Configure Cicada MCP for OpenCode",
        prompt_label="OpenCode (experimental)",
        config_relpath=Path(".mcp.json"),
        config_key="mcpServers",
        needs_dir=False,
        cli_available=False,
    ),
)

EDITOR_SPEC_BY_NAME = {spec.name: spec for spec in EDITOR_SPECS}
CLI_EDITOR_SPECS: tuple[EditorSpec, ...] = tuple(
    spec for spec in EDITOR_SPECS if spec.cli_available
)
CLI_EDITOR_NAMES: tuple[EditorType, ...] = tuple(spec.name for spec in CLI_EDITOR_SPECS)
EDITOR_PROMPT_OPTIONS: list[str] = [spec.prompt_label for spec in CLI_EDITOR_SPECS]


def get_editor_specs(names: Sequence[EditorType]) -> list[EditorSpec]:
    """Return specs for provided editor names, preserving order."""
    return [EDITOR_SPEC_BY_NAME[name] for name in names]
