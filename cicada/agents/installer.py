"""Installation logic for agents."""

from pathlib import Path

from cicada.agents.generator import load_template


def install_agent(target_dir: Path, agent_name: str) -> None:
    """Install a given agent to target directory.

    Args:
        target_dir: Target directory where agents will be installed
                   (agents will be created at target_dir/agents/)
        agent_name: The filename of the agent to install.
    """
    # Create agents directory
    agents_dir = target_dir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    # Load and write template
    content = load_template(agent_name)
    agent_file = agents_dir / agent_name
    agent_file.write_text(content)
