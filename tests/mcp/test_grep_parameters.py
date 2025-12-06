"""
Tests for grep-like parameters in search_module and search_function tools.
"""

import json

import pytest
import yaml
from mcp.types import TextContent

from cicada.mcp.server import CicadaServer


@pytest.fixture
def test_index():
    """Minimal index with keywords to enable query execution."""
    return {
        "modules": {
            "TestModule": {
                "file": "lib/test.ex",
                "line": 1,
                "moduledoc": "Test module",
                "functions": [],
                "keywords": {"test": 1.0},
            }
        },
        "metadata": {
            "indexed_at": "2024-01-15T10:30:00",
            "total_modules": 1,
            "total_functions": 0,
            "repo_path": "/test/repo",
            "cicada_version": "0.3.2",
        },
    }


@pytest.fixture
def test_server(tmp_path, test_index):
    """Create a test server with sample index."""
    index_path = tmp_path / "index.json"
    index_path.write_text(json.dumps(test_index))

    config = {
        "repository": {"path": str(tmp_path)},
        "storage": {"index_path": str(index_path)},
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump(config))

    return CicadaServer(str(config_path))


class TestSearchModuleValidation:
    """Validation tests for search_module tool's grep-like parameters."""

    @pytest.mark.parametrize(
        "params, expected_error_part",
        [
            (
                {"module_name": "MyApp.User", "head_limit": 0},
                "'head_limit' must be a positive integer",
            ),
            (
                {"module_name": "MyApp.User", "head_limit": -1},
                "'head_limit' must be a positive integer",
            ),
            (
                {"module_name": "MyApp.User", "head_limit": "5"},
                "'head_limit' must be a positive integer",
            ),
            (
                {"module_name": "MyApp.User", "offset": -1},
                "'offset' must be a non-negative integer",
            ),
            (
                {"module_name": "MyApp.User", "offset": "5"},
                "'offset' must be a non-negative integer",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_invalid_grep_parameters(self, test_server, params, expected_error_part):
        result = await test_server.call_tool("search_module", params)

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert expected_error_part in result[0].text


class TestSearchFunctionValidation:
    """Validation tests for search_function tool's grep-like parameters."""

    @pytest.mark.parametrize(
        "params, expected_error_part",
        [
            (
                {"function_name": "create_user", "head_limit": 0},
                "'head_limit' must be a positive integer",
            ),
            (
                {"function_name": "create_user", "head_limit": -1},
                "'head_limit' must be a positive integer",
            ),
            (
                {"function_name": "create_user", "head_limit": "5"},
                "'head_limit' must be a positive integer",
            ),
            (
                {"function_name": "create_user", "offset": -1},
                "'offset' must be a non-negative integer",
            ),
            (
                {"function_name": "create_user", "offset": "5"},
                "'offset' must be a non-negative integer",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_invalid_grep_parameters(self, test_server, params, expected_error_part):
        result = await test_server.call_tool("search_function", params)

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert expected_error_part in result[0].text


class TestResolveGlobPattern:
    """Tests for resolve_glob_pattern utility function."""

    def test_glob_only(self):
        """Test that glob parameter alone is used as-is."""
        from cicada.utils.path_utils import resolve_glob_pattern

        result = resolve_glob_pattern("lib/**/*.ex", None, None)
        assert result == "lib/**/*.ex"

    def test_path_only(self):
        """Test that path parameter is used with **/* suffix."""
        from cicada.utils.path_utils import resolve_glob_pattern

        result = resolve_glob_pattern(None, "lib/my_app", None)
        assert result == "lib/my_app/**/*"

    def test_type_only(self):
        """Test that type parameter is resolved to glob pattern."""
        from cicada.utils.path_utils import resolve_glob_pattern

        result = resolve_glob_pattern(None, None, "py")
        assert result == "**/*.py"

    def test_glob_and_path(self):
        """Test that glob is combined with path (path prepended)."""
        from cicada.utils.path_utils import resolve_glob_pattern

        result = resolve_glob_pattern("lib/**/*.ex", "ignored/path", None)
        # Path is prepended and leading **/ is stripped from glob
        assert result == "ignored/path/lib/**/*.ex"

    def test_path_and_type(self):
        """Test that path and type are combined."""
        from cicada.utils.path_utils import resolve_glob_pattern

        result = resolve_glob_pattern(None, "lib/my_app", "py")
        # Type "py" maps to "**/*.py", leading **/ is stripped, then prepended with path
        assert result == "lib/my_app/*.py"

    def test_all_none(self):
        """Test that all None returns None."""
        from cicada.utils.path_utils import resolve_glob_pattern

        result = resolve_glob_pattern(None, None, None)
        assert result is None

    def test_unknown_type(self):
        """Test that unknown file type returns None (not in FILE_TYPE_TO_GLOB)."""
        from cicada.utils.path_utils import resolve_glob_pattern

        result = resolve_glob_pattern(None, None, "unknown")
        # Unknown types are not in FILE_TYPE_TO_GLOB, so return None
        assert result is None

    def test_multiple_extensions_type(self):
        """Test file types that map to multiple extensions."""
        from cicada.utils.path_utils import resolve_glob_pattern

        # TypeScript should map to multiple extensions
        result = resolve_glob_pattern(None, None, "ts")
        assert result == "**/*.{ts,tsx}"

        # JavaScript should map to multiple extensions
        result = resolve_glob_pattern(None, None, "js")
        assert result == "**/*.{js,jsx}"
