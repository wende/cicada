#!/usr/bin/env python
"""
Cicada Status Command.

Provides diagnostic information about Cicada configuration and indexes.
"""

from datetime import datetime
from pathlib import Path

import yaml

from cicada.utils import (
    get_config_path,
    get_index_path,
    get_pr_index_path,
)
from cicada.utils.storage import (
    get_link_info,
    is_linked,
    validate_linked_from,
)


def get_index_info(repo_path: Path) -> dict[str, bool | str | int | None]:
    """
    Get information about the main index.

    Args:
        repo_path: Path to the repository

    Returns:
        Dictionary with index information
    """
    index_path = get_index_path(repo_path)
    config_path = get_config_path(repo_path)

    info: dict[str, bool | str | int | None] = {
        "exists": index_path.exists(),
        "path": str(index_path),
        "date": None,
        "mode": None,
        "file_size": None,
    }

    # Check if index exists
    if not info["exists"]:
        return info

    # Get file size and modification date
    try:
        stat = index_path.stat()
        info["file_size"] = stat.st_size
        info["date"] = datetime.fromtimestamp(stat.st_mtime).isoformat()
    except (OSError, ValueError):
        pass

    # Get indexing mode from config
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = yaml.safe_load(f) or {}

            mode = config.get("indexing", {}).get("mode")
            if mode in ("keywords", "embeddings"):
                info["mode"] = mode
            elif config.get("keyword_extraction") or config.get("keyword_expansion"):
                info["mode"] = "keywords"
        except (OSError, yaml.YAMLError):
            pass

    return info


def get_pr_index_info(repo_path: Path) -> dict[str, bool | str | int | None]:
    """
    Get information about the PR index.

    Args:
        repo_path: Path to the repository

    Returns:
        Dictionary with PR index information
    """
    pr_index_path = get_pr_index_path(repo_path)

    info: dict[str, bool | str | int | None] = {
        "exists": pr_index_path.exists(),
        "path": str(pr_index_path),
        "date": None,
        "file_size": None,
    }

    if not info["exists"]:
        return info

    # Get file size and modification date
    try:
        stat = pr_index_path.stat()
        info["file_size"] = stat.st_size
        info["date"] = datetime.fromtimestamp(stat.st_mtime).isoformat()
    except (OSError, ValueError):
        pass

    return info


def find_agent_files(repo_path: Path) -> dict:
    """
    Find agent files that contain 'cicada' references.

    Args:
        repo_path: Path to the repository

    Returns:
        Dictionary with agent file information
    """
    # Common agent file locations for different editors
    agent_locations = [
        (repo_path / ".claude" / "agents", "Claude Code agents"),
        (repo_path / ".cursor" / "agents", "Cursor agents"),
        (repo_path / ".vscode" / "agents", "VS Code agents"),
    ]

    # Root-level markdown files that may contain cicada instructions
    agent_md_files = [
        (repo_path / "CLAUDE.md", "Claude Code instructions"),
        (repo_path / "AGENTS.md", "Agent instructions"),
    ]

    agents_with_cicada = []

    # Check JSON agent files in editor directories
    for agent_dir, desc in agent_locations:
        if agent_dir.exists() and agent_dir.is_dir():
            for agent_file in agent_dir.glob("*.json"):
                try:
                    with open(agent_file) as f:
                        content = f.read()
                        if "cicada" in content.lower():
                            agents_with_cicada.append(
                                {
                                    "file": str(agent_file),
                                    "description": desc,
                                    "relative_path": str(agent_file.relative_to(repo_path)),
                                }
                            )
                except OSError:
                    pass

    # Check root-level markdown files
    for md_file, desc in agent_md_files:
        if md_file.exists() and md_file.is_file():
            try:
                with open(md_file) as f:
                    content = f.read()
                    if "cicada" in content.lower():
                        agents_with_cicada.append(
                            {
                                "file": str(md_file),
                                "description": desc,
                                "relative_path": str(md_file.relative_to(repo_path)),
                            }
                        )
            except OSError:
                pass

    return {
        "total_found": len(agents_with_cicada),
        "agents": agents_with_cicada,
    }


def find_mcp_files(repo_path: Path) -> dict:
    """
    Find MCP configuration files.

    Args:
        repo_path: Path to the repository

    Returns:
        Dictionary with MCP file information
    """
    mcp_files: list[dict[str, Path | str]] = [
        {
            "path": repo_path / ".mcp.json",
            "description": "Claude Code config",
            "editor": "Claude Code",
        },
        {
            "path": repo_path / ".cursor" / "mcp.json",
            "description": "Cursor config",
            "editor": "Cursor",
        },
        {
            "path": repo_path / ".vscode" / "settings.json",
            "description": "VS Code config",
            "editor": "VS Code",
        },
        {
            "path": repo_path / ".gemini" / "settings.json",
            "description": "Gemini CLI config",
            "editor": "Gemini CLI",
        },
        {
            "path": repo_path / ".codex" / "mcp.json",
            "description": "Codex config",
            "editor": "Codex",
        },
        {
            "path": repo_path / ".opencode.json",
            "description": "OpenCode config",
            "editor": "OpenCode",
        },
    ]

    existing_files = []
    for mcp_config in mcp_files:
        config_path = mcp_config["path"]
        assert isinstance(config_path, Path), "path should be a Path object"
        if config_path.exists():
            # Check if cicada is configured in the file
            has_cicada = False
            try:
                with open(config_path) as f:
                    content = f.read()
                    if "cicada" in content.lower():
                        has_cicada = True
            except OSError:
                pass

            existing_files.append(
                {
                    "path": str(config_path),
                    "description": mcp_config["description"],
                    "editor": mcp_config["editor"],
                    "has_cicada": has_cicada,
                    "relative_path": str(config_path.relative_to(repo_path)),
                }
            )

    return {
        "total_found": len(existing_files),
        "files": existing_files,
    }


