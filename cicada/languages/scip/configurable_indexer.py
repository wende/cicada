"""Configurable SCIP indexer that uses language configs."""

import shutil
from pathlib import Path

from cicada.languages.scip.configs import get_config
from cicada.languages.scip.indexer import GenericSCIPIndexer


class ConfigurableSCIPIndexer(GenericSCIPIndexer):
    """SCIP indexer configured via SCIPLanguageConfig.

    This single class replaces all the individual language indexers
    (GoSCIPIndexer, RubySCIPIndexer, etc.) by using configuration objects.

    Usage:
        indexer = ConfigurableSCIPIndexer("go")
        result = indexer.index_repository(repo_path, output_path)
    """

    def __init__(self, language: str, verbose: bool = False):
        """Initialize indexer for a specific language.

        Args:
            language: Language name (e.g., "go", "ruby", "java")
            verbose: Enable verbose output
        """
        config = get_config(language)
        if config is None:
            from cicada.languages.scip.configs import get_all_languages

            available = ", ".join(get_all_languages())
            raise ValueError(f"Unknown language: {language}. Available: {available}")

        super().__init__(verbose)
        self.config = config
        self.excluded_dirs = config.excluded_dirs

    def get_language_name(self) -> str:
        return self.config.name

    def get_file_extensions(self) -> list[str]:
        return self.config.extensions

    def get_excluded_dirs(self) -> list[str]:
        return list(self.config.excluded_dirs)

    def _find_executable(self) -> tuple[list[str], str | None]:
        """Find the first available executable and return command to use.

        Returns:
            Tuple of (command_list, executable_path) or raises RuntimeError
        """
        # Try primary command first
        if self.config.command:
            exe = self.config.command[0]
            if shutil.which(exe):
                return self.config.command, shutil.which(exe)

        # Try fallback commands
        for fallback in self.config.fallback_commands:
            if fallback:
                exe = fallback[0]
                if shutil.which(exe):
                    return fallback, shutil.which(exe)

        # Nothing found
        raise RuntimeError(f"{self.config.name} indexer not found. {self.config.install_hint}")

    def _run_scip_indexer(self, repo_path: Path) -> Path:
        """Run the SCIP indexer for this language."""
        # Run pre-index hook if defined (e.g., dart pub get)
        if self.config.pre_index_hook:
            self.config.pre_index_hook(repo_path, self.verbose)

        # Find executable and get command
        cmd, _ = self._find_executable()
        scip_file = repo_path / "index.scip"

        return self._run_scip_command(
            repo_path=repo_path,
            command=cmd,
            output_path=scip_file,
            timeout=600,
        )


# Convenience factory function
def create_indexer(language: str, verbose: bool = False) -> ConfigurableSCIPIndexer:
    """Create a SCIP indexer for the specified language.

    Args:
        language: Language name (go, ruby, java, scala, c, cpp, csharp, vb, dart)
        verbose: Enable verbose output

    Returns:
        ConfigurableSCIPIndexer instance
    """
    return ConfigurableSCIPIndexer(language, verbose)
