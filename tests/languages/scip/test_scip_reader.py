"""Comprehensive tests for SCIP reader."""

import pytest

from cicada.languages.scip import scip_pb2
from cicada.languages.scip.reader import SCIPReader


class TestSCIPReader:
    """Test SCIP file reading and parsing."""

    @pytest.fixture
    def reader(self):
        """Create a SCIPReader instance."""
        return SCIPReader()

    @pytest.fixture
    def valid_scip_file(self, tmp_path):
        """Create a valid SCIP file for testing."""
        # Create a minimal SCIP index
        index = scip_pb2.Index()
        index.metadata.version = 0  # ProtocolVersion enum (0 = UnspecifiedProtocolVersion)
        index.metadata.tool_info.name = "scip-python"
        index.metadata.tool_info.version = "0.3.0"

        # Add a document
        doc = index.documents.add()
        doc.relative_path = "test.py"
        doc.language = "python"

        # Add a symbol
        symbol = doc.symbols.add()
        symbol.symbol = "scip-python python test 1.0 test/TestClass#"
        symbol.documentation.append("Test class")

        # Save to file
        scip_file = tmp_path / "index.scip"
        with open(scip_file, "wb") as f:
            f.write(index.SerializeToString())

        return scip_file

    @pytest.fixture
    def corrupt_scip_file(self, tmp_path):
        """Create a corrupted SCIP file."""
        scip_file = tmp_path / "corrupt.scip"
        with open(scip_file, "wb") as f:
            f.write(b"not a valid protobuf")
        return scip_file

    def test_read_valid_scip_file(self, reader, valid_scip_file):
        """Should successfully read a valid SCIP file."""
        index = reader.read_index(valid_scip_file)

        assert isinstance(index, scip_pb2.Index)
        assert index.metadata.version == 0  # ProtocolVersion enum
        assert index.metadata.tool_info.name == "scip-python"
        assert len(index.documents) == 1
        assert index.documents[0].relative_path == "test.py"

    def test_read_nonexistent_file(self, reader, tmp_path):
        """Should raise FileNotFoundError for missing file."""
        nonexistent = tmp_path / "nonexistent.scip"

        with pytest.raises(FileNotFoundError) as exc_info:
            reader.read_index(nonexistent)

        assert "SCIP file not found" in str(exc_info.value)
        assert str(nonexistent) in str(exc_info.value)

    def test_read_corrupt_file(self, reader, corrupt_scip_file):
        """Should raise Exception for corrupted SCIP file."""
        with pytest.raises(Exception) as exc_info:
            reader.read_index(corrupt_scip_file)

        assert "Failed to parse SCIP file" in str(exc_info.value)
        assert str(corrupt_scip_file) in str(exc_info.value)

    def test_get_index_summary(self, reader, valid_scip_file):
        """Should generate accurate summary statistics."""
        index = reader.read_index(valid_scip_file)
        summary = reader.get_index_summary(index)

        assert summary["documents"] == 1
        assert summary["symbols"] == 1
        assert summary["occurrences"] == 0
        assert summary["scip_version"] == 0  # ProtocolVersion enum
        assert summary["tool_name"] == "scip-python"
        assert summary["tool_version"] == "0.3.0"

    def test_get_index_summary_with_multiple_documents(self, reader, tmp_path):
        """Should count symbols across multiple documents."""
        # Create index with multiple documents
        index = scip_pb2.Index()
        index.metadata.version = 0  # ProtocolVersion enum

        # Add first document with 2 symbols
        doc1 = index.documents.add()
        doc1.relative_path = "module1.py"
        doc1.symbols.add().symbol = "symbol1"
        doc1.symbols.add().symbol = "symbol2"
        doc1.occurrences.add().symbol = "symbol1"

        # Add second document with 1 symbol
        doc2 = index.documents.add()
        doc2.relative_path = "module2.py"
        doc2.symbols.add().symbol = "symbol3"
        doc2.occurrences.add().symbol = "symbol3"
        doc2.occurrences.add().symbol = "symbol3"

        # Save and read
        scip_file = tmp_path / "multi.scip"
        with open(scip_file, "wb") as f:
            f.write(index.SerializeToString())

        index = reader.read_index(scip_file)
        summary = reader.get_index_summary(index)

        assert summary["documents"] == 2
        assert summary["symbols"] == 3
        assert summary["occurrences"] == 3

    def test_get_index_summary_without_metadata(self, reader, tmp_path):
        """Should handle index without metadata gracefully."""
        # Create index without setting metadata
        # Note: Protobuf always creates metadata with defaults when deserialized
        index = scip_pb2.Index()
        doc = index.documents.add()
        doc.relative_path = "test.py"
        doc.symbols.add().symbol = "test"

        scip_file = tmp_path / "no_metadata.scip"
        with open(scip_file, "wb") as f:
            f.write(index.SerializeToString())

        index = reader.read_index(scip_file)
        summary = reader.get_index_summary(index)

        assert summary["documents"] == 1
        assert summary["symbols"] == 1
        # Protobuf creates metadata with default values
        assert summary["scip_version"] == 0  # Default ProtocolVersion
        assert summary["tool_name"] == ""  # Empty string default
        assert summary["tool_version"] == ""

    def test_get_index_summary_without_tool_info(self, reader, tmp_path):
        """Should handle metadata without tool_info gracefully."""
        index = scip_pb2.Index()
        index.metadata.version = 0  # ProtocolVersion enum
        # No tool_info set - accessing metadata.tool_info creates it with empty defaults

        doc = index.documents.add()
        doc.relative_path = "test.py"

        scip_file = tmp_path / "no_tool_info.scip"
        with open(scip_file, "wb") as f:
            f.write(index.SerializeToString())

        index = reader.read_index(scip_file)
        summary = reader.get_index_summary(index)

        assert summary["scip_version"] == 0  # ProtocolVersion enum
        # Protobuf returns empty strings for unset string fields
        assert summary["tool_name"] == ""
        assert summary["tool_version"] == ""

    def test_read_empty_scip_file(self, reader, tmp_path):
        """Should handle empty SCIP file."""
        # Create empty but valid SCIP index
        index = scip_pb2.Index()

        scip_file = tmp_path / "empty.scip"
        with open(scip_file, "wb") as f:
            f.write(index.SerializeToString())

        result = reader.read_index(scip_file)
        assert isinstance(result, scip_pb2.Index)
        assert len(result.documents) == 0

        summary = reader.get_index_summary(result)
        assert summary["documents"] == 0
        assert summary["symbols"] == 0
        assert summary["occurrences"] == 0
