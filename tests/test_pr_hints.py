#!/usr/bin/env python
"""
Tests for PR hints in search results (Phase 2 implementation).

Tests that search_module and search_function display hints about available PR context.
"""

import json

import pytest
import yaml

from cicada.mcp.server import CicadaServer


class TestPRHintsHelper:
    """Test _count_prs_for_file helper method."""

    @pytest.fixture
    def test_server_with_pr_index(self, tmp_path):
        """Create a test server with PR index"""
        from cicada.utils import get_pr_index_path

        index = {
            "modules": {
                "TestModule": {
                    "file": "lib/test.ex",
                    "line": 1,
                    "functions": [],
                }
            },
            "metadata": {"total_modules": 1, "repo_path": str(tmp_path)},
        }
        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(index, f)

        pr_index = {
            "prs": {
                "1": {"number": 1, "title": "PR 1"},
                "2": {"number": 2, "title": "PR 2"},
                "3": {"number": 3, "title": "PR 3"},
            },
            "file_to_prs": {
                "lib/test.ex": [1, 2, 3],
                "lib/other.ex": [1],
            },
            "commit_to_pr": {},
        }
        pr_index_path = get_pr_index_path(tmp_path)
        pr_index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(pr_index_path, "w") as f:
            json.dump(pr_index, f)

        config = {
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(index_path)},
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        return CicadaServer(str(config_path))

    @pytest.fixture
    def test_server_without_pr_index(self, tmp_path):
        """Create a test server without PR index"""
        index = {
            "modules": {
                "TestModule": {
                    "file": "lib/test.ex",
                    "line": 1,
                    "functions": [],
                }
            },
            "metadata": {"total_modules": 1, "repo_path": str(tmp_path)},
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

    def test_count_prs_with_index(self, test_server_with_pr_index):
        """Should count PRs correctly when PR index exists"""
        count = test_server_with_pr_index._count_prs_for_file("lib/test.ex")
        assert count == 3

        count = test_server_with_pr_index._count_prs_for_file("lib/other.ex")
        assert count == 1

        count = test_server_with_pr_index._count_prs_for_file("lib/nonexistent.ex")
        assert count == 0

    def test_count_prs_without_index(self, test_server_without_pr_index):
        """Should return 0 when PR index doesn't exist"""
        count = test_server_without_pr_index._count_prs_for_file("lib/test.ex")
        assert count == 0


class TestSearchModulePRHints:
    """Test PR hints in search_module results."""

    @pytest.fixture
    def test_server_with_pr_index(self, tmp_path):
        """Create a test server with module and PR index"""
        from cicada.utils import get_pr_index_path

        index = {
            "modules": {
                "MyApp.User": {
                    "file": "lib/my_app/user.ex",
                    "line": 1,
                    "moduledoc": "User module",
                    "functions": [
                        {
                            "name": "create",
                            "arity": 1,
                            "line": 10,
                            "doc": "Creates a user",
                            "visibility": "public",
                            "type": "def",
                        }
                    ],
                    "public_functions": 1,
                    "private_functions": 0,
                }
            },
            "metadata": {"total_modules": 1, "repo_path": str(tmp_path)},
        }
        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(index, f)

        pr_index = {
            "prs": {
                "1": {"number": 1, "title": "Add user module"},
                "2": {"number": 2, "title": "Update user validations"},
            },
            "file_to_prs": {
                "lib/my_app/user.ex": [1, 2],
            },
            "commit_to_pr": {},
        }
        pr_index_path = get_pr_index_path(tmp_path)
        pr_index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(pr_index_path, "w") as f:
            json.dump(pr_index, f)

        config = {
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(index_path)},
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        return CicadaServer(str(config_path))

    @pytest.mark.asyncio
    async def test_search_module_includes_pr_hints(self, test_server_with_pr_index):
        """Should include PR hints in markdown output when PR index available"""
        result = await test_server_with_pr_index._search_module(
            "MyApp.User", output_format="markdown"
        )

        assert len(result) == 1
        text = result[0].text

        # Should contain PR hint
        assert "💡 **Context available:**" in text
        assert "2 PRs with review comments" in text
        assert "get_file_pr_history" in text
        assert "lib/my_app/user.ex" in text

    @pytest.mark.asyncio
    async def test_search_module_no_hints_for_json(self, test_server_with_pr_index):
        """Should NOT include PR hints in JSON output"""
        result = await test_server_with_pr_index._search_module(
            "MyApp.User", output_format="json"
        )

        assert len(result) == 1
        text = result[0].text

        # Should not contain PR hint
        assert "💡 **Context available:**" not in text
        assert "get_file_pr_history" not in text

    @pytest.mark.asyncio
    async def test_search_module_no_hints_without_pr_index(self, tmp_path):
        """Should NOT include PR hints when PR index doesn't exist"""
        index = {
            "modules": {
                "MyApp.User": {
                    "file": "lib/my_app/user.ex",
                    "line": 1,
                    "moduledoc": "User module",
                    "functions": [],
                    "public_functions": 0,
                    "private_functions": 0,
                }
            },
            "metadata": {"total_modules": 1, "repo_path": str(tmp_path)},
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

        server = CicadaServer(str(config_path))
        result = await server._search_module("MyApp.User", output_format="markdown")

        assert len(result) == 1
        text = result[0].text

        # Should not contain PR hint
        assert "💡 **Context available:**" not in text
        assert "get_file_pr_history" not in text


class TestSearchFunctionPRHints:
    """Test PR hints in search_function results."""

    @pytest.fixture
    def test_server_with_pr_index(self, tmp_path):
        """Create a test server with function and PR index"""
        from cicada.utils import get_pr_index_path

        index = {
            "modules": {
                "MyApp.User": {
                    "file": "lib/my_app/user.ex",
                    "line": 1,
                    "moduledoc": "User module",
                    "functions": [
                        {
                            "name": "create",
                            "arity": 1,
                            "line": 10,
                            "doc": "Creates a user",
                            "visibility": "public",
                            "type": "def",
                        }
                    ],
                    "calls": [],
                    "public_functions": 1,
                    "private_functions": 0,
                },
                "MyApp.Auth": {
                    "file": "lib/my_app/auth.ex",
                    "line": 1,
                    "moduledoc": "Auth module",
                    "functions": [],
                    "calls": [
                        {"module": "MyApp.User", "function": "create", "arity": 1, "line": 5}
                    ],
                    "public_functions": 0,
                    "private_functions": 0,
                },
            },
            "metadata": {"total_modules": 2, "repo_path": str(tmp_path)},
        }
        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(index, f)

        pr_index = {
            "prs": {
                "1": {"number": 1, "title": "Add user module"},
                "2": {"number": 2, "title": "Add auth"},
            },
            "file_to_prs": {
                "lib/my_app/user.ex": [1],
                "lib/my_app/auth.ex": [2],
            },
            "commit_to_pr": {},
        }
        pr_index_path = get_pr_index_path(tmp_path)
        pr_index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(pr_index_path, "w") as f:
            json.dump(pr_index, f)

        config = {
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(index_path)},
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        return CicadaServer(str(config_path))

    @pytest.mark.asyncio
    async def test_search_function_includes_pr_hints(self, test_server_with_pr_index):
        """Should include PR hints in markdown output when PR index available"""
        result = await test_server_with_pr_index._search_function(
            "create", output_format="markdown"
        )

        assert len(result) == 1
        text = result[0].text

        # Should contain PR hint
        assert "💡 **Context available:**" in text
        assert "lib/my_app/user.ex" in text
        assert "1 PR with review comments" in text
        assert "get_file_pr_history" in text

    @pytest.mark.asyncio
    async def test_search_function_no_hints_for_json(self, test_server_with_pr_index):
        """Should NOT include PR hints in JSON output"""
        result = await test_server_with_pr_index._search_function(
            "create", output_format="json"
        )

        assert len(result) == 1
        text = result[0].text

        # Should not contain PR hint
        assert "💡 **Context available:**" not in text
        assert "get_file_pr_history" not in text

    @pytest.mark.asyncio
    async def test_search_function_no_hints_without_pr_index(self, tmp_path):
        """Should NOT include PR hints when PR index doesn't exist"""
        index = {
            "modules": {
                "MyApp.User": {
                    "file": "lib/my_app/user.ex",
                    "line": 1,
                    "functions": [
                        {
                            "name": "create",
                            "arity": 1,
                            "line": 10,
                            "doc": "Creates a user",
                            "visibility": "public",
                            "type": "def",
                        }
                    ],
                    "calls": [],
                }
            },
            "metadata": {"total_modules": 1, "repo_path": str(tmp_path)},
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

        server = CicadaServer(str(config_path))
        result = await server._search_function("create", output_format="markdown")

        assert len(result) == 1
        text = result[0].text

        # Should not contain PR hint
        assert "💡 **Context available:**" not in text
        assert "get_file_pr_history" not in text

    @pytest.mark.asyncio
    async def test_search_function_no_hints_when_no_prs(self, tmp_path):
        """Should NOT include PR hints when file has no PRs"""
        from cicada.utils import get_pr_index_path

        index = {
            "modules": {
                "MyApp.User": {
                    "file": "lib/my_app/user.ex",
                    "line": 1,
                    "functions": [
                        {
                            "name": "create",
                            "arity": 1,
                            "line": 10,
                            "doc": "Creates a user",
                            "visibility": "public",
                            "type": "def",
                        }
                    ],
                    "calls": [],
                }
            },
            "metadata": {"total_modules": 1, "repo_path": str(tmp_path)},
        }
        index_path = tmp_path / "index.json"
        with open(index_path, "w") as f:
            json.dump(index, f)

        # PR index exists but has no PRs for this file
        pr_index = {
            "prs": {},
            "file_to_prs": {},
            "commit_to_pr": {},
        }
        pr_index_path = get_pr_index_path(tmp_path)
        pr_index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(pr_index_path, "w") as f:
            json.dump(pr_index, f)

        config = {
            "repository": {"path": str(tmp_path)},
            "storage": {"index_path": str(index_path)},
        }
        config_path = tmp_path / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)

        server = CicadaServer(str(config_path))
        result = await server._search_function("create", output_format="markdown")

        assert len(result) == 1
        text = result[0].text

        # Should not contain PR hint because file has no PRs
        assert "💡 **Context available:**" not in text
        assert "get_file_pr_history" not in text
