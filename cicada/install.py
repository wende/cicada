#!/usr/bin/env python
"""
Cicada One-Command Setup Script.

Downloads the tool, indexes the repository, and creates .mcp.json configuration.
"""

import argparse
import importlib
import json
import subprocess
import sys
from pathlib import Path

from cicada.colors import CYAN, BLUE, GREEN, YELLOW, RED, GRAY, BOLD, DIM, RESET


def run_command(cmd, cwd=None, check=True, capture_output=True):
    """Run a shell command and return the result.

    Args:
        cmd: Either a string (for shell=True) or list of arguments (for shell=False).
             List form is preferred for security.
        cwd: Working directory for the command
        check: Whether to raise exception on non-zero exit
        capture_output: Whether to capture stdout/stderr
    """
    try:
        # Prefer list form (shell=False) for security
        use_shell = isinstance(cmd, str)
        if capture_output:
            result = subprocess.run(
                cmd,
                shell=use_shell,
                check=check,
                cwd=cwd,
                capture_output=True,
                text=True,
            )
        else:
            result = subprocess.run(cmd, shell=use_shell, check=check, cwd=cwd)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {cmd}", file=sys.stderr)
        if capture_output and hasattr(e, "stderr"):
            print(f"Error: {e.stderr}", file=sys.stderr)
        raise


