"""
Integration tests for .gitignore auto-update on first run
"""

# No unused imports
from cicada.indexer import ElixirIndexer


class TestGitignoreIntegration:
    """Integration tests for .gitignore auto-update"""

    def test_indexer_adds_cicada_to_gitignore_on_first_run(self, tmp_path):
        """Test that indexer adds .cicada/ to .gitignore on first run"""
        # Create a minimal Elixir repository
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        # Create .gitignore
        gitignore_path = repo_dir / ".gitignore"
        gitignore_path.write_text("*.beam\n_build/\n")

        # Create a simple Elixir file
        lib_dir = repo_dir / "lib"
        lib_dir.mkdir()
        ex_file = lib_dir / "example.ex"
        ex_file.write_text(
            """
defmodule Example do
  def hello do
    :world
  end
end
"""
        )

        # Run indexer (first run)
        indexer = ElixirIndexer()
        output_path = repo_dir / ".cicada" / "index.json"
        indexer.index_repository(str(repo_dir), str(output_path))

        # Verify .cicada/ was added to .gitignore
        gitignore_content = gitignore_path.read_text()
        assert ".cicada/" in gitignore_content
        assert "*.beam" in gitignore_content  # Original content preserved
        assert "_build/" in gitignore_content

    def test_indexer_does_not_add_cicada_on_subsequent_runs(self, tmp_path):
        """Test that indexer doesn't add .cicada/ on subsequent runs"""
        # Create a minimal Elixir repository
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        # Create .gitignore
        gitignore_path = repo_dir / ".gitignore"
        gitignore_path.write_text("*.beam\n_build/\n")

        # Create a simple Elixir file
        lib_dir = repo_dir / "lib"
        lib_dir.mkdir()
        ex_file = lib_dir / "example.ex"
        ex_file.write_text(
            """
defmodule Example do
  def hello do
    :world
  end
end
"""
        )

        # Run indexer twice
        indexer = ElixirIndexer()
        output_path = repo_dir / ".cicada" / "index.json"
        indexer.index_repository(str(repo_dir), str(output_path))
        indexer.index_repository(str(repo_dir), str(output_path))

        # Verify .cicada/ appears only once
        gitignore_content = gitignore_path.read_text()
        assert gitignore_content.count(".cicada") == 1

    def test_indexer_skips_gitignore_if_not_present(self, tmp_path):
        """Test that indexer works fine if .gitignore doesn't exist"""
        # Create a minimal Elixir repository without .gitignore
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        # Create a simple Elixir file
        lib_dir = repo_dir / "lib"
        lib_dir.mkdir()
        ex_file = lib_dir / "example.ex"
        ex_file.write_text(
            """
defmodule Example do
  def hello do
    :world
  end
end
"""
        )

        # Run indexer
        indexer = ElixirIndexer()
        output_path = repo_dir / ".cicada" / "index.json"
        indexer.index_repository(str(repo_dir), str(output_path))

        # Verify .gitignore was not created
        gitignore_path = repo_dir / ".gitignore"
        assert not gitignore_path.exists()

        # Verify index was created successfully
        assert output_path.exists()

    def test_indexer_skips_if_cicada_already_in_gitignore(self, tmp_path):
        """Test that indexer doesn't add .cicada/ if already present"""
        # Create a minimal Elixir repository
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        # Create .gitignore with .cicada/ already present
        gitignore_path = repo_dir / ".gitignore"
        original_content = "*.beam\n.cicada/\n_build/\n"
        gitignore_path.write_text(original_content)

        # Create a simple Elixir file
        lib_dir = repo_dir / "lib"
        lib_dir.mkdir()
        ex_file = lib_dir / "example.ex"
        ex_file.write_text(
            """
defmodule Example do
  def hello do
    :world
  end
end
"""
        )

        # Run indexer
        indexer = ElixirIndexer()
        output_path = repo_dir / ".cicada" / "index.json"
        indexer.index_repository(str(repo_dir), str(output_path))

        # Verify .gitignore content unchanged (except maybe index.json creation)
        gitignore_content = gitignore_path.read_text()
        assert gitignore_content.count(".cicada") == 1
        assert "*.beam" in gitignore_content
        assert "_build/" in gitignore_content
