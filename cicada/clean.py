#!/usr/bin/env python
"""
Cicada Clean Command.

Removes all Cicada configuration and indexes for a repository.
"""

import argparse
import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from cicada.utils import (
    get_embeddings_path,
    get_hashes_path,
    get_index_path,
    get_pr_index_path,
    get_storage_dir,
)


@dataclass
class CleanItem:
    """Represents an item to be cleaned/removed."""

    description: str
    path: Path
    is_mcp_config: bool = False


def remove_mcp_config_entry(config_path: Path, server_key: str = "cicada") -> bool:
    """
    Remove Cicada entry from an MCP configuration file.

    Args:
        config_path: Path to the MCP config file
        server_key: Server key to remove (default: "cicada")

    Returns:
        True if entry was removed, False if file doesn't exist or no entry found
    """
    if not config_path.exists():
        return False

    try:
        with open(config_path) as f:
            config = json.load(f)

        # Determine the config key based on editor type
        if ".mcp.json" in str(config_path) or ".cursor" in str(config_path):
            config_key = "mcpServers"
        elif ".vscode" in str(config_path):
            config_key = "mcp.servers"
        else:
            return False

        # Check if the key exists and remove cicada entry
        if config_key in config and server_key in config[config_key]:
            del config[config_key][server_key]

            # Write back the modified config
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)

            return True

    except (OSError, json.JSONDecodeError) as e:
        print(f"Warning: Could not process {config_path}: {e}")

    return False


def clean_index_only(repo_path: Path) -> None:
    """
    Remove only the main index files (index.json, hashes.json, and embeddings.jsonl).

    Args:
        repo_path: Path to the repository
    """
    repo_path = repo_path.resolve()

    print("=" * 60)
    print("Cicada Clean - Main Index")
    print("=" * 60)
    print()
    print(f"Repository: {repo_path}")
    print()

    # Collect index files to remove
    items_to_remove: list[CleanItem] = []

    index_path = get_index_path(repo_path)
    hashes_path = get_hashes_path(repo_path)
    embeddings_path = get_embeddings_path(repo_path)

    if index_path.exists():
        items_to_remove.append(CleanItem("Main index", index_path))
    if hashes_path.exists():
        items_to_remove.append(CleanItem("File hashes", hashes_path))
    if embeddings_path.exists():
        items_to_remove.append(CleanItem("Embeddings store", embeddings_path))

    # Show what will be removed
    if not items_to_remove:
        print("✓ No main index files found.")
        print()
        return

    print("The following items will be removed:")
    print()
    for item in items_to_remove:
        print(f"  • {item.description}: {item.path}")
    print()

    # Remove items
    removed_count = 0
    errors = []
    for item in items_to_remove:
        try:
            item.path.unlink()
            print(f"✓ Removed {item.description}")
            removed_count += 1
        except (OSError, PermissionError) as e:
            error_msg = f"Failed to remove {item.description}: {e}"
            print(f"✗ {error_msg}")
            errors.append(error_msg)

    print()
    print("=" * 60)
    if errors:
        print(
            f"⚠ Cleanup completed with errors ({removed_count}/{len(items_to_remove)} items removed)"
        )
        print("=" * 60)
        print()
        sys.exit(1)
    else:
        print(f"✓ Cleanup Complete! ({removed_count} items removed)")
        print("=" * 60)
        print()


def clean_pr_index_only(repo_path: Path) -> None:
    """
    Remove only the PR index file (pr_index.json).

    Args:
        repo_path: Path to the repository
    """
    repo_path = repo_path.resolve()

    print("=" * 60)
    print("Cicada Clean - PR Index")
    print("=" * 60)
    print()
    print(f"Repository: {repo_path}")
    print()

    pr_index_path = get_pr_index_path(repo_path)

    if not pr_index_path.exists():
        print("✓ No PR index file found.")
        print()
        return

    print("The following item will be removed:")
    print()
    print(f"  • PR index: {pr_index_path}")
    print()

    # Remove PR index
    try:
        pr_index_path.unlink()
        print("✓ Removed PR index")
        print()
        print("=" * 60)
        print("✓ Cleanup Complete!")
        print("=" * 60)
        print()
    except (OSError, PermissionError) as e:
        print(f"✗ Failed to remove PR index: {e}")
        sys.exit(1)


