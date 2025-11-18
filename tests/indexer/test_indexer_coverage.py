#!/usr/bin/env python
"""
Tests for ElixirIndexer - Focus on Missing Coverage

This test file specifically targets missing coverage in cicada/indexer.py.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cicada.indexer import ElixirIndexer


@pytest.fixture
def temp_repo(tmp_path):
    """Create a temporary Elixir repository for testing."""
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()

    # Create a simple Elixir file
    lib_dir = repo_dir / "lib"
    lib_dir.mkdir()

    test_file = lib_dir / "test.ex"
    test_file.write_text(
        """
defmodule TestModule do
  @moduledoc \"\"\"
  A test module for testing
  \"\"\"

  def test_func(arg) do
    "test string"
  end
end
"""
    )

    return repo_dir


# ===== _extract_name_keywords Error Handling Tests =====


def test_extract_name_keywords_no_identifier():
    """Test _extract_name_keywords with empty identifier."""
    indexer = ElixirIndexer(verbose=False)

    # Mock keyword extractor
    mock_extractor = MagicMock()
    mock_expander = MagicMock()

    result = indexer._extract_name_keywords("", mock_extractor, mock_expander)
    assert result == {}


def test_extract_name_keywords_no_extractor():
    """Test _extract_name_keywords with no keyword extractor."""
    indexer = ElixirIndexer(verbose=False)

    result = indexer._extract_name_keywords("TestModule", None, None)
    assert result == {}


def test_extract_name_keywords_short_words_filtered():
    """Test _extract_name_keywords filters out short words (<3 chars)."""
    indexer = ElixirIndexer(verbose=False)

    mock_extractor = MagicMock()
    mock_expander = MagicMock()

    # Identifier with only short words
    result = indexer._extract_name_keywords("AB.CD", mock_extractor, mock_expander)

    # Should return empty because all words are < 3 chars
    assert result == {}


def test_extract_name_keywords_extraction_error(capsys):
    """Test _extract_name_keywords when extraction raises exception."""
    indexer = ElixirIndexer(verbose=True)

    mock_extractor = MagicMock()
    mock_extractor.extract_keywords.side_effect = ValueError("Extraction failed")

    mock_expander = MagicMock()

    result = indexer._extract_name_keywords("TestModule", mock_extractor, mock_expander)

    assert result == {}
    captured = capsys.readouterr()
    assert "Warning: Name keyword extraction failed" in captured.err


def test_extract_name_keywords_no_expansion_result():
    """Test _extract_name_keywords when expansion doesn't return dict."""
    indexer = ElixirIndexer(verbose=False)

    mock_extractor = MagicMock()
    mock_extractor.extract_keywords.return_value = {
        "top_keywords": [("test", 1.0)],
    }

    mock_expander = MagicMock()
    mock_expander.expand_keywords.return_value = ["not", "a", "dict"]  # Wrong type

    result = indexer._extract_name_keywords("TestModule", mock_extractor, mock_expander)

    # Should still return the extracted keywords even if expansion fails
    assert "test" in result


# ===== Co-change Integration Error Paths =====


def test_parse_function_signature_invalid():
    """Test _parse_function_signature with invalid signatures."""
    indexer = ElixirIndexer(verbose=False)

    # No dot
    assert indexer._parse_function_signature("test_func/2") is None

    # No slash
    assert indexer._parse_function_signature("Module.test_func") is None

    # Invalid arity
    assert indexer._parse_function_signature("Module.func/invalid") is None


def test_extract_related_functions_with_invalid_signatures():
    """Test _extract_related_functions filters out invalid signatures."""
    indexer = ElixirIndexer(verbose=False)

    function_pairs = {
        ("MyApp.Auth.validate/2", "Invalid.Signature"): 5,
        ("MyApp.Auth.validate/2", "Valid.Function/1"): 3,
    }

    result = indexer._extract_related_functions("MyApp.Auth.validate/2", function_pairs)

    # Should only include valid signature
    assert len(result) == 1
    assert result[0]["module"] == "Valid"
    assert result[0]["function"] == "Function"


# ===== Keyword Extraction Initialization Errors =====


