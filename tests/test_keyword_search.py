"""
Comprehensive tests for keyword search functionality

Author: Cursor(Auto)
"""

import pytest
from pathlib import Path
from cicada.keyword_extractor import KeywordExtractor
from cicada.keyword_search import KeywordSearcher
from cicada.indexer import ElixirIndexer
from cicada.utils import split_camel_snake_case


class TestKeywordExtractor:
    """Tests for KeywordExtractor class"""

    def test_keyword_extractor_initialization(self):
        """Test that KeywordExtractor initializes properly"""
        extractor = KeywordExtractor(verbose=False)
        assert extractor.nlp is not None

    def test_invalid_model_size(self):
        """Test that invalid model size raises ValueError"""
        with pytest.raises(ValueError, match="Invalid model size"):
            KeywordExtractor(verbose=False, model_size="invalid")

    def test_split_camel_case(self):
        """Test splitting camelCase identifiers"""
        assert split_camel_snake_case("camelCase") == "camel case"
        assert split_camel_snake_case("getUserData") == "get user data"
        assert split_camel_snake_case("myVariableName") == "my variable name"

    def test_split_pascal_case(self):
        """Test splitting PascalCase identifiers"""
        assert split_camel_snake_case("PascalCase") == "pascal case"
        assert split_camel_snake_case("UserController") == "user controller"
        assert split_camel_snake_case("HTTPServer") == "http server"

    def test_split_snake_case(self):
        """Test splitting snake_case identifiers"""
        assert split_camel_snake_case("snake_case") == "snake case"
        assert split_camel_snake_case("get_user_data") == "get user data"
        assert split_camel_snake_case("my_variable_name") == "my variable name"

    def test_split_mixed_case(self):
        """Test splitting mixed case patterns"""
        # Mixed patterns
        assert split_camel_snake_case("getHTTPResponseCode") == "get http response code"
        assert split_camel_snake_case("parseJSONData") == "parse json data"
        assert split_camel_snake_case("XMLParser") == "xml parser"

        # PascalCase ending with uppercase acronyms (PostgreSQL, TypeScript, etc.)
        assert split_camel_snake_case("PostgreSQL") == "postgre sql"
        assert split_camel_snake_case("TypeScript") == "type script"
        assert split_camel_snake_case("JavaScript") == "java script"

    def test_extract_code_identifiers_with_splitting(self):
        """Test that code identifier extraction returns both original and split words"""
        extractor = KeywordExtractor(verbose=False)

        text = "The getUserData function uses HTTPServer class"
        identifiers, split_words = extractor.extract_code_identifiers(text)

        # Should find the identifiers
        assert "getUserData" in identifiers
        assert "HTTPServer" in identifiers

        # Should have split words
        assert "get" in split_words
        assert "user" in split_words
        assert "data" in split_words
        assert "http" in split_words
        assert "server" in split_words

    def test_extract_code_identifiers_uppercase_suffix(self):
        """Test extraction of PascalCase words ending with uppercase acronyms"""
        extractor = KeywordExtractor(verbose=False)

        text = "Using PostgreSQL and TypeScript for the backend"
        identifiers, split_words = extractor.extract_code_identifiers(text)

        # Should find the identifiers
        assert "PostgreSQL" in identifiers
        assert "TypeScript" in identifiers

        # Should split uppercase suffixes correctly
        assert "postgre" in split_words
        assert "sql" in split_words
        assert "type" in split_words
        assert "script" in split_words

    def test_extract_keywords_includes_split_words(self):
        """Test that keyword extraction includes words from split identifiers"""
        extractor = KeywordExtractor(verbose=False)

        text = "This getUserData function retrieves user information from the database"
        results = extractor.extract_keywords(text, top_n=15)

        # Check that we have split words in the results
        assert "code_split_words" in results
        assert isinstance(results["code_split_words"], list)

        # The split words should include words from getUserData
        split_words = results["code_split_words"]
        assert "get" in split_words or "user" in split_words or "data" in split_words

    def test_code_split_words_have_3x_weight(self):
        """Test that code split words are weighted 3x and full identifiers 10x in keyword rankings"""
        extractor = KeywordExtractor(verbose=False)

        # Text with code identifier "PostgreSQL" which splits into "postgre" and "sql"
        # Full identifier should have 10x weight, split words should have 3x weight
        text = "Using PostgreSQL database for storage"
        results = extractor.extract_keywords(text, top_n=10)

        # Get the keyword frequencies
        keyword_dict = dict(results["top_keywords"])

        # "postgresql" (full identifier) should have count of 10 + 1 (also appears as noun) = 11
        assert "postgresql" in keyword_dict
        assert (
            keyword_dict["postgresql"] >= 10
        ), f"Expected 'postgresql' to have weight >= 10, got {keyword_dict['postgresql']}"

        # "postgre" and "sql" are code split words and should have count of 3
        assert "postgre" in keyword_dict
        assert "sql" in keyword_dict
        assert (
            keyword_dict["postgre"] == 3
        ), f"Expected 'postgre' to have weight 3, got {keyword_dict['postgre']}"
        assert (
            keyword_dict["sql"] == 3
        ), f"Expected 'sql' to have weight 3, got {keyword_dict['sql']}"

        # Regular words like "database" should have lower counts
        if "database" in keyword_dict:
            assert (
                keyword_dict["database"] < 3
            ), "Regular words should have lower weight than code split words"

    @pytest.mark.parametrize("verbose", [False, True])
    def test_keyword_extractor_missing_model(self, monkeypatch, verbose):
        """Test that KeywordExtractor raises error when model missing"""
        import importlib

        def mock_import(name):
            raise ImportError("Model not found")

        # Mock both importlib.import_module and _download_model to simulate failed download
        monkeypatch.setattr(importlib, "import_module", mock_import)
        monkeypatch.setattr(KeywordExtractor, "_download_model", lambda self: False)

        with pytest.raises(RuntimeError, match="Failed to download spaCy model"):
            KeywordExtractor(verbose=verbose)

    def test_download_model_unknown_model(self, monkeypatch):
        """Test _download_model with unknown model name"""
        import importlib

        def mock_import(name):
            raise ImportError("Model not found")

        monkeypatch.setattr(importlib, "import_module", mock_import)

        extractor = KeywordExtractor.__new__(KeywordExtractor)
        extractor.verbose = True
        extractor.model_name = "unknown_model"

        # Should return False for unknown model
        assert extractor._download_model() is False

    def test_download_model_uv_not_found(self, monkeypatch):
        """Test _download_model when uv is not available"""
        import importlib
        import subprocess

        def mock_import(name):
            raise ImportError("Model not found")

        def mock_run(cmd, **_kwargs):
            if cmd[0] == "uv":
                raise FileNotFoundError("uv not found")
            # Simulate successful pip install
            return subprocess.CompletedProcess(cmd, 0, stdout="Success", stderr="")

        monkeypatch.setattr(importlib, "import_module", mock_import)
        monkeypatch.setattr(subprocess, "run", mock_run)

        extractor = KeywordExtractor.__new__(KeywordExtractor)
        extractor.verbose = True
        extractor.model_name = "en_core_web_md"

        # Should return False when uv is not found (no fallback to pip)
        assert extractor._download_model() is False

    def test_download_model_both_fail(self, monkeypatch):
        """Test _download_model when both uv and pip fail"""
        import importlib
        import subprocess

        def mock_import(name):
            raise ImportError("Model not found")

        def mock_run(cmd, **_kwargs):
            raise subprocess.CalledProcessError(1, cmd, stderr="Install failed")

        monkeypatch.setattr(importlib, "import_module", mock_import)
        monkeypatch.setattr(subprocess, "run", mock_run)

        extractor = KeywordExtractor.__new__(KeywordExtractor)
        extractor.verbose = False
        extractor.model_name = "en_core_web_md"

        # Should return False when both fail
        assert extractor._download_model() is False

    def test_download_succeeds_but_load_fails(self, monkeypatch):
        """Test when download succeeds but model still can't load"""
        import importlib
        import subprocess

        def mock_import(name):
            raise ImportError("Model not found")

        def mock_run(cmd, **_kwargs):
            # Simulate successful download
            return subprocess.CompletedProcess(
                cmd, 0, stdout="Installed successfully", stderr=""
            )

        monkeypatch.setattr(importlib, "import_module", mock_import)
        monkeypatch.setattr(subprocess, "run", mock_run)

        with pytest.raises(
            RuntimeError, match="Failed to load spaCy model.*after download"
        ):
            KeywordExtractor(verbose=True, model_size="medium")

    def test_download_with_verbose_output(self, monkeypatch):
        """Test download with verbose output enabled"""
        import importlib
        import subprocess
        from unittest.mock import MagicMock

        call_count = [0]
        mock_nlp = MagicMock()
        mock_module = MagicMock()
        mock_module.load = MagicMock(return_value=mock_nlp)

        def mock_import(name):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call fails (model not found)
                raise ImportError("Model not found")
            # Second call succeeds (after download)
            return mock_module

        def mock_run(cmd, **_kwargs):
            # Simulate successful download with output
            return subprocess.CompletedProcess(
                cmd, 0, stdout="Successfully installed en-core-web-md", stderr=""
            )

        monkeypatch.setattr(importlib, "import_module", mock_import)
        monkeypatch.setattr(subprocess, "run", mock_run)

        # Should succeed with verbose output
        extractor = KeywordExtractor(verbose=True, model_size="small")
        assert extractor.nlp is mock_nlp

    def test_extract_keywords_simple_basic(self):
        """Test basic keyword extraction"""
        extractor = KeywordExtractor(verbose=False)
        text = "This function validates user authentication credentials"
        keywords = extractor.extract_keywords_simple(text, top_n=5)

        assert isinstance(keywords, list)
        assert len(keywords) > 0
        assert len(keywords) <= 5
        # Should extract relevant keywords
        assert any(kw in keywords for kw in ["validate", "user", "authentication"])

    def test_extract_keywords_simple_empty_text(self):
        """Test keyword extraction with empty text"""
        extractor = KeywordExtractor(verbose=False)

        assert extractor.extract_keywords_simple("", top_n=5) == []
        assert extractor.extract_keywords_simple("   ", top_n=5) == []
        assert extractor.extract_keywords_simple(None, top_n=5) == []

    def test_extract_keywords_full_structure(self):
        """Test full keyword extraction returns proper structure"""
        extractor = KeywordExtractor(verbose=False)
        text = "Performance benchmarks measure execution speed and memory usage"
        results = extractor.extract_keywords(text, top_n=5)

        assert isinstance(results, dict)
        assert "top_keywords" in results
        assert "nouns" in results
        assert "verbs" in results
        assert "stats" in results

        # Check top_keywords format
        assert isinstance(results["top_keywords"], list)
        if results["top_keywords"]:
            # Each item should be a tuple (keyword, frequency)
            assert isinstance(results["top_keywords"][0], tuple)
            assert len(results["top_keywords"][0]) == 2

    def test_extract_keywords_programming_documentation(self):
        """Test keyword extraction from programming documentation"""
        extractor = KeywordExtractor(verbose=False)
        text = """
        Executes performance benchmarks between two implementations using Benchee.
        This module handles benchmarking of two functions with identical typespecs.
        """
        keywords = extractor.extract_keywords_simple(text, top_n=10)

        # Should extract technical terms
        assert any(kw in keywords for kw in ["performance", "benchmark", "function"])

    def test_extract_keywords_with_rich_content(self):
        """Test full keyword extraction with diverse content"""
        extractor = KeywordExtractor(verbose=True)
        text = """
        The fast HTTPServer efficiently handles multiple concurrent requests.
        It validates authentication credentials and processes getUserData operations.
        This performant system uses advanced algorithms for request_processing.
        Microsoft Azure Cloud provides scalable infrastructure.
        """
        results = extractor.extract_keywords(text, top_n=15)

        # Verify structure
        assert "nouns" in results and len(results["nouns"]) > 0
        assert "verbs" in results and len(results["verbs"]) > 0
        assert "adjectives" in results and len(results["adjectives"]) > 0
        assert "proper_nouns" in results
        assert "noun_chunks" in results
        assert "entities" in results
        assert "code_identifiers" in results
        assert "code_split_words" in results

        # Verify code identifier splitting
        assert any(
            "HTTP" in id or "getUserData" in id or "request_processing" in id
            for id in results["code_identifiers"]
        )

    def test_medium_model_on_elixir_doc(self):
        """Test medium spaCy model on Elixir documentation"""
        extractor = KeywordExtractor(verbose=True, model_size="medium")

        # Small Elixir documentation text
        text = """
        Multiplies two numbers.
        This function takes two numeric values and returns their product.
        Used for basic arithmetic operations in mathematical calculations.
        """

        keywords = extractor.extract_keywords_simple(text, top_n=8)

        # Should extract relevant mathematical/computational terms
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        assert len(keywords) <= 8

        # Should extract mathematical or computational keywords
        expected_keywords = [
            "multiply",
            "number",
            "numeric",
            "value",
            "product",
            "arithmetic",
            "operation",
            "mathematical",
            "calculation",
        ]
        # At least one of the expected keywords should be present
        assert any(
            kw in keywords for kw in expected_keywords
        ), f"Expected at least one of {expected_keywords} but got {keywords}"


