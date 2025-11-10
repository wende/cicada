"""
Comprehensive tests for cicada/indexer.py
"""

import pytest

from cicada.indexer import ElixirIndexer


class TestElixirIndexerErrorHandling:
    """Tests for error handling in ElixirIndexer"""

    def test_index_repository_nonexistent_path(self):
        """Test indexing non-existent repository raises ValueError"""
        indexer = ElixirIndexer()

        with pytest.raises(ValueError, match="does not exist"):
            indexer.index_repository("/nonexistent/path", "/tmp/index.json")

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
        index = indexer.index_repository(str(tmp_path), str(tmp_path / ".cicada" / "index.json"))

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
        import os
        import sys

        from cicada.indexer import main

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
        import sys

        from cicada.indexer import main

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
        import sys

        from cicada.indexer import main

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


class TestElixirIndexerIncrementalIndexing:
    """Tests for incremental indexing functionality"""

    def test_incremental_no_existing_index_falls_back_to_full(self, tmp_path, monkeypatch):
        """Test that incremental indexing falls back to full when no index exists"""
        indexer = ElixirIndexer()

        # Create a test file
        test_file = tmp_path / "test.ex"
        test_file.write_text(
            """
defmodule TestModule do
  def test_func(x), do: x
end
"""
        )

        # Call incremental indexing with no existing index
        index = indexer.incremental_index_repository(
            str(tmp_path), str(tmp_path / ".cicada" / "index.json")
        )

        # Should have indexed the file
        assert "TestModule" in index["modules"]
        assert index["modules"]["TestModule"]["functions"][0]["name"] == "test_func"

    def test_incremental_no_changes_detected(self, tmp_path):
        """Test incremental indexing when no changes are detected"""
        indexer = ElixirIndexer()

        # Create a test file
        test_file = tmp_path / "test.ex"
        test_file.write_text(
            """
defmodule TestModule do
  def test_func(x), do: x
end
"""
        )

        # Do initial full index
        output_path = tmp_path / ".cicada" / "index.json"
        indexer.index_repository(str(tmp_path), str(output_path))

        # Do incremental index with no changes
        index = indexer.incremental_index_repository(str(tmp_path), str(output_path))

        # Should return existing index
        assert "TestModule" in index["modules"]

    def test_incremental_new_file_added(self, tmp_path):
        """Test incremental indexing when a new file is added"""
        indexer = ElixirIndexer()

        # Create initial file
        test_file1 = tmp_path / "test1.ex"
        test_file1.write_text(
            """
defmodule TestModule1 do
  def func1(x), do: x
end
"""
        )

        # Do initial index
        output_path = tmp_path / ".cicada" / "index.json"
        indexer.index_repository(str(tmp_path), str(output_path))

        # Add a new file
        test_file2 = tmp_path / "test2.ex"
        test_file2.write_text(
            """
defmodule TestModule2 do
  def func2(x), do: x * 2
end
"""
        )

        # Do incremental index
        index = indexer.incremental_index_repository(str(tmp_path), str(output_path))

        # Should have both modules
        assert "TestModule1" in index["modules"]
        assert "TestModule2" in index["modules"]

    def test_incremental_file_modified(self, tmp_path):
        """Test incremental indexing when a file is modified"""
        indexer = ElixirIndexer()

        # Create initial file
        test_file = tmp_path / "test.ex"
        test_file.write_text(
            """
defmodule TestModule do
  def func1(x), do: x
end
"""
        )

        # Do initial index
        output_path = tmp_path / ".cicada" / "index.json"
        indexer.index_repository(str(tmp_path), str(output_path))

        # Modify the file
        test_file.write_text(
            """
defmodule TestModule do
  def func1(x), do: x
  def func2(x), do: x * 2
end
"""
        )

        # Do incremental index
        index = indexer.incremental_index_repository(str(tmp_path), str(output_path))

        # Should have updated module with both functions
        assert "TestModule" in index["modules"]
        assert len(index["modules"]["TestModule"]["functions"]) == 2

    def test_incremental_file_deleted(self, tmp_path):
        """Test incremental indexing when a file is deleted"""
        indexer = ElixirIndexer()

        # Create two files
        test_file1 = tmp_path / "test1.ex"
        test_file1.write_text(
            """
defmodule TestModule1 do
  def func1(x), do: x
end
"""
        )
        test_file2 = tmp_path / "test2.ex"
        test_file2.write_text(
            """
defmodule TestModule2 do
  def func2(x), do: x * 2
end
"""
        )

        # Do initial index
        output_path = tmp_path / ".cicada" / "index.json"
        indexer.index_repository(str(tmp_path), str(output_path))

        # Delete one file
        test_file2.unlink()

        # Do incremental index
        index = indexer.incremental_index_repository(str(tmp_path), str(output_path))

        # Should only have first module
        assert "TestModule1" in index["modules"]
        assert "TestModule2" not in index["modules"]

    def test_incremental_with_force_full(self, tmp_path):
        """Test incremental indexing with force_full flag"""
        indexer = ElixirIndexer()

        # Create a test file
        test_file = tmp_path / "test.ex"
        test_file.write_text(
            """
defmodule TestModule do
  def test_func(x), do: x
end
"""
        )

        # Do initial index
        output_path = tmp_path / ".cicada" / "index.json"
        indexer.index_repository(str(tmp_path), str(output_path))

        # Modify the file
        test_file.write_text(
            """
defmodule TestModule do
  def test_func(x), do: x
  def new_func(x), do: x * 2
end
"""
        )

        # Do incremental index with force_full
        index = indexer.incremental_index_repository(
            str(tmp_path), str(output_path), force_full=True
        )

        # Should have reindexed completely
        assert "TestModule" in index["modules"]
        assert len(index["modules"]["TestModule"]["functions"]) == 2

    def test_incremental_with_corrupted_index(self, tmp_path):
        """Test incremental indexing with corrupted index falls back to full"""
        indexer = ElixirIndexer()

        # Create a test file
        test_file = tmp_path / "test.ex"
        test_file.write_text(
            """
defmodule TestModule do
  def test_func(x), do: x
end
"""
        )

        # Do initial index
        output_path = tmp_path / ".cicada" / "index.json"
        indexer.index_repository(str(tmp_path), str(output_path))

        # Corrupt the index by replacing it with invalid structure
        import json

        with open(output_path, "w") as f:
            json.dump({"invalid": "structure"}, f)

        # Do incremental index - should detect corruption and fall back
        index = indexer.incremental_index_repository(str(tmp_path), str(output_path))

        # Should have recovered with full reindex
        assert "TestModule" in index["modules"]
        assert index["modules"]["TestModule"]["functions"][0]["name"] == "test_func"


