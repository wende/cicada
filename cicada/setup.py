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

from cicada.languages import LanguageRegistry
from cicada.languages.generic.indexer import run_generic_indexing_for_language_indexer
from cicada.utils import (
    create_storage_dir,
    get_config_path,
    get_index_path,
)

EditorType = Literal["claude", "cursor", "vs", "gemini", "codex", "opencode"]


def detect_project_language(repo_path: Path) -> str:
    """
    Detect project language from marker files.

    Args:
        repo_path: Repository root path

    Returns:
        Language name ('elixir', 'python', etc.)

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

    # Check for Rust marker
    if (repo_path / "Cargo.toml").exists():
        return "rust"

    # Check for Erlang markers
    erlang_markers = ["rebar.config", "rebar.lock", "erlang.mk"]
    for marker in erlang_markers:
        if (repo_path / marker).exists():
            return "erlang"

    # Fallback: Check for .erl files in src/ directory (common Erlang convention)
    src_dir = repo_path / "src"
    if src_dir.exists() and any(src_dir.glob("*.erl")):
        return "erlang"

    # Check for TypeScript/JavaScript markers
    ts_markers = ["tsconfig.json", "package.json"]
    for marker in ts_markers:
        if (repo_path / marker).exists():
            # Check if it's TypeScript or plain JavaScript
            if (repo_path / "tsconfig.json").exists():
                return "typescript"
            return "javascript"

    # Check for Go marker
    if (repo_path / "go.mod").exists():
        return "go"

    # Check for JVM language markers (Java, Scala)
    # Check Scala first (build.sbt is unique to Scala)
    if (repo_path / "build.sbt").exists():
        return "scala"

    # Check for Gradle/Maven projects (Java)
    jvm_markers = ["build.gradle", "build.gradle.kts", "pom.xml"]
    for marker in jvm_markers:
        if (repo_path / marker).exists():
            return "java"

    # Check for C/C++ markers
    c_markers = ["CMakeLists.txt", "Makefile", "compile_commands.json"]
    for marker in c_markers:
        if (repo_path / marker).exists():
            # Check if it's C++ or C
            if any(repo_path.rglob("*.cpp")) or any(repo_path.rglob("*.cc")):
                return "cpp"
            if any(repo_path.rglob("*.c")):
                return "c"
            # Default to C++ if marker exists but no specific files found
            return "cpp"

    # Check for Ruby marker
    if (repo_path / "Gemfile").exists():
        return "ruby"

    # Check for C#/VB (.NET) markers
    if any(repo_path.glob("*.sln")) or any(repo_path.glob("*.csproj")):
        return "csharp"
    if any(repo_path.glob("*.vbproj")):
        return "vb"

    # Check for Dart marker
    if (repo_path / "pubspec.yaml").exists():
        return "dart"

    # No recognized language
    raise ValueError(
        f"Could not detect project language in {repo_path}\n"
        "Expected one of: Python (pyproject.toml), Elixir (mix.exs), Rust (Cargo.toml), "
        "Erlang (rebar.config), TypeScript/JavaScript (package.json), Go (go.mod), "
        "Java (build.gradle/pom.xml), Scala (build.sbt), C/C++ (CMakeLists.txt/Makefile), "
        "Ruby (Gemfile), C# (*.csproj), VB (*.vbproj), Dart (pubspec.yaml)"
    )


def _setup_gitattributes(repo_path: Path) -> None:
    """
    Create or update .gitattributes and git config for Elixir function tracking.

    This enables git log -L :funcname: syntax to work with Elixir files.
    """
    import subprocess

    # Create or update .gitattributes
    gitattributes_path = repo_path / ".gitattributes"
    gitattributes_lines = ["*.ex diff=elixir", "*.exs diff=elixir"]
    created_or_updated = False

    if gitattributes_path.exists():
        existing_content = gitattributes_path.read_text()
        # Check if already configured
        if "diff=elixir" not in existing_content:
            # Append configuration
            with open(gitattributes_path, "a") as f:
                f.write("\n# Cicada: Enable git function tracking for Elixir\n")
                for line in gitattributes_lines:
                    f.write(f"{line}\n")
            print("✓ Updated .gitattributes for git function tracking")
            created_or_updated = True
    else:
        # Create new file
        with open(gitattributes_path, "w") as f:
            f.write("# Cicada: Enable git function tracking for Elixir\n")
            for line in gitattributes_lines:
                f.write(f"{line}\n")
        print("✓ Created .gitattributes for git function tracking")
        created_or_updated = True

    # Configure git diff.elixir.xfuncname pattern in local repo config
    # This pattern matches Elixir function definitions: def, defp, defmacro, etc.
    xfuncname_pattern = "^[[:space:]]*(def|defp|defmacro|defmacrop|test)[[:space:]]"

    try:
        subprocess.run(
            ["git", "config", "diff.elixir.xfuncname", xfuncname_pattern],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        if created_or_updated:
            print("✓ Configured git for Elixir function tracking")
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        # Silently ignore if git config fails (e.g., not a git repo, directory doesn't exist)
        pass


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
        "gemini": {
            "config_path": repo_path / ".gemini" / "settings.json",
            "config_key": "mcpServers",
            "needs_dir": True,
        },
        "codex": {
            "config_path": repo_path / ".codex" / "mcp.json",
            "config_key": "mcpServers",
            "needs_dir": True,
        },
        "opencode": {
            "config_path": repo_path / ".mcp.json",
            "config_key": "mcpServers",
            "needs_dir": False,
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
    indexing_mode: str | None = None,
    verbose: bool = True,
    embeddings_config: dict[str, str] | None = None,
) -> None:
    """
    Create config.yaml in storage directory.

    Args:
        repo_path: Path to the repository
        storage_dir: Path to the storage directory
        indexing_mode: Indexing mode ("keywords" or "embeddings"), None for default
        verbose: If True, print success message. If False, silently create config.
        embeddings_config: Optional embeddings configuration with 'ollama_host' and 'model'
    """
    config_path = get_config_path(repo_path)
    index_path = get_index_path(repo_path)

    if indexing_mode is None:
        indexing_mode = "keywords"

    config_content = f"""repository:
  path: {repo_path}

