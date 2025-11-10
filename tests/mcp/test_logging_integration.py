"""Integration tests for MCP server command logging."""

import json
import tempfile
from pathlib import Path

import pytest
import yaml

from cicada.mcp.server import CicadaServer


@pytest.fixture
def temp_log_dir():
    """Create a temporary directory for logs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def test_server(tmp_path, temp_log_dir, monkeypatch):
    """Create a test MCP server with logging."""
    # Create test index
    index = {
        "modules": {
            "TestModule": {
                "name": "TestModule",
                "file": "lib/test_module.ex",
                "line": 1,
                "public_functions": 1,
                "private_functions": 0,
                "functions": [
                    {
                        "name": "test_function",
                        "arity": 0,
                        "type": "def",  # Changed from "public" to "def"
                        "signature": "def test_function()",
                        "line": 5,
                    }
                ],
            }
        },
        "metadata": {"total_modules": 1},
    }

    index_path = tmp_path / "index.json"
    with open(index_path, "w") as f:
        json.dump(index, f)

    # Create config
    config = {
        "repository": {"path": str(tmp_path)},
        "storage": {"index_path": str(index_path)},
    }
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f)

    # Patch the logger to use our temp directory
    from cicada import command_logger

    original_logger = command_logger._global_logger
    command_logger._global_logger = command_logger.CommandLogger(log_dir=temp_log_dir)

    try:
        server = CicadaServer(str(config_path))
        yield server, temp_log_dir
    finally:
        # Restore original logger
        command_logger._global_logger = original_logger


@pytest.mark.asyncio
class TestMCPLoggingIntegration:
    """Test that MCP server commands are logged correctly."""

    async def test_successful_command_is_logged(self, test_server):
        """Test that a successful command execution is logged."""
        server, log_dir = test_server

        # Execute a command
        result = await server.call_tool_with_logging(
            name="search_module", arguments={"module_name": "TestModule"}
        )

        # Verify command executed successfully
        assert len(result) > 0

        # Check that a log file was created
        log_files = list(Path(log_dir).glob("*.jsonl"))
        assert len(log_files) == 1

        # Read and verify log entry
        with open(log_files[0]) as f:
            log_entry = json.loads(f.read().strip())

        assert log_entry["tool_name"] == "search_module"
        assert log_entry["arguments"] == {"module_name": "TestModule"}
        assert log_entry["success"] is True
        assert "execution_time_ms" in log_entry
        assert log_entry["execution_time_ms"] > 0
        assert "timestamp" in log_entry
        assert "response" in log_entry

    async def test_failed_command_is_logged(self, test_server):
        """Test that a failed command execution is logged with error."""
        server, log_dir = test_server

        # Execute a command that will fail
        with pytest.raises(ValueError):
            await server.call_tool_with_logging(name="invalid_tool", arguments={})

        # Check that a log file was created
        log_files = list(Path(log_dir).glob("*.jsonl"))
        assert len(log_files) == 1

        # Read and verify log entry
        with open(log_files[0]) as f:
            log_entry = json.loads(f.read().strip())

        assert log_entry["tool_name"] == "invalid_tool"
        assert log_entry["success"] is False
        assert "error" in log_entry
        assert "Unknown tool" in log_entry["error"]
        assert "execution_time_ms" in log_entry

    async def test_multiple_commands_logged(self, test_server):
        """Test that multiple commands are logged sequentially."""
        server, log_dir = test_server

        # Execute multiple commands
        await server.call_tool_with_logging(
            name="search_module", arguments={"module_name": "TestModule"}
        )
        await server.call_tool_with_logging(
            name="search_function", arguments={"function_name": "test_function"}
        )

        # Check log file
        log_files = list(Path(log_dir).glob("*.jsonl"))
        assert len(log_files) == 1

        # Read and verify both entries
        with open(log_files[0]) as f:
            lines = f.readlines()

        assert len(lines) == 2

        entry1 = json.loads(lines[0])
        assert entry1["tool_name"] == "search_module"

        entry2 = json.loads(lines[1])
        assert entry2["tool_name"] == "search_function"

    async def test_log_includes_all_arguments(self, test_server):
        """Test that log entries include all command arguments."""
        server, log_dir = test_server

        # Execute command with multiple arguments
        arguments = {
            "module_name": "TestModule",
            "format": "json",
            "private_functions": "include",
        }
        await server.call_tool_with_logging(name="search_module", arguments=arguments)

        # Read log entry
        log_files = list(Path(log_dir).glob("*.jsonl"))
        with open(log_files[0]) as f:
            log_entry = json.loads(f.read())

        # Verify all arguments are logged
        assert log_entry["arguments"] == arguments

    async def test_execution_time_accuracy(self, test_server):
        """Test that execution time is measured accurately."""
        server, log_dir = test_server

        # Execute a command
        await server.call_tool_with_logging(
            name="search_module", arguments={"module_name": "TestModule"}
        )

        # Read log entry
        log_files = list(Path(log_dir).glob("*.jsonl"))
        with open(log_files[0]) as f:
            log_entry = json.loads(f.read())

        # Execution time should be positive and reasonable (< 10 seconds)
        assert log_entry["execution_time_ms"] > 0
        assert log_entry["execution_time_ms"] < 10000

    async def test_timestamp_format(self, test_server):
        """Test that timestamp is in ISO format."""
        server, log_dir = test_server

        # Execute a command
        await server.call_tool_with_logging(
            name="search_module", arguments={"module_name": "TestModule"}
        )

        # Read log entry
        log_files = list(Path(log_dir).glob("*.jsonl"))
        with open(log_files[0]) as f:
            log_entry = json.loads(f.read())

        # Verify timestamp format
        timestamp = log_entry["timestamp"]
        assert "T" in timestamp  # ISO format includes T separator
        assert timestamp.count("-") >= 2  # Date part has dashes
        assert ":" in timestamp  # Time part has colons

    async def test_response_serialization(self, test_server):
        """Test that responses are properly serialized."""
        server, log_dir = test_server

        # Execute a command
        await server.call_tool_with_logging(
            name="search_module", arguments={"module_name": "TestModule"}
        )

        # Read log entry
        log_files = list(Path(log_dir).glob("*.jsonl"))
        with open(log_files[0]) as f:
            log_entry = json.loads(f.read())

        # Response should be serialized as a list
        assert "response" in log_entry
        assert isinstance(log_entry["response"], list)

    async def test_logger_handles_write_errors_gracefully(self, test_server, monkeypatch):
        """Test that the server continues working even if logging fails."""
        server, log_dir = test_server

        # Mock the log file opening to raise an exception
        original_open = open

        def mock_open(*args, **kwargs):
            if str(args[0]).endswith(".jsonl") and "a" in args[1]:
                raise PermissionError("Mock permission error")
            return original_open(*args, **kwargs)

        monkeypatch.setattr("builtins.open", mock_open)

        # Command should still execute successfully even if logging fails
        result = await server.call_tool_with_logging(
            name="search_module", arguments={"module_name": "TestModule"}
        )

        # Verify command executed
        assert len(result) > 0
