"""
Tests for signal handling in indexer.
"""

import signal

from cicada.indexer import ElixirIndexer


def test_graceful_interrupt_sets_flag(tmp_path):
    """Test that interrupt handler sets the _interrupted flag"""
    indexer = ElixirIndexer()

    assert indexer._interrupted is False

    # Simulate interrupt
    indexer._handle_interrupt(signal.SIGINT, None)

    assert indexer._interrupted is True


def test_interrupted_indexing_saves_partial_progress(tmp_path, monkeypatch):
    """Test that interrupted indexing saves partial progress"""
    # Create test Elixir files
    test_files = []
    for i in range(5):
        file = tmp_path / f"file{i}.ex"
        file.write_text(
            f"""
defmodule TestModule{i} do
  def test_function, do: :ok
end
        """
        )
        test_files.append(file)

    indexer = ElixirIndexer()
    output_path = tmp_path / ".cicada" / "index.json"

    # Track how many files were processed
    files_processed = []
    original_parse = indexer.parser.parse_file

    def tracked_parse(file_path):
        files_processed.append(file_path)
        # Interrupt after processing 2 files
        if len(files_processed) == 2:
            indexer._interrupted = True
        return original_parse(file_path)

    monkeypatch.setattr(indexer.parser, "parse_file", tracked_parse)

    # Run indexing (should be interrupted after 2 files)
    result = indexer.index_repository(str(tmp_path), str(output_path))

    # Verify partial progress was saved
    assert output_path.exists()
    assert len(files_processed) == 2

    # Verify hashes were saved for processed files only in centralized storage
    from cicada.utils import get_hashes_path

    hashes_path = get_hashes_path(tmp_path)
    assert hashes_path.exists()

    import json

    with open(hashes_path) as f:
        hashes_data = json.load(f)

    # Should have hashes for 2 files only
    assert len(hashes_data["hashes"]) == 2


def test_incremental_with_interrupt_continues_correctly(tmp_path, monkeypatch):
    """Test that incremental indexing continues after interrupt"""
    # Create test Elixir files
    test_files = []
    for i in range(5):
        file = tmp_path / f"file{i}.ex"
        file.write_text(
            f"""
defmodule TestModule{i} do
  def test_function, do: :ok
end
        """
        )
        test_files.append(file)

    indexer1 = ElixirIndexer()
    output_path = tmp_path / ".cicada" / "index.json"

    # First run: interrupt after 2 files
    files_processed = []
    original_parse = indexer1.parser.parse_file

    def tracked_parse_first(file_path):
        files_processed.append(file_path)
        if len(files_processed) == 2:
            indexer1._interrupted = True
        return original_parse(file_path)

    monkeypatch.setattr(indexer1.parser, "parse_file", tracked_parse_first)
    indexer1.index_repository(str(tmp_path), str(output_path))

    assert len(files_processed) == 2

    # Second run: should process remaining 3 files
    indexer2 = ElixirIndexer()
    files_processed_second = []

    def tracked_parse_second(file_path):
        files_processed_second.append(file_path)
        return original_parse(file_path)

    monkeypatch.setattr(indexer2.parser, "parse_file", tracked_parse_second)
    result = indexer2.incremental_index_repository(str(tmp_path), str(output_path))

    # Should process the 3 remaining files
    assert len(files_processed_second) == 3

    # Final index should have all 5 modules
    assert len(result["modules"]) == 5