def check_python():
    """Check if Python 3.10+ is available."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print(
            f"Error: Python 3.10+ required. Current: {version.major}.{version.minor}",
            file=sys.stderr,
        )
        sys.exit(1)
    print(f"{GREEN}✓{RESET} Python {version.major}.{version.minor} detected")


def install_cicada(target_dir, github_url=None):
    """
    Install cicada from GitHub or use existing installation.

    Args:
        target_dir: Directory where cicada will be installed
        github_url: GitHub URL to clone from (optional)

    Returns:
        Tuple of (Path to the cicada installation, bool indicating if already installed)
    """
    target_path = Path(target_dir).resolve()

    # Check if we're running from an installed package (pip/uvx)
    # In this case, the cicada module is already available
    try:
        mcp_server_module = importlib.import_module("cicada.mcp_server")
        # Get the site-packages or installation directory
        if mcp_server_module.__file__ is None:
            raise ImportError("Could not determine module path")
        package_path = Path(mcp_server_module.__file__).parent.parent
        print(f"{GREEN}✓{RESET} Using installed cicada package")
        return package_path, True  # Already installed
    except ImportError:
        pass

    # If we're already in the cicada directory, use it
    current_dir = Path.cwd()
    if (current_dir / "cicada" / "mcp_server.py").exists():
        print(f"{GREEN}✓{RESET} Using existing cicada installation at {current_dir}")
        return current_dir, False

    # Check if target directory already has cicada
    if (target_path / "cicada" / "mcp_server.py").exists():
        print(f"{GREEN}✓{RESET} Using existing cicada installation at {target_path}")
        return target_path, False

    # Download from GitHub
    if github_url:
        print(f"{BLUE}Downloading cicada from {github_url}...{RESET}")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        _ = run_command(f"git clone {github_url} {target_path}")
        print(f"{GREEN}✓{RESET} Downloaded cicada to {target_path}")
    else:
        print("Error: cicada not found and no GitHub URL provided", file=sys.stderr)
        print(
            "Hint: Run with --github-url https://github.com/wende/cicada.git",
            file=sys.stderr,
        )
        sys.exit(1)

    return target_path, False


def check_uv_available():
    """Check if uv is available on the system."""
    try:
        result = run_command("uv --version", check=False)
        return result.returncode == 0
    except Exception:
        return False


def install_dependencies_uv(cicada_dir):
    """Install Python dependencies using uv (fast!)."""
    print(f"{BLUE}Installing dependencies with uv...{RESET}")

    # Use uv to sync dependencies
    # uv will automatically create a venv and install everything
    _ = run_command(f"uv sync", cwd=cicada_dir)

    # Find the python binary uv created
    venv_path = cicada_dir / ".venv"
    python_bin = venv_path / "bin" / "python"

    if not python_bin.exists():
        # Try alternative venv location
        venv_path = cicada_dir / "venv"
        python_bin = venv_path / "bin" / "python"

    print(f"{GREEN}✓{RESET} Dependencies installed with uv")
    return python_bin


def install_dependencies_pip(cicada_dir):
    """Install Python dependencies using traditional pip (legacy method)."""
    print(f"{BLUE}Installing dependencies with pip (legacy method)...{RESET}")

    # Check if venv exists
    venv_path = cicada_dir / "venv"
    python_bin = venv_path / "bin" / "python"

    if not venv_path.exists():
        print(f"{BLUE}Creating virtual environment...{RESET}")
        _ = run_command(f"python -m venv {venv_path}")

    # Install dependencies
    requirements_file = cicada_dir / "requirements.txt"
    if requirements_file.exists():
        _ = run_command(f"{python_bin} -m pip install -r {requirements_file}")

    # Install package in editable mode
    _ = run_command(f"{python_bin} -m pip install -e {cicada_dir}")

    print(f"{GREEN}✓{RESET} Dependencies installed with pip")
    return python_bin


def install_dependencies(cicada_dir, use_uv=None):
    """
    Install Python dependencies for cicada.

    Args:
        cicada_dir: Directory where cicada is installed
        use_uv: If True, use uv; if False, use pip; if None, auto-detect

    Returns:
        Path to python binary
    """
    # Auto-detect uv if not specified (uv is preferred)
    if use_uv is None:
        use_uv = check_uv_available()
        if use_uv:
            print(
                f"{GREEN}✓{RESET} Detected uv - using it for faster installation (recommended)"
            )
        else:
            print(f"{YELLOW}⚠{RESET} uv not available - falling back to pip (slower)")

    if use_uv:
        return install_dependencies_uv(cicada_dir)
    else:
        return install_dependencies_pip(cicada_dir)


def index_repository(
    cicada_dir,
    python_bin,
    repo_path,
    fetch_pr_info=False,
    keyword_method="spacy",
    model_tier="regular",
):
    """Index the Elixir repository."""
    repo_path = Path(repo_path).resolve()
    try:
        rel_path = repo_path.relative_to(Path.cwd())
    except ValueError:
        rel_path = repo_path
    output_path = repo_path / ".cicada" / "index.json"

    # Check if .cicada directory exists (first run detection)
    is_first_run = not output_path.parent.exists()

    # Create .cicada directory
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # On first run, add .cicada/ to .gitignore if it exists
    if is_first_run:
        from cicada.utils.path_utils import ensure_gitignore_has_cicada

        if ensure_gitignore_has_cicada(repo_path):
            print(f"{GREEN}✓{RESET} Added .cicada/ to .gitignore")

    # Print indexing message without newline
    try:
        rel_repo_path = repo_path.relative_to(Path.cwd())
    except ValueError:
        rel_repo_path = repo_path
    print(f"  - Indexing repository at: {rel_repo_path}{RESET}")

    # Run indexer
    indexer_script = cicada_dir / "cicada" / "indexer.py"

    # Build command as list to prevent command injection
    cmd = [
        str(python_bin),
        str(indexer_script),
        str(repo_path),
        "--output",
        str(output_path),
        "--extract-keywords",
    ]

    if fetch_pr_info:
        cmd.append("--pr-info")

    # Add keyword extraction options
    if keyword_method == "bert":
        cmd.append("--rag")
    cmd.extend(["--model-tier", model_tier])

    # Run without capturing output so users can see download progress
    result = run_command(cmd, capture_output=False)

    try:
        rel_path = output_path.relative_to(Path.cwd())
    except ValueError:
        rel_path = output_path
    print(f"{GREEN}✓{RESET} Repository indexed at {rel_path}")
    return output_path


def detect_installation_method():
    """
    Detect how cicada is installed and return appropriate MCP command config.

    Returns:
        tuple: (command, args, cwd, description)
    """
    import shutil
    import sys

    script_path = Path(sys.argv[0]).resolve()
    script_path_str = str(script_path)

    # Check if running from a uvx cache/temporary directory
    # uvx uses temporary environments, so we should NOT use cicada-server
    # even if it's temporarily in PATH
    uvx_indicators = [
        "/.cache/uv/",
        "/tmp/",
        "tmpdir",
        "temp",
        # On some systems uvx might use other temp locations
    ]

    is_uvx = any(indicator in script_path_str for indicator in uvx_indicators)

    if is_uvx:
        # Running from uvx - use Python fallback since cicada-server won't be available later
        python_bin = sys.executable
        cicada_dir = Path(__file__).parent.parent.resolve()
        return (
            str(python_bin),
            [str(cicada_dir / "cicada" / "mcp_server.py")],
            str(cicada_dir),
            "uvx (one-time run, using Python paths)",
        )

    # Check if running from a uv tools directory (permanent install)
    if (
        ".local/share/uv/tools" in script_path_str
        or ".local/bin/cicada-" in script_path_str
    ):
        # Installed via uv tool install
        return (
            "cicada-server",
            [],
            None,
            "uv tool install (ensure ~/.local/bin is in PATH)",
        )

    # Check if cicada-server is in PATH (from uv tool install)
    if shutil.which("cicada-server"):
        return ("cicada-server", [], None, "uv tool install (permanent, fast)")

    # Fall back to python with full path
    python_bin = sys.executable
    cicada_dir = Path(__file__).parent.parent.resolve()

    return (
        str(python_bin),
        [str(cicada_dir / "cicada" / "mcp_server.py")],
        str(cicada_dir),
        "direct python (tip: install with 'uv tool install .' for faster startup)",
    )


def check_tools_in_path():
    """Check if cicada tools are in PATH."""
    import shutil

    tools = ["cicada-server", "cicada"]
    visible_tools = [tool for tool in tools if shutil.which(tool)]

    if len(visible_tools) == len(tools):
        return "all_visible"
    elif visible_tools:
        return "partial"
    else:
        return "none"


def create_mcp_config(repo_path, _cicada_dir, _python_bin):
    """Create or update .mcp.json configuration file with intelligent command detection."""
    print(f"{GREEN}✓{RESET} Creating .mcp.json configuration...")

    repo_path = Path(repo_path).resolve()
    mcp_config_path = repo_path / ".mcp.json"

    # Load existing config if present, otherwise create new one
    if mcp_config_path.exists():
        try:
            with open(mcp_config_path, "r") as f:
                config = json.load(f)
            print(f"{GREEN}✓{RESET} Found existing .mcp.json, will merge configuration")
        except (json.JSONDecodeError, IOError) as e:
            print(
                f"{YELLOW}Warning:{RESET} Could not read existing .mcp.json ({e}), creating new one"
            )
            config = {}
    else:
        config = {}

    # Ensure mcpServers section exists
    if "mcpServers" not in config:
        config["mcpServers"] = {}

    # Detect installation method and create appropriate config
    command, args, cwd, description = detect_installation_method()

    # Check if tools are visible in PATH
    tools_status = check_tools_in_path()
    if tools_status == "all_visible":
        print(f"{GREEN}✓{RESET} Installation: {description}")
    elif tools_status == "partial":
        print(f"{YELLOW}⚠{RESET}  Installation: {description}")
        print(
            f"{GRAY}   Some tools not found in PATH - add ~/.local/bin to PATH{RESET}"
        )
    else:
        print(f"{YELLOW}⚠{RESET}  Installation: {description}")
        print(f"{GRAY}   Tools not found in PATH - add ~/.local/bin to PATH{RESET}")

    # Build MCP server configuration
    from typing import Any

    server_config: dict[str, Any] = {"command": command}

    if args:
        server_config["args"] = args

    if cwd:
        server_config["cwd"] = cwd

    # Add environment variable for repo path
    server_config["env"] = {"CICADA_REPO_PATH": str(repo_path)}

    # Add or update cicada configuration
    config["mcpServers"]["cicada"] = server_config

    # Write config file
    with open(mcp_config_path, "w") as f:
        json.dump(config, f, indent=2)

    try:
        rel_path = mcp_config_path.relative_to(Path.cwd())
    except ValueError:
        rel_path = mcp_config_path
    print(f"{GREEN}✓{RESET} MCP configuration updated at {rel_path}")

    # Show what was configured
    if command != "cicada-server":
        print(f"{CYAN}ℹ{RESET}  Using Python: {command}")

    return mcp_config_path


def create_config_yaml(
    _cicada_dir,
    repo_path,
    index_path,
    keyword_method="spacy",
    model_tier="regular",
    version=None,
):
    """Create or update config.yaml in repository's .cicada directory."""
    repo_path = Path(repo_path).resolve()
    config_path = repo_path / ".cicada" / "config.yaml"

    # Ensure .cicada directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Get current version
    if version is None:
        from cicada import __version__

        version = __version__

    config_content = f"""version: {version}

repository:
  path: {repo_path}

storage:
  index_path: {index_path}

keywords:
  method: {keyword_method}
  model: {model_tier}
"""

    with open(config_path, "w") as f:
        _ = f.write(config_content)

    try:
        rel_path = config_path.relative_to(Path.cwd())
    except ValueError:
        rel_path = config_path
    print(f"{GREEN}✓{RESET} Config file created at {rel_path}")


