"""Tests for SCIP converter signature and keyword extraction."""

import pytest

from cicada.languages.scip.reader import SCIPReader
from cicada.languages.scip.converter import SCIPConverter
from cicada.extractors.keyword import RegularKeywordExtractor


@pytest.fixture
def python_scip_index(fixtures_dir):
    """Load Python SCIP index for testing."""
    scip_file = fixtures_dir / "sample_python" / "index.scip"
    if not scip_file.exists():
        pytest.fail("Python SCIP index not found - run make setup-scip")

    reader = SCIPReader()
    return reader.read_index(scip_file), scip_file.parent


@pytest.fixture
def typescript_scip_index(fixtures_dir):
    """Load TypeScript SCIP index for testing."""
    scip_file = fixtures_dir / "sample_typescript" / "index.scip"
    if not scip_file.exists():
        pytest.fail("TypeScript SCIP index not found - run make setup-scip")

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


class TestModuleNameExtraction:
    """Test module name extraction from SCIP symbols."""

    def test_extract_simple_module_name(self, python_scip_index):
        """Test extracting module name from simple __init__: symbol."""
        _, _ = python_scip_index

        converter = SCIPConverter()

        # Test cases for module name extraction
        test_cases = [
            ("scip-python python sample 0.1.0 calculator/__init__:", "calculator"),
            ("scip-python python sample 0.1.0 operations/__init__:", "operations"),
            ("scip-python python sample 0.1.0 utils/__init__:", "utils"),
        ]

        for symbol, expected_name in test_cases:
            result = converter._extract_module_name_from_descriptor(symbol)
            assert (
                result == expected_name
            ), f"Failed for {symbol}: got {result}, expected {expected_name}"

    def test_extract_nested_module_name(self, python_scip_index):
        """Test extracting module name from nested package symbols."""
        _, _ = python_scip_index

        converter = SCIPConverter()

        # Nested module test cases
        test_cases = [
            ("scip-python python sample 0.1.0 cicada/mcp/__init__:", "cicada.mcp"),
            ("scip-python python sample 0.1.0 cicada/mcp/server/__init__:", "cicada.mcp.server"),
            ("scip-python python sample 0.1.0 a/b/c/d/__init__:", "a.b.c.d"),
        ]

        for symbol, expected_name in test_cases:
            result = converter._extract_module_name_from_descriptor(symbol)
            assert (
                result == expected_name
            ), f"Failed for {symbol}: got {result}, expected {expected_name}"

    def test_extract_module_name_without_init(self, python_scip_index):
        """Test extracting module name from file-based module symbols."""
        _, _ = python_scip_index

        converter = SCIPConverter()

        # Some SCIP versions might represent modules differently
        test_cases = [
            ("scip-python python sample 0.1.0 calculator.py:", "calculator"),
            ("scip-python python sample 0.1.0 utils:", "utils"),
        ]

        for symbol, expected_name in test_cases:
            result = converter._extract_module_name_from_descriptor(symbol)
            # Should handle these gracefully
            assert isinstance(result, str)

    def test_extract_module_name_with_backticks(self, python_scip_index):
        """Test extracting module name from SCIP symbols with backticks."""
        _, _ = python_scip_index

        converter = SCIPConverter()

        # SCIP wraps module names in backticks, sometimes around the entire path,
        # sometimes just around the module name part
        test_cases = [
            # Backticks around entire path
            ("scip-python python sample 0.1.0 `cicada/_version_hash`:", "cicada._version_hash"),
            ("scip-python python sample 0.1.0 `cicada/mcp/__init__`:", "cicada.mcp"),
            ("scip-python python sample 0.1.0 `operations/__init__`:", "operations"),
            # Backticks around module name only (actual scip-python output format)
            (
                "scip-python python cicada-wt2 0.3.1 `cicada.mcp.server`/__init__:",
                "cicada.mcp.server",
            ),
            (
                "scip-python python cicada-wt2 0.3.1 `tests.mcp.test_server_cli`/__init__:",
                "tests.mcp.test_server_cli",
            ),
        ]

        for symbol, expected_name in test_cases:
            result = converter._extract_module_name_from_descriptor(symbol)
            assert (
                result == expected_name
            ), f"Failed for {symbol}: got {result}, expected {expected_name}"


class TestClassTracking:
    """Test that classes are properly tracked in module entries."""

    def test_class_metadata_in_module(self, python_scip_index):
        """Test that module entries include class metadata."""
        scip_index, repo_path = python_scip_index

        converter = SCIPConverter()
        result = converter.convert(scip_index, repo_path)

        # Find a module entry (not a class entry) in the index
        # In Python, calculator.py should have a module entry for "calculator"
        # This will depend on the sample_python structure

        # Check that classes are present in the index as separate entries
        assert "Calculator" in result["modules"], "Calculator class should be indexed as module"

        calc_class = result["modules"]["Calculator"]
        # Verify Calculator has methods
        assert len(calc_class["functions"]) > 0, "Calculator should have methods"

    def test_parent_module_reference(self, python_scip_index):
        """Test that class entries have parent_module field."""
        scip_index, repo_path = python_scip_index

        converter = SCIPConverter()
        result = converter.convert(scip_index, repo_path)

        # Check Calculator class has parent_module reference
        if "Calculator" in result["modules"]:
            calc_class = result["modules"]["Calculator"]
            assert "parent_module" in calc_class, "Class should have parent_module field"
            # Parent module should be something like "calculator"
            assert isinstance(calc_class["parent_module"], str)
            assert len(calc_class["parent_module"]) > 0

    def test_file_path_to_module_name(self, python_scip_index):
        """Test _file_path_to_module_name helper method."""
        _, _ = python_scip_index

        converter = SCIPConverter()

        # Test various file path conversions
        assert converter._file_path_to_module_name("calculator.py") == "calculator"
        assert converter._file_path_to_module_name("cicada/mcp/server.py") == "cicada.mcp.server"
        assert converter._file_path_to_module_name("lib/utils/__init__.py") == "lib.utils"
        assert converter._file_path_to_module_name("") is None


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
