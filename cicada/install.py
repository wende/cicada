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


def run_command(cmd, cwd=None, check=True):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(
            cmd, shell=True, check=check, cwd=cwd, capture_output=True, text=True
        )
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {cmd}", file=sys.stderr)
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
    print(f"✓ Python {version.major}.{version.minor} detected")


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
        package_path = Path(mcp_server_module.__file__).parent.parent
        print(f"✓ Using installed cicada package")
        return package_path, True  # Already installed
    except ImportError:
        pass

    # If we're already in the cicada directory, use it
    current_dir = Path.cwd()
    if (current_dir / "cicada" / "mcp_server.py").exists():
        print(f"✓ Using existing cicada installation at {current_dir}")
        return current_dir, False

    # Check if target directory already has cicada
    if (target_path / "cicada" / "mcp_server.py").exists():
        print(f"✓ Using existing cicada installation at {target_path}")
        return target_path, False

    # Download from GitHub
    if github_url:
        print(f"Downloading cicada from {github_url}...")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        _ = run_command(f"git clone {github_url} {target_path}")
        print(f"✓ Downloaded cicada to {target_path}")
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
    print("Installing dependencies with uv...")

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

    print("✓ Dependencies installed with uv")
    return python_bin


def install_dependencies_pip(cicada_dir):
    """Install Python dependencies using traditional pip."""
    print("Installing dependencies with pip...")

    # Check if venv exists
    venv_path = cicada_dir / "venv"
    python_bin = venv_path / "bin" / "python"

    if not venv_path.exists():
        print("Creating virtual environment...")
        _ = run_command(f"python -m venv {venv_path}")

    # Install dependencies
    requirements_file = cicada_dir / "requirements.txt"
    if requirements_file.exists():
        _ = run_command(f"{python_bin} -m pip install -r {requirements_file}")

    # Install package in editable mode
    _ = run_command(f"{python_bin} -m pip install -e {cicada_dir}")

    print("✓ Dependencies installed with pip")
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
    # Auto-detect uv if not specified
    if use_uv is None:
        use_uv = check_uv_available()
        if use_uv:
            print("✓ Detected uv - will use it for faster installation")

    if use_uv:
        return install_dependencies_uv(cicada_dir)
    else:
        return install_dependencies_pip(cicada_dir)


def index_repository(cicada_dir, python_bin, repo_path, fetch_pr_info=False):
    """Index the Elixir repository."""
    print(f"Indexing repository at {repo_path}...")

    repo_path = Path(repo_path).resolve()
    output_path = repo_path / ".cicada" / "index.json"

    # Check if .cicada directory exists (first run detection)
    is_first_run = not output_path.parent.exists()

    # Create .cicada directory
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # On first run, add .cicada/ to .gitignore if it exists
    if is_first_run:
        from cicada.utils.path_utils import ensure_gitignore_has_cicada

        if ensure_gitignore_has_cicada(repo_path):
            print("✓ Added .cicada/ to .gitignore")

    # Run indexer
    indexer_script = cicada_dir / "cicada" / "indexer.py"
    cmd = f"{python_bin} {indexer_script} {repo_path} --output {output_path}"

    if fetch_pr_info:
        cmd += " --pr-info"

    _ = run_command(cmd)

    print(f"✓ Repository indexed at {output_path}")
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

    tools = ["cicada-server", "cicada-index"]
    visible_tools = [tool for tool in tools if shutil.which(tool)]

    if len(visible_tools) == len(tools):
        return "all_visible"
    elif visible_tools:
        return "partial"
    else:
        return "none"