def create_gitattributes(repo_path):
    """Create or update .gitattributes in repository root for Elixir function tracking."""
    repo_path = Path(repo_path).resolve()
    gitattributes_path = repo_path / ".gitattributes"

    elixir_patterns = ["*.ex diff=elixir", "*.exs diff=elixir"]

    # Read existing .gitattributes if present
    existing_lines = []
    if gitattributes_path.exists():
        with open(gitattributes_path, "r") as f:
            existing_lines = [line.rstrip() for line in f.readlines()]

    # Check if elixir patterns already exist
    has_elixir = any(pattern in existing_lines for pattern in elixir_patterns)

    if has_elixir:
        print(f"{GREEN}✓{RESET} .gitattributes already has Elixir patterns")
        return gitattributes_path

    # Add elixir patterns
    with open(gitattributes_path, "a") as f:
        if existing_lines and not existing_lines[-1] == "":
            _ = f.write("\n")  # Add newline if file doesn't end with one

        _ = f.write("# Elixir function tracking for git log -L\n")
        for pattern in elixir_patterns:
            _ = f.write(f"{pattern}\n")

    print(f"{GREEN}✓{RESET} Added Elixir patterns to {gitattributes_path}")
    return gitattributes_path


def update_claude_md(repo_path):
    """Update CLAUDE.md with instructions to use cicada-mcp for Elixir codebase searches."""
    repo_path = Path(repo_path).resolve()
    claude_md_path = repo_path / "CLAUDE.md"

    # Fail silently if CLAUDE.md doesn't exist
    if not claude_md_path.exists():
        return

    instruction_content = """<cicada>
  **ALWAYS use cicada-mcp tools for Elixir code searches. NEVER use Grep/Find for these tasks.**

  ### Use cicada tools for:
  - Finding function definitions: `mcp__cicada__search_function`
  - Finding module APIs: `mcp__cicada__search_module`
  - Finding module usage: `mcp__cicada__search_module_usage`
  - Finding who wrote code: `mcp__cicada__find_pr_for_line`
  - Finding file history: `mcp__cicada__get_commit_history`

  ### DO NOT use Grep for:
  - ❌ Searching for function names
  - ❌ Finding where functions are called
  - ❌ Exploring module structure

  ### Only use Grep for:
  - ✓ Non-code files (markdown, JSON, config)
  - ✓ String literal searches
  - ✓ Pattern matching in comments
</cicada>
"""

    try:
        # Read existing content
        with open(claude_md_path, "r") as f:
            content = f.read()

        # Check if instruction already exists
        if "cicada-mcp" in content or "use the cicada-mcp MCP server" in content:
            print(f"{GREEN}✓{RESET} CLAUDE.md already mentions cicada-mcp")
            return

        # Append the instruction
        with open(claude_md_path, "a") as f:
            # Add newline if file doesn't end with one
            if content and not content.endswith("\n"):
                _ = f.write("\n")

            _ = f.write("\n")
            _ = f.write(instruction_content)

        print(f"{GREEN}✓{RESET} Updated CLAUDE.md with cicada-mcp usage instructions")
    except Exception:
        # Fail silently on any errors
        pass


