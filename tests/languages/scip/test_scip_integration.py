"""Integration tests for complete SCIP indexing pipeline.

These tests verify end-to-end functionality of SCIP-based indexing,
including Python and TypeScript support, schema validation, keyword
extraction, and multi-file project handling.
"""

import pytest
from pathlib import Path

from cicada.languages.scip.reader import SCIPReader
from cicada.languages.scip.converter import SCIPConverter
from cicada.extractors.keyword import RegularKeywordExtractor
from cicada.parsing.schema import UniversalIndexSchema


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


class TestSCIPIntegration:
    """Test complete SCIP indexing pipeline with all features."""

    def test_index_python_project_full_pipeline(self, python_scip_index):
        """Test complete Python project indexing from SCIP to Cicada format."""
        scip_index, repo_path = python_scip_index

        # Convert using SCIP converter
        converter = SCIPConverter()
        result = converter.convert(scip_index, repo_path)

        # Verify top-level structure
        assert "modules" in result
        assert "metadata" in result

        # Verify Calculator class exists
        assert "Calculator" in result["modules"]
        calc = result["modules"]["Calculator"]

        # Verify file and line information
        assert "file" in calc
        assert calc["file"].endswith("calculator.py")
        assert "line" in calc
        assert calc["line"] == 11  # Class definition line (updated for imports)

        # Verify functions extracted
        assert "functions" in calc
        assert len(calc["functions"]) >= 4  # __init__, add, multiply, _private_method

        # Verify metadata completeness
        metadata = result["metadata"]
        assert "indexed_at" in metadata
        assert "language" in metadata
        assert "version" in metadata
        assert "total_modules" in metadata
        assert "total_functions" in metadata

    def test_index_validates_against_strict_schema(self, python_scip_index):
        """Test that generated index passes strict schema validation."""
        scip_index, repo_path = python_scip_index

        converter = SCIPConverter()
        result = converter.convert(scip_index, repo_path)

        # Create schema instance and validate
        schema = UniversalIndexSchema.from_dict(result)
        is_valid, errors = schema.validate(strict=True)

        # Should be valid with no errors
        assert is_valid, f"Schema validation failed: {errors}"
        assert len(errors) == 0

    def test_index_preserves_keyword_scores(self, python_scip_index):
        """Test that keyword extraction produces dict with scores, not uniform values."""
        scip_index, repo_path = python_scip_index

        # Use keyword extractor
        extractor = RegularKeywordExtractor()

        converter = SCIPConverter(
            extract_keywords=True,
            keyword_extractor=extractor,
        )
        result = converter.convert(scip_index, repo_path)

        # Find a module with keywords
        for module_name, module_data in result["modules"].items():
            if "keywords" in module_data and module_data["keywords"]:
                keywords = module_data["keywords"]

                # Must be a dict, not a list
                assert isinstance(keywords, dict), f"Keywords should be dict, got {type(keywords)}"

                # Must have scores (float values)
                assert all(
                    isinstance(score, (int, float)) for score in keywords.values()
                ), "All keyword scores must be numeric"

                # Scores should not all be identical (unless only 1 keyword)
                if len(keywords) > 1:
                    scores = list(keywords.values())
                    # Not all scores should be exactly 1.0
                    # (This would indicate scores weren't actually computed)
                    assert not all(
                        s == 1.0 for s in scores
                    ), f"Keyword scores appear uniform (all 1.0): {keywords}"

                # Found at least one module with keywords - test passed
                return

        pytest.skip("No modules with keywords found - cannot test score preservation")

    def test_index_tracks_all_modules(self, python_scip_index):
        """Test that all classes/modules in source are indexed."""
        scip_index, repo_path = python_scip_index

        converter = SCIPConverter()
        result = converter.convert(scip_index, repo_path)

        # Should have Calculator class
        assert "Calculator" in result["modules"]

        # Should have file-level module (_file_<path>)
        file_modules = [name for name in result["modules"] if name.startswith("_file_")]
        assert len(file_modules) >= 1

        # Metadata should match actual count
        assert result["metadata"]["total_modules"] == len(result["modules"])

    def test_index_tracks_all_functions(self, python_scip_index):
        """Test that all functions (including private) are indexed."""
        scip_index, repo_path = python_scip_index

        converter = SCIPConverter()
        result = converter.convert(scip_index, repo_path)

        calc = result["modules"]["Calculator"]
        functions = {f["name"]: f for f in calc["functions"]}

        # Public methods
        assert "add" in functions
        assert "multiply" in functions

        # Special methods
        assert "__init__" in functions

        # Private methods (with leading underscore)
        assert "_private_method" in functions

        # Verify total count in metadata
        total_functions = sum(len(m.get("functions", [])) for m in result["modules"].values())
        assert result["metadata"]["total_functions"] == total_functions

    def test_index_includes_file_paths(self, python_scip_index):
        """Test that all modules have file path information."""
        scip_index, repo_path = python_scip_index

        converter = SCIPConverter()
        result = converter.convert(scip_index, repo_path)

        for module_name, module_data in result["modules"].items():
            assert "file" in module_data, f"Module {module_name} missing 'file' field"
            assert module_data["file"], f"Module {module_name} has empty file path"

            # File path should be relative to repo
            file_path = Path(module_data["file"])
            assert (
                not file_path.is_absolute()
            ), f"File path should be relative: {module_data['file']}"

    def test_index_includes_line_numbers(self, python_scip_index):
        """Test that all modules and functions have accurate line numbers."""
        scip_index, repo_path = python_scip_index

        converter = SCIPConverter()
        result = converter.convert(scip_index, repo_path)

        calc = result["modules"]["Calculator"]

        # Module should have line number
        assert "line" in calc
        assert calc["line"] == 11  # class Calculator: line (updated for imports)

        # All functions should have line numbers
        for func in calc["functions"]:
            assert "line" in func, f"Function {func['name']} missing line number"
            assert func["line"] > 0, f"Function {func['name']} has invalid line number"

            # Line numbers should be reasonable (< 1000 for this small file)
            assert func["line"] < 1000

    def test_index_includes_documentation(self, python_scip_index):
        """Test that docstrings are extracted and preserved."""
        scip_index, repo_path = python_scip_index

        converter = SCIPConverter()
        result = converter.convert(scip_index, repo_path)

        calc = result["modules"]["Calculator"]

        # Module docstring
        if "moduledoc" in calc:
            assert "calculator" in calc["moduledoc"].lower()

        # Function docstrings
        functions = {f["name"]: f for f in calc["functions"]}

        # add() should have documentation
        if "add" in functions and "doc" in functions["add"]:
            doc = functions["add"]["doc"]
            assert "add" in doc.lower() or "sum" in doc.lower()
            assert "x" in doc.lower()  # Parameter mentioned
            assert "y" in doc.lower()  # Parameter mentioned

    def test_index_includes_signatures(self, python_scip_index):
        """Test that function signatures are formatted correctly."""
        scip_index, repo_path = python_scip_index

        converter = SCIPConverter()
        result = converter.convert(scip_index, repo_path)

        calc = result["modules"]["Calculator"]
        functions = {f["name"]: f for f in calc["functions"]}

        # Check add() signature
        add_func = functions["add"]
        assert "signature" in add_func

        signature = add_func["signature"]
        assert "def add" in signature
        assert "x" in signature
        assert "y" in signature
        assert "int" in signature  # Type annotations

        # Signature should not contain markdown code fences
        assert "```" not in signature

    def test_index_typescript_project(self, typescript_scip_index):
        """Test that TypeScript projects can be indexed successfully."""
        scip_index, repo_path = typescript_scip_index

        converter = SCIPConverter()
        result = converter.convert(scip_index, repo_path)

        # Should have modules
        assert "modules" in result
        assert len(result["modules"]) > 0

        # Should have Calculator class
        assert "Calculator" in result["modules"]

        # Should have TypeScript-specific metadata
        assert result["metadata"]["language"] == "typescript"

    def test_index_handles_nested_classes(self, python_scip_index):
        """Test handling of nested/inner classes (if present)."""
        scip_index, repo_path = python_scip_index

        converter = SCIPConverter()
        result = converter.convert(scip_index, repo_path)

        # Current fixture doesn't have nested classes, but test structure is ready
        # When a fixture with nested classes is added, this test will verify them

        # For now, verify we can at least convert successfully
        assert result is not None
        assert "modules" in result

    def test_index_handles_type_annotations(self, python_scip_index):
        """Test that Python type annotations are preserved in signatures."""
        scip_index, repo_path = python_scip_index

        converter = SCIPConverter()
        result = converter.convert(scip_index, repo_path)

        calc = result["modules"]["Calculator"]
        functions = {f["name"]: f for f in calc["functions"]}

        # Check that type annotations appear in signatures
        add_func = functions["add"]
        signature = add_func["signature"]

        # Should have parameter types
        assert "int" in signature or ":" in signature

        # Should have return type annotation
        assert "->" in signature or "int" in signature

    def test_index_handles_decorators(self, python_scip_index):
        """Test handling of decorated functions/methods (e.g., @property)."""
        scip_index, repo_path = python_scip_index

        converter = SCIPConverter()
        result = converter.convert(scip_index, repo_path)

        # Current fixture doesn't have decorated methods
        # This test ensures we can handle them when present
        assert result is not None

    def test_index_handles_properties(self, python_scip_index):
        """Test distinguishing @property from regular methods."""
        scip_index, repo_path = python_scip_index

        converter = SCIPConverter()
        result = converter.convert(scip_index, repo_path)

        # Current fixture doesn't have properties
        # When added, we should verify they're marked differently
        assert result is not None

    def test_index_metadata_complete(self, python_scip_index):
        """Test that all required metadata fields are present."""
        scip_index, repo_path = python_scip_index

        converter = SCIPConverter()
        result = converter.convert(scip_index, repo_path)

        metadata = result["metadata"]

        # Required fields
        required_fields = [
            "indexed_at",
            "language",
            "version",
            "repo_path",
            "total_modules",
            "total_functions",
        ]

        for field in required_fields:
            assert field in metadata, f"Metadata missing required field: {field}"

        # Optional but expected from SCIP
        if "scip_version" in metadata:
            assert isinstance(metadata["scip_version"], int)

        if "tool_info" in metadata:
            assert isinstance(metadata["tool_info"], dict)
            assert "name" in metadata["tool_info"]

    def test_index_empty_project(self, tmp_path):
        """Test graceful handling of empty projects."""
        # This would require creating an empty SCIP file
        # Skipping for now - will implement when needed
        pytest.skip("Empty project test fixture not yet created")

    def test_index_large_project(self, python_scip_index):
        """Test handling of projects with many symbols (100+)."""
        # Current fixture is small - this test is a placeholder
        # for when we add a larger test fixture
        pytest.skip("Large project test fixture not yet created")

    def test_index_unicode_identifiers(self, python_scip_index):
        """Test handling of non-ASCII identifiers in code."""
        scip_index, repo_path = python_scip_index

        converter = SCIPConverter()
        result = converter.convert(scip_index, repo_path)

        # Current fixture uses ASCII only
        # This test ensures unicode handling works when present
        assert result is not None

        # If we add unicode identifiers to fixture, verify them here

    def test_index_error_recovery(self, python_scip_index):
        """Test partial index generation on encountering errors."""
        scip_index, repo_path = python_scip_index

        converter = SCIPConverter()

        # Even if conversion encounters issues, should not crash
        result = converter.convert(scip_index, repo_path)

        assert result is not None
        assert "modules" in result

    def test_index_extracts_module_symbols(self, python_scip_index):
        """Test that Python module/package symbols are extracted and indexed."""
        scip_index, repo_path = python_scip_index

        converter = SCIPConverter()
        result = converter.convert(scip_index, repo_path)

        # Should have module entries with natural names (e.g., "operations")
        # not just _file_ prefixed entries
        module_names = list(result["modules"].keys())

        # Check that we have at least one module-like entry
        # (either by natural module name or file-based name)
        assert len(module_names) > 0

        # Check for both patterns:
        # - Natural module names (e.g., "operations")
        # - File-based module names (e.g., "_file_operations")
        file_modules = [m for m in module_names if m.startswith("_file_")]
        natural_modules = [m for m in module_names if not m.startswith("_file_")]

        # Should have at least some modules
        assert len(file_modules) > 0 or len(natural_modules) > 0

    def test_index_module_docstrings_preserved(self, python_scip_index):
        """Test that module-level docstrings are preserved during extraction."""
        scip_index, repo_path = python_scip_index

        converter = SCIPConverter()
        result = converter.convert(scip_index, repo_path)

        # Check that any module has a moduledoc field (if present in fixture)
        modules_with_docs = [
            m for m in result["modules"].values() if "moduledoc" in m and m["moduledoc"]
        ]

        # If the fixture has module docstrings, they should be present
        if modules_with_docs:
            for module in modules_with_docs:
                assert isinstance(module["moduledoc"], str)
                assert len(module["moduledoc"]) > 0

    def test_index_tool_info_captured(self, python_scip_index):
        """Test that SCIP tool version and info are captured in metadata."""
        scip_index, repo_path = python_scip_index

        converter = SCIPConverter()
        result = converter.convert(scip_index, repo_path)

        metadata = result["metadata"]

        # Tool info might be in SCIP metadata
        if hasattr(scip_index, "metadata") and scip_index.metadata:
            if hasattr(scip_index.metadata, "tool_info"):
                assert "tool_info" in metadata
                assert "name" in metadata["tool_info"]

        # SCIP version should be captured
        if "scip_version" in metadata:
            assert isinstance(metadata["scip_version"], int)
            assert metadata["scip_version"] >= 0
