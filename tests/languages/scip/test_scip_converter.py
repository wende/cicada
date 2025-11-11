"""Tests for SCIP converter signature and keyword extraction."""

import pytest
from pathlib import Path

from cicada.languages.scip.reader import SCIPReader
from cicada.languages.scip.converter import SCIPConverter
from cicada.languages.elixir.extractors.keyword import RegularKeywordExtractor


@pytest.fixture
def python_scip_index(fixtures_dir):
    """Load Python SCIP index for testing."""
    scip_file = fixtures_dir / "sample_python" / "index.scip"
    if not scip_file.exists():
        pytest.skip("Python SCIP index not found - run scip-python first")

    reader = SCIPReader()
    return reader.read_index(scip_file), scip_file.parent


@pytest.fixture
def typescript_scip_index(fixtures_dir):
    """Load TypeScript SCIP index for testing."""
    scip_file = fixtures_dir / "sample_typescript" / "index.scip"
    if not scip_file.exists():
        pytest.skip("TypeScript SCIP index not found - run scip-typescript first")

    reader = SCIPReader()
    return reader.read_index(scip_file), scip_file.parent


class TestSignatureExtraction:
    """Test signature extraction from SCIP documentation."""

    def test_python_signature_extraction(self, python_scip_index):
        """Test signature parsing from Python SCIP documentation."""
        scip_index, repo_path = python_scip_index

        converter = SCIPConverter()
        result = converter.convert(scip_index, repo_path)

        # Check Calculator module
        assert "Calculator" in result["modules"]
        calc_module = result["modules"]["Calculator"]

        # Check functions have signatures
        functions = {f["name"]: f for f in calc_module["functions"]}

        # __init__ should have signature
        assert "__init__" in functions
        init_func = functions["__init__"]
        assert "signature" in init_func
        assert "def __init__" in init_func["signature"]
        assert "initial_value" in init_func["signature"]

        # Docstring should be separate from signature
        assert "doc" in init_func
        assert "Initialize calculator" in init_func["doc"]
        # Docstring should NOT contain the signature code block
        assert "```" not in init_func["doc"]

    def test_typescript_signature_extraction(self, typescript_scip_index):
        """Test signature parsing from TypeScript SCIP documentation."""
        scip_index, repo_path = typescript_scip_index

        converter = SCIPConverter()
        result = converter.convert(scip_index, repo_path)

        # Check Calculator module
        assert "Calculator" in result["modules"]
        calc_module = result["modules"]["Calculator"]

        # Check functions have signatures
        functions = {f["name"]: f for f in calc_module["functions"]}

        # Constructor should have signature
        assert "`<constructor>`" in functions
        constructor = functions["`<constructor>`"]
        assert "signature" in constructor
        assert "constructor" in constructor["signature"]
        assert "initialValue" in constructor["signature"]

        # Docstring should be separate (if available from SCIP indexer)
        # Note: scip-typescript may not include JSDoc comments
        if "doc" in constructor:
            assert "calculator" in constructor["doc"].lower() or len(constructor["doc"]) > 0

    def test_signature_doc_separation(self, python_scip_index):
        """Test that signatures and docstrings are properly separated."""
        scip_index, repo_path = python_scip_index

        converter = SCIPConverter()
        result = converter.convert(scip_index, repo_path)

        # Check all functions
        for module_data in result["modules"].values():
            for func in module_data.get("functions", []):
                if "signature" in func:
                    # Signature should not have markdown code fences
                    assert func["signature"].count("```") == 0

                if "doc" in func:
                    # Doc should not have code fences (signature already extracted)
                    assert func["doc"].count("```") == 0


class TestKeywordExtraction:
    """Test keyword extraction in SCIP converter."""

    def test_python_keyword_extraction(self, python_scip_index):
        """Test keyword extraction on Python code."""
        scip_index, repo_path = python_scip_index

        # Initialize with keyword extraction
        extractor = RegularKeywordExtractor(verbose=False)
        converter = SCIPConverter(extract_keywords=True, keyword_extractor=extractor, verbose=False)
        result = converter.convert(scip_index, repo_path)

        # Check Calculator module has keywords
        assert "Calculator" in result["modules"]
        calc_module = result["modules"]["Calculator"]
        assert "keywords" in calc_module
        assert isinstance(calc_module["keywords"], dict)
        assert len(calc_module["keywords"]) > 0
        # Verify all scores are numeric
        for keyword, score in calc_module["keywords"].items():
            assert isinstance(keyword, str)
            assert isinstance(score, (int, float))

        # Check functions have keywords
        functions = {f["name"]: f for f in calc_module["functions"]}
        assert "add" in functions
        add_func = functions["add"]
        assert "keywords" in add_func
        assert isinstance(add_func["keywords"], dict)
        # Should extract keywords like 'add', 'number', etc.
        keywords_lower = [k.lower() for k in add_func["keywords"].keys()]
        assert any(k in keywords_lower for k in ["add", "number"])

    def test_typescript_keyword_extraction(self, typescript_scip_index):
        """Test keyword extraction on TypeScript code."""
        scip_index, repo_path = typescript_scip_index

        # Initialize with keyword extraction
        extractor = RegularKeywordExtractor(verbose=False)
        converter = SCIPConverter(extract_keywords=True, keyword_extractor=extractor, verbose=False)
        result = converter.convert(scip_index, repo_path)

        # Check Calculator module has keywords
        assert "Calculator" in result["modules"]
        calc_module = result["modules"]["Calculator"]
        assert "keywords" in calc_module
        assert len(calc_module["keywords"]) > 0

        # Keywords should include relevant terms
        keywords_lower = [k.lower() for k in calc_module["keywords"].keys()]
        assert any(k in keywords_lower for k in ["calculator", "arithmetic"])

    def test_keyword_extraction_disabled(self, python_scip_index):
        """Test that keywords are not extracted when disabled."""
        scip_index, repo_path = python_scip_index

        converter = SCIPConverter(extract_keywords=False)
        result = converter.convert(scip_index, repo_path)

        # Modules should not have keywords
        for module_data in result["modules"].values():
            assert "keywords" not in module_data

            # Functions should not have keywords
            for func in module_data.get("functions", []):
                assert "keywords" not in func


class TestLanguageAgnostic:
    """Test that SCIP converter works across languages."""

    def test_python_and_typescript_consistency(self, python_scip_index, typescript_scip_index):
        """Test that converter produces consistent structure for both languages."""
        py_scip, py_repo = python_scip_index
        ts_scip, ts_repo = typescript_scip_index

        converter = SCIPConverter()
        py_result = converter.convert(py_scip, py_repo)
        ts_result = converter.convert(ts_scip, ts_repo)

        # Both should have same top-level structure
        assert set(py_result.keys()) == set(ts_result.keys())
        assert "modules" in py_result
        assert "metadata" in py_result

        # Modules should have same structure
        for result in [py_result, ts_result]:
            for module_data in result["modules"].values():
                assert "file" in module_data
                assert "line" in module_data
                assert "functions" in module_data

                for func in module_data["functions"]:
                    assert "name" in func
                    assert "arity" in func
                    assert "args" in func
                    assert "type" in func
                    assert "line" in func
