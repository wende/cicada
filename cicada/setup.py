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
from typing import Any, Literal, cast

from cicada.languages.elixir.indexer import ElixirIndexer
from cicada.utils import (
    create_storage_dir,
    get_config_path,
    get_index_path,
)

EditorType = Literal["claude", "cursor", "vs"]


def detect_project_language(repo_path: Path) -> str:
    """
    Detect project language from marker files.

    Args:
        repo_path: Repository root path

    Returns:
        Language name ('elixir' or 'python')

    Raises:
        ValueError: If no recognized project type found
    """
    # Check for Python markers
    python_markers = [
        "pyproject.toml",
        "setup.py",
        "requirements.txt",
        "Pipfile",
        "poetry.lock",
    ]

    for marker in python_markers:
        if (repo_path / marker).exists():
            return "python"

    # Check for Elixir marker
    if (repo_path / "mix.exs").exists():
        return "elixir"

    # No recognized language
    raise ValueError(
        f"Could not detect project language in {repo_path}\n"
        "Expected Python markers (pyproject.toml, setup.py, etc.) "
        "or Elixir marker (mix.exs)"
    )


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
        with open(config_path) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Warning: Existing config at {config_path} is malformed, creating new one: {e}")
        return {}
    except OSError as e:
        print(f"Warning: Could not read config file {config_path}: {e}")
        return {}


def _build_server_config(
    command: str, args: list, cwd: str | None, repo_path: Path, storage_dir: Path
) -> dict[str, Any]:
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
    server_config: dict[str, Any] = {"command": command}

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
    config_path = cast(Path, spec["config_path"])

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
    repo_path: Path,
    storage_dir: Path,
    language: str | None = None,
    extraction_method: str | None = None,
    expansion_method: str | None = None,
    verbose: bool = True,
) -> None:
    """
    Create config.yaml in storage directory.

    Args:
        repo_path: Path to the repository
        storage_dir: Path to the storage directory
        language: Programming language (e.g., 'elixir', 'python'). If None, auto-detect.
        extraction_method: Keyword extraction method ('regular' or 'bert'), None for default
        expansion_method: Expansion method ('lemmi', 'glove', or 'fasttext'), None for default
        verbose: If True, print success message. If False, silently create config.
    """
    from cicada.utils.config import create_default_config, save_config

    config_path = get_config_path(repo_path)
    index_path = get_index_path(repo_path)

    # Auto-detect language if not provided
    if language is None:
        language = detect_project_language(repo_path)

    # Default to regular extraction + lemmi expansion
    if extraction_method is None:
        extraction_method = "regular"
    if expansion_method is None:
        expansion_method = "lemmi"

    # Create config using the centralized config module
    config_data = create_default_config(
        language=language,
        repo_path=repo_path,
        index_path=index_path,
        extraction_method=extraction_method,
        expansion_method=expansion_method,
    )

    save_config(config_data, config_path)

    if verbose:
        print(f"✓ Config file created at {config_path}")


def index_repository(
    repo_path: Path,
    language: str | None = None,
    force_full: bool = False,
    verbose: bool = True,
) -> None:
    """
    Index the repository with keyword extraction enabled.

    Args:
        repo_path: Path to the repository
        language: Language to index ('elixir' or 'python'). If None, auto-detect.
        force_full: If True, force full reindex instead of incremental
        verbose: Whether to print progress messages (default: True)

    Raises:
        Exception: If indexing fails
    """
    try:
        # Auto-detect language if not specified
        if language is None:
            language = detect_project_language(repo_path)
            if verbose:
                print(f"Detected {language} project")

        index_path = get_index_path(repo_path)

        # Get appropriate indexer for the language
        if language == "elixir":
            indexer = ElixirIndexer(verbose=verbose)
            # Elixir supports incremental indexing
            indexer.incremental_index_repository(
                repo_path=str(repo_path),
                output_path=str(index_path),
                extract_keywords=True,
                force_full=force_full,
            )
        elif language == "python":
            # Lazy import to avoid protobuf version conflicts when not using Python
            from cicada.languages.python.indexer import PythonSCIPIndexer

            indexer = PythonSCIPIndexer(verbose=verbose)
            # MVP: Python doesn't support incremental yet, always full index
            result = indexer.index_repository(
                repo_path=repo_path,
                output_path=index_path,
                force=True,
                verbose=verbose,
            )
            if not result.get("success"):
                errors = result.get("errors", ["Unknown error"])
                raise Exception(f"Indexing failed: {'; '.join(errors)}")
        else:
            raise ValueError(f"Unsupported language: {language}")

        # Don't print duplicate message - indexer already reports completion
    except Exception as e:
        if verbose:
            print(f"Error: Failed to index repository: {e}")
            if language == "elixir":
                print("Please check that the repository contains valid Elixir files.")
            elif language == "python":
                print("Please check that the repository contains valid Python files.")
                print("Note: Python indexing requires Node.js and npm.")
        raise


