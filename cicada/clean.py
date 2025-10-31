#!/usr/bin/env python
"""
Cicada Clean Command.

Removes all Cicada configuration and indexes for a repository.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

from cicada.utils import get_storage_dir


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
        with open(config_path, "r") as f:
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

    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Could not process {config_path}: {e}")

    return False


def clean_repository(repo_path: Path, force: bool = False) -> None:
    """
    Remove all Cicada configuration and indexes for a repository.

    Args:
        repo_path: Path to the repository
        force: Skip confirmation prompt if True
    """
    repo_path = repo_path.resolve()

    print("=" * 60)
    print("Cicada Clean")
    print("=" * 60)
    print()
    print(f"Repository: {repo_path}")
    print()

    # Collect items to remove
    items_to_remove = []

    # 1. Storage directory (~/.cicada/projects/<repo_hash>/)
    storage_dir = get_storage_dir(repo_path)
    if storage_dir.exists():
        items_to_remove.append(("Storage directory", storage_dir))

    # 2. Old .cicada directory (backward compatibility)
    old_cicada_dir = repo_path / ".cicada"
    if old_cicada_dir.exists():
        items_to_remove.append(("Legacy .cicada directory", old_cicada_dir))

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
                with open(config_path, "r") as f:
                    config = json.load(f)

                config_key = (
                    "mcpServers" if ".vscode" not in str(config_path) else "mcp.servers"
                )

                if config_key in config and "cicada" in config[config_key]:
                    items_to_remove.append(
                        (desc, config_path, True)
                    )  # True = is MCP config
            except (json.JSONDecodeError, IOError):
                pass

    # Show what will be removed
    if not items_to_remove:
        print("✓ No Cicada configuration found for this repository.")
        print()
        return

    print("The following items will be removed:")
    print()
    for item in items_to_remove:
        if len(item) == 3 and item[2]:  # MCP config entry
            print(f"  • {item[0]}: Remove 'cicada' entry from {item[1]}")
        else:
            print(f"  • {item[0]}: {item[1]}")
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
    for item in items_to_remove:
        if len(item) == 3 and item[2]:  # MCP config entry
            desc, config_path, _ = item
            if remove_mcp_config_entry(config_path):
                print(f"✓ Removed 'cicada' entry from {desc}")
                removed_count += 1
        else:
            desc, path = item
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
                print(f"✓ Removed {desc}")
                removed_count += 1
            except (OSError, PermissionError) as e:
                print(f"✗ Failed to remove {desc}: {e}")

    print()
    print("=" * 60)
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
    for proj_dir in project_dirs:
        try:
            shutil.rmtree(proj_dir)
            print(f"✓ Removed {proj_dir.name}/")
            removed_count += 1
        except (OSError, PermissionError) as e:
            print(f"✗ Failed to remove {proj_dir.name}/: {e}")

    print()
    print("=" * 60)
    print(f"✓ Cleanup Complete! ({removed_count}/{len(project_dirs)} projects removed)")
    print("=" * 60)
    print()


def main():
    """Main entry point for the clean command."""
    parser = argparse.ArgumentParser(
        description="Remove all Cicada configuration and indexes for a repository",
        epilog="Examples:\n"
        "  cicada-clean -f              # Clean current repository\n"
        "  cicada-clean --all -f        # Remove ALL project storage\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "repo",
        nargs="?",
        default=None,
        help="Path to the repository (default: current directory)",
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

    # Determine repo path
    repo_path = Path(args.repo) if args.repo else Path.cwd()

    # Validate path exists
    if not repo_path.exists():
        print(f"Error: Path does not exist: {repo_path}")
        sys.exit(1)

    # Validate path is a directory
    if not repo_path.is_dir():
        print(f"Error: Path is not a directory: {repo_path}")
        sys.exit(1)

    # Run cleanup
    try:
        clean_repository(repo_path, force=args.force)
    except Exception as e:
        print(f"\nError: Cleanup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
