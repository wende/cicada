"""Interactive first-time setup menu for cicada."""

import sys
from pathlib import Path

try:
    from simple_term_menu import TerminalMenu

    has_terminal_menu = True
except ImportError:
    TerminalMenu = None  # type: ignore
    has_terminal_menu = False

from cicada.format import BOLD, GREY, PRIMARY, RESET, SELECTED, generate_gradient_ascii_art
from cicada.interactive_setup_helpers import (
    CLAUDE_MD_ITEMS,
    EDITOR_ITEMS,
    EDITOR_MAP_TEXT,
    PR_ITEMS,
    TIER_ITEMS,
    TIER_MAP,
    TIER_MAP_TEXT,
    NotElixirProjectError,
    add_to_claude_md,
    check_elixir_project,
    display_claude_md_selection,
    display_editor_selection,
    display_pr_indexing_selection,
    display_tier_selection,
    get_existing_config,
    run_pr_indexing,
    run_setup,
)

MENU_STYLE = {
    "title": "",
    "menu_cursor": "» ",
    "menu_cursor_style": ("fg_yellow", "bold"),
    "menu_highlight_style": ("fg_yellow", "bold"),
    "cycle_cursor": True,
    "clear_screen": False,
}


class MenuUnavailableError(Exception):
    """Raised when TerminalMenu cannot be used for interactive prompts."""


def _print_first_time_intro(show_header: bool) -> None:
    """Render the ASCII art banner and intro text."""
    if show_header:
        print(generate_gradient_ascii_art())
        print(f"{PRIMARY}{'=' * 70}{RESET}")
        print(f"{SELECTED}🦗 Welcome to CICADA - Elixir Code Intelligence{RESET}")
        print(f"{PRIMARY}{'=' * 70}{RESET}")
    print()
    print(f"This is your first time running CICADA in this project.{RESET}")
    print(f"Let's configure keyword extraction for code intelligence.{RESET}")
    print()


def _prompt_menu_selection(items: list[str], cancel_message: str) -> int:
    """Display a menu and return the selected index."""
    if TerminalMenu is None:
        raise MenuUnavailableError

    try:
        menu = TerminalMenu(items, **MENU_STYLE)  # type: ignore[arg-type]
    except Exception:
        raise MenuUnavailableError from None

    try:
        selection = menu.show()
    except (KeyboardInterrupt, EOFError):
        print()
        print(cancel_message)
        sys.exit(1)
    except Exception:
        raise MenuUnavailableError from None

    if selection is None:
        print()
        print(cancel_message)
        sys.exit(1)

    if isinstance(selection, tuple):
        selection = selection[0]

    return int(selection)


def _handle_menu_unavailable() -> tuple[str, str, bool, bool]:
    """Fallback to text-based setup when TerminalMenu cannot be used."""
    print(
        f"\n{GREY}Note: Terminal menu not supported, using text-based input{RESET}\n",
        file=sys.stderr,
    )
    return _text_based_setup()


def _text_based_setup() -> tuple[str, str, bool, bool]:
    """
    Fallback text-based setup for terminals that don't support simple-term-menu.

    Returns:
        tuple[str, str, bool, bool]: The selected extraction method, expansion method,
                                     whether to index PRs, and whether to add to CLAUDE.md
    """
    _print_first_time_intro(show_header=True)
    print(f"{BOLD}Step 1/3: Choose intelligence tier{RESET}")
    print()
    print("1. Fast - Term frequency + inflections (no downloads)")
    print("2. Balanced - KeyBERT + GloVe semantic expansion (261MB)")
    print("3. Maximum - KeyBERT + FastText expansion (1091MB)")
    print()

    while True:
        try:
            tier_choice = input("Enter your choice (1, 2, or 3) [default: 1]: ").strip()
            if not tier_choice:
                tier_choice = "1"
            if tier_choice in TIER_MAP_TEXT:
                method, expansion_method = TIER_MAP_TEXT[tier_choice]
                break
            print("Invalid choice. Please enter 1, 2, or 3.")
        except (KeyboardInterrupt, EOFError):
            print()
            print("Setup cancelled. Exiting...")
            sys.exit(1)

    display_tier_selection(int(tier_choice) - 1)

    # Step 2: Ask about PR indexing
    print(f"{BOLD}Step 2/3: Index pull requests?{RESET}")
    print(f"{PRIMARY}   PR indexing enables fast offline lookup of GitHub PRs{RESET}")
    print(f"{PRIMARY}   Useful for: finding which PR introduced code, viewing PR context{RESET}")
    print()
    print("1. Yes - Index PRs now (requires GitHub access)")
    print("2. No - Skip PR indexing (can run later with 'cicada-pr-indexer')")
    print()

    while True:
        try:
            pr_choice = input("Enter your choice (1 or 2) [default: 2]: ").strip()
            if not pr_choice:
                pr_choice = "2"
            if pr_choice in ("1", "2"):
                index_prs = pr_choice == "1"
                break
            print("Invalid choice. Please enter 1 or 2.")
        except (KeyboardInterrupt, EOFError):
            print()
            print(f"{SELECTED}Setup cancelled. Exiting...{RESET}")
            sys.exit(1)

    display_pr_indexing_selection(index_prs)

    # Step 3: Ask about adding to CLAUDE.md
    print(f"{BOLD}Step 3/3: Augment CLAUDE.md for AI assistants?{RESET}")
    print(f"{PRIMARY}   Add documentation to CLAUDE.md to help AI assistants{RESET}")
    print(f"{PRIMARY}   understand when and how to use Cicada tools effectively{RESET}")
    print()
    print("1. Yes - Add Cicada usage guide to CLAUDE.md (recommended)")
    print("2. No - Skip CLAUDE.md setup")
    print()

    while True:
        try:
            claude_md_choice = input("Enter your choice (1 or 2) [default: 1]: ").strip()
            if not claude_md_choice:
                claude_md_choice = "1"
            if claude_md_choice in ("1", "2"):
                add_to_claude_md_flag = claude_md_choice == "1"
                break
            print("Invalid choice. Please enter 1 or 2.")
        except (KeyboardInterrupt, EOFError):
            print()
            print(f"{SELECTED}Setup cancelled. Exiting...{RESET}")
            sys.exit(1)

    display_claude_md_selection(add_to_claude_md_flag)

    return (method, expansion_method, index_prs, add_to_claude_md_flag)


