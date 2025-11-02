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


def _text_based_setup() -> tuple[str, str]:
    """
    Fallback text-based setup for terminals that don't support simple-term-menu.

    Returns:
        tuple[str, str]: The selected extraction and expansion methods
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
    print("1. Regular - Term frequency-based extraction (fast, no ML)")
    print("2. KeyBERT - Semantic keyword extraction (AI embeddings)")
    print()

    while True:
        try:
            method_choice = input("Enter your choice (1 or 2) [default: 1]: ").strip()
            if not method_choice:
                method_choice = "1"
            if method_choice in ("1", "2"):
                method = "regular" if method_choice == "1" else "bert"
                break
            print("Invalid choice. Please enter 1 or 2.")
        except (KeyboardInterrupt, EOFError):
            print()
            print("Setup cancelled. Exiting...")
            sys.exit(1)

    # Display info based on selection
    print()
    if method == "regular":
        print(f"{BOLD}  What is Regular extraction?{RESET}")
        print(f"   Uses term frequency (TF) to identify important keywords{RESET}")
        print(f"   Fast, lightweight, no model downloads required{RESET}")
        print()
        print(f"{GREEN}✓{RESET} Selected: REGULAR")
        print()
    else:
        print(f"{SELECTED}  What is KeyBERT?{RESET}")
        print(
            f"{PRIMARY}   KeyBERT uses AI embeddings (133MB model) to find semantically similar keywords{RESET}"
        )
        print()
        print(f"{GREEN}✓{RESET} Selected: KEYBERT")
        print()

    # Step 2: Ask about keyword expansion (applies to both methods)
    print(f"{BOLD}Step 2/2: Choose keyword expansion{RESET}")
    print(
        f"{PRIMARY}   All methods include lemminflect inflections (e.g., run → runs, running, ran){RESET}"
    )
    print(f"{PRIMARY}   Optionally add word embeddings for semantic expansion:{RESET}")
    print(f'{PRIMARY}   Example: "database" → adds "postgresql", "mysql", "storage"{RESET}')
    print()
    print("1. Lemmi only - Just inflections (fast, no downloads)")
    print("2. GloVe + Lemmi - Semantic expansion (128MB download)")
    print("3. FastText + Lemmi - Better rare words (958MB download)")
    print()

    while True:
        try:
            expansion_choice = input("Enter your choice (1, 2, or 3) [default: 1]: ").strip()
            if not expansion_choice:
                expansion_choice = "1"
            if expansion_choice in ("1", "2", "3"):
                expansion_map = {"1": "lemmi", "2": "glove", "3": "fasttext"}
                expansion_method = expansion_map[expansion_choice]
                break
            print("Invalid choice. Please enter 1, 2, or 3.")
        except (KeyboardInterrupt, EOFError):
            print()
            print(f"{SELECTED}Setup cancelled. Exiting...{RESET}")
            sys.exit(1)

    print()
    if expansion_method == "lemmi":
        print(f"{GREEN}✓{RESET} Lemminflect inflections only")
    elif expansion_method == "glove":
        print(f"{GREEN}✓{RESET} GloVe + Lemmi expansion (128MB)")
    else:  # fasttext
        print(f"{GREEN}✓{RESET} FastText + Lemmi expansion (958MB)")
    print()

    return (method, expansion_method)


def show_first_time_setup() -> tuple[str, str]:
    """
    Display an interactive first-time setup menu for cicada.

    Falls back to text-based input if the terminal doesn't support simple-term-menu.

    Returns:
        tuple[str, str]: The selected extraction and expansion methods
                        e.g., ('regular', 'lemmi') or ('bert', 'glove')
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
        "Regular - Term frequency-based extraction (fast, no ML)",
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

    method = "regular" if method_index == 0 else "bert"

    # Display info based on selection
    print()
    if method == "regular":
        print(f"{BOLD}  What is Regular extraction?{RESET}")
        print(f"   Uses term frequency (TF) to identify important keywords{RESET}")
        print(f"   Fast, lightweight, no model downloads required{RESET}")
        print()
        print(f"{GREEN}✓{RESET} Selected: REGULAR")
        print()
    else:
        print(f"{SELECTED}  What is KeyBERT?{RESET}")
        print(
            f"{PRIMARY}   KeyBERT uses AI embeddings (133MB model) to find semantically similar keywords{RESET}"
        )
        print()
        print(f"{GREEN}✓{RESET} Selected: KEYBERT")
        print()

    # Step 2: Ask about keyword expansion (applies to both methods)
    print(f"{BOLD}Step 2/2: Choose keyword expansion{RESET}")
    print(
        f"{PRIMARY}   All methods include lemminflect inflections (e.g., run → runs, running, ran){RESET}"
    )
    print(f"{PRIMARY}   Optionally add word embeddings for semantic expansion:{RESET}")
    print(f'{PRIMARY}   Example: "database" → adds "postgresql", "mysql", "storage"{RESET}')
    print()

    expansion_items = [
        "Lemmi only - Just inflections (fast, no downloads)",
        "GloVe + Lemmi - Semantic expansion (128MB download)",
        "FastText + Lemmi - Better rare words (958MB download)",
    ]

    try:
        if TerminalMenu is None:
            return _text_based_setup()
        expansion_menu = TerminalMenu(
            expansion_items,
            title="",
            menu_cursor="» ",
            menu_cursor_style=("fg_yellow", "bold"),
            menu_highlight_style=("fg_yellow", "bold"),
            cycle_cursor=True,
            clear_screen=False,
        )
        expansion_index = expansion_menu.show()
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

    if expansion_index is None:
        print()
        print(f"{SELECTED}Setup cancelled. Exiting...{RESET}")
        sys.exit(1)

    expansion_map = {0: "lemmi", 1: "glove", 2: "fasttext"}
    # Cast to int to satisfy type checker (TerminalMenu.show() returns int | tuple)
    idx = int(expansion_index) if isinstance(expansion_index, int) else expansion_index[0]
    expansion_method = expansion_map[idx]

    print()
    if expansion_method == "lemmi":
        print(f"{GREEN}✓{RESET} Lemminflect inflections only")
    elif expansion_method == "glove":
        print(f"{GREEN}✓{RESET} GloVe + Lemmi expansion (128MB)")
    else:  # fasttext
        print(f"{GREEN}✓{RESET} FastText + Lemmi expansion (958MB)")
    print()

    return (method, expansion_method)


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

            return  # Exit early - don't show model selection
        except Exception:
            # If we can't read config, proceed with model selection
            pass

    # Step 2: Choose keyword extraction method
    print(f"{BOLD}Step 2/4: Choose extraction method{RESET}")

    method_items = [
        "Regular - Term frequency-based extraction (fast, no ML)",
        "KeyBERT - Semantic keyword extraction (AI embeddings)",
    ]

    if has_terminal_menu:
        try:
            if TerminalMenu is None:
                extraction_method, expansion_method = show_first_time_setup()
                # Text-based setup complete - call setup and return
                try:
                    setup(
                        cast(EditorType, editor),
                        repo_path,
                        extraction_method=extraction_method,
                        expansion_method=expansion_method,
                    )
                except Exception as e:
                    print(f"\n{PRIMARY}Error: Setup failed: {e}{RESET}")
                    sys.exit(1)
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

            method = "regular" if method_index == 0 else "bert"
        except (KeyboardInterrupt, EOFError):
            print()
            print("Setup cancelled. Exiting...")
            sys.exit(1)
        except Exception:
            print(
                f"\n{GREY}Note: Terminal menu not supported, using text-based input{RESET}\n",
                file=sys.stderr,
            )
            extraction_method, expansion_method = show_first_time_setup()
            try:
                setup(
                    cast(EditorType, editor),
                    repo_path,
                    extraction_method=extraction_method,
                    expansion_method=expansion_method,
                )
            except Exception as e:
                print(f"\n{PRIMARY}Error: Setup failed: {e}{RESET}")
                sys.exit(1)
            return
    else:
        extraction_method, expansion_method = show_first_time_setup()
        try:
            setup(
                cast(EditorType, editor),
                repo_path,
                extraction_method=extraction_method,
                expansion_method=expansion_method,
            )
        except Exception as e:
            print(f"\n{PRIMARY}Error: Setup failed: {e}{RESET}")
            sys.exit(1)
        return

    # For Regular extraction, no tier selection needed
    if method == "regular":
        print()
        print(f"{BOLD}  What is Regular extraction?{RESET}")
        print(f"   Uses term frequency (TF) to identify important keywords{RESET}")
        print(f"   Fast, lightweight, no model downloads required{RESET}")
        print()
        print(f"{GREEN}✓{RESET} Selected: REGULAR")
        print()
    else:
        # KeyBERT selected - single 133MB model
        print()
        print(f"{SELECTED}  What is KeyBERT?{RESET}")
        print(
            f"{PRIMARY}   KeyBERT uses AI embeddings (133MB model) to find semantically similar keywords{RESET}"
        )
        print()
        print(f"{GREEN}✓{RESET} Selected: KEYBERT")
        print()

    # Step 3: Ask about keyword expansion (applies to both Regular and KeyBERT)
    print(f"{BOLD}Step 3/4: Choose keyword expansion{RESET}")
    print()
    print(
        f"{PRIMARY}   All methods include lemminflect inflections (e.g., run → runs, running, ran){RESET}"
    )
    print(f"{PRIMARY}   Optionally add word embeddings for semantic expansion:{RESET}")
    print(f'{PRIMARY}   Example: "database" → adds "postgresql", "mysql", "storage"{RESET}')
    print()

    expansion_items = [
        "Lemmi only - Just inflections (fast, no downloads)",
        "GloVe + Lemmi - Semantic expansion (128MB download)",
        "FastText + Lemmi - Better rare words (958MB download)",
    ]

    expansion_index = None  # Initialize to None
    try:
        if TerminalMenu is None:
            extraction_method, expansion_method = show_first_time_setup()
            # Text-based setup complete - call setup and return
            try:
                setup(
                    cast(EditorType, editor),
                    repo_path,
                    extraction_method=extraction_method,
                    expansion_method=expansion_method,
                )
            except Exception as e:
                print(f"\n{PRIMARY}Error: Setup failed: {e}{RESET}")
                sys.exit(1)
            return
        else:
            expansion_menu = TerminalMenu(
                expansion_items,
                title="",
                menu_cursor="» ",
                menu_cursor_style=("fg_yellow", "bold"),
                menu_highlight_style=("fg_yellow", "bold"),
                cycle_cursor=True,
                clear_screen=False,
            )
            expansion_index = expansion_menu.show()
    except (KeyboardInterrupt, EOFError):
        print()
        print(f"{SELECTED}Setup cancelled. Exiting...{RESET}")
        sys.exit(1)
    except Exception:
        print(
            f"\n{GREY}Note: Terminal menu not supported, using text-based input{RESET}\n",
            file=sys.stderr,
        )
        extraction_method, expansion_method = show_first_time_setup()
        # Text-based setup complete - call setup and return
        try:
            setup(
                cast(EditorType, editor),
                repo_path,
                extraction_method=extraction_method,
                expansion_method=expansion_method,
            )
        except Exception as e:
            print(f"\n{PRIMARY}Error: Setup failed: {e}{RESET}")
            sys.exit(1)
        return

    # expansion_index is now guaranteed to be set (or we returned above)
    if expansion_index is None:
        print()
        print(f"{SELECTED}Setup cancelled. Exiting...{RESET}")
        sys.exit(1)

    # Map method ("regular" or "bert") to extraction_method
    extraction_method = method

    # Map expansion_index to expansion_method
    expansion_map = {0: "lemmi", 1: "glove", 2: "fasttext"}
    # Cast to int to satisfy type checker (TerminalMenu.show() returns int | tuple)
    idx = int(expansion_index) if isinstance(expansion_index, int) else expansion_index[0]
    expansion_method = expansion_map[idx]

    print()
    if expansion_method == "lemmi":
        print(f"{GREEN}✓{RESET} Lemminflect inflections only")
    elif expansion_method == "glove":
        print(f"{GREEN}✓{RESET} GloVe + Lemmi expansion (128MB)")
    else:  # fasttext
        print(f"{GREEN}✓{RESET} FastText + Lemmi expansion (958MB)")
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
