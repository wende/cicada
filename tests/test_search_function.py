#!/usr/bin/env python
"""
Test script for search_function MCP tool.
"""
import asyncio
import sys
from pathlib import Path

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cicada.mcp.server import CicadaServer


@pytest.mark.asyncio
async def test_search_function(tmp_path):
    """Test the search_function tool."""
    # Load test index
    import json
    import yaml

    with open("data/test_index.json") as f:
        test_index = json.load(f)

    # Create temporary config and index
    index_path = tmp_path / "index.json"
    with open(index_path, "w") as f:
        json.dump(test_index, f)

    config = {
        "repository": {"path": str(tmp_path)},
        "storage": {"index_path": str(index_path)},
    }
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f)

    # Create server with test index
    server = CicadaServer(config_path=str(config_path))

    print("Testing search_function tool...\n")

    # Test 1: Search for create_user with usage examples
    print("Test 1: Search for 'create_user' with usage examples")
    result = await server._search_function(
        "create_user", "markdown", include_usage_examples=True, max_examples=3
    )
    print(result[0].text)
    print()

    # Test 2: Search for create_user/2 (with arity)
    print("Test 2: Search for 'create_user/2'")
    result = await server._search_function("create_user/2", "json")
    print(result[0].text)
    print()

    # Test 3: Search for find_user
    print("Test 3: Search for 'find_user'")
    result = await server._search_function("find_user", "markdown")
    print(result[0].text)
    print()

    # Test 4: Search for a function that doesn't exist
    print("Test 4: Search for non-existent function")
    result = await server._search_function("nonexistent_function", "markdown")
    print(result[0].text)
    print()

    # Test 5: Search with wildcard pattern
    print("Test 5: Search for 'create*' (wildcard pattern)")
    result = await server._search_function("create*", "markdown")
    print(result[0].text)
    print()

    # Test 6: Search with OR pattern
    print("Test 6: Search for 'create_user|find_user' (OR pattern)")
    result = await server._search_function("create_user|find_user", "markdown")
    print(result[0].text)
    print()

    # Test 7: Search with wildcard OR pattern
    print("Test 7: Search for 'create*|find*' (wildcard OR pattern)")
    result = await server._search_function("create*|find*", "markdown")
    print(result[0].text)
    print()


@pytest.mark.asyncio
async def test_wildcard_function_search(tmp_path):
    """Test wildcard functionality in function search."""
    import json
    import yaml

    with open("data/test_index.json") as f:
        test_index = json.load(f)

    # Create temporary config and index
    index_path = tmp_path / "index.json"
    with open(index_path, "w") as f:
        json.dump(test_index, f)

    config = {
        "repository": {"path": str(tmp_path)},
        "storage": {"index_path": str(index_path)},
    }
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f)

    server = CicadaServer(config_path=str(config_path))

    # Test wildcard pattern matching
    result = await server._search_function("create*", "markdown")
    assert result[0].text
    # Should find functions starting with "create"
    assert "create" in result[0].text.lower()

    # Test OR pattern
    result = await server._search_function("create*|find*", "markdown")
    assert result[0].text
    # Should find both create and find functions


@pytest.mark.asyncio
async def test_wildcard_module_search(tmp_path):
    """Test wildcard functionality in module search."""
    import json
    import yaml

    with open("data/test_index.json") as f:
        test_index = json.load(f)

    # Create temporary config and index
    index_path = tmp_path / "index.json"
    with open(index_path, "w") as f:
        json.dump(test_index, f)

    config = {
        "repository": {"path": str(tmp_path)},
        "storage": {"index_path": str(index_path)},
    }
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f)

    server = CicadaServer(config_path=str(config_path))

    # Get module names from test index
    module_names = list(test_index["modules"].keys())

    if module_names:
        # Test wildcard pattern - match all modules with a prefix
        if "." in module_names[0]:
            prefix = module_names[0].split(".")[0]
            result = await server._search_module(f"{prefix}.*", "markdown")
            assert result[0].text
            # Should find modules with that prefix
            assert "Found" in result[0].text or prefix in result[0].text

        # Test OR pattern
        if len(module_names) >= 2:
            result = await server._search_module(f"{module_names[0]}|{module_names[1]}", "markdown")
            assert result[0].text
            # Should find both modules


@pytest.mark.asyncio
async def test_module_qualified_or_function_search(tmp_path):
    """Module-qualified OR patterns should return all matching functions."""
    import json
    import yaml

    with open("data/test_index.json") as f:
        test_index = json.load(f)

    index_path = tmp_path / "index.json"
    with open(index_path, "w") as f:
        json.dump(test_index, f)

    config = {
        "repository": {"path": str(tmp_path)},
        "storage": {"index_path": str(index_path)},
    }
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f)

    server = CicadaServer(config_path=str(config_path))

    result = await server._search_function(
        "MyApp.User.create_user|MyApp.User.validate_email",
        "json",
    )
    payload = json.loads(result[0].text)
    names = {entry["full_name"] for entry in payload.get("results", [])}

    assert "MyApp.User.create_user/2" in names
    assert "MyApp.User.validate_email/1" in names


@pytest.mark.asyncio
async def test_or_patterns_with_different_arities(tmp_path):
    """OR patterns can carry independent arity constraints."""
    import json
    import yaml

    with open("data/test_index.json") as f:
        test_index = json.load(f)

    index_path = tmp_path / "index.json"
    with open(index_path, "w") as f:
        json.dump(test_index, f)

    config = {
        "repository": {"path": str(tmp_path)},
        "storage": {"index_path": str(index_path)},
    }
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f)

    server = CicadaServer(config_path=str(config_path))

    result = await server._search_function("create_user/2|validate_email/1", "json")
    payload = json.loads(result[0].text)
    arities = {(entry["function"], entry["arity"]) for entry in payload.get("results", [])}

    assert ("create_user", 2) in arities
    assert ("validate_email", 1) in arities