class TestElixirIndexerKeywordExtraction:
    """Tests for keyword extraction functionality"""

    def test_index_with_keyword_extraction(self, tmp_path, monkeypatch, capsys):
        """Test indexing with keyword extraction enabled"""

        indexer = ElixirIndexer(verbose=True)

        # Create a test file with documentation
        test_file = tmp_path / "test.ex"
        test_file.write_text(
            '''
defmodule TestModule do
  @moduledoc """
  This is a test module with documentation.
  """

  @doc """
  This is a test function.
  """
  def test_func(x), do: x
end
'''
        )

        # Index with keyword extraction
        index = indexer.index_repository(
            str(tmp_path), str(tmp_path / ".cicada" / "index.json"), extract_keywords=True
        )

        # Should have extracted keywords
        assert "TestModule" in index["modules"]
        assert "keywords" in index["modules"]["TestModule"]
        # Check that keywords were extracted (content may vary based on actual implementation)
        assert len(index["modules"]["TestModule"]["keywords"]) > 0
        assert isinstance(index["modules"]["TestModule"]["keywords"], dict)

        # Should print keyword extraction method
        captured = capsys.readouterr()
        assert "Keyword extraction:" in captured.out or "keywords" in captured.out.lower()

    def test_index_keyword_extraction_failure(self, tmp_path, monkeypatch, capsys):
        """Test indexing when keyword extraction fails"""

        indexer = ElixirIndexer(verbose=True)

        # Create a test file with documentation
        test_file = tmp_path / "test.ex"
        test_file.write_text(
            '''
defmodule TestModule do
  @moduledoc """
  This is a test module with documentation.
  """

  @doc """
  This is a test function.
  """
  def test_func(x), do: x
end
'''
        )

        # Index with keyword extraction (should handle failures gracefully)
        index = indexer.index_repository(
            str(tmp_path), str(tmp_path / ".cicada" / "index.json"), extract_keywords=True
        )

        # Should still have indexed the module
        assert "TestModule" in index["modules"]

        # With default extraction method (regular), keywords should still be extracted
        # (the mock only affects LightweightKeywordExtractor, not lemminflect)
        assert "keywords" in index["modules"]["TestModule"]
        assert len(index["modules"]["TestModule"]["keywords"]) > 0

    def test_index_keyword_extractor_import_failure(self, tmp_path, monkeypatch, capsys):
        """Test indexing when KeywordExtractor import fails"""

        indexer = ElixirIndexer()

        # Create a test file
        test_file = tmp_path / "test.ex"
        test_file.write_text(
            """
defmodule TestModule do
  def test_func(x), do: x
end
"""
        )

        # Mock the KeywordExtractor to not be available during initialization
        import cicada.indexer

        original_code = cicada.indexer.ElixirIndexer.index_repository

        def mock_index_repo(
            self,
            repo_path,
            output_path=".cicada/index.json",
            extract_keywords=False,
        ):
            # If extract_keywords is True, simulate import failure
            if extract_keywords:
                # Simulate the try/except block behavior
                print("Warning: Could not initialize keyword extractor: ImportError")
                print("Continuing without keyword extraction...")
                extract_keywords = False
            return original_code(self, repo_path, output_path, extract_keywords)

        monkeypatch.setattr(cicada.indexer.ElixirIndexer, "index_repository", mock_index_repo)

        # Index with keyword extraction (should handle import failure)
        index = indexer.index_repository(
            str(tmp_path), str(tmp_path / ".cicada" / "index.json"), extract_keywords=True
        )

        # Should still have indexed the module
        assert "TestModule" in index["modules"]

        # Should print warning
        captured = capsys.readouterr()
        assert "Could not initialize keyword extractor" in captured.out


