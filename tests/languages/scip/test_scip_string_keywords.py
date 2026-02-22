"""Tests for string keyword extraction in GenericSCIPIndexer."""

import pytest
from pathlib import Path

from cicada.languages.scip.indexer import ExpansionCallback, GenericSCIPIndexer


class MockSCIPIndexer(GenericSCIPIndexer):
    """Concrete subclass for testing (TypeScript)."""

    def get_language_name(self) -> str:
        return "typescript"

    def get_file_extensions(self) -> list[str]:
        return [".ts", ".tsx"]

    def _run_scip_indexer(self, repo_path: Path) -> Path:
        raise NotImplementedError("Not needed for keyword tests")


class MockRubySCIPIndexer(GenericSCIPIndexer):
    """Concrete subclass for testing Ruby-style # comments."""

    def get_language_name(self) -> str:
        return "ruby"

    def get_file_extensions(self) -> list[str]:
        return [".rb"]

    def _run_scip_indexer(self, repo_path: Path) -> Path:
        raise NotImplementedError("Not needed for keyword tests")


class MockKeywordExtractor:
    """Returns predictable keyword results for testing."""

    def extract_keywords(self, text: str, top_n: int = 10) -> dict:
        # Split text into words, return first top_n unique words as keywords
        words = []
        seen = set()
        for w in text.lower().split():
            clean = "".join(c for c in w if c.isalnum())
            if clean and len(clean) >= 3 and clean not in seen:
                seen.add(clean)
                words.append(clean)
            if len(words) >= top_n:
                break
        return {"top_keywords": [(w, 1.0) for w in words]}


class MockPipeline:
    """No-op pipeline that doesn't expand keywords."""

    def submit(self, keywords, scores, callback, top_n=3, threshold=0.2):
        return []  # No expansions

    @property
    def stats(self):
        return {"submitted": 0, "completed": 0}


class MockExpandingPipeline:
    """Pipeline that returns expansion results to exercise _apply_expansion_result."""

    def submit(self, keywords, scores, callback, top_n=3, threshold=0.2):
        # Return one expansion result per submission
        result = {"words": [{"word": "expanded_term", "score": 0.5}]}
        return [(callback, result)]

    @property
    def stats(self):
        return {"submitted": 1, "completed": 1}


class TestExtractStringKeywords:
    """Tests for GenericSCIPIndexer._extract_string_keywords."""

    def setup_method(self):
        self.indexer = MockSCIPIndexer(verbose=False)
        self.extractor = MockKeywordExtractor()
        self.pipeline = MockPipeline()

    def test_extracts_keywords_from_source_file(self, tmp_path):
        source = tmp_path / "app.ts"
        source.write_text('const msg = "hello world greeting";\n')

        index = {
            "modules": {
                "App": {"file": "app.ts", "functions": []},
            }
        }

        result = self.indexer._extract_string_keywords(
            index, tmp_path, self.extractor, self.pipeline
        )

        assert result == 1
        module = index["modules"]["App"]
        assert "string_keywords" in module
        assert "string_sources" in module
        # Keywords should have 1.3x boost
        for score in module["string_keywords"].values():
            assert score == pytest.approx(1.3)

    def test_skips_modules_with_existing_keywords(self, tmp_path):
        source = tmp_path / "app.ts"
        source.write_text('const x = "should not extract";\n')

        index = {
            "modules": {
                "App": {
                    "file": "app.ts",
                    "functions": [],
                    "string_keywords": {"existing": 2.0},
                },
            }
        }

        result = self.indexer._extract_string_keywords(
            index, tmp_path, self.extractor, self.pipeline
        )

        assert result == 1
        # Should not overwrite existing keywords
        assert index["modules"]["App"]["string_keywords"] == {"existing": 2.0}

    def test_skips_missing_files(self, tmp_path):
        index = {
            "modules": {
                "Missing": {"file": "nonexistent.ts", "functions": []},
            }
        }

        result = self.indexer._extract_string_keywords(
            index, tmp_path, self.extractor, self.pipeline
        )

        assert result == 0
        assert "string_keywords" not in index["modules"]["Missing"]

    def test_skips_modules_without_file(self):
        index = {
            "modules": {
                "NoFile": {"functions": []},
            }
        }

        result = self.indexer._extract_string_keywords(
            index, Path("/tmp"), self.extractor, self.pipeline
        )

        assert result == 0

    def test_handles_file_with_no_strings(self, tmp_path):
        source = tmp_path / "empty.ts"
        source.write_text("const x = 42;\n")

        index = {
            "modules": {
                "Empty": {"file": "empty.ts", "functions": []},
            }
        }

        result = self.indexer._extract_string_keywords(
            index, tmp_path, self.extractor, self.pipeline
        )

        assert result == 1
        assert "string_keywords" not in index["modules"]["Empty"]

    def test_processes_multiple_modules(self, tmp_path):
        (tmp_path / "a.ts").write_text('const x = "alpha keyword";\n')
        (tmp_path / "b.ts").write_text('const y = "beta keyword";\n')

        index = {
            "modules": {
                "ModA": {"file": "a.ts", "functions": []},
                "ModB": {"file": "b.ts", "functions": []},
            }
        }

        result = self.indexer._extract_string_keywords(
            index, tmp_path, self.extractor, self.pipeline
        )

        assert result == 2
        assert "string_keywords" in index["modules"]["ModA"]
        assert "string_keywords" in index["modules"]["ModB"]

    def test_stores_string_sources(self, tmp_path):
        source = tmp_path / "app.ts"
        source.write_text('const msg = "hello world";\n')

        index = {
            "modules": {
                "App": {"file": "app.ts", "functions": []},
            }
        }

        self.indexer._extract_string_keywords(index, tmp_path, self.extractor, self.pipeline)

        sources = index["modules"]["App"]["string_sources"]
        assert len(sources) == 1
        assert sources[0]["string"] == "hello world"
        assert sources[0]["line"] == 1

    def test_empty_index(self, tmp_path):
        index = {"modules": {}}

        result = self.indexer._extract_string_keywords(
            index, tmp_path, self.extractor, self.pipeline
        )

        assert result == 0