class TestKeywordSearcher:
    """Tests for KeywordSearcher class"""

    @pytest.fixture
    def sample_index(self):
        """Create a sample index with keywords for testing"""
        return {
            "modules": {
                "MyApp.User": {
                    "file": "lib/user.ex",
                    "line": 1,
                    "keywords": ["user", "authentication", "validate"],
                    "functions": [
                        {
                            "name": "authenticate",
                            "arity": 2,
                            "line": 10,
                            "doc": "Authenticates a user",
                            "keywords": ["authenticate", "user", "credential"],
                        },
                        {
                            "name": "validate",
                            "arity": 1,
                            "line": 20,
                            "doc": "Validates user data",
                            "keywords": ["validate", "user", "data"],
                        },
                    ],
                },
                "MyApp.Post": {
                    "file": "lib/post.ex",
                    "line": 1,
                    "keywords": ["post", "content", "publish"],
                    "functions": [
                        {
                            "name": "create",
                            "arity": 1,
                            "line": 10,
                            "doc": "Creates a new post",
                            "keywords": ["create", "post", "content"],
                        }
                    ],
                },
            }
        }

    def test_keyword_searcher_initialization(self, sample_index):
        """Test KeywordSearcher initialization"""
        searcher = KeywordSearcher(sample_index)
        assert searcher.index == sample_index

    def test_search_exact_match(self, sample_index):
        """Test search with exact keyword matches"""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search(["user", "authentication"], top_n=5)

        assert len(results) > 0
        # MyApp.User module should be first (matches both keywords)
        assert results[0]["type"] == "module"
        assert results[0]["name"] == "MyApp.User"
        # BM25 score should be positive (higher is better match)
        assert results[0]["score"] > 0
        # Confidence should still be 100% (both keywords matched)
        assert results[0]["confidence"] == 100.0

    def test_search_partial_match(self, sample_index):
        """Test search with partial matches"""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search(["user", "nonexistent"], top_n=5)

        # Should find items with 'user' keyword
        assert len(results) > 0
        # Confidence should be 50% (1 out of 2 keywords matched)
        assert all(r["confidence"] == 50.0 for r in results)

    def test_search_function_match(self, sample_index):
        """Test search matching specific functions"""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search(["validate"], top_n=5)

        # Should find validate function
        function_results = [r for r in results if r["type"] == "function"]
        assert len(function_results) > 0

        validate_func = next(
            (r for r in function_results if "validate" in r["name"]), None
        )
        assert validate_func is not None
        assert validate_func["function"] == "validate"

    def test_search_no_matches(self, sample_index):
        """Test search with no matching keywords"""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search(["nonexistent", "foobar"], top_n=5)

        assert len(results) == 0

    def test_search_empty_keywords(self, sample_index):
        """Test search with empty keyword list"""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search([], top_n=5)

        assert len(results) == 0

    def test_search_case_insensitive(self, sample_index):
        """Test that search is case-insensitive"""
        searcher = KeywordSearcher(sample_index)
        results_lower = searcher.search(["user"], top_n=5)
        results_upper = searcher.search(["USER"], top_n=5)
        results_mixed = searcher.search(["UsEr"], top_n=5)

        # All should return same number of results
        assert len(results_lower) == len(results_upper) == len(results_mixed)

    def test_search_top_n_limit(self, sample_index):
        """Test that search respects top_n parameter"""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search(["user"], top_n=2)

        assert len(results) <= 2

    def test_search_sorted_by_score(self, sample_index):
        """Test that results are sorted by score descending"""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search(["user", "authentication"], top_n=5)

        # Scores should be in descending order
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_search_result_structure(self, sample_index):
        """Test that search results have correct structure"""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search(["user"], top_n=5)

        assert len(results) > 0
        result = results[0]

        # Check required fields
        assert "type" in result
        assert result["type"] in ["module", "function"]
        assert "name" in result
        assert "module" in result
        assert "file" in result
        assert "line" in result
        assert "score" in result
        assert "confidence" in result
        assert "matched_keywords" in result

        # Check that matched_keywords is a list
        assert isinstance(result["matched_keywords"], list)