def clean_repository(repo_path: Path, force: bool = False) -> None:
    """
    Remove all Cicada configuration and indexes for a repository.

    Args:
        repo_path: Path to the repository
        force: Skip confirmation prompt if True
    """
    from cicada.utils.storage import get_link_info, is_linked

    repo_path = repo_path.resolve()

    print("=" * 60)
    print("Cicada Clean")
    print("=" * 60)
    print()
    print(f"Repository: {repo_path}")
    print()

    # Check if repository is linked
    if is_linked(repo_path):
        link_info = get_link_info(repo_path)
        print("⚠ This repository is linked to another repository's index:")
        if link_info:
            print(f"  Source: {link_info.get('source_repo_path', '<missing>')}")
        print()
        print("Cleaning will only remove the link file, not the source index.")
        print("To unlink without removing other files, use: cicada unlink")
        print()

    # Collect items to remove
    items_to_remove: list[CleanItem] = []

    # 1. Storage directory (~/.cicada/projects/<repo_hash>/)
    storage_dir = get_storage_dir(repo_path)
    if storage_dir.exists():
        items_to_remove.append(CleanItem("Storage directory", storage_dir))

    # 2. Old .cicada directory (backward compatibility)
    old_cicada_dir = repo_path / ".cicada"
    if old_cicada_dir.exists():
        items_to_remove.append(CleanItem("Legacy .cicada directory", old_cicada_dir))

    # 3. MCP config files
    mcp_configs = [
        (repo_path / ".mcp.json", "Claude Code config"),
        (repo_path / ".cursor" / "mcp.json", "Cursor config"),
        (repo_path / ".vscode" / "settings.json", "VS Code config"),
    ]

    for config_path, desc in mcp_configs:
        if config_path.exists():
            # Check if cicada entry exists
            try:
                with open(config_path) as f:
                    config = json.load(f)

                config_key = "mcpServers" if ".vscode" not in str(config_path) else "mcp.servers"

                if config_key in config and "cicada" in config[config_key]:
                    items_to_remove.append(CleanItem(desc, config_path, is_mcp_config=True))
            except (OSError, json.JSONDecodeError):
                pass

    # Show what will be removed
    if not items_to_remove:
        print("✓ No Cicada configuration found for this repository.")
        print()
        return

    print("The following items will be removed:")
    print()
    for item in items_to_remove:
        if item.is_mcp_config:
            print(f"  • {item.description}: Remove 'cicada' entry from {item.path}")
        else:
            print(f"  • {item.description}: {item.path}")
    print()

    # Confirmation prompt
    if not force:
        response = input("Are you sure you want to continue? [y/N]: ")
        if response.lower() not in ["y", "yes"]:
            print("Aborted.")
            return

    print()
    print("Removing Cicada configuration...")
    print()

    # Remove items
    removed_count = 0
    errors = []
    for item in items_to_remove:
        if item.is_mcp_config:
            if remove_mcp_config_entry(item.path):
                print(f"✓ Removed 'cicada' entry from {item.description}")
                removed_count += 1
            else:
                error_msg = f"Failed to remove 'cicada' entry from {item.description}"
                print(f"✗ {error_msg}")
                errors.append(error_msg)
        else:
            try:
                if item.path.is_dir():
                    shutil.rmtree(item.path)
                else:
                    item.path.unlink()
                print(f"✓ Removed {item.description}")
                removed_count += 1
            except (OSError, PermissionError) as e:
                error_msg = f"Failed to remove {item.description}: {e}"
                print(f"✗ {error_msg}")
                errors.append(error_msg)

    print()
    print("=" * 60)
    if errors:
        print(
            f"⚠ Cleanup completed with errors ({removed_count}/{len(items_to_remove)} items removed)"
        )
        print("=" * 60)
        print()
        sys.exit(1)
    else:
        print(f"✓ Cleanup Complete! ({removed_count} items removed)")
        print("=" * 60)
        print()
        print("Next steps:")
        print("1. Restart your editor if it's currently running")
        print("2. Run 'uvx cicada <editor>' to set up Cicada again")
        print()


def clean_all_projects(force: bool = False) -> None:
    """
    Remove all Cicada storage directories for all projects.

    Args:
        force: Skip confirmation prompt if True
    """
    from pathlib import Path

    storage_base = Path.home() / ".cicada" / "projects"

    if not storage_base.exists():
        print("✓ No Cicada storage found (~/.cicada/projects/ does not exist).")
        return

    # Count project directories
    project_dirs = [d for d in storage_base.iterdir() if d.is_dir()]

    if not project_dirs:
        print("✓ No Cicada projects found in ~/.cicada/projects/")
        return

    print("=" * 60)
    print("Cicada Clean All Projects")
    print("=" * 60)
    print()
    print(f"Found {len(project_dirs)} project(s) in: {storage_base}")
    print()

    # Show project directories
    print("The following storage directories will be removed:")
    print()
    for proj_dir in sorted(project_dirs):
        print(f"  • {proj_dir.name}/")
    print()

    # Confirmation prompt
    if not force:
        response = input(
            f"Are you sure you want to remove ALL {len(project_dirs)} project(s)? [y/N]: "
        )
        if response.lower() not in ["y", "yes"]:
            print("Aborted.")
            return

    print()
    print("Removing all Cicada storage directories...")
    print()

    # Remove all project directories
    removed_count = 0
    errors = []
    for proj_dir in project_dirs:
        try:
            shutil.rmtree(proj_dir)
            print(f"✓ Removed {proj_dir.name}/")
            removed_count += 1
        except (OSError, PermissionError) as e:
            error_msg = f"Failed to remove {proj_dir.name}/: {e}"
            print(f"✗ {error_msg}")
            errors.append(error_msg)

    print()
    print("=" * 60)
    if errors:
        print(
            f"⚠ Cleanup completed with errors ({removed_count}/{len(project_dirs)} projects removed)"
        )
        print("=" * 60)
        print()
        sys.exit(1)
    else:
        print(f"✓ Cleanup Complete! ({removed_count}/{len(project_dirs)} projects removed)")
        print("=" * 60)
        print()


def main():
    """
    Main entry point for the clean command.

    Note: This function is kept for backward compatibility but the unified CLI
    in cli.py should be used instead (cicada clean).
    """
    parser = argparse.ArgumentParser(
        description="Remove all Cicada configuration and indexes for current repository",
        epilog="Examples:\n"
        "  cicada clean                 # Clean current repository\n"
        "  cicada clean -f              # Clean current repository (skip confirmation)\n"
        "  cicada clean --all           # Remove ALL project storage\n"
        "  cicada clean --all -f        # Remove ALL project storage (skip confirmation)\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Skip confirmation prompt",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Remove ALL Cicada storage for all projects (~/.cicada/projects/)",
    )

    args = parser.parse_args()

    # Handle --all flag
    if args.all:
        try:
            clean_all_projects(force=args.force)
        except Exception as e:
            print(f"\nError: Cleanup failed: {e}")
            sys.exit(1)
        return

    # Clean current directory
    repo_path = Path.cwd()

    # Run cleanup
    try:
        clean_repository(repo_path, force=args.force)
    except Exception as e:
        print(f"\nError: Cleanup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