def show_first_time_setup(show_welcome: bool = True) -> tuple[str, str, bool, bool]:
    """
    Display an interactive first-time setup menu for cicada.

    Falls back to text-based input if the terminal doesn't support simple-term-menu.

    Args:
        show_welcome: Whether to display the ASCII art banner and intro text.

    Returns:
        tuple[str, str, bool, bool]: The selected extraction method, expansion method,
                                     whether to index PRs, and whether to add to CLAUDE.md
                                     e.g., ('regular', 'lemmi', False, True) or ('bert', 'glove', True, True)
    """
    # Check if terminal menu is available and supported
    if not has_terminal_menu:
        return _text_based_setup()

    _print_first_time_intro(show_header=show_welcome)
    print(f"{BOLD}Step 1/3: Choose intelligence tier{RESET}")

    def _select_with_menu(items: list[str], cancel_message: str) -> int | None:
        try:
            return _prompt_menu_selection(items, cancel_message)
        except MenuUnavailableError:
            return None

    tier_index = _select_with_menu(TIER_ITEMS, "Setup cancelled. Exiting...")
    if tier_index is None:
        return _handle_menu_unavailable()

    method, expansion_method = TIER_MAP[tier_index]
    display_tier_selection(tier_index)

    # Step 2: Ask about PR indexing
    print(f"{BOLD}Step 2/3: Index pull requests?{RESET}")
    print(f"{PRIMARY}   PR indexing enables fast offline lookup of GitHub PRs{RESET}")
    print(f"{PRIMARY}   Useful for: finding which PR introduced code, viewing PR context{RESET}")
    print()

    pr_index = _select_with_menu(
        PR_ITEMS,
        f"{SELECTED}Setup cancelled. Exiting...{RESET}",
    )
    if pr_index is None:
        return _handle_menu_unavailable()

    index_prs = pr_index == 1
    display_pr_indexing_selection(index_prs)

    # Step 3: Ask about adding to CLAUDE.md
    print(f"{BOLD}Step 3/3: Augment CLAUDE.md for AI assistants?{RESET}")
    print(f"{PRIMARY}   Add documentation to CLAUDE.md to help AI assistants{RESET}")
    print(f"{PRIMARY}   understand when and how to use Cicada tools effectively{RESET}")
    print()

    claude_md_index = _select_with_menu(
        CLAUDE_MD_ITEMS,
        f"{SELECTED}Setup cancelled. Exiting...{RESET}",
    )
    if claude_md_index is None:
        return _handle_menu_unavailable()

    add_to_claude_md_flag = claude_md_index == 0  # "Yes" is at index 0
    display_claude_md_selection(add_to_claude_md_flag)

    return (method, expansion_method, index_prs, add_to_claude_md_flag)


def _text_based_editor_selection() -> str:
    """
    Fallback text-based editor selection for terminals that don't support simple-term-menu.

    Returns:
        str: The selected editor ('claude', 'cursor', or 'vs')
    """
    print("1. Claude Code - AI-powered code editor")
    print("2. Cursor - AI-first code editor")
    print("3. VS Code - Visual Studio Code")
    print()

    while True:
        try:
            choice = input("Enter your choice (1, 2, or 3) [default: 1]: ").strip()
            if not choice:
                choice = "1"
            if choice in EDITOR_MAP_TEXT:
                return EDITOR_MAP_TEXT[choice]
            print("Invalid choice. Please enter 1, 2, or 3.")
        except (KeyboardInterrupt, EOFError):
            print()
            print("Setup cancelled. Exiting...")
            sys.exit(1)


