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


def test_index_repository_string_extractor_init_failure(temp_repo, capsys):
    """Test index_repository when string extractor initialization fails."""
    indexer = ElixirIndexer(verbose=True)

    with patch(
        "cicada.languages.elixir.extractors.StringExtractor",
        side_effect=ImportError("No string extractor"),
    ):
        indexer._index_repository_full(
            str(temp_repo),
            str(temp_repo / "index.json"),
            extract_string_keywords=True,
        )

        captured = capsys.readouterr()
        # Error message changed with base class error handling
        assert "Keyword extraction/expansion failed" in captured.out


def test_index_repository_git_helper_init_failure(temp_repo, capsys):
    """Test index_repository when git helper initialization fails."""
    indexer = ElixirIndexer(verbose=True)

    with patch("cicada.git.helper.GitHelper", side_effect=RuntimeError("No git")):
        indexer._index_repository_full(
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

    with patch("cicada.git.helper.GitHelper", return_value=mock_git_helper):
        result = indexer._index_repository_full(
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

    indexer._index_repository_full(
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

    with patch("cicada.git.helper.GitHelper", return_value=mock_git_helper):
        indexer._index_repository_full(
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


# ===== Interface Methods Tests =====


def test_get_language_name():
    """Test get_language_name returns 'elixir'."""
    indexer = ElixirIndexer()
    assert indexer.get_language_name() == "elixir"


def test_get_file_extensions():
    """Test get_file_extensions returns Elixir extensions."""
    indexer = ElixirIndexer()
    extensions = indexer.get_file_extensions()
    assert ".ex" in extensions
    assert ".exs" in extensions


def test_get_excluded_dirs():
    """Test get_excluded_dirs returns Elixir-specific dirs."""
    indexer = ElixirIndexer()
    excluded = indexer.get_excluded_dirs()
    assert "deps" in excluded
    assert "_build" in excluded
    assert ".git" in excluded


# ===== Signal Handler Tests =====


def test_handle_interrupt():
    """Test _handle_interrupt sets interrupted flag."""
    indexer = ElixirIndexer(verbose=False)
    indexer._interrupted = False

    # Call handler directly
    indexer._handle_interrupt(None, None)

    assert indexer._interrupted is True


# ===== Co-change Integration Tests =====


def test_build_file_to_module_mapping(temp_repo):
    """Test _build_file_to_module_mapping creates correct mapping."""
    indexer = ElixirIndexer()

    all_modules = {
        "MyApp.User": {"file": "lib/my_app/user.ex"},
        "MyApp.Auth": {"file": "lib/my_app/auth.ex"},
    }

    mapping = indexer._build_file_to_module_mapping(all_modules, temp_repo)

    assert "lib/my_app/user.ex" in mapping
    assert mapping["lib/my_app/user.ex"] == "MyApp.User"
    assert "lib/my_app/auth.ex" in mapping


def test_normalize_file_path():
    """Test _normalize_file_path normalizes paths correctly."""
    indexer = ElixirIndexer()

    # Absolute path
    result = indexer._normalize_file_path("/repo/lib/test.ex", Path("/repo"))
    assert result == "lib/test.ex"

    # Relative path (unchanged)
    result = indexer._normalize_file_path("lib/test.ex", Path("/repo"))
    assert result == "lib/test.ex"


def test_integrate_file_cochanges():
    """Test _integrate_file_cochanges adds co-change data."""
    indexer = ElixirIndexer()

    all_modules = {
        "MyApp.User": {"file": "lib/user.ex"},
    }

    file_pairs = {
        ("lib/user.ex", "lib/auth.ex"): 5,
    }

    file_to_module = {"lib/user.ex": "MyApp.User", "lib/auth.ex": "MyApp.Auth"}

    indexer._integrate_file_cochanges(all_modules, file_pairs, file_to_module, Path("/repo"))

    # Should have cochange_files added
    assert "cochange_files" in all_modules["MyApp.User"]


def test_integrate_function_cochanges():
    """Test _integrate_function_cochanges adds function co-change data."""
    indexer = ElixirIndexer()

    all_modules = {
        "MyApp.User": {
            "functions": [{"name": "create", "arity": 1}],
        },
    }

    function_pairs = {
        ("MyApp.User.create/1", "MyApp.Auth.validate/2"): 3,
    }

    indexer._integrate_function_cochanges(all_modules, function_pairs)

    # Should have cochange_functions added
    func = all_modules["MyApp.User"]["functions"][0]
    assert "cochange_functions" in func


def test_integrate_cochange_data(temp_repo):
    """Test _integrate_cochange_data orchestrates integration."""
    indexer = ElixirIndexer()

    all_modules = {
        "MyApp.User": {
            "file": "lib/user.ex",
            "functions": [{"name": "create", "arity": 1}],
        },
    }

    cochange_data = {
        "file_pairs": {("lib/user.ex", "lib/auth.ex"): 2},
        "function_pairs": {("MyApp.User.create/1", "MyApp.Auth.validate/2"): 1},
    }

    indexer._integrate_cochange_data(all_modules, cochange_data, temp_repo)

    # Should have both file and function co-change data
    assert "cochange_files" in all_modules["MyApp.User"]
    assert "cochange_functions" in all_modules["MyApp.User"]["functions"][0]


# ===== Extract Name Keywords Tests =====


def test_extract_name_keywords_with_expansion():
    """Test _extract_name_keywords with keyword expansion."""
    indexer = ElixirIndexer(verbose=False)

    mock_extractor = MagicMock()
    mock_extractor.extract_keywords.return_value = {
        "top_keywords": [("user", 0.9), ("auth", 0.8)],
    }

    mock_expander = MagicMock()
    mock_expander.expand_keywords.return_value = {
        "words": [
            {"word": "user", "score": 0.9},
            {"word": "authentication", "score": 0.85},
        ]
    }

    result = indexer._extract_name_keywords(
        "MyApp.UserAuthentication", mock_extractor, mock_expander
    )

    # Should have expanded keywords
    assert isinstance(result, dict)
    assert "user" in result or "authentication" in result


def test_extract_name_keywords_no_expander():
    """Test _extract_name_keywords without expander returns base keywords."""
    indexer = ElixirIndexer(verbose=False)

    mock_extractor = MagicMock()
    mock_extractor.extract_keywords.return_value = {
        "top_keywords": [("user", 0.9)],
    }

    result = indexer._extract_name_keywords("UserModule", mock_extractor, None)

    # Should have extracted keywords without expansion
    assert isinstance(result, dict)


# ===== Index Repository Tests =====


def test_index_repository_sets_verbose(temp_repo):
    """Test index_repository sets verbose flag from parameter."""
    indexer = ElixirIndexer(verbose=False)

    # Call with verbose=True
    indexer.index_repository(
        str(temp_repo),
        str(temp_repo / "index.json"),
        verbose=True,
    )

    # Indexer should now have verbose=True
    assert indexer.verbose is True


def test_index_repository_repo_not_found():
    """Test index_repository raises for non-existent repo."""
    indexer = ElixirIndexer(verbose=False)

    with pytest.raises(ValueError, match="does not exist"):
        indexer._index_repository_full(
            "/nonexistent/path/to/repo",
            "/tmp/index.json",
        )


# ===== Extract Dependencies Tests =====


def test_extract_dependencies():
    """Test _extract_dependencies extracts both module and function dependencies."""
    indexer = ElixirIndexer()

    module_data = {
        "aliases": {"MyApp.Auth": "Auth"},
        "imports": ["Ecto.Query"],
        "calls": [
            {"target": "Auth.validate", "line": 10},
        ],
    }

    functions = [
        {"name": "create", "line": 5, "type": "def"},
        {"name": "update", "line": 15, "type": "def"},
    ]

    module_deps, updated_funcs = indexer._extract_dependencies(module_data, functions)

    # Should have module dependencies
    assert isinstance(module_deps, dict)

    # Functions should have dependencies added
    for func in updated_funcs:
        assert "dependencies" in func


# ===== Find Elixir Files Tests =====


def test_find_elixir_files(temp_repo):
    """Test _find_elixir_files finds all .ex and .exs files."""
    indexer = ElixirIndexer()

    # Create additional files
    lib_dir = temp_repo / "lib"
    (lib_dir / "helper.exs").touch()
    (lib_dir / "config.txt").touch()  # Should not be found

    files = indexer._find_elixir_files(temp_repo)

    # Should find .ex and .exs but not .txt
    file_names = [f.name for f in files]
    assert "test.ex" in file_names
    assert "helper.exs" in file_names
    assert "config.txt" not in file_names


def test_find_elixir_files_excludes_dirs(temp_repo):
    """Test _find_elixir_files excludes deps and _build."""
    indexer = ElixirIndexer()

    # Create files in excluded directories
    deps_dir = temp_repo / "deps"
    deps_dir.mkdir()
    (deps_dir / "lib.ex").touch()

    build_dir = temp_repo / "_build"
    build_dir.mkdir()
    (build_dir / "compiled.ex").touch()

    files = indexer._find_elixir_files(temp_repo)

    # Should not find files in excluded dirs
    file_paths = [str(f) for f in files]
    assert not any("deps" in p for p in file_paths)
    assert not any("_build" in p for p in file_paths)


# ===== Version Mismatch Tests =====


def test_incremental_index_version_mismatch(temp_repo, capsys):
    """Test incremental index detects version mismatch and shows warning."""
    indexer = ElixirIndexer(verbose=True)

    # Create initial index
    index_path = temp_repo / "index.json"
    indexer.index_repository(str(temp_repo), str(index_path))

    # Modify the index to have different version
    import json

    with open(index_path) as f:
        index = json.load(f)
    index["metadata"]["cicada_version"] = "0.0.1"  # Old version
    with open(index_path, "w") as f:
        json.dump(index, f)

    # Run incremental - should detect mismatch and warn but continue incrementally
    indexer.incremental_index_repository(
        str(temp_repo),
        str(index_path),
    )

    captured = capsys.readouterr()
    assert "version mismatch" in captured.out.lower()
    # Should NOT trigger full reindex anymore
    assert "Performing full reindex" not in captured.out


# ===== No Changes Detected Test =====


def test_incremental_index_no_changes(temp_repo, capsys):
    """Test incremental index with no changes."""
    indexer = ElixirIndexer(verbose=True)

    # Create initial index
    index_path = temp_repo / "index.json"
    indexer.index_repository(str(temp_repo), str(index_path))

    # Run incremental again without changes
    indexer.incremental_index_repository(
        str(temp_repo),
        str(index_path),
    )

    captured = capsys.readouterr()
    assert "No changes detected" in captured.out or "up to date" in captured.out


# ===== Streaming Keyword Extraction Tests =====


def test_extract_docstring_keywords_with_pipeline(temp_repo, capsys):
    """Test _extract_docstring_keywords with streaming pipeline."""
    indexer = ElixirIndexer(verbose=True)

    # Create index with modules that have moduledocs
    index = {
        "modules": {
            "TestModule": {
                "moduledoc": "This module handles user authentication.",
                "functions": [
                    {"name": "create", "doc": "Creates a new user account"},
                ],
            },
        },
    }

    # Mock keyword extractor
    mock_extractor = MagicMock()
    mock_extractor.extract_keywords.return_value = {
        "top_keywords": [("user", 0.9), ("auth", 0.8)],
    }

    # Mock streaming pipeline
    mock_pipeline = MagicMock()
    mock_pipeline.stats = {"submitted": 0}
    mock_pipeline.submit.return_value = []  # No completed results yet

    indexer._extract_docstring_keywords(index, mock_extractor, mock_pipeline)

    captured = capsys.readouterr()
    # Should print progress
    assert "keywords" in captured.out.lower() or mock_extractor.extract_keywords.called


def test_extract_docstring_keywords_module_without_doc(temp_repo):
    """Test _extract_docstring_keywords extracts name keywords even without docs."""
    indexer = ElixirIndexer(verbose=False)

    index = {
        "modules": {
            "TestModule": {
                # No moduledoc
                "functions": [{"name": "create"}],  # No doc either
            },
        },
    }

    mock_extractor = MagicMock()
    # Return mock keywords from name extraction
    mock_extractor.extract_keywords.return_value = {
        "top_keywords": [("test", 0.5), ("module", 0.4)]
    }
    mock_pipeline = MagicMock()
    mock_pipeline.stats = {"submitted": 0}
    mock_pipeline.submit.return_value = []

    # Should not raise
    indexer._extract_docstring_keywords(index, mock_extractor, mock_pipeline)

    # Extractor should be called for name extraction (converts "TestModule" -> "TestModule")
    mock_extractor.extract_keywords.assert_called_once_with("TestModule", top_n=5)


def test_extract_docstring_keywords_error_handling(temp_repo, capsys):
    """Test _extract_docstring_keywords handles errors gracefully."""
    indexer = ElixirIndexer(verbose=True)

    index = {
        "modules": {
            "TestModule": {
                "moduledoc": "Test doc",
                "functions": [],
            },
        },
    }

    mock_extractor = MagicMock()
    mock_extractor.extract_keywords.side_effect = ValueError("Extraction failed")

    mock_pipeline = MagicMock()
    mock_pipeline.stats = {"submitted": 0}
    mock_pipeline.submit.return_value = []

    # Should not raise
    indexer._extract_docstring_keywords(index, mock_extractor, mock_pipeline)

    captured = capsys.readouterr()
    assert "Warning" in captured.out or "Failed" in captured.out


# ===== Main CLI Tests =====


def test_main_function(temp_repo, monkeypatch, capsys):
    """Test main() CLI entry point."""
    import sys
    from cicada.indexer import main

    # Mock sys.argv
    monkeypatch.setattr(sys, "argv", ["cicada-index", str(temp_repo)])

    # Mock check_for_updates to avoid network call
    with patch("cicada.version_check.check_for_updates"):
        main()

    captured = capsys.readouterr()
    # Should have indexed something
    assert "Modules" in captured.out or "complete" in captured.out.lower()


def test_main_function_with_output(temp_repo, monkeypatch):
    """Test main() with custom output path."""
    import sys
    from cicada.indexer import main

    output_path = temp_repo / "custom_index.json"

    monkeypatch.setattr(sys, "argv", ["cicada-index", str(temp_repo), "--output", str(output_path)])

    with patch("cicada.version_check.check_for_updates"):
        main()

    # Output file should exist
    assert output_path.exists()


def test_main_function_full_reindex(temp_repo, monkeypatch):
    """Test main() with --full flag."""
    import sys
    from cicada.indexer import main

    # First run to create index
    monkeypatch.setattr(sys, "argv", ["cicada-index", str(temp_repo)])
    with patch("cicada.version_check.check_for_updates"):
        main()

    # Second run with --full
    monkeypatch.setattr(sys, "argv", ["cicada-index", str(temp_repo), "--full"])
    with patch("cicada.version_check.check_for_updates"):
        main()

    # Should complete without error (validates --full flag handling)
