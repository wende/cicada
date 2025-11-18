"""
Comprehensive tests for cicada/utils/path_utils.py
"""

from pathlib import Path

import pytest

from cicada.utils.path_utils import (
    _expand_braces,
    ensure_relative_to_repo,
    find_repo_root,
    match_file_path,
    matches_glob_pattern,
    normalize_file_path,
    resolve_to_repo_root,
)


class TestNormalizeFilePath:
    """Tests for normalize_file_path function"""

    def test_normalize_basic_path(self):
        """Test normalizing a basic path"""
        result = normalize_file_path("lib/user.ex")
        assert result == "lib/user.ex"

    def test_normalize_path_with_leading_dot_slash(self):
        """Test removing leading ./ from path"""
        result = normalize_file_path("./lib/user.ex")
        assert result == "lib/user.ex"

    def test_normalize_path_with_multiple_leading_dots(self):
        """Test removing multiple leading ./ patterns"""
        result = normalize_file_path("././lib/user.ex")
        assert result == "lib/user.ex"

    def test_normalize_path_with_trailing_whitespace(self):
        """Test removing trailing whitespace"""
        result = normalize_file_path("lib/user.ex  ")
        assert result == "lib/user.ex"

    def test_normalize_path_with_leading_whitespace(self):
        """Test removing leading whitespace"""
        result = normalize_file_path("  lib/user.ex")
        assert result == "lib/user.ex"

    def test_normalize_path_with_both_whitespace(self):
        """Test removing both leading and trailing whitespace"""
        result = normalize_file_path("  lib/user.ex  ")
        assert result == "lib/user.ex"

    def test_normalize_path_with_dot_slash_and_whitespace(self):
        """Test removing both ./ and whitespace"""
        result = normalize_file_path("  ./lib/user.ex  ")
        assert result == "lib/user.ex"

    def test_normalize_path_strip_leading_dot_false(self):
        """Test preserving leading ./ when strip_leading_dot=False"""
        result = normalize_file_path("./lib/user.ex", strip_leading_dot=False)
        assert result == "./lib/user.ex"

    def test_normalize_path_strip_trailing_whitespace_false(self):
        """Test preserving trailing whitespace when strip_trailing_whitespace=False"""
        result = normalize_file_path("lib/user.ex  ", strip_trailing_whitespace=False)
        assert result == "lib/user.ex  "

    def test_normalize_path_both_flags_false(self):
        """Test with both flags disabled"""
        result = normalize_file_path(
            "./lib/user.ex  ", strip_leading_dot=False, strip_trailing_whitespace=False
        )
        assert result == "./lib/user.ex  "

    def test_normalize_path_object(self):
        """Test normalizing a Path object"""
        path_obj = Path("./lib/user.ex")
        result = normalize_file_path(path_obj)
        assert result == "lib/user.ex"

    def test_normalize_absolute_path(self):
        """Test normalizing an absolute path (leading / is preserved)"""
        result = normalize_file_path("/repo/lib/user.ex")
        assert result == "/repo/lib/user.ex"

    def test_normalize_empty_string(self):
        """Test normalizing an empty string"""
        result = normalize_file_path("")
        assert result == ""

    def test_normalize_just_dot_slash(self):
        """Test normalizing just ./"""
        result = normalize_file_path("./")
        assert result == ""


