"""
Tests for co-change data integration in ElixirIndexer.

Covers:
- _integrate_cochange_data
- _build_file_to_module_mapping
- _normalize_file_path
- _integrate_file_cochanges
- _integrate_function_cochanges
- _extract_related_functions
"""

from pathlib import Path

import pytest

from cicada.indexer import ElixirIndexer


@pytest.fixture
def indexer():
    """Create an ElixirIndexer instance."""
    return ElixirIndexer(verbose=False)


@pytest.fixture
def sample_modules():
    """Create sample module data for co-change integration."""
    return {
        "MyApp.Auth": {
            "name": "MyApp.Auth",
            "file": "lib/my_app/auth.ex",
            "functions": [
                {"name": "authenticate", "arity": 2},
                {"name": "validate", "arity": 1},
            ],
        },
        "MyApp.User": {
            "name": "MyApp.User",
            "file": "lib/my_app/user.ex",
            "functions": [
                {"name": "get", "arity": 1},
            ],
        },
        "MyApp.Session": {
            "name": "MyApp.Session",
            "file": "lib/my_app/session.ex",
            "functions": [],
        },
    }


@pytest.fixture
def sample_cochange_data():
    """Create sample co-change analysis results."""
    return {
        "file_pairs": {
            ("lib/my_app/auth.ex", "lib/my_app/user.ex"): 15,
            ("lib/my_app/auth.ex", "lib/my_app/session.ex"): 8,
            ("lib/my_app/user.ex", "lib/my_app/session.ex"): 3,
        },
        "function_pairs": {
            ("MyApp.Auth.authenticate/2", "MyApp.User.get/1"): 10,
            ("MyApp.Auth.validate/1", "MyApp.User.get/1"): 5,
        },
        "commit_count": 50,
    }


class TestFileToModuleMapping:
    """Test building file-to-module mapping."""

    def test_build_mapping(self, indexer, sample_modules):
        """Test building reverse mapping from files to modules."""
        repo_path = Path("/repo")

        result = indexer._build_file_to_module_mapping(sample_modules, repo_path)

        assert "lib/my_app/auth.ex" in result
        assert result["lib/my_app/auth.ex"] == "MyApp.Auth"
        assert "lib/my_app/user.ex" in result
        assert result["lib/my_app/user.ex"] == "MyApp.User"

    def test_build_mapping_handles_missing_file(self, indexer):
        """Test that modules without 'file' key are skipped."""
        modules = {
            "NoFile": {"name": "NoFile"},
            "WithFile": {"name": "WithFile", "file": "lib/with_file.ex"},
        }
        repo_path = Path("/repo")

        result = indexer._build_file_to_module_mapping(modules, repo_path)

        assert "lib/with_file.ex" in result
        assert len(result) == 1


class TestNormalizePath:
    """Test file path normalization."""

    def test_normalize_absolute_path(self, indexer):
        """Test normalizing absolute path to relative."""
        repo_path = Path("/home/user/project")

        result = indexer._normalize_file_path("/home/user/project/lib/auth.ex", repo_path)

        assert result == "lib/auth.ex"

    def test_normalize_relative_path(self, indexer):
        """Test that relative paths are returned unchanged."""
        repo_path = Path("/home/user/project")

        result = indexer._normalize_file_path("lib/auth.ex", repo_path)

        assert result == "lib/auth.ex"


class TestIntegrateFileCochanges:
    """Test integrating file-level co-changes."""

    def test_integrate_adds_cochange_files(self, indexer, sample_modules, sample_cochange_data):
        """Test that file co-changes are added to modules."""
        repo_path = Path("/repo")
        file_to_module = indexer._build_file_to_module_mapping(sample_modules, repo_path)

        indexer._integrate_file_cochanges(
            sample_modules,
            sample_cochange_data["file_pairs"],
            file_to_module,
            repo_path,
        )

        # Auth should have user and session as co-changed files
        auth = sample_modules["MyApp.Auth"]
        assert "cochange_files" in auth
        files = [c["file"] for c in auth["cochange_files"]]
        assert "lib/my_app/user.ex" in files
        assert "lib/my_app/session.ex" in files

    def test_integrate_sorts_by_count(self, indexer, sample_modules, sample_cochange_data):
        """Test that co-change files are sorted by count descending."""
        repo_path = Path("/repo")
        file_to_module = indexer._build_file_to_module_mapping(sample_modules, repo_path)

        indexer._integrate_file_cochanges(
            sample_modules,
            sample_cochange_data["file_pairs"],
            file_to_module,
            repo_path,
        )

        auth = sample_modules["MyApp.Auth"]
        counts = [c["count"] for c in auth["cochange_files"]]
        # Should be sorted descending
        assert counts == sorted(counts, reverse=True)


