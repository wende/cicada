"""Statistics analyzer for MCP tool usage."""

import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from cicada.command_logger import get_logger
from cicada.utils.storage import get_repo_hash


class StatsAnalyzer:
    """Analyzes MCP tool usage statistics for a specific project."""

    def __init__(self, repo_path: Path):
        """Initialize analyzer for a specific repository.

        Args:
            repo_path: Path to the repository to analyze stats for.
        """
        self.repo_path = repo_path
        self.repo_hash = get_repo_hash(repo_path)
        self.logger = get_logger()

    def get_stats(
        self,
        days: int | None = None,
        tool_filter: str | None = None,
        time_series: bool = False,
        granularity: str = "daily",
    ) -> dict:
        """Get statistics for the project.

        Args:
            days: Number of days to look back. None = all time.
            tool_filter: Filter by specific tool name.
            time_series: Return time-series data instead of aggregate.
            granularity: "daily" or "weekly" for time series.

        Returns:
            Statistics dictionary.
        """
        # Read all logs for this project
        logs = self.logger.read_logs(repo_hash=self.repo_hash)

        # Filter by date range if specified
        if days:
            cutoff = datetime.now() - timedelta(days=days)
            logs = [log for log in logs if datetime.fromisoformat(log["timestamp"]) >= cutoff]

        # Filter by tool if specified
        if tool_filter:
            logs = [log for log in logs if log["tool_name"] == tool_filter]

        if not logs:
            return self._empty_stats()

        if time_series:
            return self._compute_time_series(logs, granularity)
        else:
            return self._compute_aggregate_stats(logs)

    def _compute_aggregate_stats(self, logs: list[dict]) -> dict:
        """Compute aggregate statistics from logs."""
        if not logs:
            return self._empty_stats()

        total_calls = len(logs)
        successful = sum(1 for log in logs if log.get("success", False))
        success_rate = (successful / total_calls * 100) if total_calls > 0 else 0

        total_exec_time = sum(log.get("execution_time_ms", 0) for log in logs)
        avg_exec_time = total_exec_time / total_calls if total_calls > 0 else 0

        total_input_tokens = sum(log.get("input_tokens", 0) for log in logs)
        total_output_tokens = sum(log.get("output_tokens", 0) for log in logs)

        # Calculate total lines (count newlines in responses)
        total_lines = 0
        for log in logs:
            if log.get("success") and log.get("response"):
                total_lines += self._count_lines(log["response"])

        # Compute per-tool breakdown
        tool_stats = {}
        for log in logs:
            tool = log["tool_name"]
            if tool not in tool_stats:
                tool_stats[tool] = {
                    "count": 0,
                    "success_count": 0,
                    "total_time_ms": 0,
                    "total_lines": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                }

            tool_stats[tool]["count"] += 1
            if log.get("success"):
                tool_stats[tool]["success_count"] += 1
            tool_stats[tool]["total_time_ms"] += log.get("execution_time_ms", 0)
            tool_stats[tool]["input_tokens"] += log.get("input_tokens", 0)
            tool_stats[tool]["output_tokens"] += log.get("output_tokens", 0)

            if log.get("success") and log.get("response"):
                tool_stats[tool]["total_lines"] += self._count_lines(log["response"])

        # Calculate averages
        for tool_stat in tool_stats.values():
            count = tool_stat["count"]
            tool_stat["avg_time_ms"] = tool_stat["total_time_ms"] / count if count > 0 else 0

        # Get date range
        timestamps = [datetime.fromisoformat(log["timestamp"]) for log in logs]
        date_range = {
            "start": min(timestamps).strftime("%Y-%m-%d"),
            "end": max(timestamps).strftime("%Y-%m-%d"),
            "days": (max(timestamps) - min(timestamps)).days + 1,
        }

        return {
            "total_calls": total_calls,
            "success_rate": round(success_rate, 1),
            "successful_calls": successful,
            "failed_calls": total_calls - successful,
            "total_execution_time_ms": round(total_exec_time, 3),
            "avg_execution_time_ms": round(avg_exec_time, 3),
            "total_lines": total_lines,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "date_range": date_range,
            "tools": tool_stats,
        }

    def _count_lines(self, response: list | dict | str) -> int:
        """Count lines in a serialized response."""
        if isinstance(response, list):
            return sum(self._count_lines(item) for item in response)
        elif isinstance(response, dict):
            text = response.get("text", "")
            return text.count("\n") + (1 if text else 0)
        elif isinstance(response, str):
            return response.count("\n") + (1 if response else 0)
        return 0

    def _compute_time_series(self, logs: list[dict], granularity: str) -> dict:
        """Compute time-series statistics."""
        # Group logs by date/week
        series_data: dict[str, dict] = defaultdict(
            lambda: {
                "calls": 0,
                "success_count": 0,
                "total_lines": 0,
                "tools": defaultdict(int),
            }
        )

        for log in logs:
            timestamp = datetime.fromisoformat(log["timestamp"])

            if granularity == "weekly":
                # ISO week format: YYYY-WW
                key = timestamp.strftime("%Y-W%W")
            else:
                # Daily format: YYYY-MM-DD
                key = timestamp.strftime("%Y-%m-%d")

            series_data[key]["calls"] += 1
            if log.get("success"):
                series_data[key]["success_count"] += 1
            if log.get("response"):
                series_data[key]["total_lines"] += self._count_lines(log["response"])
            series_data[key]["tools"][log["tool_name"]] += 1

        # Convert to list and calculate success rates
        series = []
        for date_key, data in sorted(series_data.items()):
            success_rate = data["success_count"] / data["calls"] * 100 if data["calls"] > 0 else 0
            series.append(
                {
                    "date": date_key,
                    "calls": data["calls"],
                    "success_rate": round(success_rate, 1),
                    "total_lines": data["total_lines"],
                    "tools": dict(data["tools"]),
                }
            )

        return {
            "granularity": granularity,
            "series": series,
        }

    def _empty_stats(self) -> dict:
        """Return empty statistics structure."""
        return {
            "total_calls": 0,
            "success_rate": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "total_execution_time_ms": 0,
            "avg_execution_time_ms": 0,
            "total_lines": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "date_range": None,
            "tools": {},
        }

    def format_summary(self, stats: dict) -> str:
        """Format statistics as compact summary."""
        if stats["total_calls"] == 0:
            return "No MCP tool calls recorded for this project."

        lines = []
        lines.append(f"Cicada Stats (Project: {self.repo_path})")

        if stats.get("date_range"):
            dr = stats["date_range"]
            lines.append(f"Period: {dr['start']} to {dr['end']} ({dr['days']} days)")

        lines.append("─" * 60)

        # Format execution time
        total_ms = stats["total_execution_time_ms"]
        if total_ms > 60000:
            time_str = f"{total_ms / 60000:.1f} min"
        else:
            time_str = f"{total_ms / 1000:.1f} sec"

        lines.append(
            f"Total Calls:     {stats['total_calls']:,}  ({stats['success_rate']}% success)"
        )
        lines.append(f"Execution Time:  {time_str} (avg: {stats['avg_execution_time_ms']:.0f}ms)")
        lines.append(f"Output:          {stats['total_lines']:,} lines")

        # Format token counts
        total_tokens = stats["total_input_tokens"] + stats["total_output_tokens"]
        if total_tokens > 1_000_000:
            token_str = f"~{total_tokens / 1_000_000:.1f}M"
        elif total_tokens > 1000:
            token_str = f"~{total_tokens / 1000:.0f}K"
        else:
            token_str = str(total_tokens)

        in_tokens = stats["total_input_tokens"]
        out_tokens = stats["total_output_tokens"]
        lines.append(f"Tokens:          {token_str} (in: {in_tokens:,}, out: {out_tokens:,})")

        # Top 3 tools
        tools = sorted(stats["tools"].items(), key=lambda x: x[1]["count"], reverse=True)[:3]

        if tools:
            tool_str = ", ".join(f"{name} ({data['count']})" for name, data in tools)
            lines.append(f"Top Tools:       {tool_str}")

        return "\n".join(lines)

    def format_detailed(self, stats: dict) -> str:
        """Format detailed per-tool breakdown."""
        if stats["total_calls"] == 0:
            return "No MCP tool calls recorded for this project."

        lines = [self.format_summary(stats), "", "DETAILED BREAKDOWN", "─" * 60]

        # Sort tools by call count
        tools = sorted(stats["tools"].items(), key=lambda x: x[1]["count"], reverse=True)

        for tool_name, tool_data in tools:
            lines.append(
                f"\n{tool_name:20} {tool_data['count']:5} calls  "
                f"(avg: {tool_data['avg_time_ms']:6.1f}ms)"
            )
            lines.append(
                f"  Output: {tool_data['total_lines']:,} lines  "
                f"Tokens: in={tool_data['input_tokens']:,}, out={tool_data['output_tokens']:,}"
            )

        return "\n".join(lines)

    def format_time_series(self, stats: dict) -> str:
        """Format time-series view."""
        lines = [
            f"Cicada Stats - Time Series ({stats['granularity'].title()})",
            f"Project: {self.repo_path}",
            "─" * 60,
        ]

        for entry in stats["series"]:
            lines.append(
                f"{entry['date']:12}  {entry['calls']:4} calls  "
                f"{entry['success_rate']:5.1f}% success  "
                f"{entry['total_lines']:6,} lines"
            )

            # Show top 2 tools for this period
            top_tools = sorted(entry["tools"].items(), key=lambda x: x[1], reverse=True)[:2]
            if top_tools:
                tool_str = ", ".join(f"{name} ({count})" for name, count in top_tools)
                lines.append(f"              {tool_str}")

        return "\n".join(lines)

    def format_json(self, stats: dict) -> str:
        """Format as JSON."""
        return json.dumps(stats, indent=2)

    def reset_stats(self, older_than_days: int | None = None) -> int:
        """Reset stats by deleting log files.

        Args:
            older_than_days: Only delete logs older than this. None = all logs.

        Returns:
            Number of files deleted.
        """
        return self.logger.clear_logs(older_than_days=older_than_days)