class TestResolveToRepoRoot:
    """Tests for resolve_to_repo_root function"""

    def test_resolve_relative_path(self, tmp_path):
        """Test resolving an already relative path"""
        repo_root = tmp_path
        result = resolve_to_repo_root("lib/user.ex", repo_root)
        assert result == Path("lib/user.ex")
        assert not result.is_absolute()

    def test_resolve_absolute_path_within_repo(self, tmp_path):
        """Test resolving an absolute path within repo"""
        repo_root = tmp_path
        file_path = tmp_path / "lib" / "user.ex"
        result = resolve_to_repo_root(file_path, repo_root)
        assert result == Path("lib/user.ex")
        assert not result.is_absolute()

    def test_resolve_absolute_path_outside_repo(self, tmp_path):
        """Test resolving an absolute path outside repo raises ValueError"""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        file_path = tmp_path / "other" / "user.ex"

        with pytest.raises(ValueError) as exc_info:
            resolve_to_repo_root(file_path, repo_root)
        assert "is not within repository" in str(exc_info.value)

    def test_resolve_with_string_paths(self, tmp_path):
        """Test resolving with string paths"""
        repo_root = str(tmp_path)
        file_path = str(tmp_path / "lib" / "user.ex")
        result = resolve_to_repo_root(file_path, repo_root)
        assert result == Path("lib/user.ex")

    def test_resolve_with_path_objects(self, tmp_path):
        """Test resolving with Path objects"""
        repo_root = Path(tmp_path)
        file_path = Path(tmp_path) / "lib" / "user.ex"
        result = resolve_to_repo_root(file_path, repo_root)
        assert result == Path("lib/user.ex")

    def test_resolve_nested_directory(self, tmp_path):
        """Test resolving deeply nested path"""
        repo_root = tmp_path
        file_path = tmp_path / "lib" / "myapp" / "controllers" / "user.ex"
        result = resolve_to_repo_root(file_path, repo_root)
        assert result == Path("lib/myapp/controllers/user.ex")

    def test_resolve_repo_root_itself(self, tmp_path):
        """Test resolving the repo root itself"""
        repo_root = tmp_path
        result = resolve_to_repo_root(tmp_path, repo_root)
        assert result == Path(".")

    def test_resolve_relative_with_dot_slash(self, tmp_path):
        """Test resolving relative path with leading ./"""
        repo_root = tmp_path
        result = resolve_to_repo_root("./lib/user.ex", repo_root)
        assert result == Path("./lib/user.ex")


class TestMatchFilePath:
    """Tests for match_file_path function"""

    def test_match_exact_paths(self):
        """Test exact path match"""
        assert match_file_path("lib/user.ex", "lib/user.ex") is True

    def test_match_with_leading_dot_slash(self):
        """Test matching paths with leading ./"""
        assert match_file_path("./lib/user.ex", "lib/user.ex") is True

    def test_match_absolute_with_relative(self):
        """Test matching absolute path ending with relative"""
        assert match_file_path("/repo/lib/user.ex", "lib/user.ex") is True

    def test_match_partial_path(self):
        """Test matching partial path (filename only)"""
        assert match_file_path("user.ex", "lib/user.ex") is True

    def test_match_reverse_partial(self):
        """Test matching when candidate is shorter"""
        assert match_file_path("lib/user.ex", "user.ex") is True

    def test_no_match_different_files(self):
        """Test non-matching paths"""
        assert match_file_path("lib/user.ex", "lib/admin.ex") is False

    def test_no_match_different_directories(self):
        """Test non-matching directories"""
        assert match_file_path("lib/user.ex", "test/user.ex") is False

    def test_match_with_normalize_false(self):
        """Test matching without normalization still matches via endswith"""
        # Even without normalization, "./lib/user.ex" ends with "lib/user.ex"
        assert match_file_path("./lib/user.ex", "lib/user.ex", normalize=False) is True

    def test_match_exact_with_normalize_false(self):
        """Test exact match without normalization"""
        assert match_file_path("lib/user.ex", "lib/user.ex", normalize=False) is True

    def test_match_with_path_objects(self):
        """Test matching with Path objects"""
        candidate = Path("lib/user.ex")
        target = Path("lib/user.ex")
        assert match_file_path(candidate, target) is True

    def test_match_with_whitespace(self):
        """Test matching paths with whitespace (normalized)"""
        assert match_file_path("  lib/user.ex  ", "lib/user.ex") is True

    def test_match_substring_in_middle_no_match(self):
        """Test that substring in middle doesn't match"""
        assert match_file_path("lib/user", "myapp/lib/user.ex") is False

    def test_match_case_sensitive(self):
        """Test matching is case sensitive"""
        result = match_file_path("lib/User.ex", "lib/user.ex")
        # Depends on file system, but typically should be False
        assert result is False


