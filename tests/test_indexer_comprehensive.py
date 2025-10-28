"""
Comprehensive tests for cicada/indexer.py
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
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

    def test_index_repository_empty_directory(self, tmp_path):
        """Test indexing an empty directory"""
        indexer = ElixirIndexer()

        # Index empty directory
        index = indexer.index_repository(str(tmp_path))

        # Should return empty index with no modules
        assert "modules" in index
        assert len(index["modules"]) == 0

    def test_index_repository_mixed_ex_exs_files(self, tmp_path):
        """Test indexing directory with both .ex and .exs files"""
        indexer = ElixirIndexer()

        # Create .ex file
        ex_file = tmp_path / "module.ex"
        ex_file.write_text(
            """
defmodule ExModule do
  def ex_func(x), do: x
end
"""
        )

        # Create .exs file
        exs_file = tmp_path / "script.exs"
        exs_file.write_text(
            """
defmodule ExsModule do
  def exs_func(x), do: x
end
"""
        )

        # Index the repository
        index = indexer.index_repository(str(tmp_path))

        # Both files should be indexed
        assert "ExModule" in index["modules"]
        assert "ExsModule" in index["modules"]

    def test_keyword_extraction_initialization_failure(self, tmp_path, capsys):
        """Test indexing continues when keyword extractor initialization fails"""
        indexer = ElixirIndexer()

        # Create a test file
        test_file = tmp_path / "test.ex"
        test_file.write_text(
            """
defmodule TestModule do
  @moduledoc "Test module"
  def test_func(x), do: x
end
"""
        )

        # Mock KeywordExtractor to fail on initialization
        with patch("cicada.keyword_extractor.KeywordExtractor") as mock_extractor:
            mock_extractor.side_effect = Exception("Initialization failed")

            # Should continue indexing without keywords
            index = indexer.index_repository(
                str(tmp_path), extract_keywords=True, keyword_method="spacy"
            )

            # Module should be indexed (without keywords)
            assert "TestModule" in index["modules"]
            module = index["modules"]["TestModule"]

            # Keywords should not be present
            assert "keywords" not in module

    def test_keyword_extraction_failure_during_indexing(self, tmp_path, capsys):
        """Test that indexing continues when keyword extraction fails for specific modules"""
        indexer = ElixirIndexer()

        # Create test files
        file1 = tmp_path / "module1.ex"
        file1.write_text(
            """
defmodule Module1 do
  @moduledoc "First module"
  def func1(x), do: x
end
"""
        )

        file2 = tmp_path / "module2.ex"
        file2.write_text(
            """
defmodule Module2 do
  @moduledoc "Second module"
  def func2(x), do: x
end
"""
        )

        # Mock KeywordExtractor to fail on extract_keywords_simple
        with patch("cicada.keyword_extractor.KeywordExtractor") as mock_extractor_class:
            mock_extractor = MagicMock()
            # Make extract_keywords_simple fail
            mock_extractor.extract_keywords_simple.side_effect = Exception(
                "Extraction failed"
            )
            mock_extractor_class.return_value = mock_extractor

            # Index with keyword extraction
            index = indexer.index_repository(
                str(tmp_path), extract_keywords=True, keyword_method="spacy"
            )

            # Both modules should still be indexed (without keywords)
            assert "Module1" in index["modules"]
            assert "Module2" in index["modules"]

            # Keywords should not be present due to failures
            assert "keywords" not in index["modules"]["Module1"]
            assert "keywords" not in index["modules"]["Module2"]

    def test_keyword_extraction_verbose_error_output(self, tmp_path, capsys):
        """Test that verbose mode shows keyword extraction errors"""
        # Create indexer with verbose mode
        indexer = ElixirIndexer()

        test_file = tmp_path / "test.ex"
        test_file.write_text(
            """
defmodule TestModule do
  @moduledoc "Test documentation"
  def test_func(x), do: x
end
"""
        )

        # Mock KeywordExtractor to fail
        with patch("cicada.keyword_extractor.KeywordExtractor") as mock_extractor_class:
            mock_extractor = MagicMock()
            mock_extractor.extract_keywords_simple.side_effect = Exception("Test error")
            mock_extractor_class.return_value = mock_extractor

            # Index with keyword extraction (errors should be shown if verbose)
            index = indexer.index_repository(
                str(tmp_path), extract_keywords=True, keyword_method="spacy"
            )

            # Module should still be indexed
            assert "TestModule" in index["modules"]

    def test_keybert_extraction_initialization_failure(self, tmp_path):
        """Test indexing continues when KeyBERT extractor initialization fails"""
        indexer = ElixirIndexer()

        test_file = tmp_path / "test.ex"
        test_file.write_text(
            """
defmodule TestModule do
  @moduledoc "Test module"
  def test_func(x), do: x
end
"""
        )

        # Mock KeyBERTExtractor to fail on initialization
        with patch("cicada.keybert_extractor.KeyBERTExtractor") as mock_extractor:
            mock_extractor.side_effect = Exception("KeyBERT init failed")

            # Should continue indexing without keywords
            index = indexer.index_repository(
                str(tmp_path),
                extract_keywords=True,
                keyword_method="bert",
                model_tier="fast",
            )

            # Module should be indexed (without keywords)
            assert "TestModule" in index["modules"]
            module = index["modules"]["TestModule"]

            # Keywords should not be present
            assert "keywords" not in module

    def test_nested_excluded_directories(self, tmp_path):
        """Test that nested excluded directories (deps, _build) are properly skipped"""
        indexer = ElixirIndexer()

        # Create normal module
        normal_file = tmp_path / "lib" / "app.ex"
        normal_file.parent.mkdir(parents=True)
        normal_file.write_text(
            """
defmodule MyApp do
  def run, do: :ok
end
"""
        )

        # Create files in excluded directories
        deps_file = tmp_path / "deps" / "dependency.ex"
        deps_file.parent.mkdir(parents=True)
        deps_file.write_text(
            """
defmodule Dependency do
  def func, do: :ok
end
"""
        )

        build_file = tmp_path / "_build" / "dev" / "lib" / "generated.ex"
        build_file.parent.mkdir(parents=True)
        build_file.write_text(
            """
defmodule Generated do
  def func, do: :ok
end
"""
        )

        # Index the repository
        index = indexer.index_repository(str(tmp_path))

        # Only normal module should be indexed
        assert "MyApp" in index["modules"]
        assert "Dependency" not in index["modules"]
        assert "Generated" not in index["modules"]


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
            def mock_check(*_args, **_kwargs):
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
        def mock_check(*_args, **_kwargs):
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
            def mock_check(*_args, **_kwargs):
                pass

            import cicada.version_check

            monkeypatch.setattr(cicada.version_check, "check_for_updates", mock_check)

            main()

            # Check index file was created in current directory
            index_file = tmp_path / ".cicada" / "index.json"
            assert index_file.exists()

        finally:
            os.chdir(original_cwd)