class TestIndexerKeywordExtraction:
    """Tests for keyword extraction in ElixirIndexer"""

    def test_indexer_with_keyword_extraction(self, tmp_path):
        """Test indexer with keyword extraction enabled"""
        indexer = ElixirIndexer()

        # Create test file with documentation
        test_file = tmp_path / "test.ex"
        test_file.write_text(
            '''
defmodule TestModule do
  @moduledoc """
  This module handles user authentication and validation.
  """

  @doc """
  Authenticates a user with credentials.
  """
  def authenticate(username, password), do: :ok
end
'''
        )

        # Index with keyword extraction
        index = indexer.index_repository(str(tmp_path), extract_keywords=True)

        # Check that module has keywords
        assert "TestModule" in index["modules"]
        module = index["modules"]["TestModule"]

        # Module should have keywords extracted from moduledoc
        assert "keywords" in module
        assert isinstance(module["keywords"], list)
        assert len(module["keywords"]) > 0
        # Should contain relevant keywords
        assert any(kw in module["keywords"] for kw in ["user", "authentication"])

        # Function should have keywords extracted from doc
        func = module["functions"][0]
        assert "keywords" in func
        assert isinstance(func["keywords"], list)
        assert any(kw in func["keywords"] for kw in ["authenticate", "user"])

    def test_indexer_without_keyword_extraction(self, tmp_path):
        """Test indexer with keyword extraction disabled (default)"""
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

        # Index without keyword extraction
        index = indexer.index_repository(str(tmp_path), extract_keywords=False)

        # Check that module doesn't have keywords
        assert "TestModule" in index["modules"]
        module = index["modules"]["TestModule"]
        assert "keywords" not in module

        # Function shouldn't have keywords
        func = module["functions"][0]
        assert "keywords" not in func

    def test_indexer_keyword_extraction_no_docs(self, tmp_path):
        """Test keyword extraction when there's no documentation"""
        indexer = ElixirIndexer()

        test_file = tmp_path / "test.ex"
        test_file.write_text(
            """
defmodule TestModule do
  def test_func(x), do: x
end
"""
        )

        # Index with keyword extraction
        index = indexer.index_repository(str(tmp_path), extract_keywords=True)

        # Module shouldn't have keywords (no moduledoc)
        module = index["modules"]["TestModule"]
        assert "keywords" not in module

        # Function shouldn't have keywords (no doc)
        func = module["functions"][0]
        assert "keywords" not in func