class TestExtractCommentKeywords:
    """Tests for GenericSCIPIndexer._extract_comment_keywords."""

    def setup_method(self):
        self.indexer = MockSCIPIndexer(verbose=False)
        self.extractor = MockKeywordExtractor()
        self.pipeline = MockPipeline()

    def test_extracts_keywords_from_comments(self, tmp_path):
        source = tmp_path / "app.ts"
        source.write_text("// This handles user authentication\nconst x = 1;\n")

        index = {
            "modules": {
                "App": {"file": "app.ts", "functions": []},
            }
        }

        result = self.indexer._extract_comment_keywords(
            index, tmp_path, self.extractor, self.pipeline
        )

        assert result == 1
        assert "comment_keywords" in index["modules"]["App"]

    def test_skips_modules_with_existing_comment_keywords(self, tmp_path):
        source = tmp_path / "app.ts"
        source.write_text("// should not re-extract\n")

        index = {
            "modules": {
                "App": {
                    "file": "app.ts",
                    "functions": [],
                    "comment_keywords": {"existing": 1.0},
                },
            }
        }

        result = self.indexer._extract_comment_keywords(
            index, tmp_path, self.extractor, self.pipeline
        )

        assert result == 1
        assert index["modules"]["App"]["comment_keywords"] == {"existing": 1.0}

    def test_skips_file_with_no_comments(self, tmp_path):
        source = tmp_path / "app.ts"
        source.write_text('const x = "no comments here";\n')

        index = {
            "modules": {
                "App": {"file": "app.ts", "functions": []},
            }
        }

        result = self.indexer._extract_comment_keywords(
            index, tmp_path, self.extractor, self.pipeline
        )

        assert result == 1
        assert "comment_keywords" not in index["modules"]["App"]

    def test_ignores_inline_comment_markers(self, tmp_path):
        """Inline // in code (e.g., URLs) should NOT be treated as comments."""
        source = tmp_path / "app.ts"
        source.write_text('const url = "http://example.com";\n')

        index = {
            "modules": {
                "App": {"file": "app.ts", "functions": []},
            }
        }

        result = self.indexer._extract_comment_keywords(
            index, tmp_path, self.extractor, self.pipeline
        )

        assert result == 1
        assert "comment_keywords" not in index["modules"]["App"]

    def test_skips_missing_files(self, tmp_path):
        index = {
            "modules": {
                "Missing": {"file": "nonexistent.ts", "functions": []},
            }
        }

        result = self.indexer._extract_comment_keywords(
            index, tmp_path, self.extractor, self.pipeline
        )

        assert result == 0

    def test_skips_modules_without_file(self):
        index = {
            "modules": {
                "NoFile": {"functions": []},
            }
        }

        result = self.indexer._extract_comment_keywords(
            index, Path("/tmp"), self.extractor, self.pipeline
        )

        assert result == 0


