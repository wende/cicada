"""
Comprehensive tests for keyword search functionality
"""

import pytest
from pathlib import Path
from cicada.keyword_extractor import KeywordExtractor
from cicada.keyword_search import KeywordSearcher
from cicada.indexer import ElixirIndexer


class TestKeywordExtractor:
    """Tests for KeywordExtractor class"""

    def test_keyword_extractor_initialization(self):
        """Test that KeywordExtractor initializes properly"""
        extractor = KeywordExtractor(verbose=False)
        assert extractor.nlp is not None

    def test_split_camel_case(self):
        """Test splitting camelCase identifiers"""
        extractor = KeywordExtractor(verbose=False)

        assert extractor.split_camel_snake_case("camelCase") == "camel Case"
        assert extractor.split_camel_snake_case("getUserData") == "get User Data"
        assert extractor.split_camel_snake_case("myVariableName") == "my Variable Name"

    def test_split_pascal_case(self):
        """Test splitting PascalCase identifiers"""
        extractor = KeywordExtractor(verbose=False)

        assert extractor.split_camel_snake_case("PascalCase") == "Pascal Case"
        assert extractor.split_camel_snake_case("UserController") == "User Controller"
        assert extractor.split_camel_snake_case("HTTPServer") == "HTTP Server"

    def test_split_snake_case(self):
        """Test splitting snake_case identifiers"""
        extractor = KeywordExtractor(verbose=False)

        assert extractor.split_camel_snake_case("snake_case") == "snake case"
        assert extractor.split_camel_snake_case("get_user_data") == "get user data"
        assert (
            extractor.split_camel_snake_case("my_variable_name") == "my variable name"
        )

    def test_split_mixed_case(self):
        """Test splitting mixed case patterns"""
        extractor = KeywordExtractor(verbose=False)

        # Mixed patterns
        assert (
            extractor.split_camel_snake_case("getHTTPResponseCode")
            == "get HTTP Response Code"
        )
        assert extractor.split_camel_snake_case("parseJSONData") == "parse JSON Data"
        assert extractor.split_camel_snake_case("XMLParser") == "XML Parser"

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

    def test_keyword_extractor_missing_model(self, monkeypatch):
        """Test that KeywordExtractor raises error when model missing"""
        import spacy

        def mock_load(name):
            raise OSError("Model not found")

        monkeypatch.setattr(spacy, "load", mock_load)

        with pytest.raises(RuntimeError, match="spaCy model.*not found"):
            KeywordExtractor(verbose=False)

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
        results = searcher.search(["user", "authentication"], top_n=10)

        assert len(results) > 0
        # MyApp.User module should be first (matches both keywords)
        assert results[0]["type"] == "module"
        assert results[0]["name"] == "MyApp.User"
        assert results[0]["score"] == 2
        assert results[0]["confidence"] == 100.0

    def test_search_partial_match(self, sample_index):
        """Test search with partial matches"""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search(["user", "nonexistent"], top_n=10)

        # Should find items with 'user' keyword
        assert len(results) > 0
        # Confidence should be 50% (1 out of 2 keywords matched)
        assert all(r["confidence"] == 50.0 for r in results)

    def test_search_function_match(self, sample_index):
        """Test search matching specific functions"""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search(["validate"], top_n=10)

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
        results = searcher.search(["nonexistent", "foobar"], top_n=10)

        assert len(results) == 0

    def test_search_empty_keywords(self, sample_index):
        """Test search with empty keyword list"""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search([], top_n=10)

        assert len(results) == 0

    def test_search_case_insensitive(self, sample_index):
        """Test that search is case-insensitive"""
        searcher = KeywordSearcher(sample_index)
        results_lower = searcher.search(["user"], top_n=10)
        results_upper = searcher.search(["USER"], top_n=10)
        results_mixed = searcher.search(["UsEr"], top_n=10)

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
        results = searcher.search(["user", "authentication"], top_n=10)

        # Scores should be in descending order
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_search_result_structure(self, sample_index):
        """Test that search results have correct structure"""
        searcher = KeywordSearcher(sample_index)
        results = searcher.search(["user"], top_n=10)

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
        results = searcher.search(["authentication", "user"], top_n=10)

        # Should find module and/or functions
        assert len(results) > 0

        # Check that we found the module or authenticate function
        names = [r["name"] for r in results]
        assert any("MyApp.User" in name for name in names)

    def test_search_no_keywords_in_index(self, tmp_path):
        """Test search behavior when index has no keywords"""
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

        # Search should return empty results
        searcher = KeywordSearcher(index)
        results = searcher.search(["test"], top_n=10)

        assert len(results) == 0
