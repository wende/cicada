"""
Tests for the query MCP tool.

Focus on input validation and parameter plumbing to increase coverage
for the query tool routing logic.
"""

import json
from unittest.mock import patch

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
                "moduledoc": "Test module for demonstrations",
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


class TestQueryToolValidation:
    """Input validation tests for the query tool."""

    @pytest.mark.parametrize(
        "params, expected_error_part",
        [
            ({}, "'query' is required"),
            ({"query": 123}, "'query' must be a string or list of strings"),
            (
                {"query": ["ok", 5]},
                "'query' list must contain strings or lists of strings (for synonyms)",
            ),
            ({"query": "auth", "scope": "internal"}, "'scope' must be one of"),
            ({"query": "auth", "recent": "yes"}, "'recent' must be a boolean"),
            ({"query": "auth", "filter_type": "classes"}, "'filter_type' must be one of"),
            ({"query": "auth", "match_source": "code"}, "'match_source' must be one of"),
            ({"query": "auth", "max_results": 0}, "'max_results' must be a positive integer"),
            ({"query": "auth", "show_snippets": "true"}, "'show_snippets' must be a boolean"),
        ],
    )
    @pytest.mark.asyncio
    async def test_invalid_parameters(self, test_server, params, expected_error_part):
        result = await test_server.call_tool("query", params)

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert expected_error_part in result[0].text


class TestQueryToolExecution:
    """Tests that valid parameters reach the orchestrator."""

    @pytest.mark.asyncio
    async def test_query_parameters_passed_to_orchestrator(self, test_server):
        call_args = {}

        class FakeOrchestrator:
            last_index = None

            def __init__(self, index):
                FakeOrchestrator.last_index = index

            def execute_query(self, **kwargs):
                nonlocal call_args

                call_args |= kwargs
                return "query result"

        with patch("cicada.query.QueryOrchestrator", FakeOrchestrator):
            result = await test_server.call_tool(
                "query",
                {
                    "query": ["auth"],
                    "scope": "public",
                    "recent": True,
                    "filter_type": "modules",
                    "match_source": "docs",
                    "max_results": 5,
                    "path_pattern": "lib/**",
                    "show_snippets": True,
                },
            )

            assert isinstance(result, list)
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            assert result[0].text == "query result"
        assert call_args == {
            "query": ["auth"],
            "scope": "public",
            "recent": True,
            "filter_type": "modules",
            "match_source": "docs",
            "max_results": 5,
            "path_pattern": "lib/**",
            "show_snippets": True,
        }
        assert FakeOrchestrator.last_index == test_server.index_manager.index
