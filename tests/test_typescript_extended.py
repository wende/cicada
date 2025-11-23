"""Extended tests for TypeScript support focusing on specific structures.

This test file targets specific TypeScript structures defined in
tests/fixtures/sample_typescript/typescript_features.ts
to verify they are correctly indexed and searchable.
"""

import pytest
from pathlib import Path

from cicada.languages.scip.reader import SCIPReader
from cicada.languages.scip.converter import SCIPConverter
from cicada.query import QueryOrchestrator


@pytest.fixture(scope="module")
def typescript_index():
    """Load the TypeScript SCIP index for testing."""
    fixture_path = Path(__file__).parent / "fixtures" / "sample_typescript"
    scip_path = fixture_path / "index.scip"

    if not scip_path.exists():
        pytest.skip("TypeScript SCIP index not generated. Run tests/setup_fixtures.sh")

    # Read SCIP index
    reader = SCIPReader()
    scip_index = reader.read_index(scip_path)

    # Convert SCIP index to Cicada index format
    converter = SCIPConverter(verbose=False)
    index = converter.convert(scip_index, fixture_path)

    return index


class TestTypeScriptStructures:
    """Test specific TypeScript structures."""

    def test_class_structure(self, typescript_index):
        """Test indexing of the Container class and its members."""
        orchestrator = QueryOrchestrator(typescript_index)

        # Search for the Container class
        result = orchestrator.execute_query("Container")
        assert isinstance(result, str)
        assert "Container" in result

        # Search for methods
        result = orchestrator.execute_query("getInstanceCount")
        assert "getInstanceCount" in result

        # Search for private method
        # Note: Private methods are indexed as 'private' type
        result = orchestrator.execute_query("_validateItem", scope="all")
        assert "_validateItem" in result

    def test_interface_implementation(self, typescript_index):
        """Test indexing of interfaces and their implementations."""
        orchestrator = QueryOrchestrator(typescript_index)

        # Search for DataProcessor interface
        result = orchestrator.execute_query("DataProcessor")
        assert "DataProcessor" in result

        # Search for StringProcessor class
        result = orchestrator.execute_query("StringProcessor")
        assert "StringProcessor" in result

        # Verify methods of implementation are found
        result = orchestrator.execute_query("process", filter_type="functions")
        assert "process" in result

    def test_generic_functions(self, typescript_index):
        """Test indexing of generic functions."""
        orchestrator = QueryOrchestrator(typescript_index)

        # Search for generic function mapItems
        result = orchestrator.execute_query("mapItems")
        assert "mapItems" in result

        # Search for generic function with constraint getLength
        result = orchestrator.execute_query("getLength")
        assert "getLength" in result

    def test_async_await_structure(self, typescript_index):
        """Test indexing of async functions."""
        orchestrator = QueryOrchestrator(typescript_index)

        # Search for asyncProcess
        result = orchestrator.execute_query("asyncProcess")
        assert "asyncProcess" in result

        # Search for fetchData
        result = orchestrator.execute_query("fetchData")
        assert "fetchData" in result

        # Search for AsyncHandler class
        result = orchestrator.execute_query("AsyncHandler")
        assert "AsyncHandler" in result

    def test_arrow_functions(self, typescript_index):
        """Test indexing of arrow functions."""
        orchestrator = QueryOrchestrator(typescript_index)

        # Search for arrowAdd
        result = orchestrator.execute_query("arrowAdd")
        assert "arrowAdd" in result

        # Search for arrowMultiply
        result = orchestrator.execute_query("arrowMultiply")
        assert "arrowMultiply" in result

        # Search for createAdder (higher order function)
        result = orchestrator.execute_query("createAdder")
        assert "createAdder" in result

    def test_imports_and_cross_file_references(self, typescript_index):
        """Test that symbols imported from other files are reachable."""
        orchestrator = QueryOrchestrator(typescript_index)

        # 'add' is imported in typescript_features.ts from operations.ts
        # We search for 'add' and ensure we find the definition
        result = orchestrator.execute_query("add")
        assert "add" in result

        # 'Calculator' uses 'operations.add', let's ensure we can find 'Calculator'
        result = orchestrator.execute_query("Calculator")
        assert "Calculator" in result

    def test_type_alias(self, typescript_index):
        """Test indexing of type aliases."""
        orchestrator = QueryOrchestrator(typescript_index)

        # Search for ProcessResult type alias
        result = orchestrator.execute_query("ProcessResult")
        # Depending on how SCIP handles type aliases, this might appear as a "function" (symbol) or similar
        # The key is that it is found
        assert "ProcessResult" in result