class TestKeywordSearchIntegration:
    """Integration tests for keyword search with real index"""

    def test_search_with_extracted_keywords(self, tmp_path):
        """Test end-to-end keyword search with extracted keywords"""
        # Create test files
        user_file = tmp_path / "user.ex"
        user_file.write_text(
            '''
defmodule MyApp.User do
  @moduledoc """
  Handles user authentication and authorization.
  """

  @doc """
  Authenticates a user with email and password.
  """
  def authenticate(email, password), do: :ok

  @doc """
  Validates user permissions.
  """
  def authorize(user, action), do: :ok
end
'''
        )

        # Index with keyword extraction
        indexer = ElixirIndexer()
        index = indexer.index_repository(str(tmp_path), extract_keywords=True)

        # Search for authentication-related keywords
        searcher = KeywordSearcher(index)
        results = searcher.search(["authentication", "user"], top_n=5)

        # Should find module and/or functions
        assert len(results) > 0

        # Check that we found the module or authenticate function
        names = [r["name"] for r in results]
        assert any("MyApp.User" in name for name in names)

    def test_search_no_keywords_in_index(self, tmp_path):
        """Test search behavior when index has no keywords - falls back to identifier matching"""
        # Create simple test file
        test_file = tmp_path / "test.ex"
        test_file.write_text(
            """
defmodule TestModule do
  def test_func(x), do: x
end
"""
        )

        # Index WITHOUT keyword extraction
        indexer = ElixirIndexer()
        index = indexer.index_repository(str(tmp_path), extract_keywords=False)

        # Search should fall back to identifier-based matching
        # "test" should match TestModule and test_func
        searcher = KeywordSearcher(index)
        results = searcher.search(["test"], top_n=5)

        # Should find matches using identifier names as fallback
        assert len(results) == 2  # TestModule and test_func
        result_names = [r["name"] for r in results]
        assert "TestModule" in result_names
        assert "TestModule.test_func/1" in result_names


