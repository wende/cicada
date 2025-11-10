"""Tests for command logging functionality."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from cicada.command_logger import CommandLogger


@pytest.fixture
def temp_log_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def logger(temp_log_dir):
    """Create a CommandLogger instance with a temporary directory."""
    return CommandLogger(log_dir=temp_log_dir)


class TestCommandLogger:
    """Tests for the CommandLogger class."""

    def test_init_creates_log_directory(self, temp_log_dir):
        """Test that initializing the logger creates the log directory."""
        log_dir = Path(temp_log_dir) / "new_dir"
        assert not log_dir.exists()

        logger = CommandLogger(log_dir=str(log_dir))
        assert log_dir.exists()
        assert log_dir.is_dir()

    def test_init_with_none_uses_system_temp(self):
        """Test that passing None uses the system temp directory."""
        logger = CommandLogger(log_dir=None)
        assert logger.log_dir.exists()
        assert "cicada-logs" in str(logger.log_dir)

    def test_log_command_creates_file(self, logger, temp_log_dir):
        """Test that logging a command creates a log file."""
        logger.log_command(
            tool_name="search_module",
            arguments={"module_name": "TestModule"},
            response=[{"type": "text", "text": "Module found"}],
            execution_time_ms=123.456,
        )

        # Check that a log file was created
        log_files = list(Path(temp_log_dir).glob("*.jsonl"))
        assert len(log_files) == 1

        # Check filename format (YYYY-MM-DD.jsonl)
        today = datetime.now().strftime("%Y-%m-%d")
        assert log_files[0].name == f"{today}.jsonl"

    def test_log_command_format(self, logger, temp_log_dir):
        """Test that log entries have the correct format."""
        timestamp = datetime.now()
        logger.log_command(
            tool_name="search_function",
            arguments={"function_name": "test_func", "format": "markdown"},
            response=[{"type": "text", "text": "Function found"}],
            execution_time_ms=456.789,
            timestamp=timestamp,
        )

        # Read the log file
        log_file = Path(temp_log_dir) / f"{timestamp.strftime('%Y-%m-%d')}.jsonl"
        with open(log_file) as f:
            log_entry = json.loads(f.read().strip())

        # Check fields
        assert log_entry["timestamp"] == timestamp.isoformat()
        assert log_entry["tool_name"] == "search_function"
        assert log_entry["arguments"] == {
            "function_name": "test_func",
            "format": "markdown",
        }
        assert log_entry["execution_time_ms"] == 456.789
        assert log_entry["success"] is True
        assert "response" in log_entry

    def test_log_command_with_error(self, logger, temp_log_dir):
        """Test that errors are properly logged."""
        timestamp = datetime.now()
        logger.log_command(
            tool_name="search_module",
            arguments={"module_name": "NonExistent"},
            response=None,
            execution_time_ms=12.345,
            timestamp=timestamp,
            error="Module not found",
        )

        # Read the log file
        log_file = Path(temp_log_dir) / f"{timestamp.strftime('%Y-%m-%d')}.jsonl"
        with open(log_file) as f:
            log_entry = json.loads(f.read().strip())

        # Check error fields
        assert log_entry["success"] is False
        assert log_entry["error"] == "Module not found"
        assert "response" not in log_entry

    def test_multiple_commands_same_day(self, logger, temp_log_dir):
        """Test that multiple commands on the same day append to the same file."""
        timestamp = datetime.now()

        # Log three commands
        for i in range(3):
            logger.log_command(
                tool_name=f"tool_{i}",
                arguments={"arg": i},
                response=[{"text": f"Response {i}"}],
                execution_time_ms=float(i * 100),
                timestamp=timestamp,
            )

        # Check that only one file exists
        log_files = list(Path(temp_log_dir).glob("*.jsonl"))
        assert len(log_files) == 1

        # Check that all three entries are in the file
        with open(log_files[0]) as f:
            lines = f.readlines()
        assert len(lines) == 3

        # Verify each entry
        for i, line in enumerate(lines):
            entry = json.loads(line)
            assert entry["tool_name"] == f"tool_{i}"
            assert entry["arguments"]["arg"] == i

    def test_commands_different_days(self, logger, temp_log_dir):
        """Test that commands on different days create separate files."""
        today = datetime.now()
        yesterday = today - timedelta(days=1)

        # Log command for today
        logger.log_command(
            tool_name="today_tool",
            arguments={},
            response=[{"text": "Today"}],
            execution_time_ms=100.0,
            timestamp=today,
        )

        # Log command for yesterday
        logger.log_command(
            tool_name="yesterday_tool",
            arguments={},
            response=[{"text": "Yesterday"}],
            execution_time_ms=100.0,
            timestamp=yesterday,
        )

        # Check that two files exist
        log_files = sorted(Path(temp_log_dir).glob("*.jsonl"))
        assert len(log_files) == 2

        # Check filenames
        assert log_files[0].name == yesterday.strftime("%Y-%m-%d") + ".jsonl"
        assert log_files[1].name == today.strftime("%Y-%m-%d") + ".jsonl"

    def test_get_log_files(self, logger, temp_log_dir):
        """Test getting all log files sorted by date."""
        # Create logs for different days
        dates = [
            datetime.now() - timedelta(days=2),
            datetime.now() - timedelta(days=1),
            datetime.now(),
        ]

        for date in dates:
            logger.log_command(
                tool_name="test",
                arguments={},
                response=[],
                execution_time_ms=100.0,
                timestamp=date,
            )

        # Get log files
        log_files = logger.get_log_files()
        assert len(log_files) == 3

        # Check they're sorted (oldest first)
        for i in range(len(log_files) - 1):
            assert log_files[i] < log_files[i + 1]

    def test_read_logs_specific_date(self, logger):
        """Test reading logs for a specific date."""
        today = datetime.now()
        yesterday = today - timedelta(days=1)

        # Log commands for two different days
        logger.log_command(
            tool_name="today_tool",
            arguments={"day": "today"},
            response=[],
            execution_time_ms=100.0,
            timestamp=today,
        )
        logger.log_command(
            tool_name="yesterday_tool",
            arguments={"day": "yesterday"},
            response=[],
            execution_time_ms=100.0,
            timestamp=yesterday,
        )

        # Read logs for today only
        today_logs = logger.read_logs(date=today.strftime("%Y-%m-%d"))
        assert len(today_logs) == 1
        assert today_logs[0]["tool_name"] == "today_tool"

        # Read logs for yesterday only
        yesterday_logs = logger.read_logs(date=yesterday.strftime("%Y-%m-%d"))
        assert len(yesterday_logs) == 1
        assert yesterday_logs[0]["tool_name"] == "yesterday_tool"

    def test_read_logs_all_dates(self, logger):
        """Test reading logs from all dates."""
        today = datetime.now()
        yesterday = today - timedelta(days=1)

        # Log commands for two different days
        logger.log_command(
            tool_name="tool1",
            arguments={},
            response=[],
            execution_time_ms=100.0,
            timestamp=yesterday,
        )
        logger.log_command(
            tool_name="tool2",
            arguments={},
            response=[],
            execution_time_ms=100.0,
            timestamp=today,
        )

        # Read all logs
        all_logs = logger.read_logs()
        assert len(all_logs) == 2

        # Check they're sorted by timestamp
        assert all_logs[0]["tool_name"] == "tool1"
        assert all_logs[1]["tool_name"] == "tool2"

    def test_read_logs_with_limit(self, logger):
        """Test reading logs with a limit."""
        timestamp = datetime.now()

        # Log 5 commands
        for i in range(5):
            logger.log_command(
                tool_name=f"tool_{i}",
                arguments={},
                response=[],
                execution_time_ms=100.0,
                timestamp=timestamp,
            )

        # Read with limit of 3 (should get most recent 3)
        limited_logs = logger.read_logs(limit=3)
        assert len(limited_logs) == 3
        assert limited_logs[0]["tool_name"] == "tool_2"
        assert limited_logs[1]["tool_name"] == "tool_3"
        assert limited_logs[2]["tool_name"] == "tool_4"

    def test_clear_logs_all(self, logger):
        """Test clearing all logs."""
        # Create some logs
        for i in range(3):
            logger.log_command(
                tool_name=f"tool_{i}",
                arguments={},
                response=[],
                execution_time_ms=100.0,
            )

        # Verify logs exist
        assert len(logger.get_log_files()) > 0

        # Clear all logs
        count = logger.clear_logs()
        assert count > 0
        assert len(logger.get_log_files()) == 0

    def test_clear_logs_older_than(self, logger):
        """Test clearing logs older than a certain number of days."""
        today = datetime.now()
        old_date = today - timedelta(days=10)
        recent_date = today - timedelta(days=3)

        # Create logs at different dates
        logger.log_command(
            tool_name="old_tool",
            arguments={},
            response=[],
            execution_time_ms=100.0,
            timestamp=old_date,
        )
        logger.log_command(
            tool_name="recent_tool",
            arguments={},
            response=[],
            execution_time_ms=100.0,
            timestamp=recent_date,
        )
        logger.log_command(
            tool_name="today_tool",
            arguments={},
            response=[],
            execution_time_ms=100.0,
            timestamp=today,
        )

        # Clear logs older than 5 days
        count = logger.clear_logs(older_than_days=5)
        assert count == 1  # Only the old_date log should be deleted

        # Verify correct logs remain
        remaining_files = logger.get_log_files()
        assert len(remaining_files) == 2

    def test_execution_time_precision(self, logger, temp_log_dir):
        """Test that execution time is rounded to 3 decimal places."""
        logger.log_command(
            tool_name="test_tool",
            arguments={},
            response=[],
            execution_time_ms=123.456789,
        )

        # Read the log
        log_file = list(Path(temp_log_dir).glob("*.jsonl"))[0]
        with open(log_file) as f:
            entry = json.loads(f.read())

        # Check precision
        assert entry["execution_time_ms"] == 123.457
