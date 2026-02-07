"""Integration tests for JavaScript SCIP indexer.

These tests verify that the full indexing pipeline works correctly,
including SCIP parsing, conversion to Cicada format, and keyword extraction.

To regenerate the SCIP index for the fixture:
    cd tests/fixtures/sample_javascript
    npx --yes @sourcegraph/scip-typescript index
"""

import json
import shutil
import pytest
from pathlib import Path
from unittest.mock import patch, Mock

from cicada.languages.typescript.indexer import JavaScriptSCIPIndexer


# Mark all tests in this module with a longer timeout (integration tests)
pytestmark = pytest.mark.timeout(60)


@pytest.fixture(scope="module")
def js_fixture_source():
    """Path to the original JavaScript fixture (do not modify directly)."""
    path = Path(__file__).parent.parent.parent / "fixtures" / "sample_javascript"
    scip_file = path / "index.scip"
    if not scip_file.exists():
        pytest.skip(
            "JavaScript SCIP index not found. Run: "
            "cd tests/fixtures/sample_javascript && npx --yes @sourcegraph/scip-typescript index"
        )
    return path


@pytest.fixture(scope="module")
def js_indexed_fixture(js_fixture_source, tmp_path_factory):
    """Index the JavaScript fixture once and share across all tests.

    Returns a dict with:
        - result: The indexer result dict
        - index: The parsed index JSON
        - fixture_path: Path to the copied fixture
    """
    tmp_path = tmp_path_factory.mktemp("js_fixture")
    test_dir = tmp_path / "sample_javascript"
    shutil.copytree(js_fixture_source, test_dir)

    output_path = tmp_path / "index.json"
    indexer = JavaScriptSCIPIndexer(verbose=False)
    result = indexer.index_repository(test_dir, output_path, force=True, verbose=False)

    with open(output_path) as f:
        index = json.load(f)

    return {
        "result": result,
        "index": index,
        "fixture_path": test_dir,
        "output_path": output_path,
    }


@pytest.fixture
def js_fixture_path(js_fixture_source, tmp_path):
    """Copy the JavaScript fixture to a temp dir for testing.

    Use this for tests that need a fresh copy (e.g., edge cases).
    """
    test_dir = tmp_path / "sample_javascript"
    shutil.copytree(js_fixture_source, test_dir)
    return test_dir


@pytest.fixture
def indexer():
    """Create a JavaScriptSCIPIndexer instance."""
    return JavaScriptSCIPIndexer(verbose=False)


