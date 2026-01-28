"""
Abstract base class for language-specific indexers.

All language implementations must subclass BaseIndexer and implement the abstract methods.
This is a minimal interface - enrichment (keywords, timestamps, cochange) is handled
separately by the main cicada package.
"""

from abc import ABC, abstractmethod
from pathlib import Path


class BaseIndexer(ABC):
    """
    Universal indexer interface for all programming languages.

    Each language-specific indexer (e.g., ElixirIndexer, PythonSCIPIndexer) must
    inherit from this class and implement all abstract methods.

    The indexer is responsible for:
    1. Finding source files in a repository
    2. Parsing those files (language-specific)
    3. Building the unified index structure
    4. Returning the raw index (enrichment is done separately)
    """

    # Override this in subclasses that support incremental indexing
    supports_incremental: bool = False

    def __init__(self, verbose: bool = False):
        """Initialize base indexer with common state."""
        self.verbose = verbose

    @abstractmethod
    def get_language_name(self) -> str:
        """
        Return the language identifier for this indexer.

        Returns:
            Language name in lowercase (e.g., 'elixir', 'python', 'typescript')
        """

    @abstractmethod
    def get_file_extensions(self) -> list[str]:
        """
        Return file extensions to index for this language.

        Returns:
            List of file extensions including dots (e.g., ['.ex', '.exs'], ['.py'])
        """

    @abstractmethod
    def get_excluded_dirs(self) -> list[str]:
        """
        Return language-specific directories to exclude from indexing.

        Returns:
            List of directory names to exclude (e.g., ['deps', '_build'], ['__pycache__', '.venv'])
        """

    @abstractmethod
    def index_repository(
        self,
        repo_path: str | Path,
        output_path: str | Path,
        force: bool = False,
        verbose: bool = False,
        config_path: str | Path | None = None,
    ) -> dict:
        """
        Index a repository and return the raw index.

        Args:
            repo_path: Path to the repository to index
            output_path: Path where the index.json should be saved
            force: If True, reindex all files regardless of changes
            verbose: If True, print detailed progress information
            config_path: Optional path to config.yaml for custom settings

        Returns:
            Dictionary with indexing results:
                {
                    "success": bool,
                    "modules_count": int,
                    "functions_count": int,
                    "files_indexed": int,
                    "errors": list[str]
                }
        """

    def incremental_index_repository(
        self,
        repo_path: str,
        output_path: str,
        force_full: bool = False,
        verbose: bool = True,
    ) -> dict:
        """
        Incrementally index a repository using file hashing.

        This method is optional - only indexers that support incremental indexing
        (supports_incremental = True) need to implement this.

        Note: This returns a RAW index without enrichment. Enrichment (keywords,
        timestamps, cochange) should be applied separately by the caller.

        Args:
            repo_path: Path to the repository root
            output_path: Path where the index JSON file will be saved
            force_full: If True, ignore existing hashes and do full reindex
            verbose: If True, print detailed progress information

        Returns:
            Dictionary containing the raw index data

        Raises:
            NotImplementedError: If the indexer does not support incremental indexing
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support incremental indexing. "
            f"Use index_repository() instead."
        )

    def _find_source_files(self, repo_path: Path) -> list[Path]:
        """
        Find all source files to index in the repository.

        Default implementation finds files by extension and excludes
        directories from get_excluded_dirs(). Can be overridden for
        custom file discovery logic.

        Args:
            repo_path: Repository root path

        Returns:
            List of source file paths to index
        """
        source_files = []
        extensions = self.get_file_extensions()
        excluded = set(self.get_excluded_dirs())

        for ext in extensions:
            for file_path in repo_path.rglob(f"*{ext}"):
                # Check if any parent directory is excluded
                if any(part in excluded for part in file_path.parts):
                    continue
                if file_path.is_file():
                    source_files.append(file_path)

        return sorted(source_files)

    def should_index_file(self, file_path: Path) -> bool:
        """
        Determine if a file should be indexed (optional override).

        Default implementation returns True. Override to implement custom
        filtering logic (e.g., skip files by pattern, check file size, etc.).

        Args:
            file_path: Path to check

        Returns:
            True if file should be indexed, False otherwise
        """
        return True

    def get_default_config(self) -> dict:
        """
        Return default configuration for this language (optional override).

        Returns:
            Dictionary with default config values
        """
        return {
            "language": self.get_language_name(),
            "file_extensions": self.get_file_extensions(),
            "excluded_dirs": self.get_excluded_dirs(),
        }
