#!/usr/bin/env python3
"""
GeminiCLIAdapter - Platform adapter for Gemini CLI tracking

Implements BaseTracker using Gemini CLI's OpenTelemetry telemetry export.
Monitors ~/.gemini/telemetry.log for MCP tool usage and token counts.
"""

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .base_tracker import BaseTracker
from .pricing_config import PricingConfig

# Human-readable model names for Gemini models (AC #15)
MODEL_DISPLAY_NAMES: Dict[str, str] = {
    # Gemini 3 Series
    "gemini-3-pro-preview": "Gemini 3 Pro Preview",
    # Gemini 2.5 Series
    "gemini-2.5-pro": "Gemini 2.5 Pro",
    "gemini-2.5-pro-preview": "Gemini 2.5 Pro Preview",
    "gemini-2.5-flash": "Gemini 2.5 Flash",
    "gemini-2.5-flash-preview": "Gemini 2.5 Flash Preview",
    "gemini-2.5-flash-lite": "Gemini 2.5 Flash Lite",
    # Gemini 2.0 Series
    "gemini-2.0-flash": "Gemini 2.0 Flash",
    "gemini-2.0-flash-lite": "Gemini 2.0 Flash Lite",
}

# Default exchange rate (used if not in config)
DEFAULT_USD_TO_AUD = 1.54


