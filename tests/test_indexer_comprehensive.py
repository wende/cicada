"""
Comprehensive tests for cicada/indexer.py
"""

import pytest
from pathlib import Path
from cicada.indexer import ElixirIndexer


class TestElixirIndexerErrorHandling:
    """Tests for error handling in ElixirIndexer"""

    def test_index_repository_nonexistent_path(self):
        """Test indexing non-existent repository raises ValueError"""
        indexer = ElixirIndexer()

        with pytest.raises(ValueError, match="does not exist"):
            indexer.index_repository("/nonexistent/path")

    def test_index_repository_with_parse_errors(self, tmp_path, capsys):
        """Test indexing repository with files that have parse errors"""
        indexer = ElixirIndexer()

        # Create a valid file
        valid_file = tmp_path / "valid.ex"
        valid_file.write_text(
            """
defmodule ValidModule do
  def valid_func(x), do: x
end
"""
        )

        # Create an invalid file
        invalid_file = tmp_path / "invalid.ex"
        invalid_file.write_text("defmodule Broken do\n  def incomplete(")

        # Index the repository
        index = indexer.index_repository(str(tmp_path))

        # Should skip the invalid file and continue
        assert "ValidModule" in index["modules"]
        assert "Broken" not in index["modules"]

        # Should print skip message
        captured = capsys.readouterr()
        assert "Parse error" in captured.out


class TestElixirIndexerMainFunction:
    """Tests for the main() CLI function"""

    def test_main_with_default_args(self, tmp_path, monkeypatch):
        """Test main() with default arguments"""
        from cicada.indexer import main
        import sys
        import os

        # Create a test repository
        test_file = tmp_path / "test.ex"
        test_file.write_text(
            """
defmodule TestModule do
  def test_func(x), do: x
end
"""
        )

        # Change to the tmp_path directory so index is created there
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Mock sys.argv to index current directory (tmp_path)
            monkeypatch.setattr(sys, "argv", ["indexer.py"])

            # Mock check_for_updates to do nothing
            def mock_check(*args, **kwargs):
                pass

            import cicada.version_check

            monkeypatch.setattr(cicada.version_check, "check_for_updates", mock_check)

            # Run main - should not raise
            main()

            # Check index file was created
            index_file = tmp_path / ".cicada" / "index.json"
            assert index_file.exists()
        finally:
            # Restore original directory
            os.chdir(original_cwd)

    def test_main_with_custom_output_path(self, tmp_path, monkeypatch):
        """Test main() with custom output path"""
        from cicada.indexer import main
        import sys

        test_file = tmp_path / "test.ex"
        test_file.write_text(
            """
defmodule TestModule do
  def test_func(x), do: x
end
"""
        )

        output_path = tmp_path / "custom" / "index.json"

        monkeypatch.setattr(
            sys, "argv", ["indexer.py", str(tmp_path), "--output", str(output_path)]
        )

        # Mock check_for_updates
        def mock_check(*args, **kwargs):
            pass

        import cicada.version_check

        monkeypatch.setattr(cicada.version_check, "check_for_updates", mock_check)

        main()

        # Check custom output path was used
        assert output_path.exists()

    def test_main_with_current_directory(self, tmp_path, monkeypatch):
        """Test main() with current directory (no args)"""
        from cicada.indexer import main
        import sys

        # Create test file in tmp_path
        test_file = tmp_path / "test.ex"
        test_file.write_text(
            """
defmodule TestModule do
  def test_func(x), do: x
end
"""
        )

        # Change to tmp_path directory
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Mock sys.argv with no repository argument (use current dir)
            monkeypatch.setattr(sys, "argv", ["indexer.py"])

            # Mock check_for_updates
            def mock_check(*args, **kwargs):
                pass

            import cicada.version_check

            monkeypatch.setattr(cicada.version_check, "check_for_updates", mock_check)

            main()

            # Check index file was created in current directory
            index_file = tmp_path / ".cicada" / "index.json"
            assert index_file.exists()

        finally:
            os.chdir(original_cwd)