def is_gitignored(repo_path, file_pattern):
    """
    Check if a file pattern is in .gitignore.

    Args:
        repo_path: Path to repository root
        file_pattern: Pattern to check (e.g., '.cicada/', '.mcp.json')

    Returns:
        bool: True if pattern is in .gitignore, False otherwise
    """
    repo_path = Path(repo_path).resolve()
    gitignore_path = repo_path / ".gitignore"

    if not gitignore_path.exists():
        return False

    try:
        with open(gitignore_path, "r") as f:
            content = f.read()
        # Simple check - look for the pattern in the file
        # This handles .cicada/, .cicada, /.cicada/, etc.
        base_pattern = file_pattern.rstrip("/").lstrip("/")
        return base_pattern in content
    except (IOError, OSError):
        return False


def print_setup_summary(repo_path, _index_path):
    """
    Print a summary of created files and their gitignore status.

    Args:
        repo_path: Path to repository root
        index_path: Path to the created index file
    """
    repo_path = Path(repo_path).resolve()

    print()
    print(f"Files created/modified:")
    print()

    # List of files to check
    files_created = [
        (".cicada/", "Cicada index directory"),
        (".mcp.json", "MCP server configuration"),
        (".gitattributes", "Git function tracking configuration"),
        ("CLAUDE.md", "Updated with cicada-mcp instructions"),
    ]

    # Check each file
    for file_pattern, description in files_created:
        is_ignored = is_gitignored(repo_path, file_pattern)
        file_path = repo_path / file_pattern.rstrip("/")

        if file_path.exists():
            # CLAUDE.md doesn't need a status - user decides whether to commit it
            if file_pattern == "CLAUDE.md":
                print(f"  {YELLOW}{file_pattern:20}{RESET} {description:35}")
            else:
                # .gitattributes is always green (user shouldn't gitignore it)
                if file_pattern == ".gitattributes":
                    status = f"{GREEN}✓ should be committed{RESET}"
                else:
                    status = (
                        f"{GREEN}✓ gitignored{RESET}"
                        if is_ignored
                        else f"{RED}✗ not gitignored{RESET}"
                    )
                print(f"  {YELLOW}{file_pattern:20}{RESET} {description:35} {status}")

    print()

    # Check what needs to be gitignored
    needs_gitignore = []
    if not is_gitignored(repo_path, ".cicada/"):
        needs_gitignore.append(".cicada/")
    if not is_gitignored(repo_path, ".mcp.json"):
        needs_gitignore.append(".mcp.json")

    # Show warnings if files are not gitignored
    if needs_gitignore:
        print(f"{RED}⚠️{RESET}  Warning: The following should be in .gitignore:")
        for item in needs_gitignore:
            reason = (
                "build artifacts and cache"
                if item == ".cicada/"
                else "local configuration"
            )
            print(f"{RED}   • {item:12} ({reason}){RESET}")
        print()
        print(f"{YELLOW}Add them to .gitignore with this command:{RESET}")
        items_with_newlines = "\\n".join(needs_gitignore)
        print(f"  printf '\\n{items_with_newlines}\\n' >> .gitignore")
        print()


