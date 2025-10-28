"""Interactive first-time setup menu for cicada."""

from simple_term_menu import TerminalMenu

from cicada.ascii_art import generate_gradient_ascii_art
from cicada.colors import SELECTED, PRIMARY, GREY, RESET, BOLD, GREEN


def show_first_time_setup() -> tuple[str, str]:
    """
    Display an interactive first-time setup menu for cicada.

    Returns:
        tuple[str, str]: The selected extraction method and model tier
                        e.g., ('spacy', 'regular') or ('bert', 'fast')
    """
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

    method_menu = TerminalMenu(
        method_items,
        title="",
        menu_cursor="» ",
        menu_cursor_style=("fg_yellow", "bold"),
        menu_highlight_style=("fg_yellow", "bold"),
        cycle_cursor=True,
        clear_screen=False,
    )

    try:
        method_index = method_menu.show()
    except KeyboardInterrupt:
        print()
        print(f"Setup cancelled. Exiting...")
        import sys

        sys.exit(1)

    if method_index is None:
        print()
        print(f"Setup cancelled. Exiting...")
        import sys

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
        print(
            f'{PRIMARY}   Example: "We use Kubernetes for container orchestration"{RESET}'
        )
        print(
            f'{PRIMARY}   Output: "Kubernetes", "deployment", "microservices", "DevOps"{RESET}'
        )
        print()
        tier_items = [
            "Fast (80MB, ~1s) - Recommended for bigger projects",
            "Regular [recommended] (133MB, ~1.4s) - Better semantic understanding",
            "Max (420MB, ~6.5s) - Highest quality embeddings",
        ]
        print(f"{SELECTED}Step 2/2: Choose model tier\n")

    tier_menu = TerminalMenu(
        tier_items,
        title="",
        menu_cursor="» ",
        menu_cursor_style=("fg_yellow", "bold"),
        menu_highlight_style=("fg_yellow", "bold"),
        cycle_cursor=True,
        clear_screen=False,
    )

    try:
        tier_index = tier_menu.show()
    except KeyboardInterrupt:
        print()
        print(f"{SELECTED}Setup cancelled. Exiting...{RESET}")
        import sys

        sys.exit(1)

    if tier_index is None:
        print()
        print(f"{SELECTED}Setup cancelled. Exiting...{RESET}")
        import sys

        sys.exit(1)

    tier_map = {0: "fast", 1: "regular", 2: "max"}
    tier = tier_map[tier_index]

    print()
    print(f"{GREEN}✓{RESET} Selected: {method.upper()} - {tier.capitalize()} model")
    print()

    return (method, tier)