class GeminiCLIAdapter(BaseTracker):
    """
    Gemini CLI platform adapter.

    Monitors OpenTelemetry telemetry file for MCP tool usage
    and token counts. Uses file watcher approach similar to
    Claude Code adapter.

    Telemetry must be enabled in Gemini CLI:
        export GEMINI_TELEMETRY_ENABLED=true
        export GEMINI_TELEMETRY_OUTFILE=~/.gemini/telemetry.log

    Or add to ~/.gemini/settings.json:
        {
          "telemetry": {
            "enabled": true,
            "target": "local",
            "outfile": ".gemini/telemetry.log"
          }
        }
    """

    # OpenTelemetry metric names from Gemini CLI
    METRIC_TOKEN_USAGE = "gemini_cli.token.usage"
    METRIC_TOOL_CALL_COUNT = "gemini_cli.tool.call.count"
    METRIC_TOOL_CALL_LATENCY = "gemini_cli.tool.call.latency"

    def __init__(
        self,
        project: str,
        gemini_dir: Optional[Path] = None,
        telemetry_file: Optional[Path] = None,
    ):
        """
        Initialize Gemini CLI adapter.

        Args:
            project: Project name (e.g., "mcp-audit")
            gemini_dir: Gemini config directory (default: ~/.gemini)
            telemetry_file: Custom telemetry file path (overrides gemini_dir default)
        """
        super().__init__(project=project, platform="gemini-cli")

        self.gemini_dir = gemini_dir or Path.home() / ".gemini"
        self.telemetry_file = telemetry_file or self._get_telemetry_file_path()
        self.file_position: int = 0

        # Gemini-specific: track thinking tokens separately
        self.thoughts_tokens: int = 0

        # Token tracking for correlation with tool calls
        self._pending_tokens: Dict[str, int] = {
            "input": 0,
            "output": 0,
            "cache": 0,
            "thought": 0,
        }

        # Latency tracking (keyed by function_name for correlation)
        self._pending_latencies: Dict[str, int] = {}

        # Model detection
        self.detected_model: Optional[str] = None
        self.model_name: str = "Unknown Model"

        # Initialize pricing config for cost calculation (AC #1, #2)
        self._pricing_config = PricingConfig()
        self._usd_to_aud = DEFAULT_USD_TO_AUD
        if self._pricing_config.loaded:
            rates = self._pricing_config.metadata.get("exchange_rates", {})
            self._usd_to_aud = rates.get("USD_to_AUD", DEFAULT_USD_TO_AUD)

        # Source file tracking (task-50)
        self._telemetry_had_events: bool = False

    def _get_telemetry_file_path(self) -> Path:
        """
        Determine telemetry file path from settings or environment.

        Priority:
        1. GEMINI_TELEMETRY_OUTFILE environment variable
        2. settings.json telemetry.outfile
        3. Default: ~/.gemini/telemetry.log
        """
        # Check environment variable first
        env_outfile = os.environ.get("GEMINI_TELEMETRY_OUTFILE")
        if env_outfile:
            return Path(env_outfile).expanduser()

        # Check settings.json
        settings_file = self.gemini_dir / "settings.json"
        if settings_file.exists():
            try:
                with open(settings_file) as f:
                    settings = json.load(f)
                    telemetry = settings.get("telemetry", {})
                    outfile = telemetry.get("outfile")
                    if outfile:
                        # Relative paths are relative to gemini_dir
                        outfile_path = Path(outfile)
                        if not outfile_path.is_absolute():
                            return self.gemini_dir / outfile_path
                        return outfile_path.expanduser()
            except (json.JSONDecodeError, OSError):
                pass

        # Default location
        return self.gemini_dir / "telemetry.log"

    def _ensure_telemetry_enabled(self) -> bool:
        """
        Check if telemetry is enabled, warn if not.

        Returns:
            True if telemetry appears to be enabled, False otherwise
        """
        # Check environment variable
        if os.environ.get("GEMINI_TELEMETRY_ENABLED", "").lower() == "true":
            return True

        # Check settings.json
        settings_file = self.gemini_dir / "settings.json"
        if settings_file.exists():
            try:
                with open(settings_file) as f:
                    settings = json.load(f)
                    telemetry = settings.get("telemetry", {})
                    if telemetry.get("enabled", False):
                        return True
            except (json.JSONDecodeError, OSError):
                pass

        # Warn user
        print("[Gemini CLI] Warning: Telemetry does not appear to be enabled")
        print("[Gemini CLI] Enable telemetry with one of these methods:")
        print()
        print("  Option 1: Environment variables")
        print("    export GEMINI_TELEMETRY_ENABLED=true")
        print("    export GEMINI_TELEMETRY_OUTFILE=~/.gemini/telemetry.log")
        print()
        print("  Option 2: Add to ~/.gemini/settings.json:")
        print(
            '    {"telemetry": {"enabled": true, "target": "local", "outfile": ".gemini/telemetry.log"}}'
        )
        print()
        return False

    # ========================================================================
    # Abstract Method Implementations
    # ========================================================================

    def start_tracking(self) -> None:
        """
        Start tracking Gemini CLI session.

        Monitors telemetry file for new OpenTelemetry metrics.
        """
        print(f"[Gemini CLI] Initializing tracker for: {self.project}")

        # Check telemetry configuration
        self._ensure_telemetry_enabled()

        print(f"[Gemini CLI] Monitoring: {self.telemetry_file}")

        # Start from end of file (track NEW content only)
        if self.telemetry_file.exists():
            self.file_position = self.telemetry_file.stat().st_size

        print("[Gemini CLI] Tracking started. Press Ctrl+C to stop.")

        # Main monitoring loop
        while True:
            try:
                self._process_new_telemetry()
                time.sleep(0.5)
            except KeyboardInterrupt:
                print("\n[Gemini CLI] Stopping tracker...")
                # Populate source_files before exit (task-50)
                if self._telemetry_had_events:
                    self.session.source_files = [self.telemetry_file.name]
                break

    def parse_event(self, event_data: Any) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Parse OpenTelemetry metric event.

        Args:
            event_data: JSON line from telemetry file

        Returns:
            Tuple of (tool_name, usage_dict) for MCP tool calls, or
            Tuple of ("__session__", usage_dict) for token usage events
        """
        try:
            data = json.loads(event_data)

            # Get metric name - handle different OTEL JSON formats
            metric_name = data.get("name") or data.get("metric_name", "")

            # Handle tool call count metric (primary MCP tracking)
            if self.METRIC_TOOL_CALL_COUNT in metric_name:
                return self._parse_tool_call_count(data)

            # Handle token usage metric (aggregate tracking)
            # Return session-level tokens to track all usage, not just MCP calls
            if self.METRIC_TOKEN_USAGE in metric_name:
                return self._parse_token_usage(data)

            # Handle tool latency metric (duration tracking)
            if self.METRIC_TOOL_CALL_LATENCY in metric_name:
                self._parse_tool_latency(data)
                return None

            return None

        except (json.JSONDecodeError, KeyError) as e:
            self.handle_unrecognized_line(f"Parse error: {e}")
            return None

    def get_platform_metadata(self) -> Dict[str, Any]:
        """Get Gemini CLI platform metadata."""
        return {
            "model": self.detected_model,
            "model_name": self.model_name,
            "gemini_dir": str(self.gemini_dir),
            "telemetry_file": str(self.telemetry_file),
            "thoughts_tokens": self.thoughts_tokens,
        }

    # ========================================================================
    # Telemetry Parsing Helpers
    # ========================================================================

    def _parse_tool_call_count(self, data: Dict[str, Any]) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Parse gemini_cli.tool.call.count metric.

        Only returns MCP tool calls (tool_type="mcp").
        """
        attributes = data.get("attributes", {})

        # Only track MCP tools (filter out native tools)
        tool_type = attributes.get("tool_type", "")
        if tool_type != "mcp":
            return None

        function_name = attributes.get("function_name", "")
        if not function_name.startswith("mcp__"):
            return None

        # Get pending tokens (from recent token.usage events)
        # Note: Token attribution is approximate based on timing
        usage_dict = {
            "input_tokens": self._pending_tokens.get("input", 0),
            "output_tokens": self._pending_tokens.get("output", 0),
            "cache_created_tokens": 0,  # Gemini uses different cache naming
            "cache_read_tokens": self._pending_tokens.get("cache", 0),
            "duration_ms": self._pending_latencies.pop(function_name, 0),
            "success": attributes.get("success", True),
            "decision": attributes.get("decision", "auto_accept"),
        }

        # Reset pending tokens after attribution
        self._pending_tokens = {"input": 0, "output": 0, "cache": 0, "thought": 0}

        return (function_name, usage_dict)

    def _parse_token_usage(self, data: Dict[str, Any]) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Parse gemini_cli.token.usage metric.

        Accumulates tokens by type for attribution to tool calls,
        and returns session-level token data for total tracking.

        Returns:
            Tuple of ("__session__", usage_dict) with token data
        """
        attributes = data.get("attributes", {})
        value = data.get("value", 0)

        token_type = attributes.get("type", "")

        # Build usage dict for this token event
        usage_dict = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_created_tokens": 0,
            "cache_read_tokens": 0,
        }

        if token_type == "input":
            self._pending_tokens["input"] += value
            usage_dict["input_tokens"] = value
        elif token_type == "output":
            self._pending_tokens["output"] += value
            usage_dict["output_tokens"] = value
        elif token_type == "thought":
            self._pending_tokens["thought"] += value
            self.thoughts_tokens += value  # Track cumulative for session
            # Count thought tokens as output for session totals
            usage_dict["output_tokens"] = value
        elif token_type == "cache":
            self._pending_tokens["cache"] += value
            usage_dict["cache_read_tokens"] = value

        # Model detection (AC #5)
        model = attributes.get("model")
        if model and not self.detected_model:
            self.detected_model = model
            # Map to human-readable name (AC #15)
            self.model_name = MODEL_DISPLAY_NAMES.get(model, model)
            # Set on session object for persistence
            self.session.model = model

        # Return session-level token data
        if value > 0:
            return ("__session__", usage_dict)
        return None

    def _parse_tool_latency(self, data: Dict[str, Any]) -> None:
        """
        Parse gemini_cli.tool.call.latency metric.

        Stores latency for correlation with tool calls.
        """
        attributes = data.get("attributes", {})
        value = data.get("value", 0)

        function_name = attributes.get("function_name", "")
        if function_name:
            self._pending_latencies[function_name] = int(value)

    # ========================================================================
    # File Monitoring
    # ========================================================================

    def _process_new_telemetry(self) -> None:
        """Read and process new telemetry entries."""
        if not self.telemetry_file.exists():
            return

        try:
            with open(self.telemetry_file) as f:
                f.seek(self.file_position)
                new_content = f.read()

                if new_content:
                    for line in new_content.strip().split("\n"):
                        if line.strip():
                            result = self.parse_event(line)
                            if result:
                                # Track that telemetry had events (task-50)
                                self._telemetry_had_events = True
                                tool_name, usage = result
                                self._process_tool_call(tool_name, usage)

                self.file_position = f.tell()
        except OSError as e:
            self.handle_unrecognized_line(f"Error reading telemetry: {e}")

    def _process_tool_call(self, tool_name: str, usage: Dict[str, Any]) -> None:
        """
        Process a single tool call or session event.

        Args:
            tool_name: MCP tool name or "__session__" for token usage events
            usage: Token usage and metadata dictionary
        """
        total_tokens = (
            usage["input_tokens"]
            + usage["output_tokens"]
            + usage["cache_created_tokens"]
            + usage["cache_read_tokens"]
        )

        # Handle session-level token tracking (non-MCP events)
        if tool_name == "__session__":
            # Update session token usage directly (don't record as tool call)
            self.session.token_usage.input_tokens += usage["input_tokens"]
            self.session.token_usage.output_tokens += usage["output_tokens"]
            self.session.token_usage.cache_created_tokens += usage["cache_created_tokens"]
            self.session.token_usage.cache_read_tokens += usage["cache_read_tokens"]
            self.session.token_usage.total_tokens += total_tokens

            # Recalculate cache efficiency: percentage of INPUT tokens served from cache
            total_input = (
                self.session.token_usage.input_tokens
                + self.session.token_usage.cache_created_tokens
                + self.session.token_usage.cache_read_tokens
            )
            if total_input > 0:
                self.session.token_usage.cache_efficiency = (
                    self.session.token_usage.cache_read_tokens / total_input
                )
            return

        # Extract tool parameters for duplicate detection (if available)
        content_hash = None

        # Get platform metadata
        platform_data = {
            "model": self.detected_model,
            "success": usage.get("success", True),
            "decision": usage.get("decision"),
            "thoughts_tokens": self._pending_tokens.get("thought", 0),
        }

        # Record tool call using BaseTracker
        self.record_tool_call(
            tool_name=tool_name,
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
            cache_created_tokens=usage["cache_created_tokens"],
            cache_read_tokens=usage["cache_read_tokens"],
            duration_ms=usage.get("duration_ms", 0),
            content_hash=content_hash,
            platform_data=platform_data,
        )


# ============================================================================
# Standalone Execution
# ============================================================================


def main() -> int:
    """Main entry point for standalone execution"""
    import argparse

    parser = argparse.ArgumentParser(description="Gemini CLI MCP Tracker (BaseTracker Adapter)")
    parser.add_argument("--project", default="mcp-audit", help="Project name")
    parser.add_argument(
        "--gemini-dir",
        type=Path,
        default=None,
        help="Gemini config directory (default: ~/.gemini)",
    )
    parser.add_argument(
        "--telemetry-file",
        type=Path,
        default=None,
        help="Telemetry file path (overrides gemini-dir default)",
    )
    parser.add_argument(
        "--output",
        default=str(Path.home() / ".mcp-audit" / "sessions"),
        help="Output directory for session logs (default: ~/.mcp-audit/sessions)",
    )
    args = parser.parse_args()

    # Create adapter
    print(f"Starting Gemini CLI tracker for project: {args.project}")
    adapter = GeminiCLIAdapter(
        project=args.project,
        gemini_dir=args.gemini_dir,
        telemetry_file=args.telemetry_file,
    )

    try:
        # Start tracking
        adapter.start_tracking()
    except KeyboardInterrupt:
        print("\nStopping tracker...")
    finally:
        # Finalize session
        session = adapter.finalize_session()

        # Save session data
        output_dir = Path(args.output)
        adapter.save_session(output_dir)

        print(f"\nSession saved to: {adapter.session_dir}")
        print(f"Total tokens: {session.token_usage.total_tokens:,}")
        print(f"MCP calls: {session.mcp_tool_calls.total_calls}")
        print(f"Cache efficiency: {session.token_usage.cache_efficiency:.1%}")
        print(f"Thinking tokens: {adapter.thoughts_tokens:,}")

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