def setup_multiple_editors(
    editors: list[EditorType],
    repo_path: Path,
    storage_dir: Path,
    verbose: bool = False,
) -> None:
    """
    Create MCP configs for multiple editors at once (for server mode).

    Args:
        editors: List of editor types to configure
        repo_path: Path to the repository
        storage_dir: Path to the storage directory
        verbose: If True, print progress messages
    """
    for editor in editors:
        try:
            config_path, config_content = get_mcp_config_for_editor(editor, repo_path, storage_dir)

            # Write config file
            with open(config_path, "w") as f:
                json.dump(config_content, f, indent=2)

            if verbose:
                print(f"✓ Created {editor.upper()} config at {config_path}")
        except Exception as e:
            if verbose:
                print(f"⚠ Error creating {editor.upper()} config: {e}")


def ensure_setup(
    repo_path: Path,
    editor: EditorType | None = None,
    extraction_method: str | None = None,
    expansion_method: str | None = None,
    interactive: bool = True,
    silent: bool = False,
) -> tuple[str, str]:
    """
    Ensure the repository is properly set up (unified setup entry point).

    This function provides a single entry point for all commands to ensure
    a repository is set up with config.yaml and index.json. It handles three modes:

    1. Interactive mode (interactive=True, silent=False):
       - If config missing and no tier flags: show interactive menus
       - If config exists: reuse existing settings
       - Default behavior for `cicada install`

    2. Non-interactive with flags (interactive=True/False, extraction_method provided):
       - Use provided extraction/expansion methods
       - Skip interactive menus
       - Used when tier flags (--fast/--regular/--max) are provided

    3. Silent mode (silent=True):
       - Auto-use defaults (regular + lemmi)
       - No output
       - Used by MCP server background auto-setup

    Args:
        repo_path: Path to the repository
        editor: Editor to configure (optional, for setting up MCP config)
        extraction_method: Keyword extraction method ('regular' or 'bert'), None for auto-detect
        expansion_method: Expansion method ('lemmi', 'glove', 'fasttext'), None for auto-detect
        interactive: If True, show menus when settings missing (default: True)
        silent: If True, use defaults and suppress output (default: False, for MCP server only)

    Returns:
        tuple[str, str]: Final (extraction_method, expansion_method) used

    Raises:
        SystemExit: If config missing, no flags provided, and not interactive/silent mode

    Examples:
        # Interactive setup (shows menus if needed)
        ensure_setup(repo_path, editor="claude", interactive=True)

        # With tier flags (no menus)
        ensure_setup(repo_path, editor="claude", extraction_method="regular", expansion_method="lemmi")

        # Silent mode (MCP server)
        ensure_setup(repo_path, silent=True)
    """
    config_path = get_config_path(repo_path)
    index_path = get_index_path(repo_path)

    # Check if config and index already exist
    if config_path.exists() and index_path.exists():
        # Config exists - read and return existing settings
        import yaml

        try:
            with open(config_path) as f:
                existing_config = yaml.safe_load(f)
                existing_extraction = existing_config.get("keyword_extraction", {}).get(
                    "method", "regular"
                )
                existing_expansion = existing_config.get("keyword_expansion", {}).get(
                    "method", "lemmi"
                )

            # If tier flags provided and different from existing, validate they match
            # (setup() will handle the reindex confirmation prompt)
            if extraction_method and expansion_method:
                # Caller provided explicit settings - return those (setup will handle validation)
                return (extraction_method, expansion_method)

            # No tier flags - reuse existing settings
            return (existing_extraction, existing_expansion)
        except Exception as e:
            if not silent:
                print(f"Warning: Could not load existing config: {e}", file=sys.stderr)
            # Fall through to setup with provided or default settings

    # Config doesn't exist - need to set up
    # Determine extraction and expansion methods
    if extraction_method and expansion_method:
        # Explicit settings provided (from tier flags) - use them
        return (extraction_method, expansion_method)
    elif silent:
        # Silent mode - use defaults
        return ("regular", "lemmi")
    elif interactive:
        # Interactive mode - show menus
        from cicada.interactive_setup import show_first_time_setup

        if editor is None:
            # Just return the methods - caller will handle editor selection
            extraction, expansion = show_first_time_setup()
            return (extraction, expansion)
        else:
            # Full setup with editor already known
            extraction, expansion = show_first_time_setup()
            return (extraction, expansion)
    else:
        # Non-interactive, no flags, not silent - error
        print("Error: No tier specified.", file=sys.stderr)
        print("\nYou must specify a tier for keyword extraction:", file=sys.stderr)
        print("  --fast      Fast tier: Regular extraction + lemmi expansion", file=sys.stderr)
        print(
            "  --regular   Regular tier: KeyBERT small + GloVe expansion (default)",
            file=sys.stderr,
        )
        print("  --max       Max tier: KeyBERT large + FastText expansion", file=sys.stderr)
        print("\nRun 'cicada --help' for more information.", file=sys.stderr)
        sys.exit(2)