class TestExtractStringKeywordsVerbose:
    """Tests for verbose output and edge cases."""

    def setup_method(self):
        self.extractor = MockKeywordExtractor()
        self.pipeline = MockPipeline()

    def test_verbose_output(self, tmp_path, capsys):
        indexer = MockSCIPIndexer(verbose=True)
        source = tmp_path / "app.ts"
        source.write_text('const msg = "hello world greeting";\n')

        index = {"modules": {"App": {"file": "app.ts", "functions": []}}}

        indexer._extract_string_keywords(index, tmp_path, self.extractor, self.pipeline)

        captured = capsys.readouterr()
        assert "Extracting string keywords" in captured.out

    def test_verbose_error_on_bad_file(self, tmp_path, capsys):
        indexer = MockSCIPIndexer(verbose=True)
        # Create a file that will cause a read error (binary)
        bad_file = tmp_path / "bad.ts"
        bad_file.write_bytes(b"\x80\x81\x82\x83")

        index = {"modules": {"Bad": {"file": "bad.ts", "functions": []}}}

        result = indexer._extract_string_keywords(index, tmp_path, self.extractor, self.pipeline)

        # Should handle error gracefully
        assert result >= 0

    def test_interrupted_returns_zero(self, tmp_path):
        indexer = MockSCIPIndexer(verbose=False)
        indexer._interrupted = True

        index = {"modules": {"App": {"file": "app.ts", "functions": []}}}

        result = indexer._extract_string_keywords(index, tmp_path, self.extractor, self.pipeline)

        assert result == 0

    def test_none_pipeline(self, tmp_path):
        """Test with pipeline=None (no expansion)."""
        indexer = MockSCIPIndexer(verbose=False)
        source = tmp_path / "app.ts"
        source.write_text('const msg = "hello world greeting";\n')

        index = {"modules": {"App": {"file": "app.ts", "functions": []}}}

        result = indexer._extract_string_keywords(index, tmp_path, self.extractor, None)

        assert result == 1
        assert "string_keywords" in index["modules"]["App"]


class TestExtractCommentKeywordsVerbose:
    """Tests for verbose output and edge cases in comment extraction."""

    def setup_method(self):
        self.extractor = MockKeywordExtractor()
        self.pipeline = MockPipeline()

    def test_verbose_output(self, tmp_path, capsys):
        indexer = MockSCIPIndexer(verbose=True)
        source = tmp_path / "app.ts"
        source.write_text("// handles authentication logic\nconst x = 1;\n")

        index = {"modules": {"App": {"file": "app.ts", "functions": []}}}

        indexer._extract_comment_keywords(index, tmp_path, self.extractor, self.pipeline)

        captured = capsys.readouterr()
        assert "Extracting comment keywords" in captured.out

    def test_interrupted_returns_zero(self, tmp_path):
        indexer = MockSCIPIndexer(verbose=False)
        indexer._interrupted = True

        index = {"modules": {"App": {"file": "app.ts", "functions": []}}}

        result = indexer._extract_comment_keywords(index, tmp_path, self.extractor, self.pipeline)

        assert result == 0

    def test_none_pipeline(self, tmp_path):
        """Test with pipeline=None (no expansion)."""
        indexer = MockSCIPIndexer(verbose=False)
        source = tmp_path / "app.ts"
        source.write_text("// handles authentication logic\nconst x = 1;\n")

        index = {"modules": {"App": {"file": "app.ts", "functions": []}}}

        result = indexer._extract_comment_keywords(index, tmp_path, self.extractor, None)

        assert result == 1
        assert "comment_keywords" in index["modules"]["App"]


