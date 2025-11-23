"""TypeScript repository indexer using SCIP protocol.

This indexer uses scip-typescript to generate type-aware semantic indexes
of TypeScript codebases.
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
        """Return TypeScript file extensions."""
        return [".ts", ".tsx"]

    def get_excluded_dirs(self) -> list[str]:
        """Return directories to exclude from indexing."""
        return list(self.excluded_dirs)

    def _run_scip_indexer(self, repo_path: Path) -> Path:
        """Run scip-typescript indexer.

        Note: We don't use GenericSCIPIndexer._run_scip_command() here because
        scip-typescript hardcodes its output to "index.scip" and doesn't support
        custom output paths. The generic helper creates temp files with unique names,
        which doesn't work with scip-typescript's fixed output behavior.
        """
        import subprocess

        # Security audit: Command uses list-form arguments (not shell=True),
        # so no command injection risk. All arguments are hardcoded strings.
        cmd = ["npx", "@sourcegraph/scip-typescript", "index"]

        if self.verbose:
            print(f"  Running: {' '.join(cmd)}")
            print("  (This may take several minutes for large projects...)")

        try:
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=600,
            )

            if result.returncode != 0:
                raise RuntimeError(f"scip-typescript indexing failed:\n{result.stderr}")

            # scip-typescript always creates index.scip in the repo root
            # (unlike scip-python which accepts --output flag for custom paths)
            scip_file = repo_path / "index.scip"

            if not scip_file.exists():
                raise RuntimeError(f"scip-typescript did not generate {scip_file}")

            return scip_file

        except subprocess.TimeoutExpired as e:
            raise RuntimeError(
                "scip-typescript indexing timed out after 600 seconds. "
                "Try indexing a smaller subset of the project."
            ) from e