class TestWildcardSearch:
    """Tests for wildcard search functionality"""

    def test_wildcard_matching_basic(self):
        """Test basic wildcard pattern matching"""
        searcher = KeywordSearcher({})

        # Test * wildcard
        assert searcher._match_wildcard("create*", "createUser") == True
        assert searcher._match_wildcard("create*", "createAccount") == True
        assert searcher._match_wildcard("create*", "create") == True
        assert searcher._match_wildcard("create*", "deleteUser") == False

        # Test ? wildcard is rejected
        assert searcher._match_wildcard("user?", "user1") == False
        assert searcher._match_wildcard("user?", "userA") == False
        assert searcher._match_wildcard("user?", "user") == False
        assert searcher._match_wildcard("user?", "user12") == False

        # Test exact match
        assert searcher._match_wildcard("test", "test") == True
        assert searcher._match_wildcard("test", "testing") == False

    def test_wildcard_keyword_expansion(self):
        """Test expanding wildcard patterns to matching keywords"""
        searcher = KeywordSearcher({})

        query_keywords = ["create*", "test_*"]
        document_keywords = [
            "createUser",
            "createAccount",
            "test_function",
            "test_helper",
            "user1",
            "userA",
            "admin",
        ]

        matched = searcher._expand_wildcard_keywords(query_keywords, document_keywords)

        # Should find matches for * patterns only
        assert "create*" in matched
        assert "test_*" in matched

    def test_wildcard_search_with_index(self, tmp_path):
        """Test wildcard search with actual index"""
        # Create test files
        test_file = tmp_path / "test_module.ex"
        test_file.write_text(
            """
defmodule TestModule do
  @moduledoc "Test module for wildcard search"

  @doc "Creates a new user account"
  def create_user(name), do: name

  @doc "Creates a new admin account"
  def create_admin(name), do: name

  @doc "Tests user functionality"
  def test_user_func(x), do: x

  @doc "Tests admin functionality"
  def test_admin_func(x), do: x
end
"""
        )

        # Index with keyword extraction (may not work in test environment)
        indexer = ElixirIndexer()
        index = indexer.index_repository(str(tmp_path), extract_keywords=True)

        searcher = KeywordSearcher(index)

        # Test wildcard search for create* patterns
        results = searcher.search(
            ["create*"],
            top_n=5,
        )
        assert len(results) > 0

        # Should find functions with "create" in their names
        function_names = [
            result["name"] for result in results if result["type"] == "function"
        ]
        assert any("create" in name for name in function_names)

        # Test wildcard search for test_* patterns
        results = searcher.search(
            ["test_*"],
            top_n=5,
        )
        assert len(results) > 0

        # Should find functions with "test_" in their names
        function_names = [
            result["name"] for result in results if result["type"] == "function"
        ]
        assert any("test_" in name for name in function_names)

    def test_wildcard_vs_exact_search(self, tmp_path):
        """Test that wildcard search behaves differently from exact search"""
        # Create test files
        test_file = tmp_path / "test_module.ex"
        test_file.write_text(
            """
defmodule TestModule do
  @moduledoc "Test module for wildcard comparison"

  @doc "Creates a new user account"
  def create_user(name), do: name

  @doc "Creates a new admin account"
  def create_admin(name), do: name
end
"""
        )

        # Index with keyword extraction
        indexer = ElixirIndexer()
        index = indexer.index_repository(str(tmp_path), extract_keywords=True)

        searcher = KeywordSearcher(index)

        # Exact search should find fewer results
        exact_results = searcher.search(
            ["create"],
            top_n=5,
        )

        # Wildcard search should find more results
        wildcard_results = searcher.search(
            ["create*"],
            top_n=5,
        )

        # Wildcard search should find at least as many results as exact search
        assert len(wildcard_results) >= len(exact_results)

    def test_wildcard_identifier_boost(self, tmp_path):
        """Test that wildcard matching works with identifier boost"""
        # Create test files
        test_file = tmp_path / "test_module.ex"
        test_file.write_text(
            """
defmodule TestModule do
  @moduledoc "Test module for wildcard identifier boost"

  @doc "Creates a new user account"
  def create_user(name), do: name

  @doc "Creates a new admin account"
  def create_admin(name), do: name
end
"""
        )

        # Index with keyword extraction
        indexer = ElixirIndexer()
        index = indexer.index_repository(str(tmp_path), extract_keywords=True)

        searcher = KeywordSearcher(index)

        # Search with wildcard should boost functions with matching names
        results = searcher.search(
            ["create*"],
            top_n=5,
        )

        # Results should be sorted by score (highest first)
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i]["score"] >= results[i + 1]["score"]