def create_mcp_config(repo_path, _cicada_dir, _python_bin):
    """Create or update .mcp.json configuration file with intelligent command detection."""
    print("Creating .mcp.json configuration...")

    repo_path = Path(repo_path).resolve()
    mcp_config_path = repo_path / ".mcp.json"

    # Load existing config if present, otherwise create new one
    if mcp_config_path.exists():
        try:
            with open(mcp_config_path, "r") as f:
                config = json.load(f)
            print(f"✓ Found existing .mcp.json, will merge configuration")
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not read existing .mcp.json ({e}), creating new one")
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
        print(f"✓ Installation: {description}")
    elif tools_status == "partial":
        print(f"⚠️  Installation: {description}")
        print(f"   Some tools not found in PATH - add ~/.local/bin to PATH")
    else:
        print(f"⚠️  Installation: {description}")
        print(f"   Tools not found in PATH - add ~/.local/bin to PATH")

    # Build MCP server configuration
    server_config = {"command": command}

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

    print(f"✓ MCP configuration updated at {mcp_config_path}")

    # Show what was configured
    if command == "cicada-server":
        print("✅ Using 'cicada-server' command (fast, no paths needed)")
    else:
        print(f"ℹ️  Using Python: {command}")

    return mcp_config_path


def create_config_yaml(_cicada_dir, repo_path, index_path):
    """Create or update config.yaml in repository's .cicada directory."""
    repo_path = Path(repo_path).resolve()
    config_path = repo_path / ".cicada" / "config.yaml"

    # Ensure .cicada directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    config_content = f"""repository:
  path: {repo_path}

storage:
  index_path: {index_path}
"""

    with open(config_path, "w") as f:
        _ = f.write(config_content)

    print(f"✓ Config file created at {config_path}")


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
        print(f"✓ .gitattributes already has Elixir patterns")
        return gitattributes_path

    # Add elixir patterns
    with open(gitattributes_path, "a") as f:
        if existing_lines and not existing_lines[-1] == "":
            _ = f.write("\n")  # Add newline if file doesn't end with one

        _ = f.write("# Elixir function tracking for git log -L\n")
        for pattern in elixir_patterns:
            _ = f.write(f"{pattern}\n")

    print(f"✓ Added Elixir patterns to {gitattributes_path}")
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
  - Finding file history: `mcp__cicada__get_file_history`

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
            print(f"✓ CLAUDE.md already mentions cicada-mcp")
            return

        # Append the instruction
        with open(claude_md_path, "a") as f:
            # Add newline if file doesn't end with one
            if content and not content.endswith("\n"):
                _ = f.write("\n")

            _ = f.write("\n")
            _ = f.write(instruction_content)

        print(f"✓ Updated CLAUDE.md with cicada-mcp usage instructions")
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
    # ANSI color codes
    YELLOW = "\033[93m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    RESET = "\033[0m"

    repo_path = Path(repo_path).resolve()

    print()
    print(f"{YELLOW}Files created/modified:{RESET}")
    print()

    # List of files to check
    files_created = [
        (".cicada/", "Cicada index directory"),
        (".mcp.json", "MCP server configuration"),
    ]

    # Check each file
    for file_pattern, description in files_created:
        is_ignored = is_gitignored(repo_path, file_pattern)
        file_path = repo_path / file_pattern.rstrip("/")

        if file_path.exists():
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
        print(f"{RED}⚠️  Warning: The following should be in .gitignore:{RESET}")
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

    args = parser.parse_args()

    print("=" * 60)
    print("Cicada MCP Setup")
    print("=" * 60)

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
        print(f"✓ Using Python from installed package: {python_bin}")
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
        print(f"✓ Skipping dependency installation, using {python_bin}")

    # Index repository
    index_path = index_repository(cicada_dir, python_bin, args.repo, args.pr_info)

    # Create config.yaml
    create_config_yaml(cicada_dir, args.repo, index_path)

    # Create .gitattributes for Elixir function tracking
    _ = create_gitattributes(args.repo)

    # Update CLAUDE.md with cicada-mcp usage instructions
    update_claude_md(args.repo)

    # Create .mcp.json
    _ = create_mcp_config(args.repo, cicada_dir, python_bin)

    # Print summary of created files and gitignore status
    print_setup_summary(args.repo, index_path)

    print("=" * 60)
    print("✓ Setup Complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Restart Claude Code")
    print()
    print("2. Try asking Claude Code:")
    print("   - 'Where is [Module] used?'")
    print("   - 'Show me the functions in [ModuleName]'")
    print()


if __name__ == "__main__":
    main()