def update_claude_md(repo_path: Path) -> None:
    """Update CLAUDE.md with instructions to use cicada-mcp for Elixir codebase searches."""
    import re

    from cicada.mcp.tools import get_tool_definitions

    claude_md_path = repo_path / "CLAUDE.md"

    # Fail silently if CLAUDE.md doesn't exist
    if not claude_md_path.exists():
        return

    # Auto-generate tool list from mcp/tools.py
    tools = get_tool_definitions()
    tool_list: list[str] = []

    for tool in tools:
        # Extract first sentence from description (up to first period or newline)
        if tool.description:
            desc = tool.description.split("\n")[0].strip()
            if "." in desc:
                desc = desc.split(".")[0] + "."
            line = f"  - {desc} `mcp__cicada__{tool.name}`"
            tool_list.append(line)

    tool_list_str = "\n".join(tool_list)

    # Identify the categories of tools
    grep_antipatterns = [
        "  - ❌ Searching for module structure",
        "  - ❌ Searching for function definitions",
        "  - ❌ Searching for module imports/usage",
    ]
    grep_antipatterns_str = "\n".join(grep_antipatterns)

    instruction_content = f"""<cicada>
  **ALWAYS use cicada-mcp tools for Elixir code searches. NEVER use Grep/Find for these tasks.**

  ### Use cicada tools for:
{tool_list_str}

  ### DO NOT use Grep for:
{grep_antipatterns_str}

  ### You can still use Grep for:
  - ✓ Non-code files (markdown, JSON, config)
  - ✓ String literal searches
  - ✓ Pattern matching in single line comments
</cicada>
"""

    try:
        # Read existing content
        with open(claude_md_path) as f:
            content = f.read()

        # Pattern to find existing <cicada>...</cicada> tags
        cicada_pattern = re.compile(r"<cicada>.*?</cicada>", re.DOTALL)

        # Check if <cicada> tags exist
        if cicada_pattern.search(content):
            # Replace existing content between tags
            new_content = cicada_pattern.sub(instruction_content, content)
            with open(claude_md_path, "w") as f:
                f.write(new_content)
            print("✓ Updated <cicada> instructions in CLAUDE.md")
        elif "cicada-mcp" in content.lower() or "cicada" in content.lower():
            # Content already mentions cicada, don't add duplication
            # This handles cases where users manually added cicada instructions
            print("✓ CLAUDE.md already mentions cicada, skipping update")
        else:
            # Append the instruction
            with open(claude_md_path, "a") as f:
                # Add newline if file doesn't end with one
                if content and not content.endswith("\n"):
                    f.write("\n")

                f.write("\n")
                f.write(instruction_content)

            print("✓ Added cicada-mcp usage instructions to CLAUDE.md")
    except Exception:
        # Fail silently on any errors
        pass


