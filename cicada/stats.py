"""Statistics analyzer for MCP tool usage."""

import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from cicada.command_logger import get_logger
from cicada.utils.storage import get_repo_hash, get_storage_dir


def _parse_timestamp(timestamp_str: str) -> datetime:
    """Parse ISO format timestamp string."""
    return datetime.fromisoformat(timestamp_str)


def _safe_divide(numerator: float, denominator: float, default: float = 0) -> float:
    """Divide safely, returning default if denominator is zero."""
    return numerator / denominator if denominator > 0 else default


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

    def _get_project_stats(self) -> dict:
        """Get codebase statistics (modules, functions, keywords).

        Returns:
            Dictionary with module_count, function_count, keyword_count.
        """
        try:
            storage_dir = get_storage_dir(self.repo_path)
            index_file = storage_dir / "index.json"

            if not index_file.exists():
                return {}

            with open(index_file, encoding="utf-8") as f:
                index_data = json.load(f)

            # Extract statistics from index metadata
            metadata = index_data.get("metadata", {})
            modules = index_data.get("modules", {})

            # Count unique keywords from all modules
            unique_keywords = set()
            for module_data in modules.values():
                keywords = module_data.get("keywords", {})
                if keywords:
                    unique_keywords.update(keywords.keys())

            if metadata:
                stats = {
                    "module_count": metadata.get("total_modules", 0),
                    "function_count": metadata.get("total_functions", 0),
                }
            else:
                # Fallback: count from modules if metadata not available
                total_functions = 0
                for module_data in modules.values():
                    functions = module_data.get("functions", [])
                    total_functions += len(functions)

                stats = {
                    "module_count": len(modules),
                    "function_count": total_functions,
                }

            # Always add keyword count
            stats["keyword_count"] = len(unique_keywords)
            return stats
        except (OSError, json.JSONDecodeError):
            # If index file doesn't exist or is corrupt, return empty stats
            return {}

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
        logs = self.logger.read_logs(repo_hash=self.repo_hash)
        logs = self._filter_logs(logs, days=days, tool_filter=tool_filter)

        if not logs:
            return self._empty_stats()

        return (
            self._compute_time_series(logs, granularity)
            if time_series
            else self._compute_aggregate_stats(logs)
        )

    def _filter_logs(
        self,
        logs: list[dict],
        days: int | None = None,
        tool_filter: str | None = None,
    ) -> list[dict]:
        """Filter logs by date range and/or tool name.

        Args:
            logs: List of log entries to filter.
            days: Only include logs from the last N days.
            tool_filter: Only include logs for a specific tool.

        Returns:
            Filtered list of logs.
        """
        if days:
            cutoff = datetime.now() - timedelta(days=days)
            logs = [log for log in logs if _parse_timestamp(log["timestamp"]) >= cutoff]

        if tool_filter:
            logs = [log for log in logs if log["tool_name"] == tool_filter]

        return logs

    def _compute_aggregate_stats(self, logs: list[dict]) -> dict:
        """Orchestrate aggregate statistics computation."""
        if not logs:
            return self._empty_stats()

        basic_metrics = self._aggregate_basic_metrics(logs)
        tool_stats = self._build_and_compute_tool_stats(logs)
        date_range = self._extract_date_range(logs)
        project_stats = self._get_project_stats()

        stats = {
            **basic_metrics,
            "date_range": date_range,
            "tools": tool_stats,
        }

        if project_stats:
            stats["project_stats"] = project_stats

        return stats

    def _aggregate_basic_metrics(self, logs: list[dict]) -> dict:
        """Compute basic call metrics: counts, success rate, tokens, execution time."""
        total_calls = len(logs)
        successful = sum(1 for log in logs if log.get("success", False))
        success_rate = _safe_divide(successful * 100, total_calls)

        total_exec_time = sum(log.get("execution_time_ms", 0) for log in logs)
        avg_exec_time = _safe_divide(total_exec_time, total_calls)

        total_input_tokens = sum(log.get("input_tokens", 0) for log in logs)
        total_output_tokens = sum(log.get("output_tokens", 0) for log in logs)

        total_lines = sum(
            self._count_lines(log["response"])
            for log in logs
            if log.get("success") and log.get("response")
        )

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
        }

    def _build_and_compute_tool_stats(self, logs: list[dict]) -> dict:
        """Build per-tool stats and compute averages."""
        tool_stats = {}

        # Accumulate
        for log in logs:
            tool = log["tool_name"]
            if tool not in tool_stats:
                tool_stats[tool] = self._create_empty_tool_stat()
            self._accumulate_tool_stat(tool_stats[tool], log)

        # Compute averages
        for tool_stat in tool_stats.values():
            self._compute_tool_averages(tool_stat)

        return tool_stats

    def _create_empty_tool_stat(self) -> dict:
        """Create empty tool stat dict with all required fields."""
        return {
            "count": 0,
            "success_count": 0,
            "total_time_ms": 0,
            "total_lines": 0,
            "input_tokens": 0,
            "output_tokens": 0,
        }

    def _accumulate_tool_stat(self, tool_stat: dict, log: dict) -> None:
        """Add log data to tool stat accumulator.

        Args:
            tool_stat: Tool statistics dict to update (modified in place).
            log: Individual log entry to accumulate.
        """
        tool_stat["count"] += 1
        if log.get("success"):
            tool_stat["success_count"] += 1
        tool_stat["total_time_ms"] += log.get("execution_time_ms", 0)
        tool_stat["input_tokens"] += log.get("input_tokens", 0)
        tool_stat["output_tokens"] += log.get("output_tokens", 0)

        if log.get("success") and log.get("response"):
            tool_stat["total_lines"] += self._count_lines(log["response"])

    def _compute_tool_averages(self, tool_stat: dict) -> None:
        """Compute average metrics for a tool (modifies dict in place).

        Args:
            tool_stat: Tool statistics dict to update.
        """
        count = tool_stat["count"]
        tool_stat["avg_time_ms"] = _safe_divide(tool_stat["total_time_ms"], count)
        tool_stat["avg_input_tokens"] = _safe_divide(tool_stat["input_tokens"], count)
        tool_stat["avg_output_tokens"] = _safe_divide(tool_stat["output_tokens"], count)
        tool_stat["avg_total_tokens"] = (
            tool_stat["avg_input_tokens"] + tool_stat["avg_output_tokens"]
        )

    def _extract_date_range(self, logs: list[dict]) -> dict | None:
        """Extract date range from logs.

        Args:
            logs: List of log entries.

        Returns:
            Dict with start, end, and days, or None if logs is empty.
        """
        if not logs:
            return None

        timestamps = [_parse_timestamp(log["timestamp"]) for log in logs]
        min_ts = min(timestamps)
        max_ts = max(timestamps)

        return {
            "start": min_ts.strftime("%Y-%m-%d"),
            "end": max_ts.strftime("%Y-%m-%d"),
            "days": (max_ts - min_ts).days + 1,
        }

    def _count_lines(self, response: Any) -> int:
        """Count lines in a serialized response."""
        if isinstance(response, dict):
            # Handle serialized TextContent structure first
            if response.get("type") == "text" and isinstance(response.get("text"), str):
                text = response["text"]
                return text.count("\n") + (1 if text else 0)
            # For other dicts, recurse on values
            return sum(self._count_lines(v) for v in response.values())
        if isinstance(response, list):
            return sum(self._count_lines(item) for item in response)
        if isinstance(response, str):
            # Count lines in raw strings that might be part of the response
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
            timestamp = _parse_timestamp(log["timestamp"])

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
            success_rate = _safe_divide(data["success_count"] * 100, data["calls"])
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

        # Project statistics
        project_stats = stats.get("project_stats", {})
        if project_stats:
            modules = project_stats.get("module_count", 0)
            functions = project_stats.get("function_count", 0)
            keywords = project_stats.get("keyword_count", 0)
            lines.append(
                f"Codebase:        {modules:,} modules, {functions:,} functions, "
                f"{keywords:,} keywords"
            )

        if stats.get("date_range"):
            dr = stats["date_range"]
            lines.append(f"Period:          {dr['start']} to {dr['end']} ({dr['days']} days)")

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
        avg_tokens_per_call = total_tokens / stats["total_calls"] if stats["total_calls"] > 0 else 0
        lines.append(
            f"Tokens:          {token_str} (in: {in_tokens:,}, out: {out_tokens:,}, "
            f"avg: {avg_tokens_per_call:.0f}/call)"
        )

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
                f"(avg: {tool_data['avg_time_ms']:6.1f}ms, "
                f"{tool_data['avg_total_tokens']:.0f} tokens/call)"
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
