"""Helper functions for interactive setup - non-user interactive code."""

from pathlib import Path
from typing import cast

import yaml

from cicada.format import BOLD, GREEN, GREY, PRIMARY, RESET
from cicada.setup import EditorType


class NotElixirProjectError(Exception):
    """Raised when the given path is not an Elixir project."""


# Tier configuration data
_TIER_OPTIONS = (
    ("Fast - Term frequency + inflections (no downloads)", ("regular", "lemmi")),
    ("Balanced - KeyBERT + GloVe semantic expansion (261MB)", ("bert", "glove")),
    ("Maximum - KeyBERT + FastText expansion (1091MB)", ("bert", "fasttext")),
)

TIER_ITEMS = [label for label, _ in _TIER_OPTIONS]
TIER_MAP = {idx: methods for idx, (_, methods) in enumerate(_TIER_OPTIONS)}
TIER_MAP_TEXT = {str(idx + 1): methods for idx, methods in TIER_MAP.items()}

# Editor configuration data
_EDITOR_OPTIONS = (
    ("Claude Code - AI-powered code editor", "claude"),
    ("Cursor - AI-first code editor", "cursor"),
    ("VS Code - Visual Studio Code", "vs"),
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

# CLAUDE.md documentation content
CICADA_DOCS = """
<cicada>
  **ALWAYS use cicada-mcp tools for Elixir code searches. NEVER use Grep/Find for these tasks.**

  ### Use cicada tools for:
  - PREFERRED for Elixir: View a module's complete API - functions with arity, signatures, docs, typespecs, and line numbers. `mcp__cicada__search_module`
  - PREFERRED for Elixir: Find function definitions and call sites across the codebase. `mcp__cicada__search_function`
  - PREFERRED for Elixir: Find all module usage and dependencies for impact analysis. `mcp__cicada__search_module_usage`
  - PREFERRED for git history: Discover why code exists and who wrote it. `mcp__cicada__find_pr_for_line`
  - PREFERRED for git history: Get commit log for files or functions. `mcp__cicada__get_commit_history`
  - PREFERRED for authorship: Git blame showing who wrote each line. `mcp__cicada__get_blame`
  - Get all PRs that modified a file with descriptions and review comments. `mcp__cicada__get_file_pr_history`
  - Semantic search for code by concept/topic when exact names are unknown. `mcp__cicada__search_by_keywords`
  - Find potentially unused public functions with confidence levels. `mcp__cicada__find_dead_code`

  ### DO NOT use Grep for:
  - ❌ Searching for module structure
  - ❌ Searching for function definitions
  - ❌ Searching for module imports/usage

  ### You can still use Grep for:
  - ✓ Non-code files (markdown, JSON, config)
  - ✓ String literal searches
  - ✓ Pattern matching in single line comments
</cicada>
"""


def display_tier_selection(tier_index: int) -> None:
    """
    Display confirmation message for tier selection.

    Args:
        tier_index: The selected tier index (0, 1, or 2)
    """
    print()
    if tier_index == 0:
        print(f"{GREEN}✓{RESET} Selected: FAST tier")
        print("   Term frequency extraction + inflections")
        print("   Fast, lightweight, no model downloads")
    elif tier_index == 1:
        print(f"{GREEN}✓{RESET} Selected: BALANCED tier")
        print("   KeyBERT semantic extraction (133MB)")
        print("   GloVe semantic expansion (128MB)")
        print("   Total: 261MB download")
    else:  # tier_index == 2
        print(f"{GREEN}✓{RESET} Selected: MAXIMUM tier")
        print("   KeyBERT semantic extraction (133MB)")
        print("   FastText semantic expansion (958MB)")
        print("   Total: 1091MB download")
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
        editor: The selected editor ('claude', 'cursor', or 'vs')
    """
    print()
    print(f"{GREEN}✓{RESET} Selected: {editor.upper()}")
    print()


def get_existing_config(repo_path: Path) -> tuple[str, str] | None:
    """
    Read existing configuration from the repository if it exists.

    Args:
        repo_path: Path to the repository

    Returns:
        Tuple of (extraction_method, expansion_method) if config exists, None otherwise
    """
    from cicada.utils.storage import get_config_path, get_index_path

    config_path = get_config_path(repo_path)
    index_path = get_index_path(repo_path)

    if not (config_path.exists() and index_path.exists()):
        return None

    try:
        with open(config_path) as f:
            existing_config = yaml.safe_load(f)
            extraction_method = existing_config.get("keyword_extraction", {}).get(
                "method", "regular"
            )
            expansion_method = existing_config.get("keyword_expansion", {}).get("method", "lemmi")
        return (extraction_method, expansion_method)
    except Exception:
        return None


def run_setup(
    editor: str,
    repo_path: Path,
    extraction_method: str,
    expansion_method: str,
    index_exists: bool = False,
) -> None:
    """
    Run the setup.

    Args:
        editor: The selected editor
        repo_path: Path to the repository
        extraction_method: Keyword extraction method
        expansion_method: Keyword expansion method
        index_exists: Whether the index already exists

    Raises:
        Exception: If setup fails
    """
    from cicada.setup import setup

    setup(
        cast(EditorType, editor),
        repo_path,
        extraction_method=extraction_method,
        expansion_method=expansion_method,
        index_exists=index_exists,
    )


def run_pr_indexing(repo_path: Path) -> None:
    """
    Run the PR indexer for the given repository.

    Args:
        repo_path: Path to the repository to index
    """
    from cicada.pr_indexer.indexer import PRIndexer
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
    Check if the given path is an Elixir project.

    Args:
        repo_path: Path to check

    Raises:
        NotElixirProjectError: If the path is not an Elixir project
    """
    if not (repo_path / "mix.exs").exists():
        raise NotElixirProjectError(
            f"{repo_path} does not appear to be an Elixir project (mix.exs not found)"
        )