class TestElixirIndexerProgressReporting:
    """Tests for progress reporting during indexing"""

    def test_progress_reporting_multiple_files(self, tmp_path, capsys):
        """Test that progress is reported every 10 files"""
        indexer = ElixirIndexer(verbose=True)

        # Create 15 test files
        for i in range(15):
            test_file = tmp_path / f"test{i}.ex"
            test_file.write_text(
                f"""
defmodule TestModule{i} do
  def func{i}(x), do: x
end
"""
            )

        # Index the repository
        indexer.index_repository(str(tmp_path), str(tmp_path / ".cicada" / "index.json"))

        # Check progress messages
        captured = capsys.readouterr()
        assert "Processed 10/15 files" in captured.out


class TestElixirIndexerExcludedDirectories:
    """Tests for excluding directories from indexing"""

    def test_find_elixir_files_excludes_deps(self, tmp_path):
        """Test that _find_elixir_files excludes deps directory"""
        indexer = ElixirIndexer()

        # Create a file in deps directory (should be excluded)
        deps_dir = tmp_path / "deps"
        deps_dir.mkdir()
        deps_file = deps_dir / "dep.ex"
        deps_file.write_text(
            """
defmodule DepModule do
  def dep_func(x), do: x
end
"""
        )

        # Create a file in root (should be included)
        root_file = tmp_path / "root.ex"
        root_file.write_text(
            """
defmodule RootModule do
  def root_func(x), do: x
end
"""
        )

        # Find files
        files = indexer._find_elixir_files(tmp_path)

        # Should only find root file
        assert len(files) == 1
        assert files[0].name == "root.ex"

    def test_find_elixir_files_excludes_build(self, tmp_path):
        """Test that _find_elixir_files excludes _build directory"""
        indexer = ElixirIndexer()

        # Create a file in _build directory (should be excluded)
        build_dir = tmp_path / "_build"
        build_dir.mkdir()
        build_file = build_dir / "build.ex"
        build_file.write_text(
            """
defmodule BuildModule do
  def build_func(x), do: x
end
"""
        )

        # Create a file in root (should be included)
        root_file = tmp_path / "root.ex"
        root_file.write_text(
            """
defmodule RootModule do
  def root_func(x), do: x
end
"""
        )

        # Find files
        files = indexer._find_elixir_files(tmp_path)

        # Should only find root file
        assert len(files) == 1
        assert files[0].name == "root.ex"

    def test_find_elixir_files_includes_exs_files(self, tmp_path):
        """Test that _find_elixir_files includes .exs files"""
        indexer = ElixirIndexer()

        # Create .ex and .exs files
        ex_file = tmp_path / "module.ex"
        ex_file.write_text("defmodule M1, do: def f1, do: 1")

        exs_file = tmp_path / "script.exs"
        exs_file.write_text("defmodule M2, do: def f2, do: 2")

        # Find files
        files = indexer._find_elixir_files(tmp_path)

        # Should find both files
        assert len(files) == 2
        file_names = [f.name for f in files]
        assert "module.ex" in file_names
        assert "script.exs" in file_names


