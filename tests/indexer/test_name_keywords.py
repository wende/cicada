"""
Tests for name-based keyword extraction in ElixirIndexer.

Verifies that modules and functions without documentation are still
discoverable via keywords extracted from their names in both full and
incremental indexing scenarios.
"""

from cicada.indexer import ElixirIndexer


class TestNameKeywordExtractionIncremental:
    """Test name keyword extraction in incremental indexing scenarios"""

    def test_incremental_index_extracts_name_keywords_for_new_modules(self, tmp_path):
        """Test that incremental indexing extracts name keywords for newly added modules"""
        indexer = ElixirIndexer()

        # Create initial module
        test_file = tmp_path / "initial.ex"
        test_file.write_text(
            """
defmodule Initial.Module do
  @moduledoc "Initial module"
  def func(), do: :ok
end
"""
        )

        # Full index
        output_path = tmp_path / ".cicada" / "index.json"
        indexer.index_repository(str(tmp_path), str(output_path), extract_keywords=True)

        # Add new module WITHOUT @moduledoc
        new_file = tmp_path / "new.ex"
        new_file.write_text(
            """
defmodule New.UserAuthentication do
  def login(user), do: {:ok, user}
end
"""
        )

        # Incremental index using the proper method
        index = indexer.incremental_index_repository(
            str(tmp_path), str(output_path), extract_keywords=True
        )

        # New module should have name keywords
        assert "New.UserAuthentication" in index["modules"]
        module = index["modules"]["New.UserAuthentication"]
        assert "keywords" in module
        keywords = module["keywords"]

        # Should contain keywords from the module name
        has_relevant = any(k in keywords for k in ["user", "authentication", "new"])
        assert has_relevant, f"Expected name-derived keywords, got: {list(keywords.keys())}"
