"""
RichDisplay - Rich-based TUI with in-place updating.

Uses Rich's Live display for a beautiful, real-time updating dashboard
that shows session metrics without scrolling.
"""

import contextlib
from collections import deque
from datetime import datetime
from typing import Deque, List, Optional, Tuple

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..base_tracker import SCHEMA_VERSION
from .base import DisplayAdapter
from .snapshot import DisplaySnapshot


class RichDisplay(DisplayAdapter):
    """Rich-based TUI with in-place updating dashboard.

    Provides a beautiful terminal UI that updates in place,
    showing real-time token usage, tool calls, and activity.
    """

    def __init__(
        self, refresh_rate: float = 0.5, pinned_servers: Optional[List[str]] = None
    ) -> None:
        """Initialize Rich display.

        Args:
            refresh_rate: Display refresh rate in seconds (default 0.5 = 2Hz)
            pinned_servers: List of server names to pin at top of MCP section
        """
        self.console = Console()
        self.refresh_rate = refresh_rate
        self.pinned_servers = set(pinned_servers) if pinned_servers else set()
        self.live: Optional[Live] = None
        self.recent_events: Deque[Tuple[datetime, str, int]] = deque(maxlen=5)
        self._current_snapshot: Optional[DisplaySnapshot] = None
        self._fallback_warned = False

    def start(self, snapshot: DisplaySnapshot) -> None:
        """Start the live display."""
        self._current_snapshot = snapshot
        self.live = Live(
            self._build_layout(snapshot),
            console=self.console,
            refresh_per_second=1 / self.refresh_rate,
            transient=True,  # Clear display on stop to avoid gap before summary (task-49.5)
        )
        self.live.start()

    def update(self, snapshot: DisplaySnapshot) -> None:
        """Update display with new snapshot."""
        self._current_snapshot = snapshot
        if self.live:
            try:
                self.live.update(self._build_layout(snapshot))
            except Exception as e:
                # Graceful fallback if rendering fails
                if not self._fallback_warned:
                    import sys

                    print(
                        f"Warning: TUI rendering failed ({e}), continuing without updates",
                        file=sys.stderr,
                    )
                    self._fallback_warned = True

    def on_event(self, tool_name: str, tokens: int, timestamp: datetime) -> None:
        """Add event to recent activity feed."""
        self.recent_events.append((timestamp, tool_name, tokens))

    def stop(self, snapshot: DisplaySnapshot) -> None:
        """Stop live display and show final summary."""
        if self.live:
            with contextlib.suppress(Exception):
                self.live.stop()
            self.live = None
        self._print_final_summary(snapshot)

    def _build_layout(self, snapshot: DisplaySnapshot) -> Layout:
        """Build the dashboard layout."""
        layout = Layout()

        layout.split_column(
            Layout(self._build_header(snapshot), name="header", size=6),
            Layout(self._build_tokens(snapshot), name="tokens", size=8),
            Layout(self._build_tools(snapshot), name="tools", size=12),
            Layout(self._build_activity(), name="activity", size=6),
            Layout(self._build_footer(), name="footer", size=1),
        )

        return layout

    def _build_header(self, snapshot: DisplaySnapshot) -> Panel:
        """Build header panel with project info, model, git metadata, and file monitoring (AC #6)."""
        duration = self._format_duration_human(snapshot.duration_seconds)
        version_str = f" v{snapshot.version}" if snapshot.version else ""

        header_text = Text()
        header_text.append(f"MCP Audit{version_str} - ", style="bold cyan")
        # Show session type based on tracking mode
        if snapshot.tracking_mode == "full":
            header_text.append("Full Session ↺", style="bold yellow")
        else:
            header_text.append("Live Session", style="bold cyan")
        header_text.append(f"  [{snapshot.platform}]", style="bold cyan")

        # Project and started time (task-46.2)
        started_str = snapshot.start_time.strftime("%H:%M:%S")
        header_text.append(f"\nProject: {snapshot.project}", style="white")
        header_text.append(f"  Started: {started_str}", style="dim")
        header_text.append(f"  Duration: {duration}", style="dim")

        # Model name (AC #6, #15)
        if snapshot.model_name and snapshot.model_name != "Unknown Model":
            header_text.append(f"\nModel: {snapshot.model_name}", style="green")
        elif snapshot.model_id:
            header_text.append(f"\nModel: {snapshot.model_id}", style="green")

        # Git metadata (task-46.5) and file monitoring (task-46.6)
        git_info = []
        if snapshot.git_branch:
            git_info.append(f"🌿 {snapshot.git_branch}")
        if snapshot.git_commit_short:
            git_info.append(f"@{snapshot.git_commit_short}")
        if snapshot.git_status == "dirty":
            git_info.append("*")
        if snapshot.files_monitored > 0:
            git_info.append(f"  📁 {snapshot.files_monitored} files")

        if git_info:
            header_text.append(f"\n{''.join(git_info)}", style="dim")

        return Panel(header_text, border_style="cyan")

    def _build_tokens(self, snapshot: DisplaySnapshot) -> Panel:
        """Build token usage panel with 3-column layout (task-46.8, task-46.3)."""
        table = Table(show_header=False, box=None, padding=(0, 1))
        # Column 1: Tokens (Input, Output, Total, Messages)
        table.add_column("Label1", style="dim", width=16)
        table.add_column("Value1", justify="right", width=12)
        # Column 2: Cache (Created, Read, Efficiency, Built-in)
        table.add_column("Label2", style="dim", width=16)
        table.add_column("Value2", justify="right", width=12)
        # Column 3: Cost (w/ Cache, w/o Cache, Savings)
        table.add_column("Label3", style="dim", width=16)
        table.add_column("Value3", justify="right", width=14)

        # Row 1: Input | Cache Created | Cost w/ Cache
        table.add_row(
            "Input:",
            f"{snapshot.input_tokens:,}",
            "Cache Created:",
            f"{snapshot.cache_created_tokens:,}",
            "Cost w/ Cache:",
            f"${snapshot.cost_estimate:.4f}",
        )

        # Row 2: Output | Cache Read | Cost w/o Cache
        table.add_row(
            "Output:",
            f"{snapshot.output_tokens:,}",
            "Cache Read:",
            f"{snapshot.cache_read_tokens:,}",
            "Cost w/o Cache:",
            f"${snapshot.cost_no_cache:.4f}" if snapshot.cost_no_cache > 0 else "$-.----",
        )

        # Row 2.5 (conditional): Reasoning tokens - only shown when > 0 (v1.3.0)
        # Auto-hides for Claude Code (always 0) and when not using thinking models
        if snapshot.reasoning_tokens > 0:
            table.add_row(
                "Reasoning:",
                f"{snapshot.reasoning_tokens:,}",
                "",
                "",
                "",
                "",
            )

        # Row 3: Total | Efficiency | Savings/Net Cost (task-46.3, task-47.1, task-47.2)
        # Show positive savings with 💰, negative as "Net Cost" with 💸
        # Add hint when cache is inefficient (task-47.2)
        if snapshot.cache_savings > 0:
            savings_label = "💰 Savings:"
            savings_str = f"${snapshot.cache_savings:.4f}"
            savings_pct = (
                f"({snapshot.savings_percent:.0f}%)" if snapshot.savings_percent > 0 else ""
            )
            savings_display = f"{savings_str} {savings_pct}"
        elif snapshot.cache_savings < 0:
            savings_label = "💸 Net Cost:"
            savings_str = f"${abs(snapshot.cache_savings):.4f}"
            # Add hint explaining why (task-47.2)
            hint = self._get_cache_inefficiency_hint(snapshot)
            savings_display = f"{savings_str} {hint}" if hint else savings_str
        else:
            # Zero savings - neutral display
            savings_label = "💰 Savings:"
            savings_display = "$0.0000"
        table.add_row(
            "Total:",
            f"{snapshot.total_tokens:,}",
            "Efficiency:",
            f"{snapshot.cache_efficiency:.1%}",
            savings_label,
            savings_display,
        )

        # Row 4: Messages | Built-in Tools (task-46.1, task-46.4)
        builtin_str = (
            f"{snapshot.builtin_tool_calls} ({self._format_tokens(snapshot.builtin_tool_tokens)})"
        )
        table.add_row(
            "Messages:",
            f"{snapshot.message_count}",
            "Built-in Tools:",
            builtin_str,
            "",
            "",
        )

        return Panel(table, title="Token Usage & Cost", border_style="green")

    def _build_tools(self, snapshot: DisplaySnapshot) -> Panel:
        """Build MCP Server→Tools hierarchy (AC #7, #8, #9, #13, #14)."""
        content = Text()

        # Max content lines (size=14 minus 2 for panel border)
        # Reserve 3 lines for: divider, total line, and potential truncation indicator
        max_display_lines = 9
        lines_used = 0
        servers_shown = 0
        tools_shown = 0
        truncated = False

        if snapshot.server_hierarchy:
            total_servers = len(snapshot.server_hierarchy)
            total_tools = sum(len(s[4]) for s in snapshot.server_hierarchy)

            # Task 68.11: Detect if platform provides per-tool tokens
            # Codex CLI and Gemini CLI don't provide per-tool token attribution
            # Hide token columns when ALL servers have 0 tokens (platform limitation)
            total_mcp_tokens = sum(s[2] for s in snapshot.server_hierarchy)
            show_tokens = total_mcp_tokens > 0

            # Sort servers: pinned first, then by token usage (existing order)
            server_list = list(snapshot.server_hierarchy)
            if self.pinned_servers:
                # Stable sort: pinned servers first, preserving original order within groups
                server_list.sort(key=lambda s: (0 if s[0] in self.pinned_servers else 1))

            # Show server hierarchy
            for server_data in server_list:
                server_name, server_calls, server_tokens, server_avg, tools = server_data

                # Check if we have room for this server AND at least 1 tool (need 2 lines)
                # This prevents showing a server header with no tools underneath (task-49.3)
                if lines_used >= max_display_lines - 1:
                    truncated = True
                    break

                # Server line with pin indicator if pinned
                is_pinned = server_name in self.pinned_servers
                if is_pinned:
                    content.append("  📌 ", style="yellow")
                    content.append(f"{server_name:<15}", style="yellow bold")
                else:
                    content.append(f"  {server_name:<18}", style="cyan bold")
                content.append(f" {server_calls:>3} calls", style="dim")

                # Task 68.11: Only show token columns when platform provides them
                if show_tokens:
                    tokens_str = self._format_tokens(server_tokens)
                    avg_str = self._format_tokens(server_avg)
                    content.append(f"  {tokens_str:>8}", style="white")
                    content.append(f"  (avg {avg_str}/call)", style="dim")
                content.append("\n")
                lines_used += 1
                servers_shown += 1

                # Tool breakdown (AC #9, #13)
                for tool_short, tool_calls, tool_tokens, pct_of_server in tools:
                    if lines_used >= max_display_lines:
                        truncated = True
                        break

                    content.append(f"    └─ {tool_short:<15}", style="dim")
                    content.append(f" {tool_calls:>3} calls", style="dim")

                    # Task 68.11: Only show token columns when platform provides them
                    if show_tokens:
                        tool_tokens_str = self._format_tokens(tool_tokens)
                        content.append(f"  {tool_tokens_str:>8}", style="dim")
                        content.append(f"  ({pct_of_server:.0f}% of server)", style="dim")
                    content.append("\n")
                    lines_used += 1
                    tools_shown += 1

                if truncated:
                    break

            # Truncation indicator
            if truncated:
                remaining_servers = total_servers - servers_shown
                remaining_tools = total_tools - tools_shown
                if remaining_servers > 0 and remaining_tools > 0:
                    content.append(
                        f"  ... +{remaining_servers} more server(s), +{remaining_tools} more tool(s)\n",
                        style="yellow italic",
                    )
                elif remaining_tools > 0:
                    content.append(
                        f"  ... +{remaining_tools} more tool(s)\n", style="yellow italic"
                    )

            # Summary line with MCP percentage of session (AC #14)
            total_mcp_calls = snapshot.total_tool_calls
            content.append("  ─" * 30 + "\n", style="dim")
            content.append(f"  Total MCP: {total_mcp_calls} calls", style="white")
            if show_tokens and snapshot.mcp_tokens_percent > 0:
                content.append(
                    f"  ({snapshot.mcp_tokens_percent:.0f}% of session tokens)", style="dim"
                )
        else:
            content.append("  No MCP tools called yet", style="dim italic")

        # Title includes server count
        num_servers = len(snapshot.server_hierarchy)
        title = f"MCP Servers Usage ({num_servers} servers, {snapshot.total_tool_calls} calls)"

        return Panel(content, title=title, border_style="yellow")

    def _format_tokens(self, tokens: int) -> str:
        """Format token count with K/M suffix."""
        if tokens >= 1_000_000:
            return f"{tokens / 1_000_000:.1f}M"
        elif tokens >= 1_000:
            return f"{tokens / 1_000:.0f}K"
        else:
            return str(tokens)

    def _get_cache_inefficiency_hint(self, snapshot: DisplaySnapshot) -> str:
        """Get brief explanation for cache inefficiency (task-47.2).

        Returns a short hint explaining why cache is costing more than saving.
        """
        created = snapshot.cache_created_tokens
        read = snapshot.cache_read_tokens

        # Determine the reason for inefficiency
        if created > 0 and read == 0:
            return "(new context, no reuse)"
        elif created > 0 and read > 0:
            ratio = read / created if created > 0 else 0
            if ratio < 0.1:
                return "(high creation, low reuse)"
            else:
                return "(creation > savings)"
        elif created == 0 and read == 0:
            return "(no cache activity)"
        else:
            return ""

    def _build_activity(self) -> Panel:
        """Build recent activity panel."""
        if not self.recent_events:
            content = Text("Waiting for events...", style="dim italic")
        else:
            content = Text()
            for timestamp, tool_name, tokens in self.recent_events:
                # Convert UTC timestamp to local time for display (task-68.10)
                local_time = timestamp.astimezone()
                time_str = local_time.strftime("%H:%M:%S")
                short_name = tool_name if len(tool_name) <= 40 else tool_name[:37] + "..."
                content.append(f"[{time_str}] ", style="dim")
                content.append(f"{short_name}", style="cyan")
                # Only show tokens if available (task-68.8)
                # Codex CLI doesn't provide per-tool tokens, so hide when 0
                if tokens > 0:
                    content.append(f" ({tokens:,} tokens)", style="dim")
                content.append("\n")

        return Panel(content, title="Recent Activity", border_style="blue")

    def _build_footer(self) -> Text:
        """Build footer with instructions."""
        return Text(
            "Press Ctrl+C to stop and save session",
            style="dim italic",
            justify="center",
        )

    def _format_duration(self, seconds: float) -> str:
        """Format duration as HH:MM:SS."""
        hours, remainder = divmod(int(seconds), 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def _format_duration_human(self, seconds: float) -> str:
        """Format duration in human-friendly format (task-46.7).

        Examples: "5s", "2m 30s", "1h 15m", "2h 30m 15s"
        """
        if seconds < 60:
            return f"{int(seconds)}s"

        hours, remainder = divmod(int(seconds), 3600)
        minutes, secs = divmod(remainder, 60)

        if hours > 0:
            if secs > 0:
                return f"{hours}h {minutes}m {secs}s"
            elif minutes > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{hours}h"
        else:
            if secs > 0:
                return f"{minutes}m {secs}s"
            else:
                return f"{minutes}m"

    def _print_final_summary(self, snapshot: DisplaySnapshot) -> None:
        """Print final summary after stopping with enhanced display (task-66.10)."""
        version_str = f" v{snapshot.version}" if snapshot.version else ""

        # Build summary text
        summary_parts = [
            "[bold green]Session Complete![/bold green]\n",
        ]

        # Model info
        if snapshot.model_name and snapshot.model_name != "Unknown Model":
            summary_parts.append(f"Model: {snapshot.model_name}\n")

        # Duration and rate stats (task-66.10)
        duration_human = self._format_duration_human(snapshot.duration_seconds)
        summary_parts.append(f"Duration: {duration_human}")

        # Rate statistics (task-66.10)
        if snapshot.duration_seconds > 0:
            msg_per_min = snapshot.message_count / (snapshot.duration_seconds / 60)
            tokens_per_min = snapshot.total_tokens / (snapshot.duration_seconds / 60)
            summary_parts.append(
                f"  ({snapshot.message_count} msgs @ {msg_per_min:.1f}/min, "
                f"{self._format_tokens(int(tokens_per_min))}/min)\n"
            )
        else:
            summary_parts.append(f"  ({snapshot.message_count} messages)\n")

        # Token breakdown with percentages (task-66.10)
        summary_parts.append(f"\n[bold]Tokens[/bold]: {snapshot.total_tokens:,}\n")
        if snapshot.total_tokens > 0:
            input_pct = snapshot.input_tokens / snapshot.total_tokens * 100
            output_pct = snapshot.output_tokens / snapshot.total_tokens * 100
            cache_read_pct = snapshot.cache_read_tokens / snapshot.total_tokens * 100
            cache_created_pct = snapshot.cache_created_tokens / snapshot.total_tokens * 100

            summary_parts.append(
                f"  Input: {snapshot.input_tokens:,} ({input_pct:.1f}%) | "
                f"Output: {snapshot.output_tokens:,} ({output_pct:.1f}%)\n"
            )
            # v1.3.0: Show reasoning tokens when > 0 (Gemini thoughts / Codex reasoning)
            if snapshot.reasoning_tokens > 0:
                reasoning_pct = snapshot.reasoning_tokens / snapshot.total_tokens * 100
                summary_parts.append(
                    f"  Reasoning: {snapshot.reasoning_tokens:,} ({reasoning_pct:.1f}%)\n"
                )
            if snapshot.cache_read_tokens > 0 or snapshot.cache_created_tokens > 0:
                summary_parts.append(
                    f"  Cache read: {snapshot.cache_read_tokens:,} ({cache_read_pct:.1f}%)"
                )
                if snapshot.cache_created_tokens > 0:
                    summary_parts.append(
                        f" | Cache created: {snapshot.cache_created_tokens:,} ({cache_created_pct:.1f}%)"
                    )
                summary_parts.append("\n")
        summary_parts.append(f"  Cache efficiency: {snapshot.cache_efficiency:.1%}\n")

        # Tool breakdown (task-66.10)
        summary_parts.append("\n[bold]Tools[/bold]:\n")

        # MCP tools with server breakdown
        if snapshot.total_tool_calls > 0:
            num_servers = len(snapshot.server_hierarchy) if snapshot.server_hierarchy else 0
            summary_parts.append(
                f"  MCP: {snapshot.total_tool_calls} calls across {num_servers} servers\n"
            )
            # Show top servers
            if snapshot.server_hierarchy:
                top_servers = sorted(snapshot.server_hierarchy, key=lambda s: s[2], reverse=True)[
                    :3
                ]
                server_strs = [f"{s[0]}({s[1]})" for s in top_servers]
                summary_parts.append(f"    Top: {', '.join(server_strs)}\n")
        else:
            summary_parts.append("  MCP: 0 calls\n")

        # Built-in tools (task-46.4)
        if snapshot.builtin_tool_calls > 0:
            summary_parts.append(
                f"  Built-in: {snapshot.builtin_tool_calls} calls "
                f"({self._format_tokens(snapshot.builtin_tool_tokens)})\n"
            )

        # Enhanced cost display (AC #1, #3, #4, task-47.1)
        summary_parts.append(f"\nCost w/ Cache (USD): ${snapshot.cost_estimate:.4f}\n")

        if snapshot.cost_no_cache > 0:
            summary_parts.append(f"Cost w/o Cache (USD): ${snapshot.cost_no_cache:.4f}\n")
            if snapshot.cache_savings > 0:
                summary_parts.append(
                    f"[green]💰 Cache savings: ${snapshot.cache_savings:.4f} "
                    f"({snapshot.savings_percent:.1f}% saved)[/green]\n"
                )
            elif snapshot.cache_savings < 0:
                hint = self._get_cache_inefficiency_hint(snapshot)
                hint_str = f" {hint}" if hint else ""
                summary_parts.append(
                    f"[yellow]💸 Net cost from caching: ${abs(snapshot.cache_savings):.4f}{hint_str}[/yellow]\n"
                )
            else:
                summary_parts.append("💰 Cache savings: $0.0000 (break even)\n")

        # Git metadata (task-46.5)
        if snapshot.git_branch:
            git_info = f"🌿 {snapshot.git_branch}"
            if snapshot.git_commit_short:
                git_info += f"@{snapshot.git_commit_short}"
            if snapshot.git_status == "dirty":
                git_info += " (uncommitted changes)"
            summary_parts.append(f"\n{git_info}\n")

        summary_parts.append(f"\nSchema version: {SCHEMA_VERSION}")

        # Session save location
        if snapshot.session_dir:
            summary_parts.append(f"\n\n[dim]Session saved to: {snapshot.session_dir}[/dim]")

        self.console.print(
            Panel(
                "".join(summary_parts),
                title=f"MCP Audit{version_str} - Session Summary",
                border_style="green",
            )
        )
