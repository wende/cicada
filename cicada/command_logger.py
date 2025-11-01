"""Command logging functionality for cicada-server MCP.

This module provides logging capabilities for all MCP tool executions,
storing logs in JSONL format organized by date.
"""

import asyncio
import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


class CommandLogger:
    """Logger for MCP tool executions."""

    def __init__(self, log_dir: str | None = None):
        """Initialize the command logger.

        Args:
            log_dir: Directory to store logs. If None, uses system temp directory.
        """
        if log_dir is None:
            # Use system temp directory with a cicada subdirectory
            self.log_dir = Path(tempfile.gettempdir()) / "cicada-logs"
        else:
            self.log_dir = Path(log_dir)

        # Create log directory if it doesn't exist
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _get_log_file_path(self, timestamp: datetime) -> Path:
        """Get the log file path for a given timestamp.

        Logs are organized by date (YYYY-MM-DD.jsonl).

        Args:
            timestamp: The timestamp for the log entry.

        Returns:
            Path to the log file.
        """
        date_str = timestamp.strftime("%Y-%m-%d")
        return self.log_dir / f"{date_str}.jsonl"

    def log_command(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        response: Any,
        execution_time_ms: float,
        timestamp: datetime | None = None,
        error: str | None = None,
    ) -> None:
        """Log a command execution.

        Args:
            tool_name: Name of the tool that was executed.
            arguments: Arguments passed to the tool.
            response: Response from the tool execution.
            execution_time_ms: Execution time in milliseconds.
            timestamp: Timestamp of the execution. If None, uses current time.
            error: Error message if the command failed.
        """
        if timestamp is None:
            timestamp = datetime.now()

        # Prepare the log entry
        log_entry = {
            "timestamp": timestamp.isoformat(),
            "tool_name": tool_name,
            "arguments": arguments,
            "execution_time_ms": round(execution_time_ms, 3),
        }

        # Add response or error
        if error:
            log_entry["error"] = error
            log_entry["success"] = False
        else:
            log_entry["response"] = self._serialize_response(response)
            log_entry["success"] = True

        # Get the log file path for this date
        log_file = self._get_log_file_path(timestamp)

        # Append the log entry to the file
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                json.dump(log_entry, f, ensure_ascii=False)
                f.write("\n")
        except Exception as e:
            # If logging fails, write to stderr but don't crash the server
            import sys

            print(
                f"Warning: Failed to write command log: {e}",
                file=sys.stderr,
            )

    async def log_command_async(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        response: Any,
        execution_time_ms: float,
        timestamp: datetime | None = None,
        error: str | None = None,
    ) -> None:
        """Async version of log_command that runs file I/O in a thread pool.

        This prevents blocking the event loop when logging commands.

        Args:
            tool_name: Name of the tool that was executed.
            arguments: Arguments passed to the tool.
            response: Response from the tool execution.
            execution_time_ms: Execution time in milliseconds.
            timestamp: Timestamp of the execution. If None, uses current time.
            error: Error message if the command failed.
        """
        # Run the synchronous log_command in a thread pool
        await asyncio.to_thread(
            self.log_command,
            tool_name,
            arguments,
            response,
            execution_time_ms,
            timestamp,
            error,
        )

    def _serialize_response(self, response: Any) -> Any:
        """Serialize the response for JSON storage.

        Args:
            response: The response object to serialize.

        Returns:
            JSON-serializable representation of the response.
        """
        # Handle common types first
        if isinstance(response, list):
            return [self._serialize_response(item) for item in response]
        elif isinstance(response, dict):
            return {k: self._serialize_response(v) for k, v in response.items()}
        elif hasattr(response, "text"):
            # MCP TextContent object
            return {"type": "text", "text": response.text}
        elif hasattr(response, "__dict__"):
            # Generic object - convert to string
            try:
                return str(response)
            except Exception:
                return str(response)
        else:
            return response

    def get_log_files(self) -> list[Path]:
        """Get all log files, sorted by date (oldest first).

        Returns:
            List of log file paths.
        """
        log_files = sorted(self.log_dir.glob("*.jsonl"))
        return log_files

    def read_logs(self, date: str | None = None, limit: int | None = None) -> list[dict[str, Any]]:
        """Read logs from file(s).

        Args:
            date: Date string in YYYY-MM-DD format. If None, reads all logs.
            limit: Maximum number of log entries to return (most recent).

        Returns:
            List of log entries.
        """
        logs = []

        if date:
            # Validate date format to prevent path traversal
            try:
                datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                # Invalid date format - return empty list
                return []

            # Read from specific date file
            log_file = self.log_dir / f"{date}.jsonl"
            if log_file.exists():
                logs.extend(self._read_log_file(log_file))
        else:
            # Read from all log files, sorted by date
            for log_file in self.get_log_files():
                logs.extend(self._read_log_file(log_file))

        # Sort by timestamp (most recent last)
        logs.sort(key=lambda x: x.get("timestamp", ""))

        # Apply limit if specified (return most recent)
        if limit:
            logs = logs[-limit:]

        return logs

    def _read_log_file(self, file_path: Path) -> list[dict[str, Any]]:
        """Read logs from a single JSONL file.

        Args:
            file_path: Path to the log file.

        Returns:
            List of log entries from the file.
        """
        logs = []
        try:
            with open(file_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            logs.append(json.loads(line))
                        except json.JSONDecodeError:
                            # Skip malformed lines
                            continue
        except Exception:
            # If reading fails, return what we have
            pass

        return logs

    def clear_logs(self, older_than_days: int | None = None) -> int:
        """Clear log files.

        Args:
            older_than_days: If specified, only delete logs older than this many days.
                           If None, deletes all logs.

        Returns:
            Number of files deleted.
        """
        count = 0
        now = datetime.now()

        for log_file in self.get_log_files():
            should_delete = False

            if older_than_days is None:
                # Delete all logs
                should_delete = True
            else:
                # Check if file is old enough
                try:
                    # Extract date from filename (YYYY-MM-DD.jsonl)
                    date_str = log_file.stem  # Gets filename without .jsonl
                    file_date = datetime.strptime(date_str, "%Y-%m-%d")
                    age_days = (now - file_date).days
                    if age_days > older_than_days:
                        should_delete = True
                except Exception:
                    # If we can't parse the date, skip it
                    continue

            if should_delete:
                try:
                    log_file.unlink()
                    count += 1
                except Exception:
                    pass

        return count


# Global logger instance
_global_logger: CommandLogger | None = None


def get_logger(log_dir: str | None = None) -> CommandLogger:
    """Get or create the global command logger instance.

    Args:
        log_dir: Directory to store logs. Only used on first call.

    Returns:
        CommandLogger instance.
    """
    global _global_logger
    if _global_logger is None:
        _global_logger = CommandLogger(log_dir)
    return _global_logger
