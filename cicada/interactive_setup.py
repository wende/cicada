"""Interactive first-time setup menu for cicada."""

import contextlib
import sys
from pathlib import Path

try:
    from simple_term_menu import TerminalMenu

    has_terminal_menu = True
except ImportError:
    TerminalMenu = None  # type: ignore
    has_terminal_menu = False

from cicada.format import BOLD, GREEN, GREY, PRIMARY, RESET, SELECTED, generate_gradient_ascii_art
from cicada.interactive_setup_helpers import (
    CLAUDE_MD_ITEMS,
    EDITOR_ITEMS,
    MODE_ITEMS,
    MODE_MAP,
    MODE_MAP_TEXT,
    PR_ITEMS,
    UnsupportedProjectError,
    check_elixir_project,
    display_claude_md_selection,
    display_editor_selection,
    display_embeddings_config_selection,
    display_mode_selection,
    display_pr_indexing_selection,
    get_existing_config,
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
        print(f"{SELECTED}🦗 Welcome to CICADA - Code Intelligence{RESET}")
        print(f"{PRIMARY}{'=' * 70}{RESET}")
    print()
    print(f"This is your first time running CICADA in this project.{RESET}")
    print(f"Let's configure indexing for code intelligence.{RESET}")
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


def _handle_menu_unavailable() -> tuple[str, bool, bool, dict[str, str] | None]:
    """Fallback to text-based setup when TerminalMenu cannot be used."""
    print(
        f"\n{GREY}Note: Terminal menu not supported, using text-based input{RESET}\n",
        file=sys.stderr,
    )
    return _text_based_setup()


def _text_based_setup() -> tuple[str, bool, bool, dict[str, str] | None]:
    """
    Fallback text-based setup for terminals that don't support simple-term-menu.

    Returns:
        tuple[str, bool, bool, dict | None]: The selected indexing mode, whether to index PRs,
                                              whether to add to CLAUDE.md, and embeddings config
    """
    _print_first_time_intro(show_header=True)
    print(f"{BOLD}Step 1/3: Choose indexing mode{RESET}")
    print()
    print("1. Keywords - Token-based extraction (default)")
    print("2. Embeddings - Semantic search via Ollama")
    print()

    while True:
        try:
            mode_choice = input("Enter your choice (1 or 2) [default: 1]: ").strip()
            if not mode_choice:
                mode_choice = "1"
            if mode_choice in MODE_MAP_TEXT:
                indexing_mode = MODE_MAP_TEXT[mode_choice]
                break
            print("Invalid choice. Please enter 1 or 2.")
        except (KeyboardInterrupt, EOFError):
            print()
            print("Setup cancelled. Exiting...")
            sys.exit(1)

    display_mode_selection(int(mode_choice) - 1)

    # Configure embeddings if selected
    embeddings_config = None
    if indexing_mode == "embeddings":
        embeddings_config = _configure_embeddings()

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

    return (indexing_mode, index_prs, add_to_claude_md_flag, embeddings_config)


def _prompt_ollama_url() -> str:
    """Prompt user for Ollama host URL with validation."""
    from cicada.embeddings.ollama import DEFAULT_OLLAMA_HOST, check_ollama_connection

    print(f"{BOLD}Ollama Configuration{RESET}")
    print(f"{PRIMARY}   Embeddings require Ollama running locally or remotely{RESET}")
    print()

    while True:
        try:
            url = input(f"Enter Ollama URL [{DEFAULT_OLLAMA_HOST}]: ").strip()
            if not url:
                url = DEFAULT_OLLAMA_HOST

            # Validate URL format
            if not url.startswith(("http://", "https://")):
                print(f"{PRIMARY}Invalid URL format. Must start with http:// or https://{RESET}")
                continue

            # Check connection
            print(f"{GREY}   Checking connection to {url}...{RESET}")
            if check_ollama_connection(url):
                print(f"{GREEN}✓{RESET} Connected to Ollama")
                return url
            else:
                print(f"{PRIMARY}⚠ Cannot connect to Ollama at {url}{RESET}")
                print(f"{GREY}   Make sure Ollama is running: ollama serve{RESET}")
                retry = input("Try again? [Y/n]: ").strip().lower()
                if retry == "n":
                    print(f"{GREY}   Using {url} anyway (connection may work later){RESET}")
                    return url

        except (KeyboardInterrupt, EOFError):
            print()
            print("Setup cancelled. Exiting...")
            sys.exit(1)


def _prompt_model_selection_text(ollama_host: str) -> str:
    """Text-based model selection for terminals without menu support."""
    from cicada.embeddings.ollama import DEFAULT_EMBEDDING_MODEL, get_embedding_models

    print()
    print(f"{BOLD}Select Embedding Model{RESET}")

    try:
        models = get_embedding_models(ollama_host)
        if not models:
            print(f"{PRIMARY}No models found. Using default: {DEFAULT_EMBEDDING_MODEL}{RESET}")
            print(f"{GREY}   Install with: ollama pull {DEFAULT_EMBEDDING_MODEL}{RESET}")
            return DEFAULT_EMBEDDING_MODEL

        # Show available models
        print(f"{PRIMARY}Available models:{RESET}")
        for i, model in enumerate(models[:10], 1):  # Show max 10
            marker = " (recommended)" if model == DEFAULT_EMBEDDING_MODEL else ""
            print(f"  {i}. {model}{marker}")

        if len(models) > 10:
            print(f"  ... and {len(models) - 10} more")

        print()
        while True:
            choice = input(f"Enter model number or name [{DEFAULT_EMBEDDING_MODEL}]: ").strip()
            if not choice:
                return DEFAULT_EMBEDDING_MODEL

            # Try as number
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(models):
                    return models[idx]
                print("Invalid number. Please try again.")
            except ValueError:
                # Try as name
                if choice in models:
                    return choice
                # Allow any model name (user might type one not in list)
                confirm = (
                    input(f"Model '{choice}' not in list. Use anyway? [y/N]: ").strip().lower()
                )
                if confirm in ("y", "yes"):
                    return choice
                continue

    except ConnectionError:
        print(f"{PRIMARY}Cannot fetch models. Using default: {DEFAULT_EMBEDDING_MODEL}{RESET}")
        return DEFAULT_EMBEDDING_MODEL
    except (KeyboardInterrupt, EOFError):
        print()
        print("Setup cancelled. Exiting...")
        sys.exit(1)


def _prompt_model_selection_menu(ollama_host: str) -> str | None:
    """Menu-based model selection. Returns None if menu unavailable."""
    from cicada.embeddings.ollama import DEFAULT_EMBEDDING_MODEL, get_embedding_models

    if TerminalMenu is None:
        return None

    print()
    print(f"{BOLD}Select Embedding Model{RESET}")

    try:
        models = get_embedding_models(ollama_host)
        if not models:
            print(f"{PRIMARY}No models found. Using default: {DEFAULT_EMBEDDING_MODEL}{RESET}")
            print(f"{GREY}   Install with: ollama pull {DEFAULT_EMBEDDING_MODEL}{RESET}")
            return DEFAULT_EMBEDDING_MODEL

        # Build menu items with recommendations
        menu_items = []
        for model in models[:15]:  # Limit to 15 for usability
            if model == DEFAULT_EMBEDDING_MODEL:
                menu_items.append(f"{model} (recommended)")
            else:
                menu_items.append(model)

        menu = TerminalMenu(menu_items, **MENU_STYLE)  # type: ignore[arg-type]
        selection = menu.show()

        if selection is None:
            print()
            print("Setup cancelled. Exiting...")
            sys.exit(1)

        if isinstance(selection, tuple):
            selection = selection[0]

        return models[int(selection)]

    except ConnectionError:
        print(f"{PRIMARY}Cannot fetch models. Using default: {DEFAULT_EMBEDDING_MODEL}{RESET}")
        return DEFAULT_EMBEDDING_MODEL
    except Exception:
        # Fall back to text-based selection
        return None


def _configure_embeddings() -> dict[str, str]:
    """
    Interactive configuration for embeddings.

    Returns:
        Dictionary with 'ollama_host' and 'model' keys
    """
    print()

    # Step 1: Get Ollama URL
    ollama_host = _prompt_ollama_url()

    # Step 2: Select model
    model = None
    if has_terminal_menu:
        with contextlib.suppress(Exception):
            model = _prompt_model_selection_menu(ollama_host)

    if model is None:
        model = _prompt_model_selection_text(ollama_host)

    display_embeddings_config_selection(ollama_host, model)

    return {"ollama_host": ollama_host, "model": model}


def show_first_time_setup(
    show_welcome: bool = True,
    default_index_prs: bool | None = None,
    default_add_to_claude: bool | None = None,
) -> tuple[str, bool, bool, dict[str, str] | None]:
    """
    Display an interactive first-time setup menu for cicada.

    Falls back to text-based input if the terminal doesn't support simple-term-menu.

    Args:
        show_welcome: Whether to display the ASCII art banner and intro text.
        default_index_prs: If set, skip PR indexing question and use this value.
        default_add_to_claude: If set, skip CLAUDE.md question and use this value.

    Returns:
        tuple[str, bool, bool, dict | None]: The selected indexing mode, whether to index PRs,
                                              whether to add to CLAUDE.md, and embeddings config
    """
    # Check if terminal menu is available and supported
    if not has_terminal_menu:
        # Pass defaults to text-based setup if needed (not implemented yet, but keeping consistent)
        return _text_based_setup()

    _print_first_time_intro(show_header=show_welcome)
    print(f"{BOLD}Step 1/3: Choose indexing mode{RESET}")

    def _select_with_menu(items: list[str], cancel_message: str) -> int | None:
        try:
            return _prompt_menu_selection(items, cancel_message)
        except MenuUnavailableError:
            return None

    mode_index = _select_with_menu(MODE_ITEMS, "Setup cancelled. Exiting...")
    if mode_index is None:
        return _handle_menu_unavailable()

    indexing_mode = MODE_MAP[mode_index]
    display_mode_selection(mode_index)

    # Configure embeddings if selected
    embeddings_config = None
    if indexing_mode == "embeddings":
        embeddings_config = _configure_embeddings()

    # Step 2: Ask about PR indexing
    if default_index_prs is not None:
        index_prs = default_index_prs
    else:
        print(f"{BOLD}Step 2/3: Index pull requests?{RESET}")
        print(f"{PRIMARY}   PR indexing enables fast offline lookup of GitHub PRs{RESET}")
        print(
            f"{PRIMARY}   Useful for: finding which PR introduced code, viewing PR context{RESET}"
        )
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
    if default_add_to_claude is not None:
        add_to_claude_md_flag = default_add_to_claude
    else:
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

    return (indexing_mode, index_prs, add_to_claude_md_flag, embeddings_config)


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


def show_full_interactive_setup(repo_path: str | Path | None = None) -> None:
    """
    Display full interactive setup including editor selection and keyword extraction.

    This is the main entry point when running `cicada` with no arguments or a path.

    Args:
        repo_path: Path to the repository. Defaults to current directory.
    """

    # Helper to run setup with error handling
    def _run_setup_with_error_handling(
        editor: str,
        repo_path: Path,
        indexing_mode: str,
        index_exists: bool = False,
        index_prs: bool = False,
        add_to_claude_md: bool = False,
        embeddings_config: dict[str, str] | None = None,
    ) -> None:
        try:
            run_setup(
                editor,
                repo_path,
                indexing_mode,
                index_exists=index_exists,
                index_prs=index_prs,
                add_to_claude_md=add_to_claude_md,
                embeddings_config=embeddings_config,
            )
        except Exception as e:
            print(f"\n{PRIMARY}Error: Setup failed: {e}{RESET}")
            sys.exit(1)

    # Check if we're in a supported project
    repo_path = Path.cwd() if repo_path is None else Path(repo_path).resolve()
    try:
        check_elixir_project(repo_path)
    except UnsupportedProjectError as e:
        print(f"{PRIMARY}Error: {e}{RESET}")
        print()
        print(
            "Please run cicada from the root of a supported project (Python, Elixir, or TypeScript)."
        )
        sys.exit(1)

    # Display ASCII art
    print(generate_gradient_ascii_art())

    # Step 1: Choose editor
    print(f"{PRIMARY}{'=' * 70}{RESET}")
    print(f"{SELECTED}🦗 Welcome to CICADA - Code Intelligence{RESET}")
    print(f"{PRIMARY}{'=' * 70}{RESET}")
    print()
    print(f"Let's set up Cicada for your editor and project.{RESET}")
    print()
    print(f"{BOLD}Choose your editor{RESET}")

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
        indexing_mode = existing_config
        _run_setup_with_error_handling(editor, repo_path, indexing_mode, index_exists=True)
        return

    indexing_mode, index_prs, add_to_claude_md_flag, embeddings_config = show_first_time_setup(
        show_welcome=False
    )

    print(f"{BOLD}Running setup...{RESET}")
    print()

    _run_setup_with_error_handling(
        editor,
        repo_path,
        indexing_mode,
        index_prs=index_prs,
        add_to_claude_md=add_to_claude_md_flag,
        embeddings_config=embeddings_config,
    )