class TestIntegrateFunctionCochanges:
    """Test integrating function-level co-changes."""

    def test_integrate_adds_cochange_functions(self, indexer, sample_modules, sample_cochange_data):
        """Test that function co-changes are added to functions."""
        indexer._integrate_function_cochanges(
            sample_modules, sample_cochange_data["function_pairs"]
        )

        # authenticate should have get as co-changed function
        auth = sample_modules["MyApp.Auth"]
        auth_func = next(f for f in auth["functions"] if f["name"] == "authenticate")
        assert "cochange_functions" in auth_func
        assert any(
            c["function"] == "get" and c["module"] == "MyApp.User"
            for c in auth_func["cochange_functions"]
        )

    def test_integrate_handles_empty_functions(self, indexer, sample_modules, sample_cochange_data):
        """Test that modules without functions are handled."""
        # Session has empty functions list
        indexer._integrate_function_cochanges(
            sample_modules, sample_cochange_data["function_pairs"]
        )

        session = sample_modules["MyApp.Session"]
        # Should not crash, functions list is empty
        assert session["functions"] == []


class TestExtractRelatedFunctions:
    """Test extracting related functions from co-change pairs."""

    def test_extract_finds_related(self, indexer, sample_cochange_data):
        """Test finding related functions."""
        func_pairs = sample_cochange_data["function_pairs"]

        result = indexer._extract_related_functions("MyApp.Auth.authenticate/2", func_pairs)

        assert len(result) == 1
        assert result[0]["module"] == "MyApp.User"
        assert result[0]["function"] == "get"
        assert result[0]["arity"] == 1
        assert result[0]["count"] == 10

    def test_extract_sorts_by_count(self, indexer):
        """Test that results are sorted by count descending."""
        func_pairs = {
            ("MyApp.A.func/0", "MyApp.B.low/0"): 5,
            ("MyApp.A.func/0", "MyApp.C.high/0"): 20,
            ("MyApp.A.func/0", "MyApp.D.mid/0"): 10,
        }

        result = indexer._extract_related_functions("MyApp.A.func/0", func_pairs)

        counts = [r["count"] for r in result]
        assert counts == [20, 10, 5]

    def test_extract_empty_when_no_matches(self, indexer):
        """Test that empty list is returned when no matches."""
        func_pairs = {
            ("MyApp.A.func/0", "MyApp.B.other/0"): 5,
        }

        result = indexer._extract_related_functions("NoMatch.func/0", func_pairs)

        assert result == []


class TestParseSignature:
    """Test function signature parsing."""

    def test_parse_valid_signature(self, indexer):
        """Test parsing valid function signature."""
        result = indexer._parse_function_signature("MyApp.Auth.validate/2")

        assert result is not None
        assert result["module"] == "MyApp.Auth"
        assert result["function"] == "validate"
        assert result["arity"] == 2

    def test_parse_nested_module(self, indexer):
        """Test parsing signature with nested module."""
        result = indexer._parse_function_signature("MyApp.Sub.Module.func/1")

        assert result is not None
        assert result["module"] == "MyApp.Sub.Module"
        assert result["function"] == "func"

    def test_parse_invalid_no_dot(self, indexer):
        """Test that invalid signature without dot returns None."""
        result = indexer._parse_function_signature("func/1")

        assert result is None

    def test_parse_invalid_no_slash(self, indexer):
        """Test that invalid signature without slash returns None."""
        result = indexer._parse_function_signature("MyApp.func")

        assert result is None


class TestIntegrateCochangeData:
    """Test full co-change data integration."""

    def test_integrate_all(self, indexer, sample_modules, sample_cochange_data):
        """Test full integration of co-change data."""
        repo_path = Path("/repo")

        indexer._integrate_cochange_data(sample_modules, sample_cochange_data, repo_path)

        # Check file co-changes were added
        auth = sample_modules["MyApp.Auth"]
        assert "cochange_files" in auth
        assert len(auth["cochange_files"]) > 0

        # Check function co-changes were added
        auth_func = next(f for f in auth["functions"] if f["name"] == "authenticate")
        assert "cochange_functions" in auth_func


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
