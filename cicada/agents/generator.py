"""Template loading utilities for agents."""

from importlib.resources import files


def load_template(template_name: str) -> str:
    """Load agent template from package resources.

    Args:
        template_name: Name of the template file (e.g., "cicada-code-explorer.md")

    Returns:
        String content of the template

    Raises:
        FileNotFoundError: If template file not found
    """
    template_path = files("cicada.agents.templates.agents") / template_name
    return template_path.read_text()
