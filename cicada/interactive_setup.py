"""Interactive first-time setup menu for cicada."""

import sys
from pathlib import Path
from typing import cast

try:
    from simple_term_menu import TerminalMenu

    has_terminal_menu = True
except ImportError:
    TerminalMenu = None  # type: ignore
    has_terminal_menu = False

from cicada.format import BOLD, GREEN, GREY, PRIMARY, RESET, SELECTED, generate_gradient_ascii_art
from cicada.setup import EditorType


def _text_based_setup() -> tuple[str, str, bool]:
    """
    Fallback text-based setup for terminals that don't support simple-term-menu.

    Returns:
        tuple[str, str, bool]: The selected extraction method, expansion method, and whether to index PRs
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
            if tier_choice in ("1", "2", "3"):
                tier_map = {
                    "1": ("regular", "lemmi"),
                    "2": ("bert", "glove"),
                    "3": ("bert", "fasttext"),
                }
                method, expansion_method = tier_map[tier_choice]
                break
            print("Invalid choice. Please enter 1, 2, or 3.")
        except (KeyboardInterrupt, EOFError):
            print()
            print("Setup cancelled. Exiting...")
            sys.exit(1)

    # Display info based on selection
    print()
    if tier_choice == "1":
        print(f"{GREEN}✓{RESET} Selected: FAST tier")
        print(f"   Term frequency extraction + inflections")
        print(f"   Fast, lightweight, no model downloads")
    elif tier_choice == "2":
        print(f"{GREEN}✓{RESET} Selected: BALANCED tier")
        print(f"   KeyBERT semantic extraction (133MB)")
        print(f"   GloVe semantic expansion (128MB)")
        print(f"   Total: 261MB download")
    else:  # tier 3
        print(f"{GREEN}✓{RESET} Selected: MAXIMUM tier")
        print(f"   KeyBERT semantic extraction (133MB)")
        print(f"   FastText semantic expansion (958MB)")
        print(f"   Total: 1091MB download")
    print()

    # Step 2: Ask about PR indexing
    print(f"{BOLD}Step 2/2: Index pull requests?{RESET}")
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

    print()
    if index_prs:
        print(f"{GREEN}✓{RESET} Will index pull requests")
    else:
        print(f"{GREEN}✓{RESET} Skipping PR indexing")
    print()

    return (method, expansion_method, index_prs)


def show_first_time_setup() -> tuple[str, str, bool]:
    """
    Display an interactive first-time setup menu for cicada.

    Falls back to text-based input if the terminal doesn't support simple-term-menu.

    Returns:
        tuple[str, str, bool]: The selected extraction method, expansion method, and whether to index PRs
                              e.g., ('regular', 'lemmi', False) or ('bert', 'glove', True)
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
    print(f"{BOLD}Step 1/2: Choose intelligence tier{RESET}")

    tier_items = [
        "Fast - Term frequency + inflections (no downloads)",
        "Balanced - KeyBERT + GloVe semantic expansion (261MB)",
        "Maximum - KeyBERT + FastText expansion (1091MB)",
    ]

    try:
        if TerminalMenu is None:
            return _text_based_setup()
        tier_menu = TerminalMenu(
            tier_items,
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

    # Map tier to extraction + expansion methods
    tier_map = {
        0: ("regular", "lemmi"),
        1: ("bert", "glove"),
        2: ("bert", "fasttext"),
    }
    idx = int(tier_index) if isinstance(tier_index, int) else tier_index[0]
    method, expansion_method = tier_map[idx]

    # Display info based on selection
    print()
    if idx == 0:
        print(f"{GREEN}✓{RESET} Selected: FAST tier")
        print(f"   Term frequency extraction + inflections")
        print(f"   Fast, lightweight, no model downloads")
    elif idx == 1:
        print(f"{GREEN}✓{RESET} Selected: BALANCED tier")
        print(f"   KeyBERT semantic extraction (133MB)")
        print(f"   GloVe semantic expansion (128MB)")
        print(f"   Total: 261MB download")
    else:  # idx == 2
        print(f"{GREEN}✓{RESET} Selected: MAXIMUM tier")
        print(f"   KeyBERT semantic extraction (133MB)")
        print(f"   FastText semantic expansion (958MB)")
        print(f"   Total: 1091MB download")
    print()

    # Step 2: Ask about PR indexing
    print(f"{BOLD}Step 2/2: Index pull requests?{RESET}")
    print(f"{PRIMARY}   PR indexing enables fast offline lookup of GitHub PRs{RESET}")
    print(f"{PRIMARY}   Useful for: finding which PR introduced code, viewing PR context{RESET}")
    print()

    pr_items = [
        "No - Skip PR indexing (can run later with 'cicada-pr-indexer')",
        "Yes - Index PRs now (requires GitHub access)",
    ]

    try:
        if TerminalMenu is None:
            return _text_based_setup()
        pr_menu = TerminalMenu(
            pr_items,
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

    print()
    if index_prs:
        print(f"{GREEN}✓{RESET} Will index pull requests")
    else:
        print(f"{GREEN}✓{RESET} Skipping PR indexing")
    print()

    return (method, expansion_method, index_prs)


def show_full_interactive_setup(repo_path: str | Path | None = None) -> None:
    """
    Display full interactive setup including editor selection and keyword extraction.

    This is the main entry point when running `cicada` with no arguments or a path.

    Args:
        repo_path: Path to the Elixir repository. Defaults to current directory.
    """
    from cicada.setup import setup

    # Check if we're in an Elixir project
    repo_path = Path.cwd() if repo_path is None else Path(repo_path).resolve()
    if not (repo_path / "mix.exs").exists():
        print(f"{PRIMARY}Error: {repo_path} does not appear to be an Elixir project{RESET}")
        print(f"{GREY}(mix.exs not found){RESET}")
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

    editor_items = [
        "Claude Code - AI-powered code editor",
        "Cursor - AI-first code editor",
        "VS Code - Visual Studio Code",
    ]

    if has_terminal_menu:
        try:
            if TerminalMenu is None:
                # Fallback to text-based
                editor = _text_based_editor_selection()
            else:
                editor_menu = TerminalMenu(
                    editor_items,
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

                editor_map = {0: "claude", 1: "cursor", 2: "vs"}
                editor = editor_map[
                    int(editor_index) if isinstance(editor_index, int) else editor_index[0]
                ]
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
            editor = _text_based_editor_selection()
    else:
        editor = _text_based_editor_selection()

    print()
    print(f"{GREEN}✓{RESET} Selected: {editor.upper()}")
    print()

    # Check if index already exists before showing tier selection
    from cicada.utils.storage import get_config_path, get_index_path

    config_path = get_config_path(repo_path)
    index_path = get_index_path(repo_path)

    if config_path.exists() and index_path.exists():
        # Index exists - use existing settings, don't show tier selection
        import yaml

        try:
            with open(config_path) as f:
                existing_config = yaml.safe_load(f)
                extraction_method = existing_config.get("keyword_extraction", {}).get(
                    "method", "regular"
                )
                expansion_method = existing_config.get("keyword_expansion", {}).get(
                    "method", "lemmi"
                )

            # Run setup with existing settings
            try:
                setup(
                    cast(EditorType, editor),
                    repo_path,
                    extraction_method=extraction_method,
                    expansion_method=expansion_method,
                    index_exists=True,
                )
            except Exception as e:
                print(f"\n{PRIMARY}Error: Setup failed: {e}{RESET}")
                sys.exit(1)

            return  # Exit early - don't show tier selection
        except Exception:
            # If we can't read config, proceed with tier selection
            pass

    # Step 2: Choose intelligence tier
    print(f"{BOLD}Step 2/3: Choose intelligence tier{RESET}")

    tier_items = [
        "Fast - Term frequency + inflections (no downloads)",
        "Balanced - KeyBERT + GloVe semantic expansion (261MB)",
        "Maximum - KeyBERT + FastText expansion (1091MB)",
    ]

    if has_terminal_menu:
        try:
            if TerminalMenu is None:
                extraction_method, expansion_method, index_prs = show_first_time_setup()
                # Text-based setup complete - call setup and handle PR indexing
                try:
                    setup(
                        cast(EditorType, editor),
                        repo_path,
                        extraction_method=extraction_method,
                        expansion_method=expansion_method,
                    )
                    if index_prs:
                        _run_pr_indexing(repo_path)
                except Exception as e:
                    print(f"\n{PRIMARY}Error: Setup failed: {e}{RESET}")
                    sys.exit(1)
                return
            tier_menu = TerminalMenu(
                tier_items,
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

            # Map tier to extraction + expansion methods
            tier_map = {
                0: ("regular", "lemmi"),
                1: ("bert", "glove"),
                2: ("bert", "fasttext"),
            }
            idx = int(tier_index) if isinstance(tier_index, int) else tier_index[0]
            extraction_method, expansion_method = tier_map[idx]
        except (KeyboardInterrupt, EOFError):
            print()
            print("Setup cancelled. Exiting...")
            sys.exit(1)
        except Exception:
            print(
                f"\n{GREY}Note: Terminal menu not supported, using text-based input{RESET}\n",
                file=sys.stderr,
            )
            extraction_method, expansion_method, index_prs = show_first_time_setup()
            try:
                setup(
                    cast(EditorType, editor),
                    repo_path,
                    extraction_method=extraction_method,
                    expansion_method=expansion_method,
                )
                if index_prs:
                    _run_pr_indexing(repo_path)
            except Exception as e:
                print(f"\n{PRIMARY}Error: Setup failed: {e}{RESET}")
                sys.exit(1)
            return
    else:
        extraction_method, expansion_method, index_prs = show_first_time_setup()
        try:
            setup(
                cast(EditorType, editor),
                repo_path,
                extraction_method=extraction_method,
                expansion_method=expansion_method,
            )
            if index_prs:
                _run_pr_indexing(repo_path)
        except Exception as e:
            print(f"\n{PRIMARY}Error: Setup failed: {e}{RESET}")
            sys.exit(1)
        return

    # Display info based on tier selection
    print()
    if idx == 0:
        print(f"{GREEN}✓{RESET} Selected: FAST tier")
        print(f"   Term frequency extraction + inflections")
        print(f"   Fast, lightweight, no model downloads")
    elif idx == 1:
        print(f"{GREEN}✓{RESET} Selected: BALANCED tier")
        print(f"   KeyBERT semantic extraction (133MB)")
        print(f"   GloVe semantic expansion (128MB)")
        print(f"   Total: 261MB download")
    else:  # idx == 2
        print(f"{GREEN}✓{RESET} Selected: MAXIMUM tier")
        print(f"   KeyBERT semantic extraction (133MB)")
        print(f"   FastText semantic expansion (958MB)")
        print(f"   Total: 1091MB download")
    print()

    # Step 3: Ask about PR indexing
    print(f"{BOLD}Step 3/3: Index pull requests?{RESET}")
    print(f"{PRIMARY}   PR indexing enables fast offline lookup of GitHub PRs{RESET}")
    print(f"{PRIMARY}   Useful for: finding which PR introduced code, viewing PR context{RESET}")
    print()

    pr_items = [
        "No - Skip PR indexing (can run later with 'cicada-pr-indexer')",
        "Yes - Index PRs now (requires GitHub access)",
    ]

    try:
        if TerminalMenu is None:
            extraction_method, expansion_method, index_prs = show_first_time_setup()
            # Text-based setup complete - call setup and handle PR indexing
            try:
                setup(
                    cast(EditorType, editor),
                    repo_path,
                    extraction_method=extraction_method,
                    expansion_method=expansion_method,
                )
                if index_prs:
                    _run_pr_indexing(repo_path)
            except Exception as e:
                print(f"\n{PRIMARY}Error: Setup failed: {e}{RESET}")
                sys.exit(1)
            return
        pr_menu = TerminalMenu(
            pr_items,
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
        extraction_method, expansion_method, index_prs = show_first_time_setup()
        try:
            setup(
                cast(EditorType, editor),
                repo_path,
                extraction_method=extraction_method,
                expansion_method=expansion_method,
            )
            if index_prs:
                _run_pr_indexing(repo_path)
        except Exception as e:
            print(f"\n{PRIMARY}Error: Setup failed: {e}{RESET}")
            sys.exit(1)
        return

    if pr_index is None:
        print()
        print(f"{SELECTED}Setup cancelled. Exiting...{RESET}")
        sys.exit(1)

    idx = int(pr_index) if isinstance(pr_index, int) else pr_index[0]
    index_prs = idx == 1

    print()
    if index_prs:
        print(f"{GREEN}✓{RESET} Will index pull requests")
    else:
        print(f"{GREEN}✓{RESET} Skipping PR indexing")
    print()

    # Run setup
    print(f"{BOLD}Running setup...{RESET}")
    print()

    try:
        setup(
            cast(EditorType, editor),
            repo_path,
            extraction_method=extraction_method,
            expansion_method=expansion_method,
        )

        # Run PR indexing if requested
        if index_prs:
            _run_pr_indexing(repo_path)
    except Exception as e:
        print(f"\n{PRIMARY}Error: Setup failed: {e}{RESET}")
        sys.exit(1)


def _run_pr_indexing(repo_path: Path) -> None:
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
        print(f"{GREY}Partial index may have been saved. Run 'cicada-pr-indexer' to continue.{RESET}")
        print()
    except Exception as e:
        print()
        print(f"{PRIMARY}⚠️  PR indexing failed: {e}{RESET}")
        print(f"{GREY}You can run 'cicada-pr-indexer' later to index PRs.{RESET}")
        print()


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
            if choice in ("1", "2", "3"):
                editor_map = {"1": "claude", "2": "cursor", "3": "vs"}
                return editor_map[choice]
            print("Invalid choice. Please enter 1, 2, or 3.")
        except (KeyboardInterrupt, EOFError):
            print()
            print("Setup cancelled. Exiting...")
            sys.exit(1)
