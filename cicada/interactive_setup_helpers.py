"""Helper functions for interactive setup - non-user interactive code."""

from pathlib import Path
from typing import cast

import yaml

from cicada.format import BOLD, GREEN, GREY, PRIMARY, RESET
from cicada.setup import EditorType


class UnsupportedProjectError(Exception):
    """Raised when the given path is not a supported project type."""


# Backward compatibility alias
NotElixirProjectError = UnsupportedProjectError


# Indexing mode configuration data
_MODE_OPTIONS = (
    ("Keywords - Token-based extraction (default)", "keywords"),
    ("Embeddings - Semantic search via Ollama", "embeddings"),
)

MODE_ITEMS = [label for label, _ in _MODE_OPTIONS]
MODE_MAP = {idx: mode for idx, (_, mode) in enumerate(_MODE_OPTIONS)}
MODE_MAP_TEXT = {str(idx + 1): mode for idx, mode in MODE_MAP.items()}

# Editor configuration data
_EDITOR_OPTIONS = (
    ("Claude Code", "claude"),
    ("Cursor", "cursor"),
    ("VS Code", "vs"),
    ("Gemini CLI", "gemini"),
    ("Codex", "codex"),
    ("OpenCode", "opencode"),
)

EDITOR_ITEMS = [label for label, _ in _EDITOR_OPTIONS]
EDITOR_MAP = {idx: value for idx, (_, value) in enumerate(_EDITOR_OPTIONS)}
EDITOR_MAP_TEXT = {str(idx + 1): value for idx, value in EDITOR_MAP.items()}

# PR indexing options
PR_ITEMS = [
    "No - Skip PR indexing (can run later with 'cicada-pr-indexer')",
    "Yes - Index PRs now (requires GitHub access)",
]

# CLAUDE.md options
CLAUDE_MD_ITEMS = [
    "Yes - Add Cicada usage guide to CLAUDE.md (recommended)",
    "No - Skip CLAUDE.md setup",
]


def _generate_claude_docs() -> str:
    """
    Generate CLAUDE.md documentation content focusing on the query tool.

    The query tool is the primary entry point that automatically suggests
    which specialized tools to use next, so users don't need to know about
    all available tools upfront.

    Returns:
        Formatted CLAUDE.md content with query tool documentation
    """
    return """
<cicada>
  **PRIMARY: Always use `mcp__cicada__query` for understanding Elixir code.**

  Cicada beats builtin tools for code exploration:
  - **vs Grep**: Semantic search by purpose, not literal text. Finds "authentication logic" without knowing exact function names. Understands code relationships and string literals semantically.
  - **vs Glob**: Discovers modules by functionality, not file names. Finds "rate limiting" without knowing it's in `lib/my_app/plugs/rate_limiter.ex`.
  - **vs Read**: Tells you WHICH files to read and WHY they're relevant. Shows connections between modules so you read the right files in the right order.

  ## Usage
  Query by keywords `['authentication', 'login']` or patterns `'MyApp.User.*'` or both.
  Follow returned suggestions - they tell you which specialized tool to use next.

  ## Parameters
  - `scope`: 'all' | 'public' | 'private'
  - `filter_type`: 'all' | 'modules' | 'functions'
  - `match_source`: 'all' | 'docs' | 'strings' (semantic search in code strings)
  - `recent`: true (14 days) | false (all time, default)
  - `path_pattern`: 'lib/auth/**' or '!**/test/**' (! negates)
  - `show_snippets`: true | false (default)

  ## Workflow
  1. `query(['jwt'])` → semantic matches + relationships + suggestions
  2. Follow suggestion → explore connections/usage
  3. Repeat → understand functionality

  Use Grep/Glob/Read only for non-Elixir files or when you already have exact paths/strings.
</cicada>
"""


# CLAUDE.md documentation content (generated from registered tools)
CICADA_DOCS = _generate_claude_docs()


def display_mode_selection(mode_index: int) -> None:
    """
    Display confirmation message for mode selection.

    Args:
        mode_index: The selected mode index (0 or 1)
    """
    print()
    if mode_index == 0:
        print(f"{GREEN}✓{RESET} Selected: KEYWORDS mode")
        print("   Token-based keyword extraction")
        print("   Fast, lightweight, no model downloads")
    else:
        print(f"{GREEN}✓{RESET} Selected: EMBEDDINGS mode")
        print("   Semantic search via Ollama embeddings")
        print("   Requires Ollama running locally or remotely")
    print()


def display_embeddings_config_selection(ollama_host: str, model: str) -> None:
    """
    Display confirmation message for embeddings configuration.

    Args:
        ollama_host: The Ollama host URL
        model: The selected embedding model
    """
    print()
    print(f"{GREEN}✓{RESET} Embeddings configuration:")
    print(f"   Ollama host: {ollama_host}")
    print(f"   Model: {model}")
    print()


def display_pr_indexing_selection(index_prs: bool) -> None:
    """
    Display confirmation message for PR indexing selection.

    Args:
        index_prs: Whether to index PRs
    """
    print()
    if index_prs:
        print(f"{GREEN}✓{RESET} Will index pull requests")
    else:
        print(f"{GREEN}✓{RESET} Skipping PR indexing")
    print()


