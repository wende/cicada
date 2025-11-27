"""Installation logic for agents."""

from pathlib import Path

from cicada.agents.generator import load_template


def install_agent(target_dir: Path) -> None:
    """Install cicada-code-explorer agent to target directory.

    Args:
        target_dir: Target directory where agents will be installed
                   (agents will be created at target_dir/agents/)
    """
    # Create agents directory
    agents_dir = target_dir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    # Load and write template
    content = load_template("cicada-code-explorer.md")
    agent_file = agents_dir / "cicada-code-explorer.md"
    agent_file.write_text(content)
