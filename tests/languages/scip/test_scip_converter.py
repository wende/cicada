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


class TestNormalizeKeywords:
    """Test _normalize_keywords helper method."""

    def test_empty_input(self):
        """Test with empty input returns empty dict."""
        converter = SCIPConverter()
        assert converter._normalize_keywords({}) == {}
        assert converter._normalize_keywords([]) == {}
        assert converter._normalize_keywords(None) == {}

    def test_tf_scores_format(self):
        """Test dict with 'tf_scores' key (RegularKeywordExtractor format)."""
        converter = SCIPConverter()
        input_data = {"tf_scores": {"keyword1": 0.5, "keyword2": 0.3}}
        result = converter._normalize_keywords(input_data)
        assert result == {"keyword1": 0.5, "keyword2": 0.3}

    def test_top_keywords_format(self):
        """Test dict with 'top_keywords' key (list of tuples)."""
        converter = SCIPConverter()
        input_data = {"top_keywords": [("keyword1", 0.5), ("keyword2", 0.3)]}
        result = converter._normalize_keywords(input_data)
        assert result == {"keyword1": 0.5, "keyword2": 0.3}

    def test_simple_dict_format(self):
        """Test simple dict with numeric values."""
        converter = SCIPConverter()
        input_data = {"keyword1": 0.5, "keyword2": 0.3}
        result = converter._normalize_keywords(input_data)
        assert result == {"keyword1": 0.5, "keyword2": 0.3}

    def test_dict_with_non_numeric_values(self):
        """Test dict with non-numeric values returns empty."""
        converter = SCIPConverter()
        input_data = {"keyword1": "not_a_number", "keyword2": {"nested": True}}
        result = converter._normalize_keywords(input_data)
        assert result == {}

    def test_list_of_tuples_format(self):
        """Test list of (keyword, score) tuples."""
        converter = SCIPConverter()
        input_data = [("keyword1", 0.5), ("keyword2", 0.3)]
        result = converter._normalize_keywords(input_data)
        assert result == {"keyword1": 0.5, "keyword2": 0.3}

    def test_integer_scores(self):
        """Test that integer scores are accepted."""
        converter = SCIPConverter()
        input_data = {"keyword1": 5, "keyword2": 3}
        result = converter._normalize_keywords(input_data)
        assert result == {"keyword1": 5, "keyword2": 3}


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


class TestCrossFileArityResolution:
    """Test that cross-file call dependencies resolve arity correctly."""

    def test_cross_file_arity_resolution(self, python_scip_index):
        """Test that calls to functions in other files have correct arity.

        The sample_python fixture has cross-file calls:
        - main.py calls operations.add(x, y) which has arity 2
        - utils.py calls operations.add(result, num) which has arity 2
        - utils.py calls operations.divide(total, len(numbers)) which has arity 2

        Before the fix, cross-file calls would have arity=0 because we only
        looked up arity in the current document's symbols. Now we use a global
        arity map that includes all symbols from all files.
        """
        scip_index, repo_path = python_scip_index

        # Enable reference extraction to get dependencies
        converter = SCIPConverter(extract_references=True)
        result = converter.convert(scip_index, repo_path)

        # Find the utils file module (contains cross-file calls to operations)
        utils_module = None
        for name, module_data in result["modules"].items():
            if module_data.get("file", "").endswith("utils.py"):
                utils_module = module_data
                break

        assert utils_module is not None, "Should find utils module"

        # Find functions that have dependencies on operations module
        functions_with_ops_deps = []
        for func in utils_module.get("functions", []):
            deps = func.get("dependencies", [])
            for dep in deps:
                if dep.get("module", "").endswith("operations"):
                    functions_with_ops_deps.append((func["name"], dep))

        # Should have some cross-file dependencies
        assert len(functions_with_ops_deps) > 0, "Should have cross-file dependencies"

        # Verify that cross-file calls have arity > 0
        # operations.add, operations.multiply, operations.divide all have arity 2
        for func_name, dep in functions_with_ops_deps:
            if dep["function"] in ["add", "subtract", "multiply", "divide"]:
                assert dep["arity"] == 2, (
                    f"Cross-file call {func_name} -> operations.{dep['function']} "
                    f"should have arity=2, got {dep['arity']}"
                )