class TestNameCoveragePenalty:
    """Tests for name coverage penalty that ranks exact matches higher"""

    @pytest.fixture
    def exact_vs_extra_index(self):
        """
        Create an index with two similar functions where one has extra words.
        This simulates the real-world case where:
        - create_input_generator_runtime (exact match)
        - create_invalid_input_generator_runtime (has extra word "invalid")
        """
        return {
            "modules": {
                "TestModule": {
                    "file": "lib/test.ex",
                    "line": 1,
                    "moduledoc": "Test module",
                    "keywords": ["test", "module"],
                    "functions": [
                        {
                            "name": "create_input_generator_runtime",
                            "arity": 2,
                            "line": 10,
                            "doc": "Creates input generators from type specifications. Optionally accepts a module to resolve user-defined type aliases.",
                            "keywords": [
                                "create_input_generator_runtime",
                                "input",
                                "generator",
                                "create",
                                "runtime",
                                "type",
                                "specification",
                                "module",
                                "user",
                                "alias",
                            ],
                        },
                        {
                            "name": "create_invalid_input_generator_runtime",
                            "arity": 2,
                            "line": 20,
                            "doc": "Creates invalid input generators from type specifications.",
                            "keywords": [
                                "create_invalid_input_generator_runtime",
                                "input",
                                "generator",
                                "create",
                                "runtime",
                                "invalid",
                                "type",
                                "specification",
                            ],
                        },
                    ],
                },
            }
        }

    def test_calculate_name_coverage_penalty_exact_match(self, exact_vs_extra_index):
        """Test that exact matches have no penalty"""
        searcher = KeywordSearcher(exact_vs_extra_index)

        # Doc info for exact match function
        doc_info = {
            "type": "function",
            "function": "create_input_generator_runtime",
            "name": "TestModule.create_input_generator_runtime/2",
        }

        query_keywords = ["create", "input", "generator", "runtime"]
        penalty = searcher._calculate_name_coverage_penalty(query_keywords, doc_info)

        # Exact match should have no penalty (multiplier = 1.0)
        assert penalty == 1.0

    def test_calculate_name_coverage_penalty_one_extra_word(self, exact_vs_extra_index):
        """Test that functions with one extra word get 30% penalty"""
        searcher = KeywordSearcher(exact_vs_extra_index)

        # Doc info for function with extra "invalid" word
        doc_info = {
            "type": "function",
            "function": "create_invalid_input_generator_runtime",
            "name": "TestModule.create_invalid_input_generator_runtime/2",
        }

        query_keywords = ["create", "input", "generator", "runtime"]
        penalty = searcher._calculate_name_coverage_penalty(query_keywords, doc_info)

        # One extra word = 30% penalty (multiplier = 0.7)
        assert penalty == 0.7

    def test_calculate_name_coverage_penalty_multiple_extra_words(
        self, exact_vs_extra_index
    ):
        """Test penalty scales with number of extra words"""
        searcher = KeywordSearcher(exact_vs_extra_index)

        # Function with 2 extra words
        doc_info = {
            "type": "function",
            "function": "create_invalid_temporary_input_generator",
            "name": "TestModule.create_invalid_temporary_input_generator/2",
        }

        query_keywords = ["create", "input", "generator"]
        penalty = searcher._calculate_name_coverage_penalty(query_keywords, doc_info)

        # Two extra words = 60% penalty (multiplier = 0.4)
        assert penalty == 0.4

    def test_calculate_name_coverage_penalty_module(self, exact_vs_extra_index):
        """Test that modules don't get penalized (only functions)"""
        searcher = KeywordSearcher(exact_vs_extra_index)

        # Module doc info (should not be penalized)
        doc_info = {
            "type": "module",
            "name": "Some.Long.Module.Name",
        }

        query_keywords = ["some", "module"]
        penalty = searcher._calculate_name_coverage_penalty(query_keywords, doc_info)

        # Modules should always have penalty = 1.0 (no penalty)
        assert penalty == 1.0

    def test_exact_match_ranks_higher_than_extra_word(self, exact_vs_extra_index):
        """
        Test the main fix: exact function name match should rank higher
        than a function with extra words in its name.
        """
        searcher = KeywordSearcher(exact_vs_extra_index)

        # Search for keywords that exactly match the first function's name
        results = searcher.search(["create", "input", "generator", "runtime"], top_n=5)

        # Should find both functions
        assert len(results) == 2

        # Exact match should be first
        assert results[0]["function"] == "create_input_generator_runtime"
        assert results[1]["function"] == "create_invalid_input_generator_runtime"

        # Exact match should have higher score
        assert results[0]["score"] > results[1]["score"]

    def test_bm25_b_parameter_set_correctly(self, exact_vs_extra_index):
        """Test that BM25 is initialized with b=0.4 instead of default 0.75"""
        searcher = KeywordSearcher(exact_vs_extra_index)

        # Check that bm25 exists and has the correct b parameter
        assert searcher.bm25 is not None
        # BM25Okapi stores the b parameter as an attribute
        assert hasattr(searcher.bm25, "b")
        assert searcher.bm25.b == 0.4
