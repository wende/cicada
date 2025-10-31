#!/usr/bin/env python
"""
Cicada Simplified Setup Script.

One-command setup: uvx --from cicada-mcp cicada [claude|cursor|vs]
- Indexes the repository with keyword extraction
- Stores all files in temp directory (~/.cicada/projects/<hash>/)
- Creates only MCP config file in user's repo
- Generates MCP config that uses 'uvx cicada-mcp' (works with or without permanent install)
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Literal

from cicada.indexer import ElixirIndexer
from cicada.utils import (
    create_storage_dir,
    get_index_path,
    get_config_path,
    get_hashes_path,
    get_storage_dir,
)


EditorType = Literal["claude", "cursor", "vs"]


def _load_existing_config(config_path: Path) -> dict:
    """
    Load existing configuration file with error handling.

    Args:
        config_path: Path to the config file

    Returns:
        Loaded config dict, or empty dict if file doesn't exist or is invalid
    """
    if not config_path.exists():
        return {}

    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(
            f"Warning: Existing config at {config_path} is malformed, creating new one: {e}"
        )
        return {}
    except IOError as e:
        print(f"Warning: Could not read config file {config_path}: {e}")
        return {}


def _build_server_config(
    command: str, args: list, cwd: str | None, repo_path: Path, storage_dir: Path
) -> dict:
    """
    Build the MCP server configuration.

    Args:
        command: Command to run the MCP server
        args: Command line arguments
        cwd: Working directory (optional)
        repo_path: Path to the repository
        storage_dir: Path to the storage directory

    Returns:
        Server configuration dict
    """
    server_config = {"command": command}

    if args:
        server_config["args"] = args

    if cwd:
        server_config["cwd"] = cwd

    server_config["env"] = {
        "CICADA_REPO_PATH": str(repo_path),
        "CICADA_CONFIG_DIR": str(storage_dir),
    }

    return server_config


def get_mcp_config_for_editor(
    editor: EditorType, repo_path: Path, storage_dir: Path
) -> tuple[Path, dict]:
    """
    Get the MCP configuration file path and content for a specific editor.

    Args:
        editor: Editor type (claude, cursor, vs)
        repo_path: Path to the repository
        storage_dir: Path to the storage directory

    Returns:
        Tuple of (config_file_path, config_content)
    """
    # Always use uvx for maximum compatibility
    # Works whether cicada-mcp is permanently installed or not
    command = "uvx"
    args = ["cicada-mcp"]
    cwd = None

    # Editor-specific specifications
    editor_specs = {
        "claude": {
            "config_path": repo_path / ".mcp.json",
            "config_key": "mcpServers",
            "needs_dir": False,
        },
        "cursor": {
            "config_path": repo_path / ".cursor" / "mcp.json",
            "config_key": "mcpServers",
            "needs_dir": True,
        },
        "vs": {
            "config_path": repo_path / ".vscode" / "settings.json",
            "config_key": "mcp.servers",
            "needs_dir": True,
        },
    }

    if editor not in editor_specs:
        raise ValueError(f"Unsupported editor: {editor}")

    spec = editor_specs[editor]
    config_path = spec["config_path"]

    # Create parent directory if needed
    if spec["needs_dir"]:
        config_path.parent.mkdir(exist_ok=True)

    # Load existing config
    config = _load_existing_config(config_path)

    # Ensure config section exists
    if spec["config_key"] not in config:
        config[spec["config_key"]] = {}

    # Build and add server configuration
    server_config = _build_server_config(command, args, cwd, repo_path, storage_dir)
    config[spec["config_key"]]["cicada"] = server_config

    return config_path, config


def create_config_yaml(
    repo_path: Path, storage_dir: Path, verbose: bool = True
) -> None:
    """
    Create config.yaml in storage directory.

    Args:
        repo_path: Path to the repository
        storage_dir: Path to the storage directory
        verbose: Whether to print progress messages (default: True)
    """
    config_path = get_config_path(repo_path)
    index_path = get_index_path(repo_path)

    config_content = f"""repository:
  path: {repo_path}

