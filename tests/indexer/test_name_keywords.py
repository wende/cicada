"""
Tests for name-based keyword extraction in ElixirIndexer.

This verifies that modules and functions without documentation
are still discoverable via keywords extracted from their names.
"""

import pytest

from cicada.indexer import ElixirIndexer


class TestNameKeywordExtraction:
    """Tests for extracting keywords from module and function names"""

    def test_module_without_moduledoc_extracts_name_keywords(self, tmp_path):
        """Test that modules without @moduledoc still get keywords from their name"""
        indexer = ElixirIndexer()

        # Create a test module WITHOUT @moduledoc
        test_file = tmp_path / "llm_client_test.exs"
        test_file.write_text(
            """
defmodule ThenvoiCom.LlmClientTest do
  use ExUnit.Case

  test "validates API keys" do
    assert true
  end
end
"""
        )

        # Index with keyword extraction enabled
        output_path = tmp_path / ".cicada" / "index.json"
        index = indexer.index_repository(str(tmp_path), str(output_path), extract_keywords=True)

        # Verify module was indexed
        assert "ThenvoiCom.LlmClientTest" in index["modules"]
        module = index["modules"]["ThenvoiCom.LlmClientTest"]

        # Verify keywords were extracted from the module name
        assert "keywords" in module
        keywords = module["keywords"]

        # Should contain words from "LlmClientTest" -> ["llm", "client", "test"]
        # Note: exact keywords depend on the extractor, but at least some should match
        keyword_list = list(keywords.keys())
        assert len(keyword_list) > 0, "Module should have keywords from name"

        # Check for expected keywords (may be expanded/scored differently)
        # At minimum, one of the core identifier words should be present
        has_llm_related = any(k in keywords for k in ["llm", "client", "test", "thenvoi"])
        assert has_llm_related, f"Expected name-derived keywords, got: {keyword_list}"

    def test_function_without_doc_extracts_name_keywords(self, tmp_path):
        """Test that functions without @doc still get keywords from their name"""
        indexer = ElixirIndexer()

        # Create a test module with function WITHOUT @doc
        test_file = tmp_path / "user_service.ex"
        test_file.write_text(
            """
defmodule MyApp.UserService do
  @moduledoc "User service"

  def fetch_user_data(user_id) do
    # No @doc here
    {:ok, user_id}
  end

  def validate_email_format(email) do
    # No @doc here either
    String.contains?(email, "@")
  end
end
"""
        )

        # Index with keyword extraction enabled
        output_path = tmp_path / ".cicada" / "index.json"
        index = indexer.index_repository(str(tmp_path), str(output_path), extract_keywords=True)

        # Verify module was indexed
        assert "MyApp.UserService" in index["modules"]
        module = index["modules"]["MyApp.UserService"]

        # Find the functions
        fetch_user_data = next(
            (f for f in module["functions"] if f["name"] == "fetch_user_data"), None
        )
        validate_email_format = next(
            (f for f in module["functions"] if f["name"] == "validate_email_format"),
            None,
        )

        assert fetch_user_data is not None
        assert validate_email_format is not None

        # Verify keywords were extracted from function names
        assert "keywords" in fetch_user_data
        assert "keywords" in validate_email_format

        fetch_keywords = fetch_user_data["keywords"]
        validate_keywords = validate_email_format["keywords"]

        # Check fetch_user_data keywords
        # Should contain words from "fetch_user_data" -> ["fetch", "user", "data"]
        has_fetch_related = any(k in fetch_keywords for k in ["fetch", "user", "data"])
        assert (
            has_fetch_related
        ), f"Expected fetch-related keywords, got: {list(fetch_keywords.keys())}"

        # Check validate_email_format keywords
        # Should contain words from "validate_email_format" -> ["validate", "email", "format"]
        has_validate_related = any(k in validate_keywords for k in ["validate", "email", "format"])
        assert (
            has_validate_related
        ), f"Expected validate-related keywords, got: {list(validate_keywords.keys())}"

    def test_module_with_moduledoc_merges_name_and_doc_keywords(self, tmp_path):
        """Test that modules with @moduledoc merge name and doc keywords"""
        indexer = ElixirIndexer()

        # Create a test module WITH @moduledoc
        test_file = tmp_path / "api_client.ex"
        test_file.write_text(
            """
defmodule MyApp.ApiClient do
  @moduledoc \"\"\"
  HTTP client for external API interactions.
  Handles authentication and rate limiting.
  \"\"\"

  def send_request(url) do
    {:ok, url}
  end
end
"""
        )

        # Index with keyword extraction enabled
        output_path = tmp_path / ".cicada" / "index.json"
        index = indexer.index_repository(str(tmp_path), str(output_path), extract_keywords=True)

        # Verify module was indexed
        assert "MyApp.ApiClient" in index["modules"]
        module = index["modules"]["MyApp.ApiClient"]

        # Verify keywords include BOTH name-derived and doc-derived keywords
        assert "keywords" in module
        keywords = module["keywords"]

        # Should have name keywords: ["api", "client"]
        has_name_keywords = any(k in keywords for k in ["api", "client"])

        # Should have doc keywords: ["http", "authentication", "rate", "limiting"]
        has_doc_keywords = any(
            k in keywords for k in ["http", "authentication", "external", "handles"]
        )

        assert has_name_keywords, f"Expected name-derived keywords, got: {list(keywords.keys())}"
        assert has_doc_keywords, f"Expected doc-derived keywords, got: {list(keywords.keys())}"

    def test_function_with_doc_merges_name_and_doc_keywords(self, tmp_path):
        """Test that functions with @doc merge name and doc keywords"""
        indexer = ElixirIndexer()

        # Create a test module with function WITH @doc
        test_file = tmp_path / "user_service.ex"
        test_file.write_text(
            """
defmodule MyApp.UserService do
  @moduledoc "User service"

  @doc \"\"\"
  Fetches user data from the database.
  \"\"\"
  def fetch_user_data(user_id) do
    {:ok, user_id}
  end
end
"""
        )

        # Index with keyword extraction enabled
        output_path = tmp_path / ".cicada" / "index.json"
        index = indexer.index_repository(str(tmp_path), str(output_path), extract_keywords=True)

        # Verify module was indexed
        assert "MyApp.UserService" in index["modules"]
        module = index["modules"]["MyApp.UserService"]

        # Find the function
        fetch_user_data = next(
            (f for f in module["functions"] if f["name"] == "fetch_user_data"), None
        )

        assert fetch_user_data is not None
        assert "keywords" in fetch_user_data

        keywords = fetch_user_data["keywords"]

        # Should have name keywords: ["fetch", "user", "data"]
        has_name_keywords = any(k in keywords for k in ["fetch", "user", "data"])

        # Should have doc keywords: ["database"]
        has_doc_keywords = "database" in keywords or "fetches" in keywords

        assert has_name_keywords, f"Expected name-derived keywords, got: {list(keywords.keys())}"
        assert has_doc_keywords, f"Expected doc-derived keywords, got: {list(keywords.keys())}"

    def test_camel_case_module_name_splits_correctly(self, tmp_path):
        """Test that camelCase/PascalCase module names are split correctly"""
        indexer = ElixirIndexer()

        test_file = tmp_path / "test.ex"
        test_file.write_text(
            """
defmodule HTTPServerController do
  def handle_request(req), do: req
end
"""
        )

        # Index with keyword extraction enabled
        output_path = tmp_path / ".cicada" / "index.json"
        index = indexer.index_repository(str(tmp_path), str(output_path), extract_keywords=True)

        assert "HTTPServerController" in index["modules"]
        module = index["modules"]["HTTPServerController"]

        assert "keywords" in module
        keywords = module["keywords"]

        # Should split "HTTPServerController" into ["http", "server", "controller"]
        has_expected = any(k in keywords for k in ["http", "server", "controller"])
        assert has_expected, f"Expected split keywords, got: {list(keywords.keys())}"

    def test_snake_case_function_name_splits_correctly(self, tmp_path):
        """Test that snake_case function names are split correctly"""
        indexer = ElixirIndexer()

        test_file = tmp_path / "test.ex"
        test_file.write_text(
            """
defmodule MyApp.Utils do
  @moduledoc "Utilities"

  def validate_email_address(email) do
    String.contains?(email, "@")
  end
end
"""
        )

        # Index with keyword extraction enabled
        output_path = tmp_path / ".cicada" / "index.json"
        index = indexer.index_repository(str(tmp_path), str(output_path), extract_keywords=True)

        assert "MyApp.Utils" in index["modules"]
        module = index["modules"]["MyApp.Utils"]

        func = next(
            (f for f in module["functions"] if f["name"] == "validate_email_address"),
            None,
        )
        assert func is not None
        assert "keywords" in func

        keywords = func["keywords"]

        # Should split "validate_email_address" into ["validate", "email", "address"]
        has_expected = any(k in keywords for k in ["validate", "email", "address"])
        assert has_expected, f"Expected split keywords, got: {list(keywords.keys())}"