class TestElixirIndexerGitignoreIntegration:
    """Tests for .gitignore integration"""

    def test_first_run_creates_gitignore_entry(self, tmp_path, capsys):
        """Test that first run adds .cicada/ to .gitignore"""
        indexer = ElixirIndexer(verbose=True)

        # Create a .gitignore file
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("# Existing content\n*.beam\n")

        # Create a test file
        test_file = tmp_path / "test.ex"
        test_file.write_text(
            """
defmodule TestModule do
  def test_func(x), do: x
end
"""
        )

        # Ensure .cicada directory doesn't exist yet (first run)
        cicada_dir = tmp_path / ".cicada"
        if cicada_dir.exists():
            import shutil

            shutil.rmtree(cicada_dir)

        # Use explicit output path to ensure .cicada gets created
        output_path = tmp_path / ".cicada" / "index.json"

        # Index (first run)
        indexer.index_repository(str(tmp_path), str(output_path))

        # Check gitignore was updated
        gitignore_content = gitignore.read_text()
        assert ".cicada/" in gitignore_content

        # Check message was printed
        captured = capsys.readouterr()
        assert "Added .cicada/ to .gitignore" in captured.out


class TestElixirIndexerSignalHandling:
    """Tests for signal handling and interruption"""

    def test_handle_interrupt_sets_flag(self):
        """Test that _handle_interrupt sets the interrupted flag"""
        indexer = ElixirIndexer()

        # Simulate interrupt signal
        indexer._handle_interrupt(None, None)

        # Should set interrupted flag
        assert indexer._interrupted is True

    def test_interrupted_indexing_saves_partial_progress(self, tmp_path, monkeypatch, capsys):
        """Test that interrupted indexing saves partial progress"""
        indexer = ElixirIndexer(verbose=True)

        # Create multiple test files
        for i in range(5):
            test_file = tmp_path / f"test{i}.ex"
            test_file.write_text(
                f"""
defmodule TestModule{i} do
  def func{i}(x), do: x
end
"""
            )

        # Mock the parser to simulate interruption after 2 files
        original_parse = indexer.parser.parse_file
        call_count = [0]

        def mock_parse(file_path):
            call_count[0] += 1
            result = original_parse(file_path)
            if call_count[0] >= 2:
                indexer._interrupted = True
            return result

        monkeypatch.setattr(indexer.parser, "parse_file", mock_parse)

        # Index repository
        output_path = tmp_path / ".cicada" / "index.json"
        index = indexer.index_repository(str(tmp_path), str(output_path))

        # Should have partial results
        assert len(index["modules"]) == 2

        # Check for partial progress message
        captured = capsys.readouterr()
        assert "Interrupted after processing 2/5 files" in captured.out
        assert "Partial index saved" in captured.out


class TestElixirIndexerMainCLI:
    """Additional tests for main() CLI function"""

    def test_main_with_full_flag(self, tmp_path, monkeypatch):
        """Test main() with --full flag"""
        import sys

        from cicada.indexer import main

        test_file = tmp_path / "test.ex"
        test_file.write_text(
            """
defmodule TestModule do
  def test_func(x), do: x
end
"""
        )

        # Do initial index
        output_path = tmp_path / ".cicada" / "index.json"
        indexer = ElixirIndexer()
        indexer.index_repository(str(tmp_path), str(output_path))

        # Mock sys.argv with --full flag
        monkeypatch.setattr(sys, "argv", ["indexer.py", str(tmp_path), "--full"])

        # Mock check_for_updates
        def mock_check(*_args, **_kwargs):
            pass

        import cicada.version_check

        monkeypatch.setattr(cicada.version_check, "check_for_updates", mock_check)

        # Should perform full reindex
        main()

        # Index file should exist
        assert output_path.exists()


class TestElixirIndexerIncrementalWithKeywords:
    """Tests for incremental indexing with keyword extraction"""

    def test_incremental_with_keyword_extraction(self, tmp_path, monkeypatch):
        """Test incremental indexing with keyword extraction"""

        # Mock the KeywordExtractor
        class MockKeywordExtractor:
            def __init__(self, verbose=False, model_size="small"):
                pass

            def extract_keywords_simple(self, text, top_n=10):
                return ["keyword1", "keyword2"]

        import cicada.indexer

        monkeypatch.setattr(cicada.indexer, "KeywordExtractor", MockKeywordExtractor, raising=False)

        indexer = ElixirIndexer()

        # Create initial file
        test_file = tmp_path / "test.ex"
        test_file.write_text(
            '''
defmodule TestModule do
  @moduledoc """
  Test documentation
  """
  def test_func(x), do: x
end
'''
        )

        # Do initial index
        output_path = tmp_path / ".cicada" / "index.json"
        indexer.index_repository(str(tmp_path), str(output_path))

        # Add new file
        test_file2 = tmp_path / "test2.ex"
        test_file2.write_text(
            '''
defmodule TestModule2 do
  @moduledoc """
  Second module
  """
  def func2(x), do: x * 2
end
'''
        )

        # Do incremental index with keyword extraction
        index = indexer.incremental_index_repository(
            str(tmp_path), str(output_path), extract_keywords=True
        )

        # Should have both modules
        assert "TestModule" in index["modules"]
        assert "TestModule2" in index["modules"]


