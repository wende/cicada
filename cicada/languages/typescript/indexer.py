"""TypeScript and JavaScript repository indexer using SCIP protocol.

This indexer uses scip-typescript to generate type-aware semantic indexes
of TypeScript and JavaScript codebases. The same underlying tool handles
both languages.
"""

import json
from pathlib import Path

from cicada.languages.scip.indexer import GenericSCIPIndexer

# Shared excluded directories for Node.js/TypeScript/JavaScript projects
_NODE_EXCLUDED_DIRS = {
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


class _ScipTypeScriptIndexerBase(GenericSCIPIndexer):
    """Base class for TypeScript and JavaScript indexers using scip-typescript.

    This class contains the shared logic for both TypeScript and JavaScript
    indexing since they both use the same underlying scip-typescript tool.
    """

    def __init__(self, verbose: bool = False):
        """Initialize the SCIP indexer."""
        super().__init__(verbose)
        self.excluded_dirs = _NODE_EXCLUDED_DIRS

    def get_excluded_dirs(self) -> list[str]:
        """Return directories to exclude from indexing."""
        return list(self.excluded_dirs)

    def _run_scip_indexer(self, repo_path: Path) -> Path:
        """Run scip-typescript indexer using shared subprocess helper.

        Automatically generates a tsconfig.json if no tsconfig.json exists,
        as scip-typescript requires it for proper JavaScript indexing.
        """
        # Security audit: Command uses list-form arguments (not shell=True),
        # so no command injection risk. All arguments are hardcoded strings.
        cmd = ["npx", "@sourcegraph/scip-typescript", "index"]
        scip_file = repo_path / "index.scip"

        # Check if tsconfig exists - scip-typescript requires it
        tsconfig = repo_path / "tsconfig.json"
        temp_config: Path | None = None

        if not tsconfig.exists():
            # Generate a minimal tsconfig.json for JavaScript projects
            temp_config = tsconfig
            ts_config_content = {
                "compilerOptions": {
                    "allowJs": True,
                    "checkJs": False,
                    "noEmit": True,
                    "moduleResolution": "node",
                    "target": "ES2020",
                    "module": "ESNext",
                    "esModuleInterop": True,
                    "skipLibCheck": True,
                    "resolveJsonModule": True,
                },
                "include": [
                    "**/*.ts",
                    "**/*.tsx",
                    "**/*.js",
                    "**/*.jsx",
                    "**/*.mjs",
                    "**/*.cjs",
                ],
                "exclude": ["node_modules", "dist", "build", ".git"],
            }
            with open(temp_config, "w", encoding="utf-8") as f:
                json.dump(ts_config_content, f, indent=2)
            if self.verbose:
                print("  Generated temporary tsconfig.json for indexing")

        try:
            return self._run_scip_command(
                repo_path=repo_path, command=cmd, output_path=scip_file, timeout=600
            )
        finally:
            # Clean up temporary config file if we created it
            if temp_config and temp_config.exists():
                temp_config.unlink()
                if self.verbose:
                    print("  Cleaned up temporary tsconfig.json")


class TypeScriptSCIPIndexer(_ScipTypeScriptIndexerBase):
    """Index TypeScript repositories using scip-typescript."""

    def get_language_name(self) -> str:
        """Return language identifier."""
        return "typescript"

    def get_file_extensions(self) -> list[str]:
        """Return TypeScript and JavaScript file extensions."""
        return [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"]


class JavaScriptSCIPIndexer(_ScipTypeScriptIndexerBase):
    """Index JavaScript repositories using scip-typescript.

    Uses the same underlying scip-typescript tool as TypeScriptSCIPIndexer
    but identifies as JavaScript and only returns JavaScript file extensions.
    """

    def get_language_name(self) -> str:
        """Return language identifier."""
        return "javascript"

    def get_file_extensions(self) -> list[str]:
        """Return JavaScript file extensions."""
        return [".js", ".jsx", ".mjs", ".cjs"]