def show_full_interactive_setup(repo_path: str | Path | None = None) -> None:
    """
    Display full interactive setup including editor selection and keyword extraction.

    This is the main entry point when running `cicada` with no arguments or a path.

    Args:
        repo_path: Path to the Elixir repository. Defaults to current directory.
    """

    # Helper to run setup with error handling
    def _run_setup_with_error_handling(
        editor: str,
        repo_path: Path,
        extraction_method: str,
        expansion_method: str,
        index_exists: bool = False,
    ) -> None:
        try:
            run_setup(editor, repo_path, extraction_method, expansion_method, index_exists)
        except Exception as e:
            print(f"\n{PRIMARY}Error: Setup failed: {e}{RESET}")
            sys.exit(1)

    # Check if we're in an Elixir project
    repo_path = Path.cwd() if repo_path is None else Path(repo_path).resolve()
    try:
        check_elixir_project(repo_path)
    except NotElixirProjectError as e:
        print(f"{PRIMARY}Error: {e}{RESET}")
        print()
        print("Please run cicada from the root of an Elixir project.")
        sys.exit(1)

    # Display ASCII art
    print(generate_gradient_ascii_art())

    # Step 1: Choose editor
    print(f"{PRIMARY}{'=' * 70}{RESET}")
    print(f"{SELECTED}🦗 Welcome to CICADA - Elixir Code Intelligence{RESET}")
    print(f"{PRIMARY}{'=' * 70}{RESET}")
    print()
    print(f"Let's set up Cicada for your editor and project.{RESET}")
    print()
    print(f"{BOLD}Step 1/4: Choose your editor{RESET}")

    if has_terminal_menu:
        try:
            if TerminalMenu is None:
                editor = _text_based_editor_selection()
            else:
                editor_menu = TerminalMenu(
                    EDITOR_ITEMS,
                    title="",
                    menu_cursor="» ",
                    menu_cursor_style=("fg_yellow", "bold"),
                    menu_highlight_style=("fg_yellow", "bold"),
                    cycle_cursor=True,
                    clear_screen=False,
                )
                editor_index = editor_menu.show()

                if editor_index is None:
                    print()
                    print("Setup cancelled. Exiting...")
                    sys.exit(1)

                editor_map = {
                    0: "claude",
                    1: "cursor",
                    2: "vs",
                    3: "gemini",
                    4: "codex",
                    5: "opencode",
                }
                editor = editor_map[
                    int(editor_index) if isinstance(editor_index, int) else editor_index[0]
                ]
        except (KeyboardInterrupt, EOFError):
            print()
            print("Setup cancelled. Exiting...")
            sys.exit(1)
        except Exception:
            print(
                f"\n{GREY}Note: Terminal menu not supported, using text-based input{RESET}\n",
                file=sys.stderr,
            )
            editor = _text_based_editor_selection()
    else:
        editor = _text_based_editor_selection()

    display_editor_selection(editor)

    # Check if index already exists
    existing_config = get_existing_config(repo_path)
    if existing_config is not None:
        extraction_method, expansion_method = existing_config
        _run_setup_with_error_handling(
            editor, repo_path, extraction_method, expansion_method, index_exists=True
        )
        return

    extraction_method, expansion_method, index_prs, add_to_claude_md_flag = show_first_time_setup(
        show_welcome=False
    )

    print(f"{BOLD}Running setup...{RESET}")
    print()

    _run_setup_with_error_handling(editor, repo_path, extraction_method, expansion_method)

    if index_prs:
        run_pr_indexing(repo_path)

    if add_to_claude_md_flag:
        add_to_claude_md(repo_path)


def _text_based_editor_selection() -> str:
    """
    Fallback text-based editor selection for terminals that don't support simple-term-menu.

    Returns:
        str: The selected editor ('claude', 'cursor', 'vs', 'gemini', 'codex', or 'opencode')
    """
    print("1. Claude Code - AI-powered code editor")
    print("2. Cursor - AI-first code editor")
    print("3. VS Code - Visual Studio Code")
    print("4. Gemini CLI - Google Gemini command line interface")
    print("5. Codex - AI code editor")
    print("6. OpenCode - Terminal-based AI coding agent")
    print()

    while True:
        try:
            choice = input("Enter your choice (1-6) [default: 1]: ").strip()
            if not choice:
                choice = "1"
            if choice in ("1", "2", "3", "4", "5", "6"):
                editor_map = {
                    "1": "claude",
                    "2": "cursor",
                    "3": "vs",
                    "4": "gemini",
                    "5": "codex",
                    "6": "opencode",
                }
                return editor_map[choice]
            print("Invalid choice. Please enter 1-6.")
        except (KeyboardInterrupt, EOFError):
            print()
            print("Setup cancelled. Exiting...")
            sys.exit(1)