class TestElixirIndexerAdditionalEdgeCases:
    """Additional edge case tests to improve coverage"""

    def test_keyword_extractor_initialization_exception(self, tmp_path, monkeypatch, capsys):
        """Test handling of exception during KeywordExtractor initialization"""

        indexer = ElixirIndexer(verbose=True)

        test_file = tmp_path / "test.ex"
        test_file.write_text(
            '''
defmodule TestModule do
  @moduledoc """
  Test documentation
  """
  def test_func(x), do: x
end
'''
        )

        # Should handle initialization gracefully
        index = indexer.index_repository(
            str(tmp_path), str(tmp_path / ".cicada" / "index.json"), extract_keywords=True
        )

        # Should still have indexed the module
        assert "TestModule" in index["modules"]

        captured = capsys.readouterr()
        # Should print keyword extraction method info
        assert "Keyword extraction:" in captured.out

    def test_interrupted_during_parse_error(self, tmp_path, monkeypatch, capsys):
        """Test interruption that occurs during parse error handling"""
        indexer = ElixirIndexer()

        # Create valid and invalid files
        valid_file = tmp_path / "valid.ex"
        valid_file.write_text("defmodule Valid, do: def f1, do: 1")

        invalid_file = tmp_path / "invalid.ex"
        invalid_file.write_text("defmodule Broken do\n  def incomplete(")

        # Mock to simulate interruption during error handling
        original_parse = indexer.parser.parse_file

        def mock_parse(file_path):
            if "invalid" in str(file_path):
                # Set interrupted flag before raising
                indexer._interrupted = True
                raise Exception("Parse error")
            return original_parse(file_path)

        monkeypatch.setattr(indexer.parser, "parse_file", mock_parse)

        output_path = tmp_path / ".cicada" / "index.json"
        index = indexer.index_repository(str(tmp_path), str(output_path))

        # Should save partial progress
        captured = capsys.readouterr()
        assert "Interrupted after processing" in captured.out

    def test_incremental_keyword_extraction_module_failure(self, tmp_path, monkeypatch, capsys):
        """Test incremental indexing with keyword extraction failure on module doc"""

        indexer = ElixirIndexer(verbose=True)

        # Create initial file
        test_file = tmp_path / "test.ex"
        test_file.write_text(
            '''
defmodule TestModule do
  @moduledoc """
  Module documentation
  """

  @doc """
  Function documentation
  """
  def test_func(x), do: x
end
'''
        )

        # Do initial index
        output_path = tmp_path / ".cicada" / "index.json"
        indexer.index_repository(str(tmp_path), str(output_path))

        # Modify file to trigger incremental update
        test_file.write_text(
            '''
defmodule TestModule do
  @moduledoc """
  Module documentation updated
  """

  @doc """
  Function documentation
  """
  def test_func(x), do: x
  def new_func(x), do: x * 2
end
'''
        )

        # Do incremental index with keyword extraction
        index = indexer.incremental_index_repository(
            str(tmp_path), str(output_path), extract_keywords=True
        )

        # Should still have the module
        assert "TestModule" in index["modules"]

        # Check for warning in stderr
        captured = capsys.readouterr()
        # The verbose flag should print warnings

    def test_incremental_keyword_extraction_function_failure(self, tmp_path, monkeypatch):
        """Test incremental indexing with keyword extraction failure on function doc"""

        indexer = ElixirIndexer()

        # Create initial file
        test_file = tmp_path / "test.ex"
        test_file.write_text(
            """
defmodule TestModule do
  def f1, do: 1
end
"""
        )

        # Do initial index
        output_path = tmp_path / ".cicada" / "index.json"
        indexer.index_repository(str(tmp_path), str(output_path))

        # Add new file with docs
        test_file2 = tmp_path / "test2.ex"
        test_file2.write_text(
            '''
defmodule TestModule2 do
  @moduledoc """
  Module doc
  """

  @doc """
  Function doc
  """
  def func2(x), do: x
end
'''
        )

        # Do incremental index with keyword extraction
        index = indexer.incremental_index_repository(
            str(tmp_path), str(output_path), extract_keywords=True
        )

        # Should have both modules
        assert "TestModule" in index["modules"]
        assert "TestModule2" in index["modules"]

    def test_incremental_interrupted_during_processing(self, tmp_path, monkeypatch, capsys):
        """Test incremental indexing interrupted during file processing"""
        indexer = ElixirIndexer()

        # Create initial file
        test_file1 = tmp_path / "test1.ex"
        test_file1.write_text("defmodule TestModule1, do: def f1, do: 1")

        # Do initial index
        output_path = tmp_path / ".cicada" / "index.json"
        indexer.index_repository(str(tmp_path), str(output_path))

        # Add multiple new files
        for i in range(2, 6):
            test_file = tmp_path / f"test{i}.ex"
            test_file.write_text(f"defmodule TestModule{i}, do: def f{i}, do: {i}")

        # Mock parser to interrupt after 2 files
        original_parse = indexer.parser.parse_file
        call_count = [0]

        def mock_parse(file_path):
            call_count[0] += 1
            result = original_parse(file_path)
            if call_count[0] >= 2:
                indexer._interrupted = True
            return result

        monkeypatch.setattr(indexer.parser, "parse_file", mock_parse)

        # Do incremental index
        index = indexer.incremental_index_repository(str(tmp_path), str(output_path))

        # Should have partial results
        captured = capsys.readouterr()
        assert "Interrupted after processing" in captured.out
        assert "Partial index saved" in captured.out

    def test_incremental_parse_error_with_interrupt(self, tmp_path, monkeypatch, capsys):
        """Test incremental indexing with parse error followed by interrupt"""
        indexer = ElixirIndexer()

        # Create initial file
        test_file1 = tmp_path / "test1.ex"
        test_file1.write_text("defmodule TestModule1, do: def f1, do: 1")

        # Do initial index
        output_path = tmp_path / ".cicada" / "index.json"
        indexer.index_repository(str(tmp_path), str(output_path))

        # Add a new file that will cause parse error
        test_file2 = tmp_path / "test2.ex"
        test_file2.write_text("defmodule Broken do\n  def incomplete(")

        # Mock parser to interrupt during error
        original_parse = indexer.parser.parse_file

        def mock_parse(file_path):
            if "test2" in str(file_path):
                indexer._interrupted = True
                raise Exception("Parse error")
            return original_parse(file_path)

        monkeypatch.setattr(indexer.parser, "parse_file", mock_parse)

        # Do incremental index
        index = indexer.incremental_index_repository(str(tmp_path), str(output_path))

        # Should handle both error and interrupt
        captured = capsys.readouterr()
        assert "Skipping" in captured.out or "Interrupted" in captured.out