class TestFindRepoRoot:
    """Tests for find_repo_root function"""

    def test_find_repo_root_from_repo_root(self, tmp_path):
        """Test finding repo root when starting at root"""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        result = find_repo_root(tmp_path)
        assert result == tmp_path

    def test_find_repo_root_from_subdirectory(self, tmp_path):
        """Test finding repo root from subdirectory"""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        sub_dir = tmp_path / "lib" / "myapp"
        sub_dir.mkdir(parents=True)

        result = find_repo_root(sub_dir)
        assert result == tmp_path

    def test_find_repo_root_from_deeply_nested(self, tmp_path):
        """Test finding repo root from deeply nested directory"""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        deep_dir = tmp_path / "a" / "b" / "c" / "d" / "e"
        deep_dir.mkdir(parents=True)

        result = find_repo_root(deep_dir)
        assert result == tmp_path

    def test_find_repo_root_not_in_repo(self, tmp_path):
        """Test finding repo root when not in a git repo"""
        result = find_repo_root(tmp_path)
        assert result is None

    def test_find_repo_root_with_string_path(self, tmp_path):
        """Test finding repo root with string path"""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        result = find_repo_root(str(tmp_path))
        assert result == tmp_path

    def test_find_repo_root_from_current_directory(self, tmp_path, monkeypatch):
        """Test finding repo root from current directory (no start_path)"""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        # Change to temp directory
        monkeypatch.chdir(tmp_path)

        result = find_repo_root()
        assert result == tmp_path

    def test_find_repo_root_parent_is_repo(self, tmp_path):
        """Test finding repo root when parent contains .git"""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        sub_dir = tmp_path / "subdir"
        sub_dir.mkdir()

        result = find_repo_root(sub_dir)
        assert result == tmp_path

    def test_find_repo_root_with_git_file(self, tmp_path):
        """Test finding repo root when .git is a file (like in worktrees)"""
        git_file = tmp_path / ".git"
        git_file.write_text("gitdir: /somewhere")

        result = find_repo_root(tmp_path)
        assert result == tmp_path


class TestEnsureRelativeToRepo:
    """Tests for ensure_relative_to_repo function"""

    def test_ensure_relative_with_relative_path(self, tmp_path):
        """Test ensuring relative path stays relative"""
        result = ensure_relative_to_repo("lib/user.ex", tmp_path)
        assert result == "lib/user.ex"

    def test_ensure_relative_with_absolute_path(self, tmp_path):
        """Test converting absolute path to relative"""
        file_path = tmp_path / "lib" / "user.ex"
        result = ensure_relative_to_repo(file_path, tmp_path)
        assert result == "lib/user.ex"

    def test_ensure_relative_with_dot_slash(self, tmp_path):
        """Test normalizing path with leading ./"""
        result = ensure_relative_to_repo("./lib/user.ex", tmp_path)
        assert result == "lib/user.ex"

    def test_ensure_relative_with_whitespace(self, tmp_path):
        """Test normalizing path with whitespace"""
        result = ensure_relative_to_repo("  lib/user.ex  ", tmp_path)
        assert result == "lib/user.ex"

    def test_ensure_relative_with_absolute_and_normalization(self, tmp_path):
        """Test converting and normalizing absolute path"""
        file_path = tmp_path / "." / "lib" / "user.ex"
        result = ensure_relative_to_repo(file_path, tmp_path)
        assert result == "lib/user.ex"

    def test_ensure_relative_outside_repo_raises(self, tmp_path):
        """Test path outside repo raises ValueError"""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        file_path = tmp_path / "other" / "file.ex"

        with pytest.raises(ValueError) as exc_info:
            ensure_relative_to_repo(file_path, repo_root)
        assert "is not within repository" in str(exc_info.value)

    def test_ensure_relative_with_string_paths(self, tmp_path):
        """Test with string paths"""
        file_path = str(tmp_path / "lib" / "user.ex")
        result = ensure_relative_to_repo(file_path, str(tmp_path))
        assert result == "lib/user.ex"

    def test_ensure_relative_with_path_objects(self, tmp_path):
        """Test with Path objects"""
        file_path = Path(tmp_path) / "lib" / "user.ex"
        result = ensure_relative_to_repo(file_path, Path(tmp_path))
        assert result == "lib/user.ex"

    def test_ensure_relative_nested_path(self, tmp_path):
        """Test with deeply nested path"""
        file_path = tmp_path / "lib" / "myapp" / "controllers" / "user.ex"
        result = ensure_relative_to_repo(file_path, tmp_path)
        assert result == "lib/myapp/controllers/user.ex"