def display_claude_md_selection(add_to_claude_md: bool) -> None:
    """
    Display confirmation message for CLAUDE.md selection.

    Args:
        add_to_claude_md: Whether to add to CLAUDE.md
    """
    print()
    if add_to_claude_md:
        print(f"{GREEN}✓{RESET} Will add Cicada guide to CLAUDE.md")
    else:
        print(f"{GREEN}✓{RESET} Skipping CLAUDE.md setup")
    print()


def display_editor_selection(editor: str) -> None:
    """
    Display confirmation message for editor selection.

    Args:
        editor: The selected editor ('claude', 'cursor', 'vs', 'gemini', or 'codex')
    """
    print()
    print(f"{GREEN}✓{RESET} Selected: {editor.upper()}")
    print()


def get_existing_config(repo_path: Path) -> str | None:
    """
    Read existing configuration from the repository if it exists.

    Args:
        repo_path: Path to the repository

    Returns:
        Indexing mode if config exists, None otherwise
    """
    from cicada.utils.storage import get_config_path, get_index_path

    config_path = get_config_path(repo_path)
    index_path = get_index_path(repo_path)

    if not (config_path.exists() and index_path.exists()):
        return None

    try:
        with open(config_path) as f:
            existing_config = yaml.safe_load(f) or {}
            mode = existing_config.get("indexing", {}).get("mode")
            if mode in ("keywords", "embeddings"):
                return mode
            if existing_config.get("keyword_extraction") or existing_config.get(
                "keyword_expansion"
            ):
                return "keywords"
        return "keywords"
    except Exception:
        return None


def run_setup(
    editor: str,
    repo_path: Path,
    indexing_mode: str,
    index_exists: bool = False,
    index_prs: bool = False,
    add_to_claude_md: bool = False,
    embeddings_config: dict[str, str] | None = None,
) -> None:
    """
    Run the setup.

    Args:
        editor: The selected editor
        repo_path: Path to the repository
        indexing_mode: Indexing mode
        index_exists: Whether the index already exists
        index_prs: Whether to index PRs
        add_to_claude_md: Whether to add to CLAUDE.md
        embeddings_config: Optional embeddings configuration with 'ollama_host' and 'model'

    Raises:
        Exception: If setup fails
    """
    from cicada.setup import setup

    setup(
        cast(EditorType, editor),
        repo_path,
        indexing_mode=indexing_mode,
        index_exists=index_exists,
        index_prs=index_prs,
        add_to_claude_md=add_to_claude_md,
        embeddings_config=embeddings_config,
    )


def run_pr_indexing(repo_path: Path) -> None:
    """
    Run the PR indexer for the given repository.

    Args:
        repo_path: Path to the repository to index
    """
    from cicada.github.pr_indexer.indexer import PRIndexer
    from cicada.utils.storage import get_pr_index_path

    print()
    print(f"{BOLD}Indexing pull requests...{RESET}")
    print()

    try:
        indexer = PRIndexer(repo_path=str(repo_path))
        output_path = get_pr_index_path(repo_path)
        indexer.index_repository(output_path=str(output_path), incremental=True)
        print()
        print(f"{GREEN}✓{RESET} PR indexing complete!")
        print()
    except KeyboardInterrupt:
        print()
        print(f"{PRIMARY}⚠️  PR indexing interrupted by user.{RESET}")
        print(
            f"{GREY}Partial index may have been saved. Run 'cicada-pr-indexer' to continue.{RESET}"
        )
        print()
    except Exception as e:
        print()
        print(f"{PRIMARY}⚠️  PR indexing failed: {e}{RESET}")
        print(f"{GREY}You can run 'cicada-pr-indexer' later to index PRs.{RESET}")
        print()


def add_to_claude_md(repo_path: Path) -> None:
    """
    Add Cicada usage documentation to CLAUDE.md file.

    Args:
        repo_path: Path to the repository
    """
    print()
    print(f"{BOLD}Adding Cicada guide to CLAUDE.md...{RESET}")
    print()

    claude_md_path = repo_path / "CLAUDE.md"

    try:
        # Check if CLAUDE.md exists
        if claude_md_path.exists():
            # Read existing content
            with open(claude_md_path) as f:
                content = f.read()

            # Check if cicada docs already exist
            if "<cicada>" in content:
                print(f"{GREY}Cicada documentation already exists in CLAUDE.md{RESET}")
                print()
                return

            # Append to existing file
            with open(claude_md_path, "a") as f:
                f.write("\n" + CICADA_DOCS)

            print(f"{GREEN}✓{RESET} Added Cicada guide to existing CLAUDE.md")
        else:
            # Create new CLAUDE.md file
            with open(claude_md_path, "w") as f:
                f.write("# Project Instructions for AI Assistants\n")
                f.write(CICADA_DOCS)

            print(f"{GREEN}✓{RESET} Created CLAUDE.md with Cicada guide")

        print()
    except Exception as e:
        print()
        print(f"{PRIMARY}⚠️  Failed to add Cicada guide to CLAUDE.md: {e}{RESET}")
        print(f"{GREY}You can manually add the Cicada documentation later.{RESET}")
        print()


def check_elixir_project(repo_path: Path) -> None:
    """
    Check if the given path is a supported project type.

    Args:
        repo_path: Path to check

    Raises:
        UnsupportedProjectError: If the path is not a supported project type
    """
    from cicada.setup import detect_project_language

    try:
        detect_project_language(repo_path)
    except ValueError as e:
        raise UnsupportedProjectError(str(e)) from e
