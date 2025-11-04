"""Template rendering system for language-specific code formatting.

This module provides a TemplateRenderer class that loads and renders templates
from language-specific directories using Python's built-in string.Template.
"""

import logging
from pathlib import Path
from string import Template

logger = logging.getLogger(__name__)


class TemplateRenderer:
    """Renders language-specific templates for code formatting.

    This class loads template files from cicada/languages/{language}/format/
    and renders them using Python's string.Template for variable substitution.

    If a template is not found for the specified language, it falls back to
    the Elixir template with a warning.

    Attributes:
        language: The programming language (e.g., "python", "elixir")
        languages_dir: Path to the languages directory
        _template_cache: Cache of loaded Template objects

    Example:
        >>> renderer = TemplateRenderer("python")
        >>> signature = renderer.render("signature",
        ...                             func_name="my_function",
        ...                             args="x: int, y: str",
        ...                             return_annotation=" -> bool:")
        >>> print(signature)
        def my_function(x: int, y: str) -> bool:
    """

    def __init__(self, language: str):
        """Initialize the template renderer for a specific language.

        Args:
            language: The programming language (e.g., "python", "elixir")
        """
        self.language = language.lower()
        # Navigate from cicada/format/ to cicada/languages/
        self.languages_dir = Path(__file__).parent.parent / "languages"
        self._template_cache: dict[str, Template] = {}

        # Validate that the languages directory exists
        if not self.languages_dir.exists():
            logger.warning(
                f"Languages directory not found: {self.languages_dir}. "
                "Templates will not be available."
            )

    def render(self, template_name: str, **variables) -> str:
        """Render a template with the given variables.

        Args:
            template_name: Name of the template file (without .txt extension)
            **variables: Template variables to substitute

        Returns:
            The rendered template string

        Raises:
            FileNotFoundError: If template not found for any supported language
            ValueError: If template has missing required variables

        Example:
            >>> renderer = TemplateRenderer("python")
            >>> result = renderer.render("signature",
            ...                          func_name="test",
            ...                          args="a, b",
            ...                          return_annotation=":")
        """
        template = self._load_template(template_name)

        try:
            return template.substitute(**variables)
        except KeyError as e:
            missing_var = str(e).strip("'")
            raise ValueError(
                f"Template '{template_name}' requires variable '{missing_var}' "
                f"which was not provided. Available variables: {list(variables.keys())}"
            ) from e

    def safe_render(self, template_name: str, **variables) -> str:
        """Render a template with safe substitution (allows missing variables).

        This method uses safe_substitute which leaves placeholders unchanged
        if the corresponding variable is not provided.

        Args:
            template_name: Name of the template file (without .txt extension)
            **variables: Template variables to substitute

        Returns:
            The rendered template string with missing variables left as $variable

        Example:
            >>> renderer = TemplateRenderer("python")
            >>> result = renderer.safe_render("signature",
            ...                               func_name="test")
            # Result might be: "def test($args)$return_annotation"
        """
        template = self._load_template(template_name)
        return template.safe_substitute(**variables)

    def _load_template(self, template_name: str) -> Template:
        """Load a template from disk, with caching and fallback support.

        Attempts to load from the language-specific directory first, then
        falls back to Elixir templates if not found.

        Args:
            template_name: Name of the template file (without .txt extension)

        Returns:
            A string.Template object

        Raises:
            FileNotFoundError: If template not found for any supported language
        """
        # Check cache first
        cache_key = f"{self.language}:{template_name}"
        if cache_key in self._template_cache:
            return self._template_cache[cache_key]

        # Try language-specific template
        template_path = self._get_template_path(template_name)

        if template_path.exists():
            template_content = template_path.read_text()
            template = Template(template_content)
            self._template_cache[cache_key] = template
            logger.debug(f"Loaded template: {template_path}")
            return template

        # Fallback to Elixir template if not the default language
        if self.language != "elixir":
            logger.warning(
                f"Template '{template_name}' not found for language '{self.language}' "
                f"at {template_path}. Falling back to Elixir template."
            )
            fallback_path = self.languages_dir / "elixir" / "format" / f"{template_name}.txt"

            if fallback_path.exists():
                template_content = fallback_path.read_text()
                template = Template(template_content)
                # Cache under the original key to avoid repeated warnings
                self._template_cache[cache_key] = template
                logger.debug(f"Loaded fallback template: {fallback_path}")
                return template

        # No template found
        raise FileNotFoundError(
            f"Template '{template_name}' not found for language '{self.language}'. "
            f"Expected at: {template_path}"
        )

    def _get_template_path(self, template_name: str) -> Path:
        """Get the file path for a template.

        Args:
            template_name: Name of the template file (without .txt extension)

        Returns:
            Path to the template file
        """
        return self.languages_dir / self.language / "format" / f"{template_name}.txt"

    def clear_cache(self):
        """Clear the template cache.

        This is useful during development or testing when templates are
        modified and need to be reloaded.
        """
        self._template_cache.clear()
        logger.debug("Template cache cleared")

    def template_exists(self, template_name: str) -> bool:
        """Check if a template exists for the current language.

        Args:
            template_name: Name of the template file (without .txt extension)

        Returns:
            True if the template exists, False otherwise
        """
        template_path = self._get_template_path(template_name)
        return template_path.exists()

    def get_available_templates(self) -> list[str]:
        """Get a list of available template names for the current language.

        Returns:
            List of template names (without .txt extension)
        """
        format_dir = self.languages_dir / self.language / "format"

        if not format_dir.exists():
            return []

        templates = []
        for template_file in format_dir.glob("*.txt"):
            templates.append(template_file.stem)

        return sorted(templates)