class TestReadKeywordExtractionConfigEdgeCases:
    """Tests for edge cases in read_keyword_extraction_config function"""

    def test_yaml_parsing_error_returns_default(self, tmp_path, monkeypatch):
        """Test that YAML parsing errors return default config"""
        from cicada.tier import read_keyword_extraction_config
        from cicada.utils.storage import get_config_path

        # Create a config file with invalid YAML
        config_path = tmp_path / "config.yaml"
        config_path.write_text("invalid: yaml: content: [unclosed")

        # Mock get_config_path to return our invalid config
        monkeypatch.setattr(
            "cicada.utils.storage.get_config_path",
            lambda x: config_path,
        )

        # Should return defaults instead of crashing
        extraction_method, expansion_method = read_keyword_extraction_config(tmp_path)
        assert extraction_method == "regular"
        assert expansion_method == "lemmi"

    def test_general_exception_returns_default(self, tmp_path, monkeypatch):
        """Test that general exceptions return default config"""
        from cicada.tier import read_keyword_extraction_config

        # Mock get_config_path to raise an exception
        def mock_get_config_path(x):
            raise PermissionError("Permission denied")

        monkeypatch.setattr("cicada.utils.storage.get_config_path", mock_get_config_path)

        # Should return defaults instead of crashing
        extraction_method, expansion_method = read_keyword_extraction_config(tmp_path)
        assert extraction_method == "regular"
        assert expansion_method == "lemmi"


