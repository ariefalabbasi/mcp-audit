"""
RichDisplay - Rich-based TUI with in-place updating.

Uses Rich's Live display for a beautiful, real-time updating dashboard
that shows session metrics without scrolling.

Supports Catppuccin color themes (dark/light) and ASCII mode for
terminals with limited Unicode support.
"""

import contextlib
from collections import deque
from datetime import datetime
from typing import Deque, List, Optional, Tuple

from rich import box
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..base_tracker import SCHEMA_VERSION
from .ascii_mode import ascii_emoji, get_box_style, is_ascii_mode
from .base import DisplayAdapter
from .snapshot import DisplaySnapshot
from .theme_detect import get_active_theme
from .themes import _ThemeType


class RichDisplay(DisplayAdapter):
    """Rich-based TUI with in-place updating dashboard.

    Provides a beautiful terminal UI that updates in place,
    showing real-time token usage, tool calls, and activity.

    Supports Catppuccin color themes for light/dark mode and
    ASCII mode for legacy terminal compatibility.
    """

    def __init__(
        self,
        refresh_rate: float = 0.5,
        pinned_servers: Optional[List[str]] = None,
        theme: Optional[str] = None,
    ) -> None:
        """Initialize Rich display.

        Args:
            refresh_rate: Display refresh rate in seconds (default 0.5 = 2Hz)
            pinned_servers: List of server names to pin at top of MCP section
            theme: Theme name override (default: auto-detect from environment)
        """
        self.console = Console()
        self.refresh_rate = refresh_rate
        self.pinned_servers = set(pinned_servers) if pinned_servers else set()
        self.live: Optional[Live] = None
        self.recent_events: Deque[Tuple[datetime, str, int]] = deque(maxlen=5)
        self._current_snapshot: Optional[DisplaySnapshot] = None
        self._fallback_warned = False

        # Theme support (task-83)
        self.theme: _ThemeType = get_active_theme(override=theme)
        self.ascii_mode: bool = is_ascii_mode()
        self.box_style: box.Box = get_box_style()

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
        """Build header panel with project info, model, git metadata, and file monitoring."""
        duration = self._format_duration_human(snapshot.duration_seconds)
        version_str = f" v{snapshot.version}" if snapshot.version else ""

        header_text = Text()
        header_text.append(f"MCP Audit{version_str} - ", style=f"bold {self.theme.title}")
        # Show session type based on tracking mode
        if snapshot.tracking_mode == "full":
            sync_indicator = ascii_emoji("↺")
            header_text.append(f"Full Session {sync_indicator}", style=f"bold {self.theme.warning}")
        else:
            header_text.append("Live Session", style=f"bold {self.theme.title}")
        header_text.append(f"  [{snapshot.platform}]", style=f"bold {self.theme.title}")

        # Project and started time
        started_str = snapshot.start_time.strftime("%H:%M:%S")
        header_text.append(f"\nProject: {snapshot.project}", style=self.theme.primary_text)
        header_text.append(f"  Started: {started_str}", style=self.theme.dim_text)
        header_text.append(f"  Duration: {duration}", style=self.theme.dim_text)

        # Model name
        if snapshot.model_name and snapshot.model_name != "Unknown Model":
            header_text.append(f"\nModel: {snapshot.model_name}", style=self.theme.success)
        elif snapshot.model_id:
            header_text.append(f"\nModel: {snapshot.model_id}", style=self.theme.success)

        # Git metadata and file monitoring
        git_info = []
        if snapshot.git_branch:
            branch_emoji = ascii_emoji("🌿")
            git_info.append(f"{branch_emoji} {snapshot.git_branch}")
        if snapshot.git_commit_short:
            git_info.append(f"@{snapshot.git_commit_short}")
        if snapshot.git_status == "dirty":
            git_info.append("*")
        if snapshot.files_monitored > 0:
            files_emoji = ascii_emoji("📁")
            git_info.append(f"  {files_emoji} {snapshot.files_monitored} files")

        if git_info:
            header_text.append(f"\n{''.join(git_info)}", style=self.theme.dim_text)

        return Panel(header_text, border_style=self.theme.header_border, box=self.box_style)

    def _build_tokens(self, snapshot: DisplaySnapshot) -> Panel:
        """Build token usage panel with 3-column layout."""
        table = Table(show_header=False, box=None, padding=(0, 1))
        # Column 1: Tokens (Input, Output, Total, Messages)
        table.add_column("Label1", style=self.theme.dim_text, width=16)
        table.add_column("Value1", justify="right", width=12)
        # Column 2: Cache (Created, Read, Efficiency, Built-in)
        table.add_column("Label2", style=self.theme.dim_text, width=16)
        table.add_column("Value2", justify="right", width=12)
        # Column 3: Cost (w/ Cache, w/o Cache, Savings)
        table.add_column("Label3", style=self.theme.dim_text, width=16)
        table.add_column("Value3", justify="right", width=14)

        # Data quality indicator (v1.5.0 - task-103.5)
        # "~" prefix for estimated values, nothing for exact
        approx = "~" if snapshot.accuracy_level == "estimated" else ""

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

        # Row 2.5 (conditional): Reasoning tokens - only shown when > 0
        if snapshot.reasoning_tokens > 0:
            table.add_row(
                "Reasoning:",
                f"{snapshot.reasoning_tokens:,}",
                "",
                "",
                "",
                "",
            )

        # Row 3: Total | Efficiency | Savings/Net Cost
        savings_emoji = ascii_emoji("💰")
        cost_emoji = ascii_emoji("💸")
        if snapshot.cache_savings > 0:
            savings_label = f"{savings_emoji} Savings:"
            savings_str = f"${snapshot.cache_savings:.4f}"
            savings_pct = (
                f"({snapshot.savings_percent:.0f}%)" if snapshot.savings_percent > 0 else ""
            )
            savings_display = f"{savings_str} {savings_pct}"
        elif snapshot.cache_savings < 0:
            savings_label = f"{cost_emoji} Net Cost:"
            savings_str = f"${abs(snapshot.cache_savings):.4f}"
            hint = self._get_cache_inefficiency_hint(snapshot)
            savings_display = f"{savings_str} {hint}" if hint else savings_str
        else:
            # Zero savings - neutral display
            savings_label = f"{savings_emoji} Savings:"
            savings_display = "$0.0000"
        # Show "~" prefix for estimated token counts (v1.5.0 - task-103.5)
        total_display = (
            f"{approx}{snapshot.total_tokens:,}" if approx else f"{snapshot.total_tokens:,}"
        )
        table.add_row(
            "Total:",
            total_display,
            "Efficiency:",
            f"{snapshot.cache_efficiency:.1%}",
            savings_label,
            savings_display,
        )

        # Row 4: Messages | Built-in Tools
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

        # Panel title includes accuracy indicator (v1.5.0 - task-103.5)
        if snapshot.accuracy_level == "estimated":
            confidence_pct = int(snapshot.data_quality_confidence * 100)
            title = f"Token Usage & Cost (~{confidence_pct}% accuracy)"
        else:
            title = "Token Usage & Cost"

        return Panel(
            table,
            title=title,
            border_style=self.theme.tokens_border,
            box=self.box_style,
        )

    def _build_tools(self, snapshot: DisplaySnapshot) -> Panel:
        """Build MCP Server→Tools hierarchy."""
        content = Text()

        # Max content lines (size=14 minus 2 for panel border)
        max_display_lines = 9
        lines_used = 0
        servers_shown = 0
        tools_shown = 0
        truncated = False

        if snapshot.server_hierarchy:
            total_servers = len(snapshot.server_hierarchy)
            total_tools = sum(len(s[4]) for s in snapshot.server_hierarchy)

            # Detect if platform provides per-tool tokens
            total_mcp_tokens = sum(s[2] for s in snapshot.server_hierarchy)
            show_tokens = total_mcp_tokens > 0

            # Sort servers: pinned first, then by token usage
            server_list = list(snapshot.server_hierarchy)
            if self.pinned_servers:
                server_list.sort(key=lambda s: (0 if s[0] in self.pinned_servers else 1))

            # Show server hierarchy
            for server_data in server_list:
                server_name, server_calls, server_tokens, server_avg, tools = server_data

                if lines_used >= max_display_lines - 1:
                    truncated = True
                    break

                # Server line with pin indicator if pinned
                is_pinned = server_name in self.pinned_servers
                if is_pinned:
                    pin_emoji = ascii_emoji("📌")
                    content.append(f"  {pin_emoji} ", style=self.theme.pinned_indicator)
                    content.append(
                        f"{server_name:<15}", style=f"{self.theme.pinned_indicator} bold"
                    )
                else:
                    content.append(f"  {server_name:<18}", style=f"{self.theme.server_name} bold")
                content.append(f" {server_calls:>3} calls", style=self.theme.dim_text)

                if show_tokens:
                    tokens_str = self._format_tokens(server_tokens)
                    avg_str = self._format_tokens(server_avg)
                    content.append(f"  {tokens_str:>8}", style=self.theme.primary_text)
                    content.append(f"  (avg {avg_str}/call)", style=self.theme.dim_text)
                content.append("\n")
                lines_used += 1
                servers_shown += 1

                # Tool breakdown
                for tool_short, tool_calls, tool_tokens, pct_of_server in tools:
                    if lines_used >= max_display_lines:
                        truncated = True
                        break

                    content.append(f"    └─ {tool_short:<15}", style=self.theme.dim_text)
                    content.append(f" {tool_calls:>3} calls", style=self.theme.dim_text)

                    if show_tokens:
                        tool_tokens_str = self._format_tokens(tool_tokens)
                        content.append(f"  {tool_tokens_str:>8}", style=self.theme.dim_text)
                        content.append(
                            f"  ({pct_of_server:.0f}% of server)", style=self.theme.dim_text
                        )
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
                        style=f"{self.theme.warning} italic",
                    )
                elif remaining_tools > 0:
                    content.append(
                        f"  ... +{remaining_tools} more tool(s)\n",
                        style=f"{self.theme.warning} italic",
                    )

            # Summary line with MCP percentage of session
            total_mcp_calls = snapshot.total_tool_calls
            content.append("  ─" * 30 + "\n", style=self.theme.dim_text)
            content.append(f"  Total MCP: {total_mcp_calls} calls", style=self.theme.primary_text)
            if show_tokens and snapshot.mcp_tokens_percent > 0:
                content.append(
                    f"  ({snapshot.mcp_tokens_percent:.0f}% of session tokens)",
                    style=self.theme.dim_text,
                )
        else:
            content.append("  No MCP tools called yet", style=f"{self.theme.dim_text} italic")

        # Add estimation info for platforms that estimate MCP tokens (task-69.32)
        if snapshot.estimated_tool_calls > 0 and snapshot.estimation_method:
            content.append("\n")
            method = snapshot.estimation_method
            content.append(
                f"  MCP tokens estimated via {method}. See github.com/littlebearapps/mcp-audit",
                style=f"{self.theme.dim_text} italic",
            )

        # Title includes server count
        num_servers = len(snapshot.server_hierarchy)
        title = f"MCP Servers Usage ({num_servers} servers, {snapshot.total_tool_calls} calls)"

        return Panel(content, title=title, border_style=self.theme.mcp_border, box=self.box_style)

    def _format_tokens(self, tokens: int) -> str:
        """Format token count with K/M suffix."""
        if tokens >= 1_000_000:
            return f"{tokens / 1_000_000:.1f}M"
        elif tokens >= 1_000:
            return f"{tokens / 1_000:.0f}K"
        else:
            return str(tokens)

    def _get_cache_inefficiency_hint(self, snapshot: DisplaySnapshot) -> str:
        """Get brief explanation for cache inefficiency.

        Returns a short hint explaining why cache is costing more than saving.
        """
        created = snapshot.cache_created_tokens
        read = snapshot.cache_read_tokens

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
            content = Text("Waiting for events...", style=f"{self.theme.dim_text} italic")
        else:
            content = Text()
            for timestamp, tool_name, tokens in self.recent_events:
                local_time = timestamp.astimezone()
                time_str = local_time.strftime("%H:%M:%S")
                short_name = tool_name if len(tool_name) <= 40 else tool_name[:37] + "..."
                content.append(f"[{time_str}] ", style=self.theme.dim_text)
                content.append(f"{short_name}", style=self.theme.tool_name)
                if tokens > 0:
                    content.append(f" ({tokens:,} tokens)", style=self.theme.dim_text)
                content.append("\n")

        return Panel(
            content,
            title="Recent Activity",
            border_style=self.theme.activity_border,
            box=self.box_style,
        )

    def _build_footer(self) -> Text:
        """Build footer with instructions."""
        return Text(
            "Press Ctrl+C to stop and save session",
            style=f"{self.theme.dim_text} italic",
            justify="center",
        )

    def _format_duration(self, seconds: float) -> str:
        """Format duration as HH:MM:SS."""
        hours, remainder = divmod(int(seconds), 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def _format_duration_human(self, seconds: float) -> str:
        """Format duration in human-friendly format.

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
        """Print final summary after stopping with enhanced display."""
        version_str = f" v{snapshot.version}" if snapshot.version else ""

        # Emoji for summary display
        savings_emoji = ascii_emoji("💰")
        cost_emoji = ascii_emoji("💸")
        branch_emoji = ascii_emoji("🌿")

        # Build summary text
        summary_parts = [
            f"[bold {self.theme.success}]Session Complete![/]\n",
        ]

        # Model info
        if snapshot.model_name and snapshot.model_name != "Unknown Model":
            summary_parts.append(f"Model: {snapshot.model_name}\n")

        # Duration and rate stats
        duration_human = self._format_duration_human(snapshot.duration_seconds)
        summary_parts.append(f"Duration: {duration_human}")

        # Rate statistics
        if snapshot.duration_seconds > 0:
            msg_per_min = snapshot.message_count / (snapshot.duration_seconds / 60)
            tokens_per_min = snapshot.total_tokens / (snapshot.duration_seconds / 60)
            summary_parts.append(
                f"  ({snapshot.message_count} msgs @ {msg_per_min:.1f}/min, "
                f"{self._format_tokens(int(tokens_per_min))}/min)\n"
            )
        else:
            summary_parts.append(f"  ({snapshot.message_count} messages)\n")

        # Token breakdown with percentages
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
            # Show reasoning tokens when > 0 (Gemini thoughts / Codex reasoning)
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

        # Tool breakdown
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

        # Token estimation indicator
        if snapshot.estimated_tool_calls > 0:
            method = snapshot.estimation_method or "estimated"
            encoding = snapshot.estimation_encoding or ""
            if encoding:
                summary_parts.append(
                    f"    [{self.theme.dim_text}]({snapshot.estimated_tool_calls} calls with {method} estimation, {encoding})[/]\n"
                )
            else:
                summary_parts.append(
                    f"    [{self.theme.dim_text}]({snapshot.estimated_tool_calls} calls with {method} estimation)[/]\n"
                )

        # Built-in tools
        if snapshot.builtin_tool_calls > 0:
            summary_parts.append(
                f"  Built-in: {snapshot.builtin_tool_calls} calls "
                f"({self._format_tokens(snapshot.builtin_tool_tokens)})\n"
            )

        # Enhanced cost display
        summary_parts.append(f"\nCost w/ Cache (USD): ${snapshot.cost_estimate:.4f}\n")

        if snapshot.cost_no_cache > 0:
            summary_parts.append(f"Cost w/o Cache (USD): ${snapshot.cost_no_cache:.4f}\n")
            if snapshot.cache_savings > 0:
                summary_parts.append(
                    f"[{self.theme.success}]{savings_emoji} Cache savings: ${snapshot.cache_savings:.4f} "
                    f"({snapshot.savings_percent:.1f}% saved)[/]\n"
                )
            elif snapshot.cache_savings < 0:
                hint = self._get_cache_inefficiency_hint(snapshot)
                hint_str = f" {hint}" if hint else ""
                summary_parts.append(
                    f"[{self.theme.warning}]{cost_emoji} Net cost from caching: ${abs(snapshot.cache_savings):.4f}{hint_str}[/]\n"
                )
            else:
                summary_parts.append(f"{savings_emoji} Cache savings: $0.0000 (break even)\n")

        # Git metadata
        if snapshot.git_branch:
            git_info = f"{branch_emoji} {snapshot.git_branch}"
            if snapshot.git_commit_short:
                git_info += f"@{snapshot.git_commit_short}"
            if snapshot.git_status == "dirty":
                git_info += " (uncommitted changes)"
            summary_parts.append(f"\n{git_info}\n")

        summary_parts.append(f"\nSchema version: {SCHEMA_VERSION}")

        # Data quality disclaimer (v1.5.0 - task-103.5)
        if snapshot.accuracy_level == "estimated":
            confidence_pct = int(snapshot.data_quality_confidence * 100)
            summary_parts.append(
                f"\n[{self.theme.dim_text}]Data quality: MCP tool tokens estimated via "
                f"{snapshot.token_source} (~{confidence_pct}% accuracy)[/]"
            )

        # Session save location
        if snapshot.session_dir:
            summary_parts.append(
                f"\n\n[{self.theme.dim_text}]Session saved to: {snapshot.session_dir}[/]"
            )

        self.console.print(
            Panel(
                "".join(summary_parts),
                title=f"MCP Audit{version_str} - Session Summary",
                border_style=self.theme.summary_border,
                box=self.box_style,
            )
        )
