"""
Server command handler - Silent MCP server mode.

This module implements the `cicada server` / `cicada-mcp server` command,
which starts the MCP server in silent mode with auto-setup using defaults.
"""

import asyncio
import os
import sys
from argparse import Namespace
from pathlib import Path

from cicada.setup import EditorType, create_config_yaml, index_repository, setup_multiple_editors
from cicada.utils import create_storage_dir, get_config_path, get_index_path


def handle_server(args: Namespace) -> None:
    """
    Handle the server subcommand.

    Behavior:
    - SILENT: no prompts, no interactive menus
    - Auto-setup if needed (uses default model: lemminflect)
    - Creates editor configs if flags provided (--claude, --cursor, --vs)
    - Starts MCP server on stdio

    Args:
        args: Parsed command line arguments with attributes:
            - repo: Optional repository path
            - claude: Create Claude config
            - cursor: Create Cursor config
            - vs: Create VS Code config
            - nlp: Force lemminflect
            - rag: Force BERT
            - fast: Use fast tier
            - max: Use max tier
    """
    # Determine repository path
    repo_path = Path(args.repo).resolve() if args.repo else Path.cwd().resolve()

    # Validate it's an Elixir project
    if not (repo_path / "mix.exs").exists():
        print(
            f"Error: {repo_path} does not appear to be an Elixir project (mix.exs not found)",
            file=sys.stderr,
        )
        sys.exit(1)

    # Validate flag combinations
    if (args.fast or args.max) and not args.rag:
        print("Error: --fast or --max requires --rag", file=sys.stderr)
        sys.exit(1)

    if args.nlp and args.rag:
        print("Error: Cannot specify both --nlp and --rag", file=sys.stderr)
        sys.exit(1)

    # Create storage directory
    storage_dir = create_storage_dir(repo_path)

    # Determine keyword extraction method and tier
    keyword_method = None
    keyword_tier = None

    if args.nlp:
        keyword_method = "lemminflect"
        keyword_tier = "regular"
    elif args.rag:
        keyword_method = "bert"
        if args.fast:
            keyword_tier = "fast"
        elif args.max:
            keyword_tier = "max"
        else:
            keyword_tier = "regular"

    # Check if setup is needed
    config_path = get_config_path(repo_path)
    index_path = get_index_path(repo_path)
    needs_setup = not (config_path.exists() and index_path.exists())

    if needs_setup:
        # Silent setup with defaults
        # If no method specified, default to lemminflect (fastest, no downloads)
        if keyword_method is None:
            keyword_method = "lemminflect"
            keyword_tier = "regular"

        # Create config.yaml (silent)
        create_config_yaml(repo_path, storage_dir, keyword_method, keyword_tier, verbose=False)

        # Index repository (silent)
        try:
            index_repository(repo_path, force_full=False, verbose=False)
        except Exception as e:
            print(f"Error during indexing: {e}", file=sys.stderr)
            sys.exit(1)

    # Create editor configs if flags provided
    editors_to_configure: list[EditorType] = []
    if args.claude:
        editors_to_configure.append("claude")
    if args.cursor:
        editors_to_configure.append("cursor")
    if args.vs:
        editors_to_configure.append("vs")

    if editors_to_configure:
        try:
            setup_multiple_editors(editors_to_configure, repo_path, storage_dir, verbose=False)
        except Exception as e:
            print(f"Error creating editor configs: {e}", file=sys.stderr)
            sys.exit(1)

    # Set environment variable for MCP server
    os.environ["CICADA_REPO_PATH"] = str(repo_path)

    # Start MCP server (silent)
    from cicada.mcp_server import async_main

    asyncio.run(async_main())
