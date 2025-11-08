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
    EDITOR_MAP,
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


def _text_based_setup() -> tuple[str, str, bool, bool]:
    """
    Fallback text-based setup for terminals that don't support simple-term-menu.

    Returns:
        tuple[str, str, bool, bool]: The selected extraction method, expansion method,
                                     whether to index PRs, and whether to add to CLAUDE.md
    """
    print(f"{PRIMARY}{'=' * 70}{RESET}")
    print(f"{SELECTED}🦗 Welcome to CICADA - Elixir Code Intelligence{RESET}")
    print(f"{PRIMARY}{'=' * 70}{RESET}")
    print()
    print(f"This is your first time running CICADA in this project.{RESET}")
    print(f"Let's configure keyword extraction for code intelligence.{RESET}")
    print()
    print(f"{BOLD}Step 1/2: Choose intelligence tier{RESET}")
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


def show_first_time_setup() -> tuple[str, str, bool, bool]:
    """
    Display an interactive first-time setup menu for cicada.

    Falls back to text-based input if the terminal doesn't support simple-term-menu.

    Returns:
        tuple[str, str, bool, bool]: The selected extraction method, expansion method,
                                     whether to index PRs, and whether to add to CLAUDE.md
                                     e.g., ('regular', 'lemmi', False, True) or ('bert', 'glove', True, True)
    """
    # Check if terminal menu is available and supported
    if not has_terminal_menu:
        return _text_based_setup()

    # Display ASCII art
    print(generate_gradient_ascii_art())

    # Step 1: Choose intelligence tier
    print(f"{PRIMARY}{'=' * 70}{RESET}")
    print(f"{SELECTED}🦗 Welcome to CICADA - Elixir Code Intelligence{RESET}")
    print(f"{PRIMARY}{'=' * 70}{RESET}")
    print()
    print(f"This is your first time running CICADA in this project.{RESET}")
    print(f"Let's configure keyword extraction for code intelligence.{RESET}")
    print()
    print(f"{BOLD}Step 1/3: Choose intelligence tier{RESET}")

    try:
        if TerminalMenu is None:
            return _text_based_setup()
        tier_menu = TerminalMenu(
            TIER_ITEMS,
            title="",
            menu_cursor="» ",
            menu_cursor_style=("fg_yellow", "bold"),
            menu_highlight_style=("fg_yellow", "bold"),
            cycle_cursor=True,
            clear_screen=False,
        )
        tier_index = tier_menu.show()
    except (KeyboardInterrupt, EOFError):
        print()
        print("Setup cancelled. Exiting...")
        sys.exit(1)
    except Exception:
        # Terminal doesn't support the menu - fall back to text-based
        print(
            f"\n{GREY}Note: Terminal menu not supported, using text-based input{RESET}\n",
            file=sys.stderr,
        )
        return _text_based_setup()

    if tier_index is None:
        print()
        print("Setup cancelled. Exiting...")
        sys.exit(1)

    idx = int(tier_index) if isinstance(tier_index, int) else tier_index[0]
    method, expansion_method = TIER_MAP[idx]
    display_tier_selection(idx)

    # Step 2: Ask about PR indexing
    print(f"{BOLD}Step 2/3: Index pull requests?{RESET}")
    print(f"{PRIMARY}   PR indexing enables fast offline lookup of GitHub PRs{RESET}")
    print(f"{PRIMARY}   Useful for: finding which PR introduced code, viewing PR context{RESET}")
    print()

    try:
        if TerminalMenu is None:
            return _text_based_setup()
        pr_menu = TerminalMenu(
            PR_ITEMS,
            title="",
            menu_cursor="» ",
            menu_cursor_style=("fg_yellow", "bold"),
            menu_highlight_style=("fg_yellow", "bold"),
            cycle_cursor=True,
            clear_screen=False,
        )
        pr_index = pr_menu.show()
    except (KeyboardInterrupt, EOFError):
        print()
        print(f"{SELECTED}Setup cancelled. Exiting...{RESET}")
        sys.exit(1)
    except Exception:
        print(
            f"\n{GREY}Note: Terminal menu not supported, using text-based input{RESET}\n",
            file=sys.stderr,
        )
        return _text_based_setup()

    if pr_index is None:
        print()
        print(f"{SELECTED}Setup cancelled. Exiting...{RESET}")
        sys.exit(1)

    idx = int(pr_index) if isinstance(pr_index, int) else pr_index[0]
    index_prs = idx == 1
    display_pr_indexing_selection(index_prs)

    # Step 3: Ask about adding to CLAUDE.md
    print(f"{BOLD}Step 3/3: Augment CLAUDE.md for AI assistants?{RESET}")
    print(f"{PRIMARY}   Add documentation to CLAUDE.md to help AI assistants{RESET}")
    print(f"{PRIMARY}   understand when and how to use Cicada tools effectively{RESET}")
    print()

    try:
        if TerminalMenu is None:
            return _text_based_setup()
        claude_md_menu = TerminalMenu(
            CLAUDE_MD_ITEMS,
            title="",
            menu_cursor="» ",
            menu_cursor_style=("fg_yellow", "bold"),
            menu_highlight_style=("fg_yellow", "bold"),
            cycle_cursor=True,
            clear_screen=False,
        )
        claude_md_index = claude_md_menu.show()
    except (KeyboardInterrupt, EOFError):
        print()
        print(f"{SELECTED}Setup cancelled. Exiting...{RESET}")
        sys.exit(1)
    except Exception:
        print(
            f"\n{GREY}Note: Terminal menu not supported, using text-based input{RESET}\n",
            file=sys.stderr,
        )
        return _text_based_setup()

    if claude_md_index is None:
        print()
        print(f"{SELECTED}Setup cancelled. Exiting...{RESET}")
        sys.exit(1)

    idx = int(claude_md_index) if isinstance(claude_md_index, int) else claude_md_index[0]
    add_to_claude_md_flag = idx == 0  # "Yes" is at index 0
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

                editor = EDITOR_MAP[
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

    # Step 2: Choose intelligence tier
    print(f"{BOLD}Step 2/4: Choose intelligence tier{RESET}")

    if has_terminal_menu:
        try:
            if TerminalMenu is None:
                extraction_method, expansion_method, index_prs, add_to_claude_md_flag = (
                    show_first_time_setup()
                )
                _run_setup_with_error_handling(
                    editor, repo_path, extraction_method, expansion_method
                )
                if index_prs:
                    run_pr_indexing(repo_path)
                if add_to_claude_md_flag:
                    add_to_claude_md(repo_path)
                return

            tier_menu = TerminalMenu(
                TIER_ITEMS,
                title="",
                menu_cursor="» ",
                menu_cursor_style=("fg_yellow", "bold"),
                menu_highlight_style=("fg_yellow", "bold"),
                cycle_cursor=True,
                clear_screen=False,
            )
            tier_index = tier_menu.show()

            if tier_index is None:
                print()
                print("Setup cancelled. Exiting...")
                sys.exit(1)

            idx = int(tier_index) if isinstance(tier_index, int) else tier_index[0]
            extraction_method, expansion_method = TIER_MAP[idx]
        except (KeyboardInterrupt, EOFError):
            print()
            print("Setup cancelled. Exiting...")
            sys.exit(1)
        except Exception:
            print(
                f"\n{GREY}Note: Terminal menu not supported, using text-based input{RESET}\n",
                file=sys.stderr,
            )
            extraction_method, expansion_method, index_prs, add_to_claude_md_flag = (
                show_first_time_setup()
            )
            _run_setup_with_error_handling(editor, repo_path, extraction_method, expansion_method)
            if index_prs:
                run_pr_indexing(repo_path)
            if add_to_claude_md_flag:
                add_to_claude_md(repo_path)
            return
    else:
        extraction_method, expansion_method, index_prs, add_to_claude_md_flag = (
            show_first_time_setup()
        )
        _run_setup_with_error_handling(editor, repo_path, extraction_method, expansion_method)
        if index_prs:
            run_pr_indexing(repo_path)
        if add_to_claude_md_flag:
            add_to_claude_md(repo_path)
        return

    display_tier_selection(idx)

    # Step 3: Ask about PR indexing
    print(f"{BOLD}Step 3/4: Index pull requests?{RESET}")
    print(f"{PRIMARY}   PR indexing enables fast offline lookup of GitHub PRs{RESET}")
    print(f"{PRIMARY}   Useful for: finding which PR introduced code, viewing PR context{RESET}")
    print()

    try:
        if TerminalMenu is None:
            extraction_method, expansion_method, index_prs, add_to_claude_md_flag = (
                show_first_time_setup()
            )
            _run_setup_with_error_handling(editor, repo_path, extraction_method, expansion_method)
            if index_prs:
                run_pr_indexing(repo_path)
            if add_to_claude_md_flag:
                add_to_claude_md(repo_path)
            return

        pr_menu = TerminalMenu(
            PR_ITEMS,
            title="",
            menu_cursor="» ",
            menu_cursor_style=("fg_yellow", "bold"),
            menu_highlight_style=("fg_yellow", "bold"),
            cycle_cursor=True,
            clear_screen=False,
        )
        pr_index = pr_menu.show()
    except (KeyboardInterrupt, EOFError):
        print()
        print(f"{SELECTED}Setup cancelled. Exiting...{RESET}")
        sys.exit(1)
    except Exception:
        print(
            f"\n{GREY}Note: Terminal menu not supported, using text-based input{RESET}\n",
            file=sys.stderr,
        )
        extraction_method, expansion_method, index_prs, add_to_claude_md_flag = (
            show_first_time_setup()
        )
        _run_setup_with_error_handling(editor, repo_path, extraction_method, expansion_method)
        if index_prs:
            run_pr_indexing(repo_path)
        if add_to_claude_md_flag:
            add_to_claude_md(repo_path)
        return

    if pr_index is None:
        print()
        print(f"{SELECTED}Setup cancelled. Exiting...{RESET}")
        sys.exit(1)

    idx = int(pr_index) if isinstance(pr_index, int) else pr_index[0]
    index_prs = idx == 1
    display_pr_indexing_selection(index_prs)

    # Step 4: Ask about adding to CLAUDE.md
    print(f"{BOLD}Step 4/4: Augment CLAUDE.md for AI assistants?{RESET}")
    print(f"{PRIMARY}   Add documentation to CLAUDE.md to help AI assistants{RESET}")
    print(f"{PRIMARY}   understand when and how to use Cicada tools effectively{RESET}")
    print()

    try:
        if TerminalMenu is None:
            extraction_method, expansion_method, index_prs, add_to_claude_md_flag = (
                show_first_time_setup()
            )
            _run_setup_with_error_handling(editor, repo_path, extraction_method, expansion_method)
            if index_prs:
                run_pr_indexing(repo_path)
            if add_to_claude_md_flag:
                add_to_claude_md(repo_path)
            return

        claude_md_menu = TerminalMenu(
            CLAUDE_MD_ITEMS,
            title="",
            menu_cursor="» ",
            menu_cursor_style=("fg_yellow", "bold"),
            menu_highlight_style=("fg_yellow", "bold"),
            cycle_cursor=True,
            clear_screen=False,
        )
        claude_md_index = claude_md_menu.show()
    except (KeyboardInterrupt, EOFError):
        print()
        print(f"{SELECTED}Setup cancelled. Exiting...{RESET}")
        sys.exit(1)
    except Exception:
        print(
            f"\n{GREY}Note: Terminal menu not supported, using text-based input{RESET}\n",
            file=sys.stderr,
        )
        extraction_method, expansion_method, index_prs, add_to_claude_md_flag = (
            show_first_time_setup()
        )
        _run_setup_with_error_handling(editor, repo_path, extraction_method, expansion_method)
        if index_prs:
            run_pr_indexing(repo_path)
        if add_to_claude_md_flag:
            add_to_claude_md(repo_path)
        return

    if claude_md_index is None:
        print()
        print(f"{SELECTED}Setup cancelled. Exiting...{RESET}")
        sys.exit(1)

    idx = int(claude_md_index) if isinstance(claude_md_index, int) else claude_md_index[0]
    add_to_claude_md_flag = idx == 0  # "Yes" is at index 0
    display_claude_md_selection(add_to_claude_md_flag)

    # Run setup
    print(f"{BOLD}Running setup...{RESET}")
    print()

    _run_setup_with_error_handling(editor, repo_path, extraction_method, expansion_method)

    # Run PR indexing if requested
    if index_prs:
        run_pr_indexing(repo_path)

    # Add to CLAUDE.md if requested
    if add_to_claude_md_flag:
        add_to_claude_md(repo_path)
