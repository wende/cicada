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

from cicada.ascii_art import generate_gradient_ascii_art
from cicada.colors import BOLD, GREEN, GREY, PRIMARY, RESET, SELECTED
from cicada.setup import EditorType


def _text_based_setup() -> tuple[str, str]:
    """
    Fallback text-based setup for terminals that don't support simple-term-menu.

    Returns:
        tuple[str, str]: The selected extraction method and model tier
    """
    print(f"{PRIMARY}{'=' * 70}{RESET}")
    print(f"{SELECTED}🦗 Welcome to CICADA - Elixir Code Intelligence{RESET}")
    print(f"{PRIMARY}{'=' * 70}{RESET}")
    print()
    print(f"This is your first time running CICADA in this project.{RESET}")
    print(f"Let's configure keyword extraction for code intelligence.{RESET}")
    print()
    print(f"{BOLD}Step 1/2: Choose extraction method{RESET}")
    print()
    print("1. Lemminflect - Grammar-based keyword extraction (fast, proven)")
    print("2. KeyBERT - Semantic keyword extraction (AI embeddings)")
    print()

    while True:
        try:
            method_choice = input("Enter your choice (1 or 2) [default: 1]: ").strip()
            if not method_choice:
                method_choice = "1"
            if method_choice in ("1", "2"):
                method = "lemminflect" if method_choice == "1" else "bert"
                break
            print("Invalid choice. Please enter 1 or 2.")
        except (KeyboardInterrupt, EOFError):
            print()
            print("Setup cancelled. Exiting...")
            sys.exit(1)

    # For lemminflect, no tier selection - it's always the same
    print()
    if method == "lemminflect":
        print(f"{BOLD}  What is Lemminflect?{RESET}")
        print(f"   Lemminflect finds keywords using grammar rules + word importance{RESET}")
        print()
        print(f"{GREEN}✓{RESET} Selected: LEMMINFLECT")
        print()
        return ("lemminflect", "regular")

    # For KeyBERT, ask for tier
    print(f"{SELECTED}  What is KeyBERT?{RESET}")
    print(f"{PRIMARY}   KeyBERT uses AI embeddings to find semantically similar keywords{RESET}")
    print()
    print("1. Fast (80MB, ~1s) - Recommended for bigger projects")
    print("2. Regular (133MB, ~1.4s) - Better semantic understanding [recommended]")
    print("3. Max (420MB, ~6.5s) - Highest quality embeddings")

    print()
    print(f"{BOLD}Step 2/2: Choose model tier{RESET}")
    print()

    while True:
        try:
            tier_choice = input("Enter your choice (1, 2, or 3) [default: 2]: ").strip()
            if not tier_choice:
                tier_choice = "2"
            if tier_choice in ("1", "2", "3"):
                tier_map = {"1": "fast", "2": "regular", "3": "max"}
                tier = tier_map[tier_choice]
                break
            print("Invalid choice. Please enter 1, 2, or 3.")
        except (KeyboardInterrupt, EOFError):
            print()
            print(f"{SELECTED}Setup cancelled. Exiting...{RESET}")
            sys.exit(1)

    print()
    print(f"{GREEN}✓{RESET} Selected: KeyBERT - {tier.capitalize()} model")
    print()

    return ("bert", tier)


