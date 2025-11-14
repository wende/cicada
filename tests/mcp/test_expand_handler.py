#!/usr/bin/env python
"""
Tests for ExpandHandler - Result expansion functionality.

Tests the expand_result tool that allows drilling down into search results.
"""

import json

import pytest
import yaml

from cicada.mcp.server import CicadaServer


class TestExpandHandler:
    """Test expand_result tool functionality."""

    @pytest.fixture
    def test_server(self, tmp_path):
        """Create a test server instance with sample data."""
        # Create sample index with modules and functions
        index = {
            "modules": {
                "MyApp.Auth": {
                    "file": "lib/my_app/auth.ex",
                    "line": 1,
                    "doc": "Authentication and authorization module",
                    "keywords": {"authentication": 0.9, "auth": 0.8},
                    "functions": [
                        {
                            "name": "verify_token",
                            "arity": 2,
                            "line": 10,
                            "doc": "Verifies JWT token and returns claims",
                            "type": "def",
                            "keywords": {"verify": 0.9, "token": 0.8, "jwt": 0.7},
                        },
                        {
                            "name": "hash_password",
                            "arity": 1,
                            "line": 20,
                            "doc": "Hashes a password using bcrypt",
                            "type": "def",
                            "keywords": {"hash": 0.9, "password": 0.8},
                        },
                    ],
                    "public_functions": 2,
                    "private_functions": 0,
                },
                "MyApp.User": {
                    "file": "lib/my_app/user.ex",
                    "line": 1,
                    "doc": "User management module",
                    "keywords": {"user": 0.9, "management": 0.7},
                    "functions": [
                        {
                            "name": "create_user",
                            "arity": 1,
                            "line": 15,
                            "doc": "Creates a new user",
                            "type": "def",
                            "keywords": {"create": 0.9, "user": 0.8},
                        }
                    ],
                    "public_functions": 1,
                    "private_functions": 0,
                },
            },
            "call_graph": {
                "MyApp.Auth.verify_token/2": {
                    "calls": ["MyApp.Token.decode/1"],
                    "called_by": ["MyApp.AuthController.authenticate/2"],
                }
            },
            "metadata": {"total_modules": 2, "repo_path": str(tmp_path)},
        }

        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(index, f)

        config = {
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(index_path)},
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        return CicadaServer(str(config_path))

    @pytest.mark.asyncio
    async def test_expand_function_shows_full_details(self, test_server):
        """Test expanding a function by full reference shows complete details."""
        result = await test_server.call_tool(
            "expand_result",
            {
                "identifier": "MyApp.Auth.verify_token/2",
                "type": "function",
            },
        )

        assert len(result) == 1
        text = result[0].text

        # Should contain function details
        assert "verify_token" in text
        assert "MyApp.Auth" in text
        assert "Verifies JWT token" in text
        assert "lib/my_app/auth.ex" in text

    @pytest.mark.asyncio
    async def test_expand_module_shows_all_functions(self, test_server):
        """Test expanding a module shows all functions and module details."""
        result = await test_server.call_tool(
            "expand_result",
            {
                "identifier": "MyApp.Auth",
                "type": "module",
            },
        )

        assert len(result) == 1
        text = result[0].text

        # Should contain module details
        assert "MyApp.Auth" in text

        # Should list functions
        assert "verify_token" in text
        assert "hash_password" in text
        assert "lib/my_app/auth.ex" in text

        # Should show function counts
        assert "2 public" in text or "Public:" in text

    @pytest.mark.asyncio
    async def test_expand_auto_detects_type(self, test_server):
        """Test that type='auto' correctly detects module vs function."""
        # Test auto-detect for function (has arity)
        result_func = await test_server.call_tool(
            "expand_result",
            {
                "identifier": "MyApp.User.create_user/1",
                "type": "auto",
            },
        )

        assert len(result_func) == 1
        assert "create_user" in result_func[0].text
        assert "Creates a new user" in result_func[0].text

        # Test auto-detect for module (no arity)
        result_mod = await test_server.call_tool(
            "expand_result",
            {
                "identifier": "MyApp.User",
                "type": "auto",
            },
        )

        assert len(result_mod) == 1
        assert "MyApp.User" in result_mod[0].text
        assert "create_user" in result_mod[0].text  # Should show the function

    @pytest.mark.asyncio
    async def test_expand_missing_identifier_errors(self, test_server):
        """Test that missing identifier parameter returns error."""
        result = await test_server.call_tool("expand_result", {})

        assert len(result) == 1
        text = result[0].text.lower()
        assert "identifier" in text
        assert "required" in text

    @pytest.mark.asyncio
    async def test_expand_nonexistent_identifier_errors(self, test_server):
        """Test that nonexistent identifier returns helpful error."""
        result = await test_server.call_tool(
            "expand_result",
            {
                "identifier": "NonExistent.Module",
                "type": "module",
            },
        )

        assert len(result) == 1
        text = result[0].text.lower()
        assert "not found" in text or "nonexistent" in text.lower()
