"""Dart repository indexer using SCIP protocol.

This indexer uses scip-dart to generate type-aware semantic indexes
of Dart codebases.
"""

from pathlib import Path

from cicada.languages.scip.indexer import GenericSCIPIndexer


class DartSCIPIndexer(GenericSCIPIndexer):
    """Index Dart repositories using scip-dart."""

    def __init__(self, verbose: bool = False):
        """Initialize the Dart SCIP indexer."""
        super().__init__(verbose)
        self.excluded_dirs = {
            "build",
            ".dart_tool",
            ".git",
            "node_modules",
            ".pub-cache",
        }

    def get_language_name(self) -> str:
        """Return language identifier."""
        return "dart"

    def get_file_extensions(self) -> list[str]:
        """Return Dart file extensions."""
        return [".dart"]

    def get_excluded_dirs(self) -> list[str]:
        """Return directories to exclude from indexing."""
        return list(self.excluded_dirs)

    def _run_scip_indexer(self, repo_path: Path) -> Path:
        """Run scip_dart indexer."""
        import shutil
        import subprocess

        # Check if dart and scip_dart are available
        dart_cmd = shutil.which("dart")
        if not dart_cmd:
            raise RuntimeError(
                "dart command not found. Install Dart SDK: https://dart.dev/get-dart"
            )

        if not shutil.which("scip_dart"):
            raise RuntimeError("scip_dart not found. Install via: dart pub global activate scip")

        # Check if package_config.json exists, if not run dart pub get
        package_config = repo_path / ".dart_tool" / "package_config.json"
        if not package_config.exists():
            if self.verbose:
                print("  Running dart pub get to generate package_config.json...")
            try:
                result = subprocess.run(
                    [dart_cmd, "pub", "get"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if result.returncode != 0 and self.verbose:
                    print(f"  Warning: dart pub get returned {result.returncode}")
                    if result.stderr:
                        print(f"  Stderr: {result.stderr.strip()[:200]}")
                # Continue anyway - scip_dart might still work
            except subprocess.TimeoutExpired:
                if self.verbose:
                    print("  Warning: dart pub get timed out")

        # scip_dart takes project path as argument, outputs to index.scip
        cmd = ["scip_dart", "./"]
        scip_file = repo_path / "index.scip"

        return self._run_scip_command(
            repo_path=repo_path, command=cmd, output_path=scip_file, timeout=600
        )
