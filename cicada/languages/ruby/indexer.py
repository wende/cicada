"""Ruby repository indexer using SCIP protocol.

This indexer uses scip-ruby (powered by Sorbet) to generate
type-aware semantic indexes of Ruby codebases.
"""

import json
import subprocess
import tempfile
from pathlib import Path

from cicada.languages.ruby.scip_installer import SCIPRubyInstaller
from cicada.languages.scip.converter import SCIPConverter
from cicada.languages.scip.reader import SCIPReader
from cicada.parsing.base_indexer import BaseIndexer
from cicada.utils.keyword_utils import get_keyword_extractor_from_config


class RubySCIPIndexer(BaseIndexer):
    """Index Ruby repositories using scip-ruby."""

    def __init__(self, verbose: bool = False):
        """
        Initialize the Ruby SCIP indexer.

        Args:
            verbose: If True, print detailed progress information
        """
        self.verbose = verbose
        self.excluded_dirs = {
            "vendor",
            ".bundle",
            "tmp",
            "log",
            ".git",
            "node_modules",
            "coverage",
            "public",
            ".rbs_collection",
            "sorbet",
        }

    def get_language_name(self) -> str:
        """Return language identifier."""
        return "ruby"

    def get_file_extensions(self) -> list[str]:
        """Return Ruby file extensions."""
        return [".rb", ".rake", ".gemspec"]

    def get_excluded_dirs(self) -> list[str]:
        """Return directories to exclude from indexing."""
        return list(self.excluded_dirs)

    def index_repository(
        self,
        repo_path: str | Path,
        output_path: str | Path,
        force: bool = False,
        verbose: bool = False,
        config_path: str | Path | None = None,
    ) -> dict:
        """
        Index Ruby repository using scip-ruby.

        Args:
            repo_path: Path to repository root
            output_path: Path to save index.json
            force: If True, reindex even if up-to-date (MVP: always reindex)
            verbose: If True, print detailed progress
            config_path: Optional config file (MVP: unused)

        Returns:
            Dict with indexing results

        Raises:
            RuntimeError: If scip-ruby is not available or indexing fails
        """
        repo_path = Path(repo_path).resolve()
        output_path = Path(output_path).resolve()

        if verbose or self.verbose:
            print(f"Indexing Ruby repository: {repo_path}")

        # 1. Ensure scip-ruby is installed
        self._ensure_scip_ruby_installed()

        # 2. Run scip-ruby indexer
        scip_file = self._run_scip_ruby(repo_path)

        try:
            # 3. Read .scip file
            reader = SCIPReader()
            scip_index = reader.read_index(scip_file)

            if verbose or self.verbose:
                summary = reader.get_index_summary(scip_index)
                print(
                    f"  SCIP index: {summary['documents']} documents, "
                    f"{summary['symbols']} symbols"
                )

            # 4. Initialize keyword extractor from config (universal)
            extract_keywords, keyword_extractor = get_keyword_extractor_from_config(
                repo_path, verbose=(verbose or self.verbose)
            )

            # 5. Convert to Cicada format with optional keyword extraction
            converter = SCIPConverter(
                extract_keywords=extract_keywords,
                keyword_extractor=keyword_extractor,
                verbose=self.verbose,
            )
            cicada_index = converter.convert(scip_index, repo_path)

            # 6. Save to output path
            self._save_index(cicada_index, output_path)

            # 7. Build result summary
            all_modules = cicada_index.get("modules", {})
            modules_count = len(all_modules)
            functions_count = cicada_index.get("metadata", {}).get("total_functions", 0)

            # Count files vs classes for better reporting
            file_count = sum(1 for name in all_modules if name.startswith("_file_"))
            class_count = modules_count - file_count

            if verbose or self.verbose:
                if class_count > 0:
                    print(
                        f"  Indexed {file_count} files, {class_count} classes, {functions_count} methods"
                    )
                else:
                    print(f"  Indexed {modules_count} modules, {functions_count} methods")
                print(f"  Index saved to: {output_path}")

            return {
                "success": True,
                "modules_count": modules_count,
                "functions_count": functions_count,
                "files_indexed": len(scip_index.documents),
                "errors": [],
            }

        except Exception as e:
            error_msg = f"Failed to process SCIP index: {e}"
            if verbose or self.verbose:
                print(f"  Error: {error_msg}")
            return {
                "success": False,
                "modules_count": 0,
                "functions_count": 0,
                "files_indexed": 0,
                "errors": [error_msg],
            }

        finally:
            # 8. Cleanup temporary .scip file
            if scip_file.exists():
                scip_file.unlink()
                if verbose or self.verbose:
                    print(f"  Cleaned up temporary file: {scip_file}")

    def _ensure_scip_ruby_installed(self):
        """
        Ensure scip-ruby is installed, auto-install if needed.

        Raises:
            RuntimeError: If gem is not available or installation fails
        """
        if SCIPRubyInstaller.is_scip_ruby_installed():
            if self.verbose:
                version = SCIPRubyInstaller.get_scip_ruby_version()
                print(f"  Using scip-ruby {version}")
            return

        # Check gem availability
        if not SCIPRubyInstaller.is_gem_available():
            raise RuntimeError(
                "gem is required to install scip-ruby.\n"
                "Install Ruby from: https://www.ruby-lang.org/\n"
                "Or install scip-ruby manually: gem install scip-ruby"
            )

        # Auto-install
        print("Installing scip-ruby (this may take a minute)...")
        success = SCIPRubyInstaller.install_scip_ruby(verbose=self.verbose)

        if not success:
            raise RuntimeError(
                "Failed to install scip-ruby.\n"
                "Try installing manually: gem install scip-ruby"
            )

        print("✓ scip-ruby installed successfully")

    def _run_scip_ruby(self, repo_path: Path) -> Path:
        """
        Run scip-ruby indexer on repository.

        Args:
            repo_path: Repository root path

        Returns:
            Path to generated .scip file

        Raises:
            RuntimeError: If scip-ruby execution fails
        """
        # Create temporary file for .scip output
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".scip", delete=False, dir=repo_path
        ) as tmp:
            scip_file = Path(tmp.name)

        # Determine command - use bundle exec if available and Gemfile present
        has_gemfile = (repo_path / "Gemfile").exists()
        use_bundle = has_gemfile and SCIPRubyInstaller.is_bundle_available()

        if use_bundle:
            cmd = [
                "bundle",
                "exec",
                "scip-ruby",
                "--output",
                str(scip_file),
            ]
        else:
            cmd = [
                "scip-ruby",
                "--output",
                str(scip_file),
            ]

        if self.verbose:
            print(f"  Running: {' '.join(cmd)}")
            print("  (This may take several minutes for large projects...)")

        try:
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
            )

            if result.returncode != 0:
                raise RuntimeError(f"scip-ruby indexing failed:\n{result.stderr}")

            if not scip_file.exists():
                raise RuntimeError(f"scip-ruby did not generate {scip_file}")

            return scip_file

        except subprocess.TimeoutExpired as e:
            if scip_file.exists():
                scip_file.unlink()
            raise RuntimeError(
                "scip-ruby indexing timed out after 10 minutes. "
                "Try indexing a smaller subset of the project."
            ) from e
        except Exception:
            if scip_file.exists():
                scip_file.unlink()
            raise

    def _save_index(self, index: dict, output_path: Path):
        """
        Save index to JSON file.

        Args:
            index: Cicada index dictionary
            output_path: Path to save to
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