class TestMatchesGlobPattern:
    """Tests for matches_glob_pattern function"""

    def test_simple_wildcard_match(self):
        """Test simple * wildcard matching"""
        assert matches_glob_pattern("lib/user.ex", "lib/*.ex") is True
        assert matches_glob_pattern("test/user.ex", "test/*.ex") is True

    def test_simple_wildcard_no_match(self):
        """Test simple * wildcard not matching wrong extension"""
        assert matches_glob_pattern("lib/user.heex", "lib/*.ex") is False

    def test_simple_wildcard_does_not_match_subdirs(self):
        """Test that * does not match across directory separators"""
        assert matches_glob_pattern("lib/auth/user.ex", "lib/*.ex") is False

    def test_double_star_matches_any_depth(self):
        """Test ** matches files at any directory depth"""
        assert matches_glob_pattern("lib/user.ex", "**/*.ex") is True
        assert matches_glob_pattern("lib/auth/user.ex", "**/*.ex") is True
        assert matches_glob_pattern("lib/auth/controllers/user.ex", "**/*.ex") is True
        assert matches_glob_pattern("test/unit/user_test.ex", "**/*.ex") is True

    def test_double_star_with_prefix(self):
        """Test ** with directory prefix"""
        assert matches_glob_pattern("lib/user.ex", "lib/**/*.ex") is True
        assert matches_glob_pattern("lib/auth/user.ex", "lib/**/*.ex") is True
        assert matches_glob_pattern("lib/auth/controllers/user.ex", "lib/**/*.ex") is True
        assert matches_glob_pattern("test/user.ex", "lib/**/*.ex") is False

    def test_brace_expansion_basic(self):
        """Test basic brace expansion {a,b}"""
        assert matches_glob_pattern("lib/user.ex", "**/*.{ex,heex}") is True
        assert matches_glob_pattern("lib/user.heex", "**/*.{ex,heex}") is True
        assert matches_glob_pattern("lib/user.js", "**/*.{ex,heex}") is False

    def test_brace_expansion_multiple_options(self):
        """Test brace expansion with multiple options"""
        assert matches_glob_pattern("lib/user.ex", "**/*.{ex,heex,eex}") is True
        assert matches_glob_pattern("lib/user.heex", "**/*.{ex,heex,eex}") is True
        assert matches_glob_pattern("lib/user.eex", "**/*.{ex,heex,eex}") is True
        assert matches_glob_pattern("lib/user.js", "**/*.{ex,heex,eex}") is False

    def test_brace_expansion_with_simple_wildcard(self):
        """Test brace expansion with simple * wildcard"""
        assert matches_glob_pattern("lib/user.ex", "lib/*.{ex,heex}") is True
        assert matches_glob_pattern("lib/user.heex", "lib/*.{ex,heex}") is True
        assert matches_glob_pattern("lib/auth/user.ex", "lib/*.{ex,heex}") is False

    def test_pattern_with_leading_dot_slash(self):
        """Test pattern with leading ./ is normalized"""
        assert matches_glob_pattern("lib/user.ex", "./lib/*.ex") is True
        assert matches_glob_pattern("./lib/user.ex", "lib/*.ex") is True
        assert matches_glob_pattern("./lib/user.ex", "./lib/*.ex") is True

    def test_pattern_matching_test_files(self):
        """Test pattern matching test files"""
        assert matches_glob_pattern("test/user_test.ex", "**/*_test.ex") is True
        assert matches_glob_pattern("test/unit/user_test.ex", "**/*_test.ex") is True
        assert matches_glob_pattern("lib/user.ex", "**/*_test.ex") is False

    def test_exact_filename_pattern(self):
        """Test pattern matching exact filename"""
        assert matches_glob_pattern("mix.exs", "mix.exs") is True
        assert matches_glob_pattern("lib/mix.exs", "mix.exs") is False

    def test_pattern_with_path_object(self):
        """Test matching with Path object"""
        path = Path("lib/user.ex")
        assert matches_glob_pattern(path, "lib/*.ex") is True

    def test_complex_pattern_nested_braces(self):
        """Test pattern with multiple brace groups"""
        # Pattern: lib/**/*.{ex,heex}
        assert matches_glob_pattern("lib/auth/user.ex", "lib/**/*.{ex,heex}") is True
        assert matches_glob_pattern("lib/auth/view.heex", "lib/**/*.{ex,heex}") is True
        assert matches_glob_pattern("test/auth/user.ex", "lib/**/*.{ex,heex}") is False

    def test_pattern_matching_specific_subdirectory(self):
        """Test pattern matching specific subdirectory"""
        assert matches_glob_pattern("lib/auth/user.ex", "lib/auth/*.ex") is True
        assert matches_glob_pattern("lib/admin/user.ex", "lib/auth/*.ex") is False
        assert matches_glob_pattern("lib/auth/controllers/user.ex", "lib/auth/*.ex") is False

    def test_pattern_empty_string(self):
        """Test matching empty string pattern"""
        assert matches_glob_pattern("", "") is True
        assert matches_glob_pattern("lib/user.ex", "") is False

    def test_pattern_with_special_chars(self):
        """Test pattern with dots in filename"""
        assert matches_glob_pattern("lib/user.controller.ex", "**/*.ex") is True
        assert matches_glob_pattern("lib/user.controller.ex", "**/*.controller.ex") is True