@pytest.mark.asyncio
async def test_file_path_wildcard_function_search(tmp_path):
    """File-path wildcards should scope function searches."""
    import json
    import yaml

    with open("data/test_index.json") as f:
        test_index = json.load(f)

    index_path = tmp_path / "index.json"
    with open(index_path, "w") as f:
        json.dump(test_index, f)

    config = {
        "repository": {"path": str(tmp_path)},
        "storage": {"index_path": str(index_path)},
    }
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f)

    server = CicadaServer(config_path=str(config_path))

    # Should match create_user in lib/my_app/user.ex
    result = await server._search_function("lib/my_app/*.ex:create*", "json")
    payload = json.loads(result[0].text)
    matched = {entry["full_name"] for entry in payload.get("results", [])}

    assert "MyApp.User.create_user/2" in matched

    # Combining two file-scoped patterns via OR should union their matches
    result = await server._search_function(
        "lib/my_app/*.ex:create*|lib/my_app_web/controllers/*.ex:create", "json"
    )
    payload = json.loads(result[0].text)
    matched = {entry["full_name"] for entry in payload.get("results", [])}

    assert "MyApp.User.create_user/2" in matched
    assert "MyApp.UserController.create/2" in matched


@pytest.mark.asyncio
async def test_module_wildcard_with_nested_segments(tmp_path):
    """Module search should support multi-segment wildcards like MyApp.*.Module."""
    import json
    import yaml

    with open("data/test_index.json") as f:
        test_index = json.load(f)

    # Add a nested module to verify multi-segment wildcard matching
    test_index["modules"]["MyApp.Sub.Module"] = {
        "file": "lib/my_app/sub/module.ex",
        "line": 1,
        "moduledoc": "Nested module for testing.",
        "keywords": {"module": 1.0},
        "functions": [
            {
                "name": "create_user",
                "arity": 1,
                "line": 10,
                "doc": "Creates a user from nested module",
                "type": "def",
                "signature": "create_user(attrs)",
                "examples": None,
                "return_type": None,
                "guards": [],
                "keywords": {"create": 1.0},
            }
        ],
    }

    index_path = tmp_path / "index.json"
    with open(index_path, "w") as f:
        json.dump(test_index, f)

    config = {
        "repository": {"path": str(tmp_path)},
        "storage": {"index_path": str(index_path)},
    }
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f)

    server = CicadaServer(config_path=str(config_path))

    result = await server._search_module("MyApp.*.Module", "markdown")
    text = result[0].text

    assert "MyApp.Sub.Module" in text
    assert "MyApp.User" not in text  # ensure suffix constraint is respected


@pytest.mark.asyncio
async def test_search_function_with_changed_since(tmp_path):
    """Test changed_since filtering in search_function."""
    import json
    import yaml
    from datetime import datetime, timedelta, timezone

    # Create test index with functions having different timestamps (timezone-aware)
    old_date = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
    recent_date = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()

    test_index = {
        "modules": {
            "MyApp.User": {
                "file": "lib/user.ex",
                "line": 1,
                "functions": [
                    {
                        "name": "create_user",
                        "arity": 2,
                        "line": 10,
                        "type": "def",
                        "created_at": old_date,
                        "last_modified_at": recent_date,  # Modified recently
                        "modification_count": 5,
                    },
                    {
                        "name": "delete_user",
                        "arity": 1,
                        "line": 20,
                        "type": "def",
                        "created_at": old_date,
                        "last_modified_at": old_date,  # Not modified recently
                        "modification_count": 1,
                    },
                ],
                "public_functions": 2,
                "private_functions": 0,
            }
        },
        "metadata": {"total_modules": 1, "repo_path": str(tmp_path)},
    }

    index_path = tmp_path / "index.json"
    with open(index_path, "w") as f:
        json.dump(test_index, f)

    config = {
        "repository": {"path": str(tmp_path)},
        "storage": {"index_path": str(index_path)},
    }
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f)

    server = CicadaServer(config_path=str(config_path))

    # Test: Search with changed_since='7d' should only return create_user
    result = await server._search_function("*_user", "json", changed_since="7d")
    data = json.loads(result[0].text)

    # JSON format returns dict with "results" key
    assert data["total_matches"] == 1
    assert data["results"][0]["function"] == "create_user"

    # Test: Search without changed_since should return both
    result = await server._search_function("*_user", "json")
    data = json.loads(result[0].text)

    assert data["total_matches"] == 2


@pytest.mark.asyncio
async def test_search_function_changed_since_no_timestamp(tmp_path):
    """Test that functions without timestamps are skipped when using changed_since."""
    import json
    import yaml

    test_index = {
        "modules": {
            "MyApp.User": {
                "file": "lib/user.ex",
                "line": 1,
                "functions": [
                    {
                        "name": "legacy_function",
                        "arity": 0,
                        "line": 10,
                        "type": "def",
                        # No timestamp fields
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
        json.dump(test_index, f)

    config = {
        "repository": {"path": str(tmp_path)},
        "storage": {"index_path": str(index_path)},
    }
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f)

    server = CicadaServer(config_path=str(config_path))

    # Functions without timestamps should be skipped when using changed_since
    result = await server._search_function("legacy_function", "json", changed_since="7d")
    data = json.loads(result[0].text)

    # No results returns error structure
    assert "error" in data
    assert data["error"] == "Function not found"


if __name__ == "__main__":
    asyncio.run(test_search_function())
