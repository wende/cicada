"""TypeScript and JavaScript repository indexer using SCIP protocol.

This indexer uses scip-typescript to generate type-aware semantic indexes
of TypeScript and JavaScript codebases. The same underlying tool handles
both languages.
"""

from pathlib import Path

from cicada.languages.scip.indexer import GenericSCIPIndexer


class TypeScriptSCIPIndexer(GenericSCIPIndexer):
    """Index TypeScript repositories using scip-typescript."""

    def __init__(self, verbose: bool = False):
        """Initialize the TypeScript SCIP indexer."""
        super().__init__(verbose)
        self.excluded_dirs = {
            "node_modules",
            ".git",
            "dist",
            "build",
            "coverage",
            ".next",
            ".nuxt",
            "out",
            ".cache",
        }

    def get_language_name(self) -> str:
        """Return language identifier."""
        return "typescript"

    def get_file_extensions(self) -> list[str]:
        """Return TypeScript and JavaScript file extensions."""
        return [".ts", ".tsx", ".js", ".jsx"]

    def get_excluded_dirs(self) -> list[str]:
        """Return directories to exclude from indexing."""
        return list(self.excluded_dirs)

    def _run_scip_indexer(self, repo_path: Path) -> Path:
        """Run scip-typescript indexer using shared subprocess helper."""

        # Security audit: Command uses list-form arguments (not shell=True),
        # so no command injection risk. All arguments are hardcoded strings.
        cmd = ["npx", "@sourcegraph/scip-typescript", "index"]
        scip_file = repo_path / "index.scip"

        return self._run_scip_command(
            repo_path=repo_path, command=cmd, output_path=scip_file, timeout=600
        )


class JavaScriptSCIPIndexer(TypeScriptSCIPIndexer):
    """Index JavaScript repositories using scip-typescript.

    This is a thin wrapper around TypeScriptSCIPIndexer that identifies
    as JavaScript. The underlying scip-typescript tool handles both
    languages identically.
    """

    def get_language_name(self) -> str:
        """Return language identifier."""
        return "javascript"

    def get_file_extensions(self) -> list[str]:
        """Return JavaScript file extensions."""
        return [".js", ".jsx", ".mjs", ".cjs"]
