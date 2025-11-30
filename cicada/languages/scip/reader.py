"""SCIP index file reader.

Provides functionality to load and parse .scip files (Protocol Buffer format).
"""

from pathlib import Path

import cicada.languages.scip.scip_pb2 as scip_pb2


class SCIPReader:
    """Read and parse SCIP index files."""

    def read_index(self, scip_file: Path) -> scip_pb2.Index:
        """
        Load and parse a .scip file.

        Args:
            scip_file: Path to .scip file

        Returns:
            Parsed SCIP Index protobuf message

        Raises:
            FileNotFoundError: If .scip file doesn't exist
            Exception: If file is corrupted or cannot be parsed
        """
        if not scip_file.exists():
            raise FileNotFoundError(f"SCIP file not found: {scip_file}")

        try:
            with open(scip_file, "rb") as f:
                index = scip_pb2.Index()
                index.ParseFromString(f.read())
                return index
        except Exception as e:
            raise Exception(f"Failed to parse SCIP file {scip_file}: {e}") from e

    def get_index_summary(self, index: scip_pb2.Index) -> dict:
        """
        Generate human-readable summary of index contents.

        Args:
            index: Parsed SCIP Index

        Returns:
            Dictionary containing summary statistics
        """
        total_documents = len(index.documents)
        total_symbols = sum(len(doc.symbols) for doc in index.documents)
        total_occurrences = sum(len(doc.occurrences) for doc in index.documents)

        return {
            "documents": total_documents,
            "symbols": total_symbols,
            "occurrences": total_occurrences,
            "scip_version": index.metadata.version if index.metadata else "unknown",
            "tool_name": (
                index.metadata.tool_info.name
                if index.metadata and index.metadata.tool_info
                else "unknown"
            ),
            "tool_version": (
                index.metadata.tool_info.version
                if index.metadata and index.metadata.tool_info
                else "unknown"
            ),
        }