def setup(
    editor: EditorType,
    repo_path: Path | None = None,
    extraction_method: str | None = None,
    expansion_method: str | None = None,
    index_exists: bool = False,
) -> None:
    """
    Run the complete setup for the specified editor.

    Args:
        editor: Editor type (claude, cursor, vs)
        repo_path: Path to the repository (defaults to current directory)
        extraction_method: Keyword extraction method ('regular' or 'bert'), None for default
        expansion_method: Expansion method ('lemmi', 'glove', or 'fasttext'), None for default
        index_exists: If True, skip banner and show condensed output (index already exists)
    """
    # Determine repository path
    if repo_path is None:
        repo_path = Path.cwd()
    repo_path = repo_path.resolve()

    # Detect language
    try:
        language = detect_project_language(repo_path)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Create storage directory
    storage_dir = create_storage_dir(repo_path)

    # Show condensed output if index already exists
    if index_exists:
        # Determine method for display
        display_extraction = extraction_method if extraction_method else "regular"
        display_expansion = expansion_method if expansion_method else "lemmi"
        print(f"Detected {language} project")
        print(
            f"✓ Found existing index ({display_extraction.upper()} + {display_expansion.upper()})"
        )
        # Skip indexing when index_exists is True - we're just reusing it
        should_index = False
        force_full = False
        # Ensure config.yaml is up to date with current settings
        create_config_yaml(
            repo_path,
            storage_dir,
            language=language,
            extraction_method=extraction_method,
            expansion_method=expansion_method,
            verbose=False,
        )
    else:
        # Show full banner for new setup
        print("=" * 60)
        print(f"Cicada Setup for {editor.upper()}")
        print("=" * 60)
        print()
        print(f"Detected language: {language}")
        print(f"Repository: {repo_path}")
        print(f"Storage: {storage_dir}")
        print()

        # Check if config already exists and determine if we need to reindex
        config_path = get_config_path(repo_path)
        index_path = get_index_path(repo_path)
        should_index = True
        force_full = False

        if config_path.exists() and index_path.exists():
            import yaml

            try:
                with open(config_path) as f:
                    existing_config = yaml.safe_load(f)
                    existing_extraction = existing_config.get("keyword_extraction", {}).get(
                        "method", "regular"
                    )
                    existing_expansion = existing_config.get("keyword_expansion", {}).get(
                        "method", "lemmi"
                    )

                    # Determine new methods (default to regular + lemmi if not specified)
                    new_extraction = extraction_method if extraction_method else "regular"
                    new_expansion = expansion_method if expansion_method else "lemmi"

                    # Check if settings changed
                    settings_changed = (existing_extraction != new_extraction) or (
                        existing_expansion != new_expansion
                    )

                    if settings_changed:
                        print("=" * 60)
                        print("⚠️  WARNING: Index Already Exists")
                        print("=" * 60)
                        print()
                        print(
                            f"This repository already has an index with {existing_extraction.upper()} + {existing_expansion.upper()}."
                        )
                        print(
                            f"You are now switching to {new_extraction.upper()} + {new_expansion.upper()}."
                        )
                        print()
                        print(
                            "This will require reindexing the ENTIRE codebase, which may take several minutes."
                        )
                        print()

                        # Ask for confirmation
                        response = input("Do you want to continue? [y/N]: ").strip().lower()
                        if response not in ("y", "yes"):
                            print("\nSetup cancelled.")
                            sys.exit(0)
                        print()
                        force_full = True  # Force full reindex when settings change
                    else:
                        # Settings unchanged - just use existing index
                        print(
                            f"✓ Using existing index ({existing_extraction.upper()} + {existing_expansion.upper()})"
                        )
                        print()
                        should_index = False
            except Exception:
                # If we can't read the config, just proceed with indexing
                pass

        # Create/update config.yaml BEFORE indexing (indexer reads this to determine keyword method)
        create_config_yaml(
            repo_path,
            storage_dir,
            language=language,
            extraction_method=extraction_method,
            expansion_method=expansion_method,
            verbose=False,
        )

        # Index repository if needed
        if should_index:
            index_repository(repo_path, language=language, force_full=force_full)
            print()

    # Update CLAUDE.md with cicada instructions (only for Claude Code editor)
    if editor == "claude":
        update_claude_md(repo_path)

    # Create MCP config for the editor
    config_path, config_content = get_mcp_config_for_editor(editor, repo_path, storage_dir)

    # Check if MCP config already exists
    mcp_config_existed = config_path.exists()

    # Write config file
    with open(config_path, "w") as f:
        json.dump(config_content, f, indent=2)

    if index_exists:
        # Show condensed success message
        mcp_verb = "updated" if mcp_config_existed else "created"
        print(f"✓ MCP configuration {mcp_verb} at {config_path}")
        print()
        print(f"Storage: {storage_dir}")
        print()
        print(f"Restart {editor.upper()}.")
        print("To reindex from scratch: cicada clean -f")
        print()
    else:
        # Show simplified success message for first-time setup
        print(f"Project config created at: {config_path}")
        print()
        print(f"Restart {editor.upper()}.")
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
        print("   • Access to cicada-index with enhanced keyword extraction (BERT/lemminflect)")
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

    # Check if it's an Elixir or Python repository
    try:
        detect_project_language(repo_path)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Run setup
    try:
        setup(args.editor, repo_path)
    except Exception as e:
        print(f"\nError: Setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
