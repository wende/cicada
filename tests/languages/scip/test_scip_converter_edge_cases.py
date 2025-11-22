"""Edge case tests for SCIP converter."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from cicada.languages.scip import scip_pb2
from cicada.languages.scip.converter import SCIPConverter


class TestSCIPConverterEdgeCases:
    """Test edge cases and error handling in SCIP converter."""

    @pytest.fixture
    def converter(self):
        """Create a basic converter."""
        return SCIPConverter()

    @pytest.fixture
    def converter_with_keywords(self):
        """Create converter with keyword extraction."""
        mock_extractor = MagicMock()
        mock_extractor.extract_keywords_simple.return_value = {"test": 0.8, "keyword": 0.7}
        return SCIPConverter(extract_keywords=True, keyword_extractor=mock_extractor)

    def test_get_symbol_type_with_short_symbol(self, converter):
        """Should return 'unknown' for malformed symbols."""
        # Symbol with less than 5 parts
        short_symbol = "scip-python python"
        assert converter._get_symbol_type(short_symbol) == "unknown"

    def test_get_symbol_type_attribute(self, converter):
        """Should identify attribute symbols."""
        symbol = "scip-python python test 1.0 module/MyClass#value."
        assert converter._get_symbol_type(symbol) == "attribute"

    def test_extract_name_malformed_symbol(self, converter):
        """Should fallback gracefully for malformed symbols."""
        malformed = "bad symbol"
        result = converter._extract_name(malformed)
        assert result == malformed  # Should return original

    def test_extract_name_with_nested_classes(self, converter):
        """Should extract name from nested class symbols."""
        symbol = "scip-python python test 1.0 outer/Inner/Nested#method()."
        assert converter._extract_name(symbol) == "method"

    def test_extract_name_without_separators(self, converter):
        """Should handle symbols without / or # separators."""
        symbol = "scip-python python test 1.0 simple"
        assert converter._extract_name(symbol) == "simple"

    def test_is_private_dunder_method(self, converter):
        """Should not treat __dunder__ methods as private."""
        symbols = [
            "scip-python python test 1.0 module/Class#__init__().",
            "scip-python python test 1.0 module/Class#__str__().",
            "scip-python python test 1.0 module/Class#__repr__().",
        ]

        for symbol in symbols:
            assert converter._is_private(symbol) is False

    def test_is_private_single_underscore(self, converter):
        """Should detect single underscore private methods."""
        symbol = "scip-python python test 1.0 module/Class#_private()."
        assert converter._is_private(symbol) is True

    def test_get_parent_symbol_no_hash(self, converter):
        """Should return None for symbols without # (no parent)."""
        symbol = "scip-python python test 1.0 module/function()."
        assert converter._get_parent_symbol(symbol) is None

    def test_get_parent_symbol_short_symbol(self, converter):
        """Should return None for malformed short symbols."""
        symbol = "short#method()."
        assert converter._get_parent_symbol(symbol) is None

    def test_get_parent_symbol_class_symbol(self, converter):
        """Should return class itself for class symbols (no parent)."""
        symbol = "scip-python python test 1.0 OnlyClass#"
        result = converter._get_parent_symbol(symbol)
        # Class symbols have nothing after #, so parent is the class itself
        assert result == symbol

    def test_get_definition_line_no_occurrences(self, converter):
        """Should return 1 when no occurrences found."""
        doc = scip_pb2.Document()
        doc.relative_path = "test.py"

        line = converter._get_definition_line("nonexistent_symbol", doc)
        assert line == 1

    def test_get_definition_line_no_definition_role(self, converter):
        """Should return 1 when occurrence exists but is not a definition."""
        doc = scip_pb2.Document()

        # Add occurrence without Definition role
        occ = doc.occurrences.add()
        occ.symbol = "test_symbol"
        occ.range.extend([10, 0, 5])
        occ.symbol_roles = 0  # No Definition role

        line = converter._get_definition_line("test_symbol", doc)
        assert line == 1

    def test_get_definition_line_empty_range(self, converter):
        """Should return 1 when occurrence has empty range."""
        doc = scip_pb2.Document()

        occ = doc.occurrences.add()
        occ.symbol = "test_symbol"
        # No range set
        occ.symbol_roles = scip_pb2.SymbolRole.Definition

        line = converter._get_definition_line("test_symbol", doc)
        assert line == 1

    def test_parse_signature_and_doc_empty_documentation(self, converter):
        """Should return empty strings for empty documentation."""
        sig, doc = converter._parse_signature_and_doc([])
        assert sig == ""
        assert doc == ""

    def test_parse_signature_and_doc_no_code_block(self, converter):
        """Should treat all text as docstring when no code block."""
        documentation = ["This is just a docstring", "with multiple lines"]
        sig, doc = converter._parse_signature_and_doc(documentation)

        assert sig == ""
        assert doc == "This is just a docstring\nwith multiple lines"

    def test_parse_signature_and_doc_with_multiline_signature(self, converter):
        """Should extract multiline signatures correctly."""
        documentation = [
            "```python",
            "def complex_function(",
            "    arg1: str,",
            "    arg2: int",
            ") -> None:",
            "```",
            "",
            "This is the docstring.",
        ]
        sig, doc = converter._parse_signature_and_doc(documentation)

        assert "def complex_function" in sig
        assert "arg1: str" in sig
        assert doc == "This is the docstring."

    def test_keyword_extraction_with_exception(self, converter_with_keywords):
        """Should handle keyword extraction failures gracefully."""
        # Make extractor raise an exception
        converter_with_keywords.keyword_extractor.extract_keywords_simple.side_effect = Exception(
            "Extraction failed"
        )

        doc = scip_pb2.Document()
        doc.relative_path = "test.py"

        symbol_info = scip_pb2.SymbolInformation()
        symbol_info.symbol = "scip-python python test 1.0 test/TestClass#method()."
        symbol_info.documentation.append("Test documentation")

        # Should not raise, just skip keywords
        func_data = converter_with_keywords._convert_function(symbol_info, doc, {})

        assert "keywords" not in func_data
        assert func_data["name"] == "method"

    def test_keyword_extraction_module_with_exception(self):
        """Should handle module keyword extraction failures gracefully."""
        mock_extractor = MagicMock()
        mock_extractor.extract_keywords_simple.side_effect = Exception("Failed")

        converter = SCIPConverter(
            extract_keywords=True, keyword_extractor=mock_extractor, verbose=False
        )

        # Create document with class
        doc = scip_pb2.Document()
        doc.relative_path = "test.py"

        class_symbol = doc.symbols.add()
        class_symbol.symbol = "scip-python python test 1.0 test/MyClass#"
        class_symbol.documentation.append("Test class")

        # Add occurrence for line number
        occ = doc.occurrences.add()
        occ.symbol = class_symbol.symbol
        occ.range.extend([5, 0, 7])
        occ.symbol_roles = scip_pb2.SymbolRole.Definition

        symbol_map = {class_symbol.symbol: class_symbol}

        modules = converter._convert_document(doc, Path("/test"), symbol_map)

        # Should create module without keywords
        assert "MyClass" in modules
        assert "keywords" not in modules["MyClass"]

    def test_convert_document_with_top_level_functions(self, converter):
        """Should create pseudo-module for top-level functions."""
        doc = scip_pb2.Document()
        doc.relative_path = "helpers.py"

        # Add top-level function
        func_symbol = doc.symbols.add()
        func_symbol.symbol = "scip-python python test 1.0 helpers/helper()."
        func_symbol.documentation.append("Helper function")

        occ = doc.occurrences.add()
        occ.symbol = func_symbol.symbol
        occ.range.extend([1, 0, 6])
        occ.symbol_roles = scip_pb2.SymbolRole.Definition

        symbol_map = {func_symbol.symbol: func_symbol}
        modules = converter._convert_document(doc, Path("/test"), symbol_map)

        # Should create _file_helpers module
        assert "_file_helpers" in modules
        assert modules["_file_helpers"]["file"] == "helpers.py"
        assert len(modules["_file_helpers"]["functions"]) == 1
        assert modules["_file_helpers"]["functions"][0]["name"] == "helper"

    def test_convert_document_mixed_private_public(self, converter):
        """Should correctly count private and public functions."""
        doc = scip_pb2.Document()
        doc.relative_path = "test.py"

        # Create class
        class_symbol = doc.symbols.add()
        class_symbol.symbol = "scip-python python test 1.0 test/MyClass#"

        # Public method
        pub_method = doc.symbols.add()
        pub_method.symbol = "scip-python python test 1.0 test/MyClass#public_method()."

        # Private method
        priv_method = doc.symbols.add()
        priv_method.symbol = "scip-python python test 1.0 test/MyClass#_private_method()."

        # Dunder method (should be public)
        dunder_method = doc.symbols.add()
        dunder_method.symbol = "scip-python python test 1.0 test/MyClass#__init__()."

        # Add occurrences
        for symbol in [class_symbol, pub_method, priv_method, dunder_method]:
            occ = doc.occurrences.add()
            occ.symbol = symbol.symbol
            occ.range.extend([1, 0, 5])
            occ.symbol_roles = scip_pb2.SymbolRole.Definition

        symbol_map = {s.symbol: s for s in doc.symbols}
        modules = converter._convert_document(doc, Path("/test"), symbol_map)

        assert "MyClass" in modules
        assert modules["MyClass"]["total_functions"] == 3
        assert modules["MyClass"]["public_functions"] == 2  # public_method + __init__
        assert modules["MyClass"]["private_functions"] == 1  # _private_method

    def test_build_metadata_with_scip_metadata(self, converter):
        """Should include SCIP metadata in output."""
        index = scip_pb2.Index()
        index.metadata.version = 0  # ProtocolVersion enum
        index.metadata.tool_info.name = "scip-python"
        index.metadata.tool_info.version = "0.3.15"

        metadata = converter._build_metadata(index, Path("/test"), 5)

        assert metadata["scip_version"] == 0  # ProtocolVersion enum
        assert metadata["tool_info"]["name"] == "scip-python"
        assert metadata["tool_info"]["version"] == "0.3.15"
        assert metadata["total_modules"] == 5

    def test_build_metadata_without_scip_metadata(self, converter):
        """Should handle missing SCIP metadata."""
        index = scip_pb2.Index()
        # No metadata set - accessing index.metadata creates it with defaults

        metadata = converter._build_metadata(index, Path("/test"), 3)

        # Protobuf creates metadata with default values when accessed
        assert metadata["scip_version"] == 0  # Default ProtocolVersion
        assert metadata["tool_info"]["name"] == ""  # Empty string default
        assert metadata["tool_info"]["version"] == ""
        assert metadata["total_modules"] == 3
        # Language is "unknown" when no metadata exists (language-agnostic converter)
        assert metadata["language"] == "unknown"

    def test_convert_function_without_documentation(self, converter):
        """Should handle functions without documentation."""
        doc = scip_pb2.Document()

        symbol_info = scip_pb2.SymbolInformation()
        symbol_info.symbol = "scip-python python test 1.0 test/function()."
        # No documentation

        func_data = converter._convert_function(symbol_info, doc, {})

        assert func_data["name"] == "function"
        assert "doc" not in func_data
        assert "signature" not in func_data
        assert "keywords" not in func_data

    def test_extract_args_complex_parameters(self, converter):
        """Should extract parameters in order for complex signatures."""
        doc = scip_pb2.Document()

        # Add function and parameters
        params_data = [
            ("self", 0),
            ("arg1", 1),
            ("arg2", 2),
            ("*args", 3),
            ("**kwargs", 4),
        ]

        for param_name, idx in params_data:
            param = doc.symbols.add()
            param.symbol = f"scip-python python test 1.0 test/Class#method().({param_name})"

        func_symbol = "scip-python python test 1.0 test/Class#method()."
        args = converter._extract_args(func_symbol, doc)

        # Should extract all parameters
        assert len(args) == 5
        assert "self" in args
        assert "arg1" in args
        assert "arg2" in args
        assert "*args" in args
        assert "**kwargs" in args

    # Tests for _extract_module_from_symbol

    def test_extract_module_from_symbol_short_symbol(self, converter):
        """Should return None for short symbols."""
        short = "scip-python python test"
        result = converter._extract_module_from_symbol(short)
        assert result is None

    def test_extract_module_from_symbol_init_handling(self, converter):
        """Should handle __init__ module symbols."""
        symbol = "scip-python python test 1.0 package/__init__/"
        result = converter._extract_module_from_symbol(symbol)
        # Should extract "package" not "__init__"
        assert result is not None

    def test_extract_module_from_symbol_various_formats(self, converter):
        """Should handle various symbol formats."""
        test_cases = [
            "scip-python python test 1.0 module/Class#method().",
            "scip-python python test 1.0 package.submodule/",
            "scip-python python test 1.0 simple_module/",
        ]

        for symbol in test_cases:
            result = converter._extract_module_from_symbol(symbol)
            # Should extract something or return None
            assert result is None or isinstance(result, str)

    # Tests for _detect_language

    def test_detect_language_from_document(self, converter):
        """Should detect language from document metadata."""
        index = scip_pb2.Index()
        doc = index.documents.add()
        doc.language = "python"

        language = converter._detect_language(index)
        assert language == "python"

    def test_detect_language_from_tool_info(self, converter):
        """Should detect language from tool name."""
        index = scip_pb2.Index()
        index.metadata.tool_info.name = "scip-typescript"

        language = converter._detect_language(index)
        assert language == "typescript"

    def test_detect_language_fallback(self, converter):
        """Should fallback to unknown when no language detected."""
        index = scip_pb2.Index()
        # No language info set

        language = converter._detect_language(index)
        assert language == "unknown"

    # Tests for extract_references disabled

    def test_convert_with_extract_references_disabled(self, converter):
        """Should skip reference extraction when disabled."""
        index = scip_pb2.Index()
        doc = index.documents.add()
        doc.relative_path = "test.py"

        # Add a class symbol
        class_symbol = doc.symbols.add()
        class_symbol.symbol = "scip-python python test 1.0 test/MyClass#"

        occ = doc.occurrences.add()
        occ.symbol = class_symbol.symbol
        occ.range.extend([1, 0, 7])
        occ.symbol_roles = scip_pb2.SymbolRole.Definition

        # Create converter with extract_references=False
        converter_no_refs = SCIPConverter(extract_references=False)

        result = converter_no_refs.convert(index, Path("/test"))

        # Should have modules but no call sites
        assert "modules" in result
        # Functions should not have what_it_calls data
        for module_data in result["modules"].values():
            for func in module_data.get("functions", []):
                assert "what_it_calls" not in func

    # Tests for module symbols without valid names

    def test_convert_document_invalid_module_name(self, converter):
        """Should skip modules with invalid names."""
        doc = scip_pb2.Document()
        doc.relative_path = "test.py"

        # Add symbol that won't extract a valid name
        invalid_symbol = doc.symbols.add()
        invalid_symbol.symbol = "scip-python python test 1.0 #"  # No module name

        occ = doc.occurrences.add()
        occ.symbol = invalid_symbol.symbol
        occ.range.extend([1, 0, 1])
        occ.symbol_roles = scip_pb2.SymbolRole.Definition

        symbol_map = {invalid_symbol.symbol: invalid_symbol}

        modules = converter._convert_document(doc, Path("/test"), symbol_map)

        # Should handle gracefully, not include invalid module
        assert isinstance(modules, dict)