def show_first_time_setup() -> tuple[str, str]:
    """
    Display an interactive first-time setup menu for cicada.

    Falls back to text-based input if the terminal doesn't support simple-term-menu.

    Returns:
        tuple[str, str]: The selected extraction method and model tier
                        e.g., ('lemminflect', 'regular') or ('bert', 'fast')
    """
    # Check if terminal menu is available and supported
    if not has_terminal_menu:
        return _text_based_setup()

    # Display ASCII art
    print(generate_gradient_ascii_art())

    # Step 1: Choose extraction method
    print(f"{PRIMARY}{'=' * 70}{RESET}")
    print(f"{SELECTED}🦗 Welcome to CICADA - Elixir Code Intelligence{RESET}")
    print(f"{PRIMARY}{'=' * 70}{RESET}")
    print()
    print(f"This is your first time running CICADA in this project.{RESET}")
    print(f"Let's configure keyword extraction for code intelligence.{RESET}")
    print()
    print(f"{BOLD}Step 1/2: Choose extraction method{RESET}")

    method_items = [
        "Lemminflect - Grammar-based keyword extraction (fast, proven)",
        "KeyBERT - Semantic keyword extraction (AI embeddings)",
    ]

    try:
        if TerminalMenu is None:
            return _text_based_setup()
        method_menu = TerminalMenu(
            method_items,
            title="",
            menu_cursor="» ",
            menu_cursor_style=("fg_yellow", "bold"),
            menu_highlight_style=("fg_yellow", "bold"),
            cycle_cursor=True,
            clear_screen=False,
        )
        method_index = method_menu.show()
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

    if method_index is None:
        print()
        print("Setup cancelled. Exiting...")
        sys.exit(1)

    method = "lemminflect" if method_index == 0 else "bert"

    # For lemminflect, no tier selection - it's always the same
    print()
    if method == "lemminflect":
        print(f"{BOLD}  What is Lemminflect?{RESET}")
        print(f"   Lemminflect finds keywords using grammar rules + word importance{RESET}")
        print(f'   Example: "We use Kubernetes for container orchestration"{RESET}')
        print(f'   Output: "Kubernetes", "container", "orchestration"{RESET}')
        print()
        print(f"{GREEN}✓{RESET} Selected: LEMMINFLECT")
        print()
        return ("lemminflect", "regular")

    # For KeyBERT, ask for tier
    print(f"{SELECTED}  What is KeyBERT?{RESET}")
    print(f"{PRIMARY}   KeyBERT uses AI embeddings to find semantically similar keywords{RESET}")
    print(f'{PRIMARY}   Example: "We use Kubernetes for container orchestration"{RESET}')
    print(f'{PRIMARY}   Output: "Kubernetes", "deployment", "microservices", "DevOps"{RESET}')
    print()
    tier_items = [
        "Fast (80MB, ~1s) - Recommended for bigger projects",
        "Regular [recommended] (133MB, ~1.4s) - Better semantic understanding",
        "Max (420MB, ~6.5s) - Highest quality embeddings",
    ]
    print(f"{SELECTED}Step 2/2: Choose model tier\n")

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
        print(f"{SELECTED}Setup cancelled. Exiting...{RESET}")
        sys.exit(1)
    except Exception:
        # Terminal doesn't support the menu - fall back to text-based
        print(
            f"\n{GREY}Note: Terminal menu not supported, using text-based input{RESET}\n",
            file=sys.stderr,
        )
        # Recreate the selection for model tier based on already selected method
        return _text_based_setup()

    if tier_index is None:
        print()
        print(f"{SELECTED}Setup cancelled. Exiting...{RESET}")
        sys.exit(1)

    tier_map = {0: "fast", 1: "regular", 2: "max"}
    # Ensure tier_index is treated as int (TerminalMenu.show() returns int | tuple | None)
    tier = tier_map[int(tier_index) if isinstance(tier_index, int) else tier_index[0]]

    print()
    print(f"{GREEN}✓{RESET} Selected: KeyBERT - {tier.capitalize()} model")
    print()

    return ("bert", tier)


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
    print(f"{BOLD}Step 1/3: Choose your editor{RESET}")

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

    # Check if index already exists before showing model selection
    from cicada.utils.storage import get_config_path, get_index_path

    config_path = get_config_path(repo_path)
    index_path = get_index_path(repo_path)

    if config_path.exists() and index_path.exists():
        # Index exists - use existing settings, don't show model selection
        import yaml

        try:
            with open(config_path) as f:
                existing_config = yaml.safe_load(f)
                method = existing_config.get("keyword_extraction", {}).get("method", "lemminflect")
                tier = existing_config.get("keyword_extraction", {}).get("tier", "regular")

            # Run setup with existing settings
            try:
                setup(
                    cast(EditorType, editor),
                    repo_path,
                    keyword_method=method,
                    keyword_tier=tier,
                    index_exists=True,
                )
            except Exception as e:
                print(f"\n{PRIMARY}Error: Setup failed: {e}{RESET}")
                sys.exit(1)

            return  # Exit early - don't show model selection
        except Exception:
            # If we can't read config, proceed with model selection
            pass

    # Step 2: Choose keyword extraction method
    print(f"{BOLD}Step 2/3: Choose extraction method{RESET}")

    method_items = [
        "Lemminflect - Grammar-based keyword extraction (fast, proven)",
        "KeyBERT - Semantic keyword extraction (AI embeddings)",
    ]

    if has_terminal_menu:
        try:
            if TerminalMenu is None:
                method, tier = show_first_time_setup()
                return
            method_menu = TerminalMenu(
                method_items,
                title="",
                menu_cursor="» ",
                menu_cursor_style=("fg_yellow", "bold"),
                menu_highlight_style=("fg_yellow", "bold"),
                cycle_cursor=True,
                clear_screen=False,
            )
            method_index = method_menu.show()

            if method_index is None:
                print()
                print("Setup cancelled. Exiting...")
                sys.exit(1)

            method = "lemminflect" if method_index == 0 else "bert"
        except (KeyboardInterrupt, EOFError):
            print()
            print("Setup cancelled. Exiting...")
            sys.exit(1)
        except Exception:
            print(
                f"\n{GREY}Note: Terminal menu not supported, using text-based input{RESET}\n",
                file=sys.stderr,
            )
            method, tier = show_first_time_setup()
            return
    else:
        method, tier = show_first_time_setup()
        return

    # For lemminflect, no tier selection needed - always uses default
    if method == "lemminflect":
        print()
        print(f"{BOLD}  What is Lemminflect?{RESET}")
        print(f"   Lemminflect finds keywords using grammar rules + word importance{RESET}")
        print()
        print(f"{GREEN}✓{RESET} Selected: LEMMINFLECT")
        print()
        tier = "regular"  # Default tier (not used for lemminflect, but needed for API)
    else:
        # Step 3: Choose model tier (only for BERT)
        print()
        print(f"{SELECTED}  What is KeyBERT?{RESET}")
        print(
            f"{PRIMARY}   KeyBERT uses AI embeddings to find semantically similar keywords{RESET}"
        )

        tier_items = [
            "Fast (80MB, ~1s) - Recommended for bigger projects",
            "Regular [recommended] (133MB, ~1.4s) - Better semantic understanding",
            "Max (420MB, ~6.5s) - Highest quality embeddings",
        ]

        print()
        print(f"{BOLD}Step 3/3: Choose model tier{RESET}")
        print()

        try:
            if TerminalMenu is None:
                method, tier = show_first_time_setup()
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
        except (KeyboardInterrupt, EOFError):
            print()
            print(f"{SELECTED}Setup cancelled. Exiting...{RESET}")
            sys.exit(1)
        except Exception:
            print(
                f"\n{GREY}Note: Terminal menu not supported, using text-based input{RESET}\n",
                file=sys.stderr,
            )
            method, tier = show_first_time_setup()
            return

        if tier_index is None:
            print()
            print(f"{SELECTED}Setup cancelled. Exiting...{RESET}")
            sys.exit(1)

        tier_map = {0: "fast", 1: "regular", 2: "max"}
        tier = tier_map[int(tier_index) if isinstance(tier_index, int) else tier_index[0]]

        print()
        print(f"{GREEN}✓{RESET} Selected: KeyBERT - {tier.capitalize()} model")
        print()

    # Run setup
    print(f"{BOLD}Running setup...{RESET}")
    print()

    try:
        setup(cast(EditorType, editor), repo_path, keyword_method=method, keyword_tier=tier)
    except Exception as e:
        print(f"\n{PRIMARY}Error: Setup failed: {e}{RESET}")
        sys.exit(1)


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
