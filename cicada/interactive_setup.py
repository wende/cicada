"""Interactive first-time setup menu for cicada."""

import sys

try:
    from simple_term_menu import TerminalMenu

    has_terminal_menu = True
except ImportError:
    TerminalMenu = None  # type: ignore
    has_terminal_menu = False

from cicada.ascii_art import generate_gradient_ascii_art
from cicada.colors import BOLD, GREEN, GREY, PRIMARY, RESET, SELECTED


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
    print("1. spaCy - Grammar-based keyword extraction (fast, proven)")
    print("2. KeyBERT - Semantic keyword extraction (AI embeddings)")
    print()

    while True:
        try:
            method_choice = input("Enter your choice (1 or 2) [default: 1]: ").strip()
            if not method_choice:
                method_choice = "1"
            if method_choice in ("1", "2"):
                method = "spacy" if method_choice == "1" else "bert"
                break
            print("Invalid choice. Please enter 1 or 2.")
        except (KeyboardInterrupt, EOFError):
            print()
            print("Setup cancelled. Exiting...")
            sys.exit(1)

    print()
    if method == "spacy":
        print(f"{BOLD}  What is spaCy?{RESET}")
        print(f"   spaCy finds keywords using grammar rules + word importance{RESET}")
        print()
        print("1. Fast (12MB, ~0.5s) - Recommended for most projects")
        print("2. Regular (40MB, ~0.8s) - Balanced accuracy and speed [recommended]")
        print("3. Max (560MB, ~2s) - Highest accuracy, slower")
    else:
        print(f"{SELECTED}  What is KeyBERT?{RESET}")
        print(
            f"{PRIMARY}   KeyBERT uses AI embeddings to find semantically similar keywords{RESET}"
        )
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
    print(f"{GREEN}✓{RESET} Selected: {method.upper()} - {tier.capitalize()} model")
    print()

    return (method, tier)


def show_first_time_setup() -> tuple[str, str]:
    """
    Display an interactive first-time setup menu for cicada.

    Falls back to text-based input if the terminal doesn't support simple-term-menu.

    Returns:
        tuple[str, str]: The selected extraction method and model tier
                        e.g., ('spacy', 'regular') or ('bert', 'fast')
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
        "spaCy - Grammar-based keyword extraction (fast, proven)",
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

    method = "spacy" if method_index == 0 else "bert"

    # Step 2: Choose model tier
    print()
    if method == "spacy":
        print(f"{BOLD}  What is spaCy?{RESET}")
        print(f"   spaCy finds keywords using grammar rules + word importance{RESET}")
        print(f'   Example: "We use Kubernetes for container orchestration"{RESET}')
        print(f'   Output: "Kubernetes", "container", "orchestration"{RESET}')
        print()
        tier_items = [
            "Fast (12MB, ~0.5s) - Recommended for most projects",
            "Regular [recommended] (40MB, ~0.8s) - Balanced accuracy and speed",
            "Max (560MB, ~2s) - Highest accuracy, slower",
        ]
    else:
        print(f"{SELECTED}  What is KeyBERT?{RESET}")
        print(
            f"{PRIMARY}   KeyBERT uses AI embeddings to find semantically similar keywords{RESET}"
        )
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
    print(f"{GREEN}✓{RESET} Selected: {method.upper()} - {tier.capitalize()} model")
    print()

    return (method, tier)