storage:
  index_path: {index_path}

indexing:
  mode: {indexing_mode}
"""

    # Add embeddings configuration if provided
    if embeddings_config:
        ollama_host = embeddings_config.get("ollama_host", "http://localhost:11434")
        model = embeddings_config.get("model", "nomic-embed-text")
        config_content += f"""
embeddings:
  ollama_host: {ollama_host}
  model: {model}
"""

    with open(config_path, "w") as f:
        f.write(config_content)

    if verbose:
        print(f"✓ Config file created at {config_path}")


def index_repository(
    repo_path: Path, language: str, force_full: bool = False, verbose: bool = True
) -> None:
    """
    Index the repository with keyword extraction enabled.

    Args:
        repo_path: Path to the repository
        language: Programming language (e.g., 'python', 'elixir', 'typescript')
        force_full: If True, force full reindex instead of incremental
        verbose: Whether to print progress messages (default: True)

    Raises:
        Exception: If indexing fails
    """
    try:
        index_path = get_index_path(repo_path)
        config_path = get_config_path(repo_path)
        from cicada.index_mode import ensure_supported_mode, read_indexing_mode_config

        indexing_mode = read_indexing_mode_config(repo_path)
        ensure_supported_mode(indexing_mode)

        # Use standard indexer interface
        indexer = LanguageRegistry.get_indexer(language)
        # Check if indexer supports incremental_index_repository (new unified API)
        if hasattr(indexer, "incremental_index_repository"):
            indexer.incremental_index_repository(
                repo_path=str(repo_path),
                output_path=str(index_path),
                extract_keywords=True,
                compute_timestamps=True,
                extract_cochange=True,  # Enable co-change analysis by default
                force_full=force_full,
                verbose=verbose,
            )
        else:
            # Fallback to basic interface for legacy indexers
            indexer.index_repository(
                repo_path=str(repo_path),
                output_path=str(index_path),
                force=force_full,
                verbose=verbose,
                config_path=str(config_path),
            )
        run_generic_indexing_for_language_indexer(
            indexer,
            repo_path,
            index_path,
            verbose=verbose,
        )
        # Don't print duplicate message - indexer already reports completion
    except Exception as e:
        if verbose:
            print(f"Error: Failed to index repository: {e}")
            print(f"Please check that the repository contains valid {language} files.")
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


def update_claude_md(repo_path: Path, editor: EditorType | None = None) -> None:
    """Update CLAUDE.md and AGENTS.md with instructions to use cicada-mcp for Elixir and Python codebase searches.

    Args:
        repo_path: Path to the repository
        editor: Editor type - defaults to None which updates CLAUDE.md (for backward compatibility)
    """
    from cicada.mcp.tools import get_tool_definitions

    claude_md_path = repo_path / "CLAUDE.md"
    agents_md_path = repo_path / "AGENTS.md"

    # Process CLAUDE.md if no editor specified (backward compatibility) or if editor is 'claude'
    if (editor is None or editor == "claude") and claude_md_path.exists():
        _update_md_file(claude_md_path, get_tool_definitions())

    # Process AGENTS.md for all editors if it exists (when editor is specified)
    if editor is not None and agents_md_path.exists():
        _update_md_file(agents_md_path, get_tool_definitions())


def _update_md_file(md_path: Path, tools) -> None:
    """Update a markdown file with cicada tool instructions.

    Args:
        md_path: Path to the markdown file (CLAUDE.md or AGENTS.md)
        tools: Tool definitions from get_tool_definitions()
    """
    import re

    # Auto-generate tool list from tools
    tool_list: list[str] = []

    for tool in tools:
        # Skip deprecated tools
        if tool.description and "DEPRECATED" in tool.description:
            continue

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
  **ALWAYS use cicada-mcp tools for Elixir and Python code searches. NEVER use Grep/Find for these tasks.**

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
        with open(md_path) as f:
            content = f.read()

        # Pattern to find existing <cicada>...</cicada> tags
        cicada_pattern = re.compile(r"<cicada>.*?</cicada>", re.DOTALL)

        # Check if <cicada> tags exist
        if cicada_pattern.search(content):
            # Replace existing content between tags
            new_content = cicada_pattern.sub(instruction_content, content)
            with open(md_path, "w") as f:
                f.write(new_content)
            print(f"✓ Updated <cicada> instructions in {md_path.name}")
        else:
            # Append the instruction
            with open(md_path, "a") as f:
                # Add newline if file doesn't end with one
                if content and not content.endswith("\n"):
                    f.write("\n")

                f.write("\n")
                f.write(instruction_content)

            print(f"✓ Added cicada-mcp usage instructions to {md_path.name}")
    except Exception:
        # Fail silently on any errors
        pass


def setup(
    editor: EditorType,
    repo_path: Path | None = None,
    indexing_mode: str | None = None,
    index_exists: bool = False,
    index_prs: bool = False,
    add_to_claude_md: bool = False,
    embeddings_config: dict[str, str] | None = None,
) -> None:
    """
    Run the complete setup for the specified editor.

    Args:
        editor: Editor type (claude, cursor, vs)
        repo_path: Path to the repository (defaults to current directory)
        indexing_mode: Indexing mode ("keywords" or "embeddings"), None for default
        index_exists: If True, skip banner and show condensed output (index already exists)
        index_prs: If True, index pull requests
        add_to_claude_md: If True, add Cicada guide to CLAUDE.md
        embeddings_config: Optional embeddings configuration with 'ollama_host' and 'model'
    """
    # Determine repository path
    if repo_path is None:
        repo_path = Path.cwd()
    repo_path = repo_path.resolve()

    # Detect project language
    language = detect_project_language(repo_path)

    # Create storage directory
    storage_dir = create_storage_dir(repo_path)
    if indexing_mode is None:
        from cicada.index_mode import read_indexing_mode_config

        indexing_mode = read_indexing_mode_config(repo_path)

    # Show condensed output if index already exists
    if index_exists:
        print(f"✓ Found existing index (mode: {indexing_mode.upper()})")
        # Skip indexing when index_exists is True - we're just reusing it
        should_index = False
        force_full = False
        # Ensure config.yaml is up to date with current settings
        create_config_yaml(
            repo_path,
            storage_dir,
            indexing_mode,
            verbose=False,
            embeddings_config=embeddings_config,
        )
    else:
        # Show full banner for new setup
        print("=" * 60)
        print(f"Cicada Setup for {editor.upper()}")
        print("=" * 60)
        print()
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
                    existing_mode = existing_config.get("indexing", {}).get("mode")
                    if existing_mode not in ("keywords", "embeddings"):
                        if existing_config.get("keyword_extraction") or existing_config.get(
                            "keyword_expansion"
                        ):
                            existing_mode = "keywords"
                        else:
                            existing_mode = "keywords"

                    new_mode = indexing_mode

                    # Check if settings changed
                    settings_changed = existing_mode != new_mode

                    if settings_changed:
                        print("=" * 60)
                        print("⚠️  WARNING: Index Already Exists")
                        print("=" * 60)
                        print()
                        print(
                            f"This repository already has an index with mode {existing_mode.upper()}."
                        )
                        print(f"You are now switching to {new_mode.upper()}.")
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
                        print(f"✓ Using existing index (mode: {existing_mode.upper()})")
                        print()
                        should_index = False
            except Exception:
                # If we can't read the config, just proceed with indexing
                pass

        # Create/update config.yaml BEFORE indexing (indexer reads this to determine keyword method)
        create_config_yaml(
            repo_path,
            storage_dir,
            indexing_mode,
            verbose=False,
            embeddings_config=embeddings_config,
        )

        # Index repository if needed
        if should_index:
            from cicada.index_mode import INDEX_MODE_EMBEDDINGS, ensure_supported_mode

            ensure_supported_mode(indexing_mode)
            index_repository(repo_path, language, force_full=force_full)

            # Run embeddings indexing if embeddings mode is selected
            if indexing_mode == INDEX_MODE_EMBEDDINGS:
                import json as json_module

                from cicada.embeddings.indexer import EmbeddingsIndexer

                print("Creating embeddings via Ollama...")
                embeddings_indexer = EmbeddingsIndexer(repo_path, verbose=True)

                # Load the index data for embeddings
                index_path = get_index_path(repo_path)
                with open(index_path) as f:
                    index_data = json_module.load(f)

                embeddings_indexer.index_from_parsed_data(index_data)
                print("✓ Embeddings created")

            print()

    # Update CLAUDE.md with cicada instructions (only for Claude Code editor)
    if editor == "claude" and not add_to_claude_md:
        update_claude_md(repo_path)

    # Create or update .gitattributes for git function tracking
    # This enables git log -L :funcname: syntax for Elixir files
    _setup_gitattributes(repo_path)

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

    # Run PR indexing if requested
    if index_prs:
        # Import locally to avoid circular dependencies
        try:
            from cicada.interactive_setup_helpers import run_pr_indexing

            run_pr_indexing(repo_path)
        except ImportError:
            # Fallback if module structure is different than expected
            print("Warning: Could not import run_pr_indexing")

    # Add guide to CLAUDE.md if requested
    if add_to_claude_md:
        # Import locally to avoid circular dependencies
        try:
            from cicada.interactive_setup_helpers import add_to_claude_md as doc_add_to_claude_md

            doc_add_to_claude_md(repo_path)
        except ImportError:
            print("Warning: Could not import add_to_claude_md")

    # Check if running via uvx and suggest permanent installation
    import shutil

    # Check for either cicada-mcp or cicada-server (backwards compat)
    if not (shutil.which("cicada-mcp") or shutil.which("cicada-server")):
        print("💡 Tip: For best experience, install Cicada permanently:")
        print("   uv tool install cicada-mcp")
        print()
        print("   Benefits:")
        print("   • Faster MCP server startup (no uvx overhead)")
        print("   • Access to cicada-index with keyword extraction")
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
        choices=["claude", "cursor", "vs", "opencode"],
        help="Editor to configure (claude=Claude Code, cursor=Cursor, vs=VS Code, opencode=OpenCode)",
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

    # Detect and validate project language
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