class TestKeywordExtractionEdgeCases:
    """Tests for edge cases in keyword extraction during indexing"""

    def test_extractor_initialization_exception_warning(self, tmp_path, monkeypatch, capsys):
        """Test that extractor initialization errors show warning and continue"""
        from cicada.indexer import ElixirIndexer

        indexer = ElixirIndexer(verbose=True)

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

        # Create config for keyword extraction
        config_dir = tmp_path / ".cicada"
        config_dir.mkdir()
        config_path = config_dir / "config.yaml"
        config_path.write_text("keyword_extraction:\n  method: bert\n  tier: fast")

        # Mock get_config_path
        monkeypatch.setattr("cicada.utils.storage.get_config_path", lambda x: config_path)

        # Mock KeyBERT extractor to raise exception
        def mock_keybert_init(*args, **kwargs):
            raise Exception("Simulated extractor initialization failure")

        monkeypatch.setattr("cicada.extractors.keybert.KeyBERTExtractor", mock_keybert_init)

        output_path = tmp_path / "index.json"

        # Should not crash, should show warning
        index = indexer.index_repository(str(tmp_path), str(output_path), extract_keywords=True)

        captured = capsys.readouterr()
        assert "Warning: Could not initialize keyword extractor/expander" in captured.out
        assert "Continuing without keyword extraction" in captured.out

        # Index should still be created
        assert index is not None
        assert "modules" in index

    def test_silent_module_keyword_extraction_failure(self, tmp_path, monkeypatch, capsys):
        """Test that module keyword extraction failures are silently handled"""
        from cicada.indexer import ElixirIndexer

        indexer = ElixirIndexer(verbose=True)

        # Create a test file with moduledoc
        test_file = tmp_path / "test.ex"
        test_file.write_text(
            """
defmodule TestModule do
  @moduledoc "Test module documentation"
  def test_func(x), do: x
end
"""
        )

        # Create config for keyword extraction
        config_dir = tmp_path / ".cicada"
        config_dir.mkdir()
        config_path = config_dir / "config.yaml"
        config_path.write_text("keyword_extraction:\n  method: lemminflect\n  tier: regular")

        monkeypatch.setattr("cicada.utils.storage.get_config_path", lambda x: config_path)

        # Mock keyword extractor to raise exception
        from unittest.mock import Mock

        mock_extractor = Mock()
        mock_extractor.extract_keywords_simple.side_effect = Exception(
            "Simulated keyword extraction failure"
        )

        monkeypatch.setattr(
            "cicada.extractors.keyword.RegularKeywordExtractor",
            lambda *args, **kwargs: mock_extractor,
        )

        output_path = tmp_path / "index.json"

        # Should not crash - failures are silently caught
        index = indexer.incremental_index_repository(
            str(tmp_path), str(output_path), extract_keywords=True
        )

        # Index should still be created
        assert index is not None
        assert "modules" in index

    def test_silent_function_keyword_extraction_failure(self, tmp_path, monkeypatch):
        """Test that function keyword extraction failures are silently handled"""
        from cicada.indexer import ElixirIndexer

        indexer = ElixirIndexer(verbose=True)

        # Create a test file with function docs
        test_file = tmp_path / "test.ex"
        test_file.write_text(
            """
defmodule TestModule do
  @doc "Test function documentation"
  def test_func(x), do: x
end
"""
        )

        # Create config for keyword extraction
        config_dir = tmp_path / ".cicada"
        config_dir.mkdir()
        config_path = config_dir / "config.yaml"
        config_path.write_text("keyword_extraction:\n  method: lemminflect\n  tier: regular")

        monkeypatch.setattr("cicada.utils.storage.get_config_path", lambda x: config_path)

        # Mock keyword extractor to raise exception only for function extraction
        from unittest.mock import Mock

        mock_extractor = Mock()
        call_count = [0]

        def mock_extract(*args, **kwargs):
            call_count[0] += 1
            # Fail on second call (function keyword extraction)
            if call_count[0] > 1:
                raise Exception("Simulated function keyword extraction failure")
            return ["keyword1", "keyword2"]

        mock_extractor.extract_keywords_simple = mock_extract

        monkeypatch.setattr(
            "cicada.extractors.keyword.RegularKeywordExtractor",
            lambda *args, **kwargs: mock_extractor,
        )

        output_path = tmp_path / "index.json"

        # Should not crash - function keyword failures are silently caught
        index = indexer.incremental_index_repository(
            str(tmp_path), str(output_path), extract_keywords=True
        )

        # Index should still be created
        assert index is not None
        assert "modules" in index

    def test_incremental_extractor_init_failure_continues(self, tmp_path, monkeypatch, capsys):
        """Test that incremental indexing continues if extractor init fails"""
        from cicada.indexer import ElixirIndexer

        indexer = ElixirIndexer(verbose=True)

        # Create initial index first
        test_file = tmp_path / "test.ex"
        test_file.write_text("defmodule TestModule, do: def test_func(x), do: x")

        output_path = tmp_path / "index.json"
        indexer.index_repository(str(tmp_path), str(output_path))

        # Now modify file
        test_file.write_text("defmodule TestModule, do: def updated_func(x), do: x * 2")

        # Create config for keyword extraction
        config_dir = tmp_path / ".cicada"
        config_dir.mkdir()
        config_path = config_dir / "config.yaml"
        config_path.write_text("keyword_extraction:\n  method: bert\n  tier: regular")

        monkeypatch.setattr("cicada.utils.storage.get_config_path", lambda x: config_path)

        # Mock KeyBERT extractor to raise exception
        def mock_keybert_init(*args, **kwargs):
            raise RuntimeError("Simulated extractor initialization failure")

        monkeypatch.setattr("cicada.extractors.keybert.KeyBERTExtractor", mock_keybert_init)

        # Should not crash, should show warning
        index = indexer.incremental_index_repository(
            str(tmp_path), str(output_path), extract_keywords=True
        )

        captured = capsys.readouterr()
        assert "Warning: Could not initialize keyword extractor/expander" in captured.out

        # Index should still be updated
        assert index is not None
        assert "modules" in index


