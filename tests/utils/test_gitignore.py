"""Tests for cicada.utils.gitignore.GitIgnoreFilter."""

from pathlib import Path

from cicada.utils.gitignore import GitIgnoreFilter


class TestGitIgnoreFilter:
    def test_ignores_git_directory(self, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        f = GitIgnoreFilter(tmp_path)
        assert f.is_dir_ignored(".git")

    def test_respects_gitignore_patterns(self, tmp_path):
        (tmp_path / ".gitignore").write_text("build/\n*.pyc\n")
        f = GitIgnoreFilter(tmp_path)
        assert f.is_dir_ignored("build")
        assert f.is_ignored("foo.pyc")
        assert not f.is_ignored("foo.py")

    def test_respects_git_info_exclude(self, tmp_path):
        info_dir = tmp_path / ".git" / "info"
        info_dir.mkdir(parents=True)
        (info_dir / "exclude").write_text("secret/\n")
        f = GitIgnoreFilter(tmp_path)
        assert f.is_dir_ignored("secret")
        assert not f.is_dir_ignored("public")

    def test_no_gitignore_still_ignores_dot_git(self, tmp_path):
        f = GitIgnoreFilter(tmp_path)
        assert f.is_dir_ignored(".git")
        assert not f.is_ignored("main.py")

    def test_wildcard_patterns(self, tmp_path):
        (tmp_path / ".gitignore").write_text("generated/\n*.log\ndist/\n")
        f = GitIgnoreFilter(tmp_path)
        assert f.is_dir_ignored("generated")
        assert f.is_dir_ignored("dist")
        assert f.is_ignored("app.log")
        assert f.is_ignored("nested/deep.log")
        assert not f.is_ignored("app.py")

    def test_negation_patterns(self, tmp_path):
        (tmp_path / ".gitignore").write_text("*.log\n!important.log\n")
        f = GitIgnoreFilter(tmp_path)
        assert f.is_ignored("debug.log")
        assert not f.is_ignored("important.log")

    def test_comments_and_blank_lines_in_exclude(self, tmp_path):
        info_dir = tmp_path / ".git" / "info"
        info_dir.mkdir(parents=True)
        (info_dir / "exclude").write_text("# comment\n\ntmp/\n")
        f = GitIgnoreFilter(tmp_path)
        assert f.is_dir_ignored("tmp")

    def test_comments_and_whitespace_in_gitignore(self, tmp_path):
        (tmp_path / ".gitignore").write_text("   # comment\n\n  build/\n")
        f = GitIgnoreFilter(tmp_path)
        assert f.is_dir_ignored("build")

    def test_get_ignored_files_respects_negation(self, tmp_path):
        (tmp_path / ".gitignore").write_text("generated/*\n!generated/schema.py\n")
        generated = tmp_path / "generated"
        generated.mkdir()
        (generated / "schema.py").write_text("SCHEMA = {}")
        (generated / "ignored.py").write_text("x = 1")
        (generated / "other.txt").write_text("ignored")

        f = GitIgnoreFilter(tmp_path)
        ignored_py = f.get_ignored_files(suffixes=(".py",))

        assert "generated/ignored.py" in ignored_py
        assert "generated/schema.py" not in ignored_py
        assert "generated/other.txt" not in ignored_py


class TestBaseIndexerGitignoreIntegration:
    """Verify _find_source_files respects .gitignore via BaseIndexer."""

    def test_gitignored_files_excluded(self, tmp_path):
        from cicada.indexer import ElixirIndexer

        (tmp_path / ".gitignore").write_text("generated/\n")
        gen_dir = tmp_path / "generated"
        gen_dir.mkdir()
        (gen_dir / "auto.ex").write_text("defmodule Auto, do: nil")

        (tmp_path / "real.ex").write_text("defmodule Real, do: nil")

        indexer = ElixirIndexer()
        files = indexer._find_source_files(tmp_path)
        names = [f.name for f in files]
        assert "real.ex" in names
        assert "auto.ex" not in names

    def test_works_without_gitignore(self, tmp_path):
        from cicada.indexer import ElixirIndexer

        (tmp_path / "app.ex").write_text("defmodule App, do: nil")
        indexer = ElixirIndexer()
        files = indexer._find_source_files(tmp_path)
        assert len(files) == 1
        assert files[0].name == "app.ex"

    def test_excluded_dirs_still_respected(self, tmp_path):
        from cicada.indexer import ElixirIndexer

        deps_dir = tmp_path / "deps"
        deps_dir.mkdir()
        (deps_dir / "lib.ex").write_text("defmodule Dep, do: nil")

        (tmp_path / "app.ex").write_text("defmodule App, do: nil")

        indexer = ElixirIndexer()
        files = indexer._find_source_files(tmp_path)
        names = [f.name for f in files]
        assert "app.ex" in names
        assert "lib.ex" not in names