class TestDocstringDerivedArity:
    """Test that arity from docstrings is used for dependency resolution."""

    def test_docstring_arity_enriches_global_map(self):
        """Test that docstring-derived arity updates global arity map.

        This addresses the PR feedback about dependency arity ignoring
        docstring-only signatures. When SCIP doesn't emit parameter occurrences
        (symbol_data.arity == 0), but the function has a signature in its
        documentation, we should extract the arity from the docstring and
        use it for dependency resolution.
        """
        from unittest.mock import MagicMock, patch
        from pathlib import Path

        converter = SCIPConverter(extract_references=True)

        # Create a mock SCIP index with:
        # 1. A function with no parameter occurrences but has a docstring signature
        # 2. A caller function that calls the first function
        mock_index = MagicMock()
        mock_doc = MagicMock()
        mock_doc.relative_path = "test.py"
        mock_doc.occurrences = []

        # Mock symbol info with docstring containing signature
        mock_symbol_info = MagicMock()
        mock_symbol_info.symbol = "scip-python python test 1.0 test/callee()."
        mock_symbol_info.documentation = [
            "```python\ndef callee(a: int, b: str, c: float) -> bool:\n```",
            "A test function with three parameters.",
        ]

        mock_doc.symbols = [mock_symbol_info]
        mock_index.documents = [mock_doc]

        # Patch the methods we need
        with patch.object(converter, "_extract_document_data") as mock_extract:
            from cicada.languages.scip.converter import DocumentData, SymbolData

            # Create symbol data with arity=0 (no parameter occurrences)
            symbol_data = SymbolData(
                symbol="scip-python python test 1.0 test/callee().",
                line=10,
                symbol_type="function",
                parent_symbol=None,
                arity=0,  # No parameter occurrences
            )

            doc_data = DocumentData(
                relative_path="test.py",
                aliases={},
                symbols={"scip-python python test 1.0 test/callee().": symbol_data},
                function_ranges=[],
                function_start_lines=[],
                call_sites=[],
                dependencies=[],
            )

            mock_extract.return_value = doc_data

            # Build the symbol map as the converter would
            symbol_map = {mock_symbol_info.symbol: mock_symbol_info}

            with patch.object(converter, "_build_symbol_map", return_value=symbol_map):
                with patch.object(converter, "_process_document_data", return_value={}):
                    with patch.object(
                        converter,
                        "_build_metadata",
                        return_value={"language": "python"},
                    ):
                        # Run the convert method
                        converter.convert(mock_index, Path("/test"))

                        # The Phase 1.5 should have extracted arity from docstring
                        # and passed it to _process_document_data via global_arity_map
                        # We can verify by checking the call args
                        call_args = converter._process_document_data.call_args
                        global_arity_map = call_args[0][2]  # Third positional arg

                        # The docstring has 3 args: a, b, c
                        assert (
                            global_arity_map.get("scip-python python test 1.0 test/callee().") == 3
                        ), f"Expected arity 3 from docstring, got {global_arity_map}"

    def test_parameter_occurrences_take_precedence(self):
        """Test that parameter occurrences take precedence over docstring arity.

        When SCIP emits parameter occurrences, we should use that arity
        even if the docstring suggests a different number (e.g., docstring
        might include optional params not tracked by SCIP).
        """
        from unittest.mock import MagicMock, patch
        from pathlib import Path

        converter = SCIPConverter(extract_references=True)

        mock_index = MagicMock()
        mock_doc = MagicMock()
        mock_doc.relative_path = "test.py"
        mock_doc.occurrences = []

        # Docstring says 3 args, but SCIP found 2 parameter occurrences
        mock_symbol_info = MagicMock()
        mock_symbol_info.symbol = "scip-python python test 1.0 test/func()."
        mock_symbol_info.documentation = [
            "```python\ndef func(a: int, b: str, c: float = None) -> bool:\n```",
        ]

        mock_doc.symbols = [mock_symbol_info]
        mock_index.documents = [mock_doc]

        with patch.object(converter, "_extract_document_data") as mock_extract:
            from cicada.languages.scip.converter import DocumentData, SymbolData

            # Symbol has arity=2 from parameter occurrences
            symbol_data = SymbolData(
                symbol="scip-python python test 1.0 test/func().",
                line=10,
                symbol_type="function",
                parent_symbol=None,
                arity=2,  # Parameter occurrences found 2 params
            )

            doc_data = DocumentData(
                relative_path="test.py",
                aliases={},
                symbols={"scip-python python test 1.0 test/func().": symbol_data},
                function_ranges=[],
                function_start_lines=[],
                call_sites=[],
                dependencies=[],
            )

            mock_extract.return_value = doc_data

            symbol_map = {mock_symbol_info.symbol: mock_symbol_info}

            with patch.object(converter, "_build_symbol_map", return_value=symbol_map):
                with patch.object(converter, "_process_document_data", return_value={}):
                    with patch.object(
                        converter,
                        "_build_metadata",
                        return_value={"language": "python"},
                    ):
                        converter.convert(mock_index, Path("/test"))

                        call_args = converter._process_document_data.call_args
                        global_arity_map = call_args[0][2]

                        # Should use arity from parameter occurrences (2),
                        # not docstring (3)
                        assert (
                            global_arity_map.get("scip-python python test 1.0 test/func().") == 2
                        ), f"Expected arity 2 from param occurrences, got {global_arity_map}"