def test_index_repository_keyword_extractor_init_failure(temp_repo, capsys):
    """Test index_repository when keyword extractor initialization fails."""
    indexer = ElixirIndexer(verbose=True)

    with patch(
        "cicada.indexer.read_keyword_extraction_config",
        return_value=("bert", "glove"),
    ):
        with patch(
            "cicada.elixir.extractors.keybert.KeyBERTExtractor",
            side_effect=ImportError("No keybert"),
        ):
            # Should fall back to not extracting keywords
            result = indexer.index_repository(
                str(temp_repo),
                str(temp_repo / "index.json"),
                extract_keywords=True,
            )

            captured = capsys.readouterr()
            assert "Warning: Could not initialize keyword extractor" in captured.out


def test_index_repository_string_extractor_init_failure(temp_repo, capsys):
    """Test index_repository when string extractor initialization fails."""
    indexer = ElixirIndexer(verbose=True)

    with patch(
        "cicada.elixir.extractors.StringExtractor",
        side_effect=ImportError("No string extractor"),
    ):
        result = indexer.index_repository(
            str(temp_repo),
            str(temp_repo / "index.json"),
            extract_string_keywords=True,
        )

        captured = capsys.readouterr()
        assert "Warning: Could not initialize string extractor" in captured.out


def test_index_repository_git_helper_init_failure(temp_repo, capsys):
    """Test index_repository when git helper initialization fails."""
    indexer = ElixirIndexer(verbose=True)

    with patch("cicada.indexer.GitHelper", side_effect=RuntimeError("No git")):
        result = indexer.index_repository(
            str(temp_repo),
            str(temp_repo / "index.json"),
            compute_timestamps=True,
        )

        captured = capsys.readouterr()
        assert "Warning: Could not initialize git helper" in captured.out


# ===== Git Timestamp Computation Errors =====


def test_index_repository_timestamp_computation_error(temp_repo):
    """Test that timestamp computation errors are silently skipped."""
    indexer = ElixirIndexer(verbose=False)

    mock_git_helper = MagicMock()
    mock_git_helper.get_functions_evolution_batch.side_effect = RuntimeError("Git error")

    with patch("cicada.indexer.GitHelper", return_value=mock_git_helper):
        result = indexer.index_repository(
            str(temp_repo),
            str(temp_repo / "index.json"),
            compute_timestamps=True,
        )

        # Should complete without timestamps
        assert "TestModule" in result["modules"]
        # Functions should not have timestamp fields due to error
        func = result["modules"]["TestModule"]["functions"][0]
        assert "created_at" not in func


# ===== Progress Reporting Tests =====


def test_index_repository_progress_reporting_single_line(temp_repo, capsys):
    """Test progress reporting without timestamps (single line)."""
    indexer = ElixirIndexer(verbose=True)

    # Create multiple files to trigger progress reporting
    lib_dir = temp_repo / "lib"
    for i in range(15):  # More than PROGRESS_REPORT_INTERVAL (10)
        file = lib_dir / f"test_{i}.ex"
        file.write_text(
            f"""
defmodule TestModule{i} do
  def test do
    :ok
  end
end
"""
        )

    result = indexer.index_repository(
        str(temp_repo), str(temp_repo / "index.json"), extract_keywords=False
    )

    captured = capsys.readouterr()
    # Should show progress updates
    assert "Processed" in captured.out
    assert "files" in captured.out


def test_index_repository_progress_reporting_multi_line(temp_repo, capsys):
    """Test progress reporting with timestamps (multi-line)."""
    indexer = ElixirIndexer(verbose=True)

    # Create multiple files
    lib_dir = temp_repo / "lib"
    for i in range(15):
        file = lib_dir / f"test_{i}.ex"
        file.write_text(
            f"""
defmodule TestModule{i} do
  def test do
    :ok
  end
end
"""
        )

    # Mock git helper to enable multi-line progress
    mock_git_helper = MagicMock()
    mock_git_helper.get_functions_evolution_batch.return_value = {}

    with patch("cicada.indexer.GitHelper", return_value=mock_git_helper):
        result = indexer.index_repository(
            str(temp_repo),
            str(temp_repo / "index.json"),
            compute_timestamps=True,
        )

        captured = capsys.readouterr()
        # Should show both file and timestamp progress
        assert "Processed" in captured.out or "Computing timestamps" in captured.out


# ===== File Parsing Error Handling =====