class TestExtractCommentKeywordsRuby:
    """Tests for Ruby-style # comment extraction."""

    def setup_method(self):
        self.indexer = MockRubySCIPIndexer(verbose=False)
        self.extractor = MockKeywordExtractor()
        self.pipeline = MockPipeline()

    def test_extracts_ruby_hash_comments(self, tmp_path):
        source = tmp_path / "app.rb"
        source.write_text("# This handles user authentication\nx = 1\n")

        index = {
            "modules": {
                "App": {"file": "app.rb", "functions": []},
            }
        }

        result = self.indexer._extract_comment_keywords(
            index, tmp_path, self.extractor, self.pipeline
        )

        assert result == 1
        assert "comment_keywords" in index["modules"]["App"]

    def test_skips_ruby_file_with_no_comments(self, tmp_path):
        source = tmp_path / "app.rb"
        source.write_text("x = 42\n")

        index = {
            "modules": {
                "App": {"file": "app.rb", "functions": []},
            }
        }

        result = self.indexer._extract_comment_keywords(
            index, tmp_path, self.extractor, self.pipeline
        )

        assert result == 1
        assert "comment_keywords" not in index["modules"]["App"]

    def test_skips_ruby_modules_with_existing_comment_keywords(self, tmp_path):
        source = tmp_path / "app.rb"
        source.write_text("# should not re-extract\n")

        index = {
            "modules": {
                "App": {
                    "file": "app.rb",
                    "functions": [],
                    "comment_keywords": {"existing": 1.0},
                },
            }
        }

        result = self.indexer._extract_comment_keywords(
            index, tmp_path, self.extractor, self.pipeline
        )

        assert result == 1
        assert index["modules"]["App"]["comment_keywords"] == {"existing": 1.0}

    def test_ruby_ignores_inline_hash_in_strings(self, tmp_path):
        """Inline # in code (e.g., string interpolation markers) should NOT be comments."""
        source = tmp_path / "app.rb"
        source.write_text('msg = "item #1 in list"\n')

        index = {
            "modules": {
                "App": {"file": "app.rb", "functions": []},
            }
        }

        result = self.indexer._extract_comment_keywords(
            index, tmp_path, self.extractor, self.pipeline
        )

        assert result == 1
        assert "comment_keywords" not in index["modules"]["App"]

    def test_ruby_skips_missing_files(self, tmp_path):
        index = {
            "modules": {
                "Missing": {"file": "nonexistent.rb", "functions": []},
            }
        }

        result = self.indexer._extract_comment_keywords(
            index, tmp_path, self.extractor, self.pipeline
        )

        assert result == 0

    def test_ruby_skips_modules_without_file(self):
        index = {
            "modules": {
                "NoFile": {"functions": []},
            }
        }

        result = self.indexer._extract_comment_keywords(
            index, Path("/tmp"), self.extractor, self.pipeline
        )

        assert result == 0


class TestExpansionPipeline:
    """Tests that exercise the expansion pipeline callback path."""

    def setup_method(self):
        self.extractor = MockKeywordExtractor()
        self.pipeline = MockExpandingPipeline()

    def test_string_keywords_with_expansion(self, tmp_path):
        indexer = MockSCIPIndexer(verbose=False)
        source = tmp_path / "app.ts"
        source.write_text('const msg = "hello world greeting";\n')

        index = {"modules": {"App": {"file": "app.ts", "functions": []}}}

        result = indexer._extract_string_keywords(index, tmp_path, self.extractor, self.pipeline)

        assert result == 1
        kw = index["modules"]["App"]["string_keywords"]
        # Expansion should have replaced keywords with expanded results
        assert "expanded_term" in kw

    def test_comment_keywords_with_expansion(self, tmp_path):
        indexer = MockSCIPIndexer(verbose=False)
        source = tmp_path / "app.ts"
        source.write_text("// handles user authentication logic\nconst x = 1;\n")

        index = {"modules": {"App": {"file": "app.ts", "functions": []}}}

        result = indexer._extract_comment_keywords(index, tmp_path, self.extractor, self.pipeline)

        assert result == 1
        kw = index["modules"]["App"]["comment_keywords"]
        assert "expanded_term" in kw


class TestVerboseErrorHandling:
    """Tests for verbose error paths in both extraction methods."""

    def setup_method(self):
        self.extractor = MockKeywordExtractor()
        self.pipeline = MockPipeline()

    def test_string_extraction_verbose_error(self, tmp_path, capsys):
        indexer = MockSCIPIndexer(verbose=True)
        # Create a file that will cause UnicodeDecodeError
        bad_file = tmp_path / "bad.ts"
        bad_file.write_bytes(b"\xff\xfe" + b"\x00" * 100)

        index = {"modules": {"Bad": {"file": "bad.ts", "functions": []}}}

        indexer._extract_string_keywords(index, tmp_path, self.extractor, self.pipeline)

        captured = capsys.readouterr()
        assert "Warning: Failed to extract strings" in captured.out

    def test_comment_extraction_verbose_error(self, tmp_path, capsys):
        indexer = MockSCIPIndexer(verbose=True)
        # Create a file that will cause UnicodeDecodeError
        bad_file = tmp_path / "bad.ts"
        bad_file.write_bytes(b"\xff\xfe" + b"\x00" * 100)

        index = {"modules": {"Bad": {"file": "bad.ts", "functions": []}}}

        indexer._extract_comment_keywords(index, tmp_path, self.extractor, self.pipeline)

        captured = capsys.readouterr()
        assert "Warning: Failed to extract comments" in captured.out