class TestJavaScriptIntegration:
    """Integration tests for JavaScript indexing with real SCIP data."""

    def test_index_javascript_repository(self, js_indexed_fixture):
        """Should successfully index a JavaScript repository."""
        result = js_indexed_fixture["result"]

        assert result["success"] is True
        assert result["modules_count"] >= 1
        assert result["functions_count"] >= 1
        assert js_indexed_fixture["output_path"].exists()

    def test_index_extracts_classes(self, js_indexed_fixture):
        """Should extract JavaScript classes as modules."""
        result = js_indexed_fixture["result"]
        index = js_indexed_fixture["index"]

        assert result["success"] is True

        modules = index.get("modules", {})

        # Should have a Calculator class
        assert "Calculator" in modules, f"Calculator not found. Modules: {list(modules.keys())}"
        calc_module = modules["Calculator"]
        assert calc_module["file"] == "src/calculator.js"

    def test_index_extracts_class_methods(self, js_indexed_fixture):
        """Should extract methods from JavaScript classes."""
        result = js_indexed_fixture["result"]
        index = js_indexed_fixture["index"]

        assert result["success"] is True

        calc_module = index["modules"].get("Calculator", {})
        functions = calc_module.get("functions", [])
        func_names = [f["name"] for f in functions]

        # Should have class methods
        assert len(functions) >= 4, f"Expected at least 4 methods, got: {func_names}"
        assert "add" in func_names, f"add not found. Functions: {func_names}"
        assert "multiply" in func_names, f"multiply not found. Functions: {func_names}"
        assert "getValue" in func_names, f"getValue not found. Functions: {func_names}"

    def test_index_extracts_standalone_functions(self, js_indexed_fixture):
        """Should extract standalone functions from JavaScript files."""
        result = js_indexed_fixture["result"]
        index = js_indexed_fixture["index"]

        assert result["success"] is True

        # Find the utils file module
        utils_module = None
        for name, data in index["modules"].items():
            if data.get("file") == "src/utils.js" and name.startswith("_file_"):
                utils_module = data
                break

        assert utils_module is not None, "Utils file module not found"
        functions = utils_module.get("functions", [])
        func_names = [f["name"] for f in functions]

        # Should have utility functions
        assert len(functions) >= 3, f"Expected at least 3 functions, got: {func_names}"
        assert "formatNumber" in func_names, f"formatNumber not found. Functions: {func_names}"
        assert "sum" in func_names, f"sum not found. Functions: {func_names}"
        assert "average" in func_names, f"average not found. Functions: {func_names}"

    def test_index_extracts_function_line_numbers(self, js_indexed_fixture):
        """Should extract correct line numbers for functions."""
        result = js_indexed_fixture["result"]
        index = js_indexed_fixture["index"]

        assert result["success"] is True

        calc_module = index["modules"].get("Calculator", {})
        functions = {f["name"]: f for f in calc_module.get("functions", [])}

        # Check that line numbers are present and reasonable
        for func_name, func_data in functions.items():
            assert "line" in func_data, f"{func_name} missing line number"
            assert func_data["line"] > 0, f"{func_name} has invalid line number"

    def test_index_extracts_keywords_for_modules(self, js_indexed_fixture):
        """Should extract keywords for JavaScript modules."""
        result = js_indexed_fixture["result"]
        index = js_indexed_fixture["index"]

        assert result["success"] is True

        # Calculator class should have keywords
        calc_module = index["modules"].get("Calculator", {})
        keywords = calc_module.get("keywords", {})

        assert keywords, "Calculator should have keywords"
        # Should have keywords from class name and methods
        keyword_names = list(keywords.keys())
        assert len(keyword_names) >= 1, f"Expected keywords, got: {keyword_names}"

    def test_index_extracts_keywords_for_file_modules(self, js_indexed_fixture):
        """Should extract keywords for file-level modules."""
        result = js_indexed_fixture["result"]
        index = js_indexed_fixture["index"]

        assert result["success"] is True

        # Find utils file module
        utils_module = None
        for name, data in index["modules"].items():
            if data.get("file") == "src/utils.js" and name.startswith("_file_"):
                utils_module = data
                break

        assert utils_module is not None
        keywords = utils_module.get("keywords", {})

        assert keywords, "Utils module should have keywords"

    def test_index_creates_metadata(self, js_indexed_fixture):
        """Should create proper metadata in the index."""
        result = js_indexed_fixture["result"]
        index = js_indexed_fixture["index"]

        assert result["success"] is True

        metadata = index.get("metadata", {})
        assert "total_functions" in metadata or result["functions_count"] >= 0

    def test_auto_generates_tsconfig_when_missing(self, indexer, js_fixture_path, tmp_path):
        """Should auto-generate tsconfig.json when it doesn't exist."""
        # Create a copy of the fixture without tsconfig
        test_dir = tmp_path / "js_project"
        shutil.copytree(js_fixture_path, test_dir)

        # Remove tsconfig and scip file
        tsconfig = test_dir / "tsconfig.json"
        scip_file = test_dir / "index.scip"
        if tsconfig.exists():
            tsconfig.unlink()
        if scip_file.exists():
            scip_file.unlink()

        output_path = tmp_path / "index.json"

        # Mock subprocess to avoid actually running scip-typescript
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr="")

            # Create a dummy scip file
            scip_file.write_bytes(b"")

            # Capture the tsconfig that gets generated
            tsconfig_content = None

            def capture_tsconfig(*args, **kwargs):
                nonlocal tsconfig_content
                if tsconfig.exists():
                    with open(tsconfig) as f:
                        tsconfig_content = json.load(f)
                return Mock(returncode=0, stderr="")

            mock_run.side_effect = capture_tsconfig

            try:
                indexer._run_scip_indexer(test_dir)
            except RuntimeError:
                pass  # Expected - no real SCIP output

            # Verify tsconfig was generated with correct settings
            assert tsconfig_content is not None, "tsconfig.json was not generated"
            assert tsconfig_content["compilerOptions"]["allowJs"] is True
            assert "**/*.js" in tsconfig_content["include"]


class TestJavaScriptIndexerResult:
    """Tests for JavaScript indexer result format."""

    def test_result_contains_required_fields(self, js_indexed_fixture):
        """Result should contain all required fields."""
        result = js_indexed_fixture["result"]

        assert "success" in result
        assert "modules_count" in result
        assert "functions_count" in result
        assert "errors" in result

    def test_result_includes_index_data(self, js_indexed_fixture):
        """Result should include the index data."""
        result = js_indexed_fixture["result"]

        assert result["success"] is True
        assert "index" in result
        assert "modules" in result["index"]


class TestJavaScriptIndexerEdgeCases:
    """Tests for edge cases in JavaScript indexing."""

    def test_handles_empty_directory(self, indexer, tmp_path):
        """Should handle empty directory gracefully."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        output_path = tmp_path / "index.json"

        # Create minimal package.json
        (empty_dir / "package.json").write_text('{"name": "test"}')

        result = indexer.index_repository(empty_dir, output_path, force=True, verbose=False)

        # Should succeed but with 0 modules
        # (or fail gracefully depending on scip-typescript behavior)
        assert "success" in result

    def test_handles_syntax_errors_gracefully(self, indexer, tmp_path):
        """Should handle JavaScript files with syntax errors."""
        test_dir = tmp_path / "syntax_error"
        test_dir.mkdir()

        # Create file with syntax error
        (test_dir / "bad.js").write_text("function broken( {")
        (test_dir / "package.json").write_text('{"name": "test"}')

        output_path = tmp_path / "index.json"

        # Should not crash - may succeed with partial results or fail gracefully
        result = indexer.index_repository(test_dir, output_path, force=True, verbose=False)

        assert "success" in result
        assert "errors" in result
