#!/usr/bin/env python
"""
Cicada Simplified Setup Script.

One-command setup: uvx cicada [claude|cursor|vs]
- Indexes the repository with keyword extraction
- Stores all files in temp directory (~/.cicada/projects/<hash>/)
- Creates only MCP config file in user's repo
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
    # Detect installation method
    import shutil

    # Check if cicada-server is available
    has_cicada_server = shutil.which("cicada-server") is not None

    if has_cicada_server:
        command = "cicada-server"
        args = []
        cwd = None
    else:
        # Fallback to python with module path
        python_bin = sys.executable
        command = str(python_bin)
        args = ["-m", "cicada.mcp_server"]
        cwd = None

    if editor == "claude":
        # Claude Code uses .mcp.json
        config_path = repo_path / ".mcp.json"

        # Load existing config if present
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    config = json.load(f)
            except (json.JSONDecodeError, IOError):
                config = {}
        else:
            config = {}

        # Ensure mcpServers section exists
        if "mcpServers" not in config:
            config["mcpServers"] = {}

        # Build server configuration
        server_config = {"command": command}

        if args:
            server_config["args"] = args

        if cwd:
            server_config["cwd"] = cwd

        # Add environment variables
        server_config["env"] = {
            "CICADA_REPO_PATH": str(repo_path),
            "CICADA_CONFIG_DIR": str(storage_dir),
        }

        # Add or update cicada configuration
        config["mcpServers"]["cicada"] = server_config

        return config_path, config

    elif editor == "cursor":
        # Cursor uses .cursor/mcp.json (similar to Claude Code)
        config_dir = repo_path / ".cursor"
        config_dir.mkdir(exist_ok=True)
        config_path = config_dir / "mcp.json"

        # Load existing config if present
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    config = json.load(f)
            except (json.JSONDecodeError, IOError):
                config = {}
        else:
            config = {}

        # Ensure mcpServers section exists
        if "mcpServers" not in config:
            config["mcpServers"] = {}

        # Build server configuration
        server_config = {"command": command}

        if args:
            server_config["args"] = args

        if cwd:
            server_config["cwd"] = cwd

        # Add environment variables
        server_config["env"] = {
            "CICADA_REPO_PATH": str(repo_path),
            "CICADA_CONFIG_DIR": str(storage_dir),
        }

        # Add or update cicada configuration
        config["mcpServers"]["cicada"] = server_config

        return config_path, config

    elif editor == "vs":
        # VS Code uses .vscode/settings.json with MCP extension
        config_dir = repo_path / ".vscode"
        config_dir.mkdir(exist_ok=True)
        config_path = config_dir / "settings.json"

        # Load existing config if present
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    config = json.load(f)
            except (json.JSONDecodeError, IOError):
                config = {}
        else:
            config = {}

        # Ensure mcp.servers section exists
        if "mcp.servers" not in config:
            config["mcp.servers"] = {}

        # Build server configuration
        server_config = {"command": command}

        if args:
            server_config["args"] = args

        if cwd:
            server_config["cwd"] = cwd

        # Add environment variables
        server_config["env"] = {
            "CICADA_REPO_PATH": str(repo_path),
            "CICADA_CONFIG_DIR": str(storage_dir),
        }

        # Add or update cicada configuration
        config["mcp.servers"]["cicada"] = server_config

        return config_path, config

    else:
        raise ValueError(f"Unsupported editor: {editor}")


def create_config_yaml(repo_path: Path, storage_dir: Path) -> None:
    """
    Create config.yaml in storage directory.

    Args:
        repo_path: Path to the repository
        storage_dir: Path to the storage directory
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

    print(f"✓ Config file created at {config_path}")


def index_repository(repo_path: Path) -> None:
    """
    Index the repository with keyword extraction enabled.

    Args:
        repo_path: Path to the repository
    """
    print(f"Indexing repository at {repo_path}...")
    print("(Keyword extraction enabled with small spaCy model)")

    index_path = get_index_path(repo_path)
    indexer = ElixirIndexer(verbose=True)

    # Index with keyword extraction enabled by default
    # Note: Using 'small' model for compatibility with uvx
    # For better accuracy, install permanently and use cicada-index with --spacy-model medium/large
    indexer.index_repository(
        repo_path=str(repo_path),
        output_path=str(index_path),
        extract_keywords=True,
        spacy_model="small",
    )

    print(f"✓ Repository indexed at {index_path}")


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
    if not shutil.which("cicada-server"):
        print("💡 Tip: For best experience, install Cicada permanently:")
        print("   uv tool install git+https://github.com/wende/cicada.git@v0.1.1")
        print()
        print("   Benefits:")
        print("   • Faster MCP server startup")
        print("   • Access to cicada-index with medium/large spaCy models")
        print("   • PR indexing with cicada-index-pr")
        print()


def main():
    """Main entry point for the simplified setup script."""
    parser = argparse.ArgumentParser(
        description="Cicada One-Command Setup",
        epilog="Example: uvx cicada claude",
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

    # Check if it's an Elixir repository
    if not (repo_path / "mix.exs").exists():
        print(f"Error: {repo_path} does not appear to be an Elixir project")
        print("(mix.exs not found)")
        sys.exit(1)

    # Run setup
    setup(args.editor, repo_path)


if __name__ == "__main__":
    main()
