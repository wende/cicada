import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cicada.languages.rust.string_extractor import RustStringExtractor
from cicada.languages.scip.converter import SCIPConverter
from cicada.languages.scip.reader import SCIPReader
from cicada.parsing.base_indexer import BaseIndexer
from cicada.utils.hash_utils import (
    compute_hashes_for_files,
    detect_file_changes,
    load_file_hashes,
    save_file_hashes,
)
from cicada.utils.keyword_utils import read_keyword_extraction_config
from cicada.utils.storage import get_hashes_path


@dataclass
class ExpansionCallback:
    target: dict[str, Any]
    target_key: str


class RustSCIPIndexer(BaseIndexer):
    def __init__(self, verbose: bool = False):
        super().__init__(verbose=verbose)
        self.excluded_dirs = {
            "target",
            ".git",
            "node_modules",
            "vendor",
        }

    def get_language_name(self) -> str:
        return "rust"

    def get_file_extensions(self) -> list[str]:
        return [".rs"]

    def get_excluded_dirs(self) -> list[str]:
        return list(self.excluded_dirs)

    def index_repository(
        self,
        repo_path: str | Path,
        output_path: str | Path,
        force: bool = False,
        verbose: bool = False,
        config_path: str | Path | None = None,
    ) -> dict:
        return self.incremental_index_repository(
            repo_path=str(repo_path),
            output_path=str(output_path),
            extract_keywords=True,
            extract_string_keywords=False,
            compute_timestamps=True,
            extract_cochange=False,
            force_full=force,
            verbose=verbose,
        )

    def incremental_index_repository(
        self,
        repo_path: str,
        output_path: str,
        extract_keywords: bool = False,
        extract_string_keywords: bool = False,
        compute_timestamps: bool = True,
        extract_cochange: bool = False,
        force_full: bool = False,
        verbose: bool = True,
    ) -> dict:
        self.verbose = verbose
        self._interrupted = False
        repo_path_obj = Path(repo_path).resolve()
        output_path_obj = Path(output_path).resolve()
        self._start_timing()

        if self.verbose:
            print(f"Indexing Rust repository: {repo_path_obj}")

        hashes_path = get_hashes_path(repo_path_obj)
        existing_hashes = load_file_hashes(str(hashes_path))
        rust_files = list(self._find_rust_files(repo_path_obj))
        relative_files = [str(f.relative_to(repo_path_obj)) for f in rust_files]
        new_files, modified_files, deleted_files = detect_file_changes(
            relative_files, existing_hashes, str(repo_path_obj)
        )

        if not force_full and not new_files and not modified_files and not deleted_files:
            if self.verbose:
                print("  No changes detected. Index is up to date.")
            if output_path_obj.exists():
                with open(output_path_obj) as f:
                    existing_index = json.load(f)
                return {
                    "success": True,
                    "modules_count": len(existing_index.get("modules", {})),
                    "functions_count": existing_index.get("metadata", {}).get("total_functions", 0),
                    "files_indexed": 0,
                    "errors": [],
                    "skipped": True,
                }

        self._ensure_rust_analyzer_installed()
        scip_file = self._run_rust_analyzer(repo_path_obj)

        try:
            reader = SCIPReader()
            scip_index = reader.read_index(scip_file)

            keyword_extractor = None
            keyword_expander = None
            if extract_keywords or extract_string_keywords:
                try:
                    extraction_method, expansion_method = read_keyword_extraction_config(
                        repo_path_obj
                    )
                    if extraction_method == "bert":
                        from cicada.extractors.keybert import KeyBERTExtractor

                        keyword_extractor = KeyBERTExtractor(verbose=self.verbose)
                    else:
                        from cicada.extractors.keyword import RegularKeywordExtractor

                        keyword_extractor = RegularKeywordExtractor(verbose=self.verbose)
                    from cicada.parallel_expander import ParallelKeywordExpander

                    keyword_expander = ParallelKeywordExpander(
                        expansion_type=expansion_method, verbose=self.verbose
                    )
                except Exception:
                    pass

            converter = SCIPConverter(
                extract_keywords=False, keyword_extractor=None, verbose=self.verbose
            )
            cicada_index = converter.convert(scip_index, repo_path_obj)

            skipped_phases = self._run_enrichment_pipeline(
                cicada_index,
                repo_path_obj,
                extract_keywords=extract_keywords,
                extract_string_keywords=extract_string_keywords,
                compute_timestamps=compute_timestamps,
                extract_cochange=extract_cochange,
                keyword_extractor=keyword_extractor,
                keyword_expander=keyword_expander,
            )

            self._save_index(cicada_index, output_path_obj)
            if rust_files:
                current_hashes = compute_hashes_for_files([str(f) for f in rust_files])
                save_file_hashes(str(hashes_path.parent), current_hashes)

            all_modules = cicada_index.get("modules", {})
            return {
                "success": True,
                "modules_count": len(all_modules),
                "functions_count": cicada_index.get("metadata", {}).get("total_functions", 0),
                "files_indexed": len(scip_index.documents),
                "errors": [],
                "interrupted": self._interrupted,
                "skipped_phases": skipped_phases,
            }

        except Exception as e:
            if self.verbose:
                print(f"  Error: {e}")
            return {
                "success": False,
                "modules_count": 0,
                "functions_count": 0,
                "files_indexed": 0,
                "errors": [str(e)],
            }
        finally:
            if scip_file.exists():
                scip_file.unlink()

    def _find_rust_files(self, repo_path: Path) -> list[Path]:
        rust_files = []
        for rs_file in repo_path.rglob("*.rs"):
            if any(excluded in rs_file.parts for excluded in self.excluded_dirs):
                continue
            rust_files.append(rs_file)
        return rust_files

    def _ensure_rust_analyzer_installed(self):
        if shutil.which("rust-analyzer"):
            return
        raise RuntimeError("rust-analyzer is required.")

    def _run_rust_analyzer(self, repo_path: Path) -> Path:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".scip", delete=False) as tmp:
            scip_file = Path(tmp.name)
        cmd = ["rust-analyzer", "scip", str(repo_path), "--output", str(scip_file)]
        try:
            subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=600,
                check=True,
            )
            return scip_file
        except Exception:
            if scip_file.exists():
                scip_file.unlink()
            raise

    def _extract_string_keywords(
        self, index: dict, repo_path: Path, keyword_extractor, pipeline
    ) -> int:
        if self._interrupted:
            return 0
        string_extractor = RustStringExtractor(min_length=3)
        processed = 0
        try:
            for module_data in index.get("modules", {}).values():
                if self._interrupted:
                    break
                file_path = module_data.get("file")
                if not file_path or not (repo_path / file_path).exists():
                    continue
                source_code = (repo_path / file_path).read_text(encoding="utf-8")
                strings = string_extractor.extract_from_source(source_code)
                if strings:
                    module_data["string_sources"] = strings
                    all_text = " ".join(s["string"] for s in strings)
                    if all_text.strip():
                        kw = keyword_extractor.extract_keywords(all_text, top_n=15)
                        sk = {k: s * 1.3 for k, s in kw.get("top_keywords", [])}
                        if sk:
                            module_data["string_keywords"] = sk
                            if pipeline:
                                cb = ExpansionCallback(
                                    target=module_data, target_key="string_keywords"
                                )
                                for c, r in pipeline.submit(
                                    list(sk.keys()), sk, cb, top_n=3, threshold=0.2
                                ):
                                    self._apply_expansion_result(c, r)
                    processed += 1
        except KeyboardInterrupt:
            self._interrupted = True
        return processed

    def _save_index(self, index: dict, output_path: Path):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