def test_index_repository_file_parsing_error(temp_repo):
    """Test that file parsing errors don't stop the indexing process."""
    indexer = ElixirIndexer(verbose=False)

    # Mock parser to raise error on second file
    original_parse = indexer.parser.parse_file

    def mock_parse(file_path):
        if "bad.ex" in str(file_path):
            raise ValueError("Parse error")
        return original_parse(file_path)

    indexer.parser.parse_file = mock_parse

    # Create a file that will trigger the mock error
    lib_dir = temp_repo / "lib"
    bad_file = lib_dir / "bad.ex"
    bad_file.write_text("defmodule Bad do\nend")

    result = indexer.index_repository(str(temp_repo), str(temp_repo / "index.json"))

    # Should still index the good file
    assert "TestModule" in result["modules"]


# ===== Incremental Index Tests =====


def test_incremental_index_git_helper_init_failure(temp_repo, capsys):
    """Test incremental index when git helper fails to initialize."""
    indexer = ElixirIndexer(verbose=True)

    # Create initial index
    index_path = temp_repo / "index.json"
    indexer.index_repository(str(temp_repo), str(index_path))

    # Modify file
    lib_dir = temp_repo / "lib"
    test_file = lib_dir / "test.ex"
    test_file.write_text(
        """
defmodule TestModule do
  def new_func do
    :ok
  end
end
"""
    )

    with patch("cicada.git.helper.GitHelper", side_effect=RuntimeError("No git")):
        result = indexer.incremental_index_repository(
            str(temp_repo),
            str(index_path),
            compute_timestamps=True,
        )

        captured = capsys.readouterr()
        assert "Warning: Could not initialize git helper" in captured.out


def test_incremental_index_file_processing_error(temp_repo):
    """Test incremental index handles file processing errors gracefully."""
    indexer = ElixirIndexer(verbose=False)

    # Create initial index
    index_path = temp_repo / "index.json"
    indexer.index_repository(str(temp_repo), str(index_path))

    # Mock parser to raise error
    original_parse = indexer.parser.parse_file

    def mock_parse(file_path):
        if "bad.ex" in str(file_path):
            raise ValueError("Parse error")
        return original_parse(file_path)

    indexer.parser.parse_file = mock_parse

    # Create a file that will trigger error
    lib_dir = temp_repo / "lib"
    bad_file = lib_dir / "bad.ex"
    bad_file.write_text("defmodule Bad do\nend")

    result = indexer.incremental_index_repository(
        str(temp_repo),
        str(index_path),
    )

    # Should still complete
    assert result is not None


# ===== Interrupted Indexing Tests =====


def test_index_repository_interrupted_completion(temp_repo, capsys):
    """Test interrupted indexing shows proper completion message."""
    indexer = ElixirIndexer(verbose=True)

    # Create multiple files
    lib_dir = temp_repo / "lib"
    for i in range(5):
        file = lib_dir / f"test_{i}.ex"
        file.write_text(
            f"""
defmodule TestModule{i} do
  def test do
    :ok
  end
end
"""
        )

    # Mock _check_and_report_interruption to simulate interruption
    original_check = indexer._check_and_report_interruption

    def mock_check(files_processed, total_files):
        if files_processed >= 2:  # Interrupt after processing 2 files
            indexer._interrupted = True
            return original_check(files_processed, total_files)
        return False

    indexer._check_and_report_interruption = mock_check

    result = indexer.index_repository(str(temp_repo), str(temp_repo / "index.json"))

    captured = capsys.readouterr()
    assert "Partial index saved" in captured.out or "Interrupted after processing" in captured.out


def test_incremental_index_interrupted_completion(temp_repo, capsys):
    """Test interrupted incremental indexing shows proper message."""
    indexer = ElixirIndexer(verbose=True)

    # Create initial index
    index_path = temp_repo / "index.json"
    indexer.index_repository(str(temp_repo), str(index_path))

    # Create new files
    lib_dir = temp_repo / "lib"
    for i in range(5):
        file = lib_dir / f"new_{i}.ex"
        file.write_text(
            f"""
defmodule NewModule{i} do
  def test do
    :ok
  end
end
"""
        )

    # Mock _check_and_report_interruption to simulate interruption
    original_check = indexer._check_and_report_interruption

    def mock_check(files_processed, total_files):
        if files_processed >= 2:  # Interrupt after processing 2 files
            indexer._interrupted = True
            return original_check(files_processed, total_files)
        return False

    indexer._check_and_report_interruption = mock_check

    result = indexer.incremental_index_repository(str(temp_repo), str(index_path))

    captured = capsys.readouterr()
    assert "Partial index saved" in captured.out or "Interrupted after processing" in captured.out
