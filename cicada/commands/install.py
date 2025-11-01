"""
Install command handler - Interactive setup mode.

This module implements the `cicada install` / `cicada-mcp install` command,
which provides interactive setup with editor and model selection.
"""

import sys
from argparse import Namespace
from pathlib import Path

from cicada.interactive_setup import show_first_time_setup
from cicada.setup import EditorType, setup
from cicada.utils import get_config_path, get_index_path


def handle_install(args: Namespace) -> None:
    """
    Handle the install subcommand.

    Behavior:
    - INTERACTIVE: shows prompts and menus
    - Can skip prompts with flags (--claude, --cursor, --vs, --nlp, --rag)
    - Creates editor config and indexes repository

    Args:
        args: Parsed command line arguments with attributes:
            - repo: Optional repository path
            - claude: Skip editor selection, use Claude
            - cursor: Skip editor selection, use Cursor
            - vs: Skip editor selection, use VS Code
            - nlp: Skip model selection, use Lemminflect
            - rag: Skip model selection, use BERT
            - fast: Use fast tier
            - max: Use max tier
    """
    # Determine repository path
    repo_path = Path(args.repo).resolve() if args.repo else Path.cwd().resolve()

    # Validate it's an Elixir project
    if not (repo_path / "mix.exs").exists():
        print(f"Error: {repo_path} does not appear to be an Elixir project", file=sys.stderr)
        print("(mix.exs not found)", file=sys.stderr)
        sys.exit(1)

    # Validate flag combinations
    if (args.fast or args.max) and not args.rag:
        print("Error: --fast or --max requires --rag", file=sys.stderr)
        sys.exit(1)

    if args.nlp and args.rag:
        print("Error: Cannot specify both --nlp and --rag", file=sys.stderr)
        sys.exit(1)

    # Count editor flags
    editor_flags = [args.claude, args.cursor, args.vs]
    editor_count = sum(editor_flags)

    if editor_count > 1:
        print("Error: Can only specify one editor flag for install command", file=sys.stderr)
        sys.exit(1)

    # Determine editor from flags
    editor: EditorType | None = None
    if args.claude:
        editor = "claude"
    elif args.cursor:
        editor = "cursor"
    elif args.vs:
        editor = "vs"

    # Determine keyword method and tier from flags
    keyword_method = None
    keyword_tier = None

    if args.nlp:
        keyword_method = "lemminflect"
        keyword_tier = "regular"
    elif args.rag:
        keyword_method = "bert"
        if args.fast:
            keyword_tier = "fast"
        elif args.max:
            keyword_tier = "max"
        else:
            keyword_tier = "regular"

    # Check if index already exists
    config_path = get_config_path(repo_path)
    index_path = get_index_path(repo_path)
    index_exists = config_path.exists() and index_path.exists()

    # If no flags provided, use full interactive setup
    if editor is None and keyword_method is None:
        from cicada.interactive_setup import show_full_interactive_setup

        show_full_interactive_setup()
        return

    # If only model flags provided (no editor), prompt for editor
    if editor is None:
        # Show editor selection menu
        from simple_term_menu import TerminalMenu

        print("Select editor to configure:")
        print()
        editor_options = [
            "Claude Code (Claude AI assistant)",
            "Cursor (AI-powered code editor)",
            "VS Code (Visual Studio Code)",
        ]
        editor_menu = TerminalMenu(editor_options, title="Choose your editor:")
        menu_idx = editor_menu.show()

        if menu_idx is None:
            print("\nSetup cancelled.")
            sys.exit(0)

        # Map menu index to editor type (menu_idx is guaranteed to be int here)
        assert isinstance(menu_idx, int), "menu_idx must be an integer"
        editor_map: tuple[EditorType, EditorType, EditorType] = ("claude", "cursor", "vs")
        editor = editor_map[menu_idx]

    # If only editor flag provided (no model), prompt for model (unless index exists)
    if keyword_method is None and not index_exists:
        keyword_method, keyword_tier = show_first_time_setup()

    # If index exists but no model flags, use existing settings
    if keyword_method is None and index_exists:
        import yaml

        try:
            with open(config_path) as f:
                existing_config = yaml.safe_load(f)
                keyword_method = existing_config.get("keyword_extraction", {}).get(
                    "method", "lemminflect"
                )
                keyword_tier = existing_config.get("keyword_extraction", {}).get("tier", "regular")
        except Exception:
            # If we can't read config, use defaults
            keyword_method = "lemminflect"
            keyword_tier = "regular"

    # Run setup
    try:
        setup(
            editor,
            repo_path,
            keyword_method=keyword_method,
            keyword_tier=keyword_tier,
            index_exists=index_exists,
        )
    except Exception as e:
        print(f"\nError: Setup failed: {e}", file=sys.stderr)
        sys.exit(1)