storage:
  index_path: {index_path}
"""

    with open(config_path, "w") as f:
        f.write(config_content)

    if verbose:
        print(f"✓ Config file created at {config_path}")


def index_repository(repo_path: Path, verbose: bool = True) -> None:
    """
    Index the repository with keyword extraction enabled.

    Args:
        repo_path: Path to the repository
        verbose: Whether to print progress messages (default: True)

    Raises:
        Exception: If indexing fails
    """
    try:
        index_path = get_index_path(repo_path)
        indexer = ElixirIndexer(verbose=verbose)

        # Index with keyword extraction enabled by default
        # Note: Using 'small' model for compatibility with uvx
        # For better accuracy, install permanently and use cicada-index with --spacy-model medium/large
        indexer.index_repository(
            repo_path=str(repo_path),
            output_path=str(index_path),
            extract_keywords=True,
            spacy_model="small",
        )

        if verbose:
            print(f"✓ Repository indexed at {index_path}")
    except Exception as e:
        if verbose:
            print(f"Error: Failed to index repository: {e}")
            print("Please check that the repository contains valid Elixir files.")
        raise


def setup(editor: EditorType, repo_path: Path | None = None) -> None:
    """
    Run the complete setup for the specified editor.

    Args:
        editor: Editor type (claude, cursor, vs)
        repo_path: Path to the repository (defaults to current directory)
    """
    # Determine repository path
    if repo_path is None:
        repo_path = Path.cwd()
    repo_path = repo_path.resolve()

    print("=" * 60)
    print(f"Cicada Setup for {editor.upper()}")
    print("=" * 60)
    print()

    # Create storage directory
    print(f"Repository: {repo_path}")
    storage_dir = create_storage_dir(repo_path)
    print(f"Storage: {storage_dir}")
    print()

    # Index repository
    index_repository(repo_path)
    print()

    # Create config.yaml
    create_config_yaml(repo_path, storage_dir)
    print()

    # Create MCP config for the editor
    config_path, config_content = get_mcp_config_for_editor(
        editor, repo_path, storage_dir
    )

    # Write config file
    with open(config_path, "w") as f:
        json.dump(config_content, f, indent=2)

    print(f"✓ MCP configuration created at {config_path}")
    print()

    print("=" * 60)
    print("✓ Setup Complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print(f"1. Restart {editor.upper()}")
    print("2. Cicada MCP server will be available automatically")
    print()
    print("Storage location:")
    print(f"  {storage_dir}")
    print()
    print("All index files are stored outside your repository.")
    print(f"Only {config_path.name} was added to your repo.")
    print()

    # Check if running via uvx and suggest permanent installation
    import shutil

    # Check for either cicada-mcp or cicada-server (backwards compat)
    if not (shutil.which("cicada-mcp") or shutil.which("cicada-server")):
        print("💡 Tip: For best experience, install Cicada permanently:")
        print("   uv tool install cicada-mcp")
        print()
        print("   Benefits:")
        print("   • Faster MCP server startup (no uvx overhead)")
        print("   • Access to cicada-index with medium/large spaCy models")
        print("   • PR indexing with cicada-index-pr")
        print()


def main():
    """Main entry point for the simplified setup script."""
    parser = argparse.ArgumentParser(
        description="Cicada One-Command Setup",
        epilog="Example: uvx --from cicada-mcp cicada claude",
    )
    parser.add_argument(
        "editor",
        choices=["claude", "cursor", "vs"],
        help="Editor to configure (claude=Claude Code, cursor=Cursor, vs=VS Code)",
    )
    parser.add_argument(
        "repo",
        nargs="?",
        default=None,
        help="Path to the Elixir repository (default: current directory)",
    )

    args = parser.parse_args()

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

    # Check if it's an Elixir repository
    if not (repo_path / "mix.exs").exists():
        print(f"Error: {repo_path} does not appear to be an Elixir project")
        print("(mix.exs not found)")
        sys.exit(1)

    # Run setup
    try:
        setup(args.editor, repo_path)
    except Exception as e:
        print(f"\nError: Setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