def check_repository(repo_path: Path) -> None:
    """
    Display diagnostic information about Cicada configuration for a repository.

    Args:
        repo_path: Path to the repository
    """
    from cicada.utils.storage import get_storage_dir

    repo_path = repo_path.resolve()

    print("=" * 70)
    print("Cicada Status")
    print("=" * 70)
    print()
    print(f"Repository: {repo_path}")

    try:
        storage_dir = get_storage_dir(repo_path)
        print(f"Config Dir: {storage_dir}")
    except Exception:
        pass

    print()

    # 1. Index status
    print("1. INDEX STATUS")
    print("-" * 70)
    index_info = get_index_info(repo_path)
    if index_info["exists"]:
        print(f"✓ Index exists: {index_info['path']}")
        if index_info["date"]:
            print(f"  Built: {index_info['date']}")
        if index_info["file_size"] and isinstance(index_info["file_size"], int):
            size_mb = index_info["file_size"] / (1024 * 1024)
            print(f"  Size: {size_mb:.2f} MB")
        if index_info["mode"]:
            print(f"  Mode: {index_info['mode']}")
    else:
        print("✗ No index found")
    print()

    # 2. PR Index status
    print("2. PR INDEX STATUS")
    print("-" * 70)
    pr_info = get_pr_index_info(repo_path)
    if pr_info["exists"]:
        print(f"✓ PR index exists: {pr_info['path']}")
        if pr_info["date"]:
            print(f"  Built: {pr_info['date']}")
        if pr_info["file_size"] and isinstance(pr_info["file_size"], int):
            size_mb = pr_info["file_size"] / (1024 * 1024)
            print(f"  Size: {size_mb:.2f} MB")
    else:
        print("✗ No PR index found")
    print()

    # 3. Agent files
    print("3. AGENT FILES WITH CICADA")
    print("-" * 70)
    agents = find_agent_files(repo_path)
    if agents["total_found"] > 0:
        print(f"✓ Found {agents['total_found']} agent file(s) with cicada:")
        for agent in agents["agents"]:
            print(f"  • {agent['relative_path']}")
            print(f"    ({agent['description']})")
    else:
        print("✗ No agent files with cicada found")
    print()

    # 4. MCP files
    print("4. MCP CONFIGURATION FILES")
    print("-" * 70)
    mcp_files = find_mcp_files(repo_path)
    if mcp_files["total_found"] > 0:
        print(f"✓ Found {mcp_files['total_found']} MCP config file(s):")
        for mcp_file in mcp_files["files"]:
            cicada_str = " (with cicada)" if mcp_file["has_cicada"] else ""
            print(f"  • ({mcp_file['editor']}) {mcp_file['relative_path']}{cicada_str}")
    else:
        print("✗ No MCP config files found")
    print()

    # 5. Link status
    print("5. LINK STATUS")
    print("-" * 70)

    # Check forward link (this repo links to another)
    has_forward_link = is_linked(repo_path)
    if has_forward_link:
        link_info = get_link_info(repo_path)
        if link_info:
            print(f"This repo links to: {link_info.get('source_repo_path', 'unknown')}")
            if link_info.get("linked_at"):
                print(f"  Linked at: {link_info['linked_at']}")
    else:
        print("This repo is not linked to any source repository")

    print()

    # Check reverse links (other repos link to this one)
    validation_results = validate_linked_from(repo_path)
    valid_links = []
    stale_links = []
    for entry, is_valid, reason in validation_results:
        if is_valid:
            valid_links.append((entry, reason))
        else:
            stale_links.append((entry, reason))

    if valid_links:
        print(f"Repositories linking to this ({len(valid_links)} valid):")
        for entry, _ in valid_links:
            print(f"  • {entry.get('target_repo_path', 'unknown')}")
    else:
        print("No other repositories link to this repo")

    if stale_links:
        print()
        print(f"Stale reverse links ({len(stale_links)}):")
        for entry, reason in stale_links:
            print(f"  • {entry.get('target_repo_path', 'unknown')} ({reason})")

    print()

    # Check if there are any active links
    has_any_links = has_forward_link or len(valid_links) > 0

    # Summary
    print("=" * 70)
    status_items = [
        ("Index", index_info["exists"]),
        ("PR Index", pr_info["exists"]),
        ("Agent files", agents["total_found"] > 0),
        ("MCP files", mcp_files["total_found"] > 0),
        ("Links", has_any_links),
    ]

    configured_count = sum(1 for _, exists in status_items if exists)
    print(f"Summary: {configured_count}/{len(status_items)} components configured")
    print("=" * 70)
    print()