def check_config_version(repo_path):
    """
    Check if config.yaml exists and compare its version with current version.

    Returns:
        tuple: (config_exists, needs_upgrade, old_version)
            - config_exists: True if config.yaml exists
            - needs_upgrade: True if config version < current version
            - old_version: The version string from config, or None
    """
    import yaml
    from cicada import __version__ as current_version

    repo_path = Path(repo_path).resolve()
    config_path = repo_path / ".cicada" / "config.yaml"

    if not config_path.exists():
        return False, False, None

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        old_version = config.get("version") if config else None

        if old_version is None:
            # No version field - old config format
            return True, True, "unknown"

        # Compare versions (simple string comparison works for semver)
        needs_upgrade = old_version < current_version
        return True, needs_upgrade, old_version

    except Exception:
        # If we can't read/parse config, treat as needs upgrade
        return True, True, "unknown"


def main():
    """Main entry point for the setup script."""
    parser = argparse.ArgumentParser(
        description="One-command setup for Cicada MCP server",
        epilog="Example: python setup.py /path/to/elixir/project",
    )
    _ = parser.add_argument(
        "repo",
        nargs="?",
        default=".",
        help="Path to the Elixir repository to index (default: current directory)",
    )
    _ = parser.add_argument(
        "--cicada-dir",
        help="Directory where cicada is or will be installed (default: ~/.cicada)",
    )
    _ = parser.add_argument(
        "--github-url",
        help="GitHub URL to clone cicada from (if not already installed)",
    )
    _ = parser.add_argument(
        "--pr-info",
        action="store_true",
        help="Fetch PR information during indexing (requires GitHub CLI and may be slow)",
    )
    _ = parser.add_argument(
        "--skip-install",
        action="store_true",
        help="Skip installing dependencies (use if already installed)",
    )
    _ = parser.add_argument(
        "--use-uv",
        action="store_true",
        help="Force use of uv for dependency installation (faster)",
    )
    _ = parser.add_argument(
        "--use-pip",
        action="store_true",
        help="Force use of pip for dependency installation (traditional)",
    )
    _ = parser.add_argument(
        "--init",
        action="store_true",
        help="Force reconfiguration with interactive setup menu",
    )

    # Keyword extraction method selection
    _ = parser.add_argument(
        "--rag",
        action="store_true",
        help="Use KeyBERT (semantic embeddings) instead of spaCy (grammar-based). "
        "Provides better semantic understanding but slower initialization.",
    )

    # Create mutually exclusive group for model tier selection
    model_group = parser.add_mutually_exclusive_group()
    _ = model_group.add_argument(
        "--fast",
        action="store_const",
        const="fast",
        dest="model_flag",
        help="Fast model tier (spaCy: 12MB, KeyBERT: 80MB) - recommended",
    )
    _ = model_group.add_argument(
        "--regular",
        action="store_const",
        const="regular",
        dest="model_flag",
        help="Regular model tier (spaCy: 40MB, KeyBERT: 133MB) - balanced",
    )
    _ = model_group.add_argument(
        "--max",
        action="store_const",
        const="max",
        dest="model_flag",
        help="Max model tier (spaCy: 560MB, KeyBERT: 420MB) - highest quality",
    )

    args = parser.parse_args()

    # Check version and determine if we need to show interactive setup
    repo_path = Path(args.repo).resolve()
    config_exists, needs_upgrade, old_version = check_config_version(repo_path)

    # Determine if we should show interactive menu
    # Only show interactive menu if:
    # 1. --init flag is provided, OR
    # 2. First-time run (config doesn't exist) AND no CLI flags provided
    cli_flags_provided = args.model_flag or args.rag

    show_interactive = False
    if args.init:
        # --init flag forces reconfiguration only if no CLI flags provided
        show_interactive = not cli_flags_provided
    elif not config_exists and not cli_flags_provided:
        # First-time run with no CLI flags - show interactive menu
        show_interactive = True
    elif needs_upgrade and not cli_flags_provided:
        # Version upgrade detected and no model flags provided - ask user
        from cicada import __version__ as current_version

        print()
        print(f"{CYAN}{'=' * 70}{RESET}")
        print(f"{CYAN}🔄 Cicada version upgrade detected!{RESET}")
        print(f"{CYAN}   Installed version: {old_version}{RESET}")
        print(f"{CYAN}   Current version:   {current_version}{RESET}")
        print(f"{CYAN}{'=' * 70}{RESET}")
        print()
        response = (
            input("Would you like to reconfigure cicada? [Y/n]: ").strip().lower()
        )
        if response in ["", "y", "yes"]:
            show_interactive = True

    # Determine keyword extraction method and model tier
    # Priority: CLI flags > interactive menu > default (spacy, regular)
    if show_interactive:
        # First-time run or user confirmed reconfiguration - show interactive menu
        from cicada.interactive_setup import show_first_time_setup

        keyword_method, model_tier = show_first_time_setup()
    else:
        # Determine from CLI flags or use defaults
        keyword_method = "bert" if args.rag else "spacy"
        model_tier = args.model_flag if args.model_flag else "regular"

    # Store the selected configuration back in args for consistency
    args.keyword_method = keyword_method
    args.model_tier = model_tier

    # Check Python version
    check_python()

    # Determine cicada directory
    if args.cicada_dir:
        cicada_dir = Path(args.cicada_dir).resolve()
    else:
        # Use current directory if we're in cicada, otherwise use ~/.cicada
        current_dir = Path.cwd()
        if (current_dir / "cicada" / "mcp_server.py").exists():
            cicada_dir = current_dir
        else:
            cicada_dir = Path.home() / ".cicada"

    # Install or locate cicada
    cicada_dir, is_already_installed = install_cicada(cicada_dir, args.github_url)

    # Install dependencies (skip if already installed via pip/uvx)
    if is_already_installed:
        # Package already installed, use current Python
        python_bin = sys.executable
        print(f"{GREEN}✓{RESET} Using Python from installed package: {python_bin}")
    elif not args.skip_install:
        # Determine which package manager to use
        use_uv = None
        if args.use_uv:
            use_uv = True
        elif args.use_pip:
            use_uv = False
        # Otherwise use_uv=None for auto-detect

        python_bin = install_dependencies(cicada_dir, use_uv=use_uv)
    else:
        # Try to find existing python binary
        python_bin = cicada_dir / ".venv" / "bin" / "python"
        if not python_bin.exists():
            python_bin = cicada_dir / "venv" / "bin" / "python"
        if not python_bin.exists():
            python_bin = sys.executable
        print(f"{GREEN}✓{RESET} Skipping dependency installation, using {python_bin}")

    # Index repository
    index_path = index_repository(
        cicada_dir,
        python_bin,
        args.repo,
        args.pr_info,
        args.keyword_method,
        args.model_tier,
    )

    # Create config.yaml
    create_config_yaml(
        cicada_dir, args.repo, index_path, args.keyword_method, args.model_tier
    )

    # Create .gitattributes for Elixir function tracking
    _ = create_gitattributes(args.repo)

    # Update CLAUDE.md with cicada-mcp usage instructions
    update_claude_md(args.repo)

    # Create .mcp.json
    _ = create_mcp_config(args.repo, cicada_dir, python_bin)

    # Print summary of created files and gitignore status
    print_setup_summary(args.repo, index_path)

    print(f"{CYAN}{'=' * 60}{RESET}")
    print(f"{YELLOW}✓ Setup Complete!{RESET}")
    print(f"{CYAN}{'=' * 60}{RESET}")
    print()
    print(f"Next steps:")
    print(f"1. Restart Claude Code")
    print()
    print(f"2. Try asking Claude Code:")
    print(f"   - 'Where is [Module] used?'")
    print(f"   - 'Show me the functions in [ModuleName]")
    print()


if __name__ == "__main__":
    main()