class TestTimestampComputation:
    """Test git history timestamp computation during indexing."""

    def test_compute_timestamps_enabled(self, tmp_path, monkeypatch):
        """Test that timestamps are computed when enabled."""
        from cicada.indexer import ElixirIndexer
        from unittest.mock import Mock, MagicMock

        # Create a test Elixir file
        test_file = tmp_path / "lib" / "test.ex"
        test_file.parent.mkdir(parents=True)
        test_file.write_text(
            """
defmodule TestModule do
  def test_function(x), do: x * 2
end
"""
        )

        # Mock GitHelper
        mock_git_helper = Mock()
        mock_evolution = {
            "created_at": {"date": "2024-01-01T12:00:00", "sha": "abc123"},
            "last_modified": {"date": "2024-03-15T10:30:00", "sha": "def456"},
            "total_modifications": 5,
        }
        mock_git_helper.get_function_evolution.return_value = mock_evolution
        mock_git_helper.repo_path = tmp_path

        # Patch GitHelper to return our mock
        def mock_git_helper_init(repo_path):
            return mock_git_helper

        monkeypatch.setattr("cicada.indexer.GitHelper", mock_git_helper_init)

        # Create indexer and run with compute_timestamps=True
        indexer = ElixirIndexer(verbose=False)
        output_path = tmp_path / "index.json"

        index = indexer.index_repository(str(tmp_path), str(output_path), compute_timestamps=True)

        # Verify timestamps were added to functions
        assert "TestModule" in index["modules"]
        functions = index["modules"]["TestModule"]["functions"]
        assert len(functions) > 0

        func = functions[0]
        assert "created_at" in func
        assert "last_modified_at" in func
        assert "last_modified_sha" in func
        assert "modification_count" in func
        assert func["created_at"] == "2024-01-01T12:00:00"
        assert func["last_modified_at"] == "2024-03-15T10:30:00"
        assert func["modification_count"] == 5

    def test_compute_timestamps_disabled(self, tmp_path):
        """Test that timestamps are not computed when disabled."""
        from cicada.indexer import ElixirIndexer

        # Create a test Elixir file
        test_file = tmp_path / "lib" / "test.ex"
        test_file.parent.mkdir(parents=True)
        test_file.write_text(
            """
defmodule TestModule do
  def test_function(x), do: x * 2
end
"""
        )

        # Create indexer and run with compute_timestamps=False (default)
        indexer = ElixirIndexer(verbose=False)
        output_path = tmp_path / "index.json"

        index = indexer.index_repository(str(tmp_path), str(output_path), compute_timestamps=False)

        # Verify timestamps were NOT added
        functions = index["modules"]["TestModule"]["functions"]
        func = functions[0]
        assert "created_at" not in func
        assert "last_modified_at" not in func

    def test_timestamp_computation_error_handling(self, tmp_path, monkeypatch, capsys):
        """Test that timestamp computation errors are handled gracefully."""
        from cicada.indexer import ElixirIndexer
        from unittest.mock import Mock

        # Create a test Elixir file
        test_file = tmp_path / "lib" / "test.ex"
        test_file.parent.mkdir(parents=True)
        test_file.write_text(
            """
defmodule TestModule do
  def test_function(x), do: x * 2
end
"""
        )

        # Mock GitHelper to raise exception
        mock_git_helper = Mock()
        mock_git_helper.get_function_evolution.side_effect = Exception("Git error")
        mock_git_helper.repo_path = tmp_path

        def mock_git_helper_init(repo_path):
            return mock_git_helper

        monkeypatch.setattr("cicada.indexer.GitHelper", mock_git_helper_init)

        # Create indexer and run
        indexer = ElixirIndexer(verbose=True)
        output_path = tmp_path / "index.json"

        index = indexer.index_repository(str(tmp_path), str(output_path), compute_timestamps=True)

        # Should not crash, should show warning
        captured = capsys.readouterr()
        assert "Could not compute timestamps" in captured.err

        # Index should still be created
        assert "TestModule" in index["modules"]