class TestExpandBraces:
    """Tests for _expand_braces helper function"""

    def test_expand_no_braces(self):
        """Test pattern without braces returns as-is"""
        result = _expand_braces("**/*.ex")
        assert result == ["**/*.ex"]

    def test_expand_simple_braces(self):
        """Test simple brace expansion"""
        result = _expand_braces("**/*.{ex,heex}")
        assert set(result) == {"**/*.ex", "**/*.heex"}

    def test_expand_multiple_alternatives(self):
        """Test brace expansion with multiple alternatives"""
        result = _expand_braces("**/*.{ex,heex,eex}")
        assert set(result) == {"**/*.ex", "**/*.heex", "**/*.eex"}

    def test_expand_braces_with_spaces(self):
        """Test brace expansion handles spaces in alternatives"""
        result = _expand_braces("**/*.{ex, heex}")
        assert set(result) == {"**/*.ex", "**/*.heex"}

    def test_expand_multiple_brace_groups(self):
        """Test pattern with multiple brace groups"""
        result = _expand_braces("{lib,test}/**/*.{ex,heex}")
        # Should expand to: lib/**/*.ex, lib/**/*.heex, test/**/*.ex, test/**/*.heex
        assert set(result) == {
            "lib/**/*.ex",
            "lib/**/*.heex",
            "test/**/*.ex",
            "test/**/*.heex",
        }

    def test_expand_single_alternative(self):
        """Test brace with single alternative"""
        result = _expand_braces("**/*.{ex}")
        assert result == ["**/*.ex"]
