#!/usr/bin/env python3
"""
CodexCLIAdapter - Platform adapter for Codex CLI tracking

Implements BaseTracker for Codex CLI's output format.
"""

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from .base_tracker import BaseTracker
from .pricing_config import PricingConfig

# Human-readable model names for OpenAI models (AC #15)
MODEL_DISPLAY_NAMES: Dict[str, str] = {
    # GPT-5 Series
    "gpt-5.1": "GPT-5.1",
    "gpt-5-mini": "GPT-5 Mini",
    "gpt-5-nano": "GPT-5 Nano",
    "gpt-5-pro": "GPT-5 Pro",
    # GPT-4.1 Series
    "gpt-4.1": "GPT-4.1",
    "gpt-4.1-mini": "GPT-4.1 Mini",
    "gpt-4.1-nano": "GPT-4.1 Nano",
    # O-Series
    "o4-mini": "O4 Mini",
    "o3-mini": "O3 Mini",
    "o1-preview": "O1 Preview",
    "o1-mini": "O1 Mini",
    # GPT-4o Series
    "gpt-4o": "GPT-4o",
    "gpt-4o-mini": "GPT-4o Mini",
}

# Default exchange rate (used if not in config)
DEFAULT_USD_TO_AUD = 1.54


class CodexCLIAdapter(BaseTracker):
    """
    Codex CLI platform adapter.

    Wraps the `codex` command as a subprocess and monitors stdout/stderr
    for MCP tool usage events. Uses process wrapper approach.
    """

    def __init__(self, project: str, codex_args: list[str] | None = None):
        """
        Initialize Codex CLI adapter.

        Args:
            project: Project name (e.g., "mcp-audit")
            codex_args: Additional arguments to pass to codex command
        """
        super().__init__(project=project, platform="codex-cli")

        self.codex_args = codex_args or []
        self.detected_model: Optional[str] = None
        self.model_name: str = "Unknown Model"
        self.process: Optional[subprocess.Popen[str]] = None

        # Initialize pricing config for cost calculation (AC #1, #2)
        self._pricing_config = PricingConfig()
        self._usd_to_aud = DEFAULT_USD_TO_AUD
        if self._pricing_config.loaded:
            rates = self._pricing_config.metadata.get("exchange_rates", {})
            self._usd_to_aud = rates.get("USD_to_AUD", DEFAULT_USD_TO_AUD)

        # Source tracking (task-50)
        # Codex CLI uses process wrapper approach, not file watching.
        # Track "codex:stdout" as source when events are received.
        self._has_received_events: bool = False

    # ========================================================================
    # Abstract Method Implementations
    # ========================================================================

    def start_tracking(self) -> None:
        """
        Start tracking Codex CLI session.

        Launches codex as subprocess and monitors output.
        """
        print(f"[Codex CLI] Starting tracker for project: {self.project}")
        print(f"[Codex CLI] Launching codex with args: {self.codex_args}")

        # Launch codex as subprocess
        self.process = subprocess.Popen(
            ["codex"] + self.codex_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line buffered
            universal_newlines=True,
        )

        print("[Codex CLI] Process started. Monitoring output...")

        # Monitor output
        try:
            assert self.process.stdout is not None, "Process stdout is None"
            while True:
                # Read from stdout
                line = self.process.stdout.readline()
                if not line:
                    # Process ended - populate source_files before exit (task-50)
                    if self._has_received_events:
                        self.session.source_files = ["codex:stdout"]
                    break

                # Parse event
                result = self.parse_event(line)
                if result:
                    # Track that we received events from stdout (task-50)
                    self._has_received_events = True
                    tool_name, usage = result
                    self._process_tool_call(tool_name, usage)

        except KeyboardInterrupt:
            print("\n[Codex CLI] Stopping tracker...")
            # Populate source_files before exit (task-50)
            if self._has_received_events:
                self.session.source_files = ["codex:stdout"]
            if self.process:
                self.process.terminate()
                self.process.wait(timeout=5)

    def parse_event(self, event_data: Any) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Parse Codex CLI output event.

        Codex CLI outputs JSONL with event types:
        - turn_context: Contains model information
        - event_msg with payload.type="token_count": Token usage
        - response_item with payload.type="function_call": Tool calls (including MCP)

        Args:
            event_data: Text line from codex stdout/stderr or session JSONL

        Returns:
            Tuple of (tool_name, usage_dict) for MCP tool calls, or
            Tuple of ("__session__", usage_dict) for token usage events
        """
        try:
            # Codex CLI outputs JSON events
            line = str(event_data).strip()
            if not line:
                return None

            # Try to parse as JSON
            data = json.loads(line)
            event_type = data.get("type", "")
            payload = data.get("payload", {})

            # Handle turn_context events for model detection
            if event_type == "turn_context":
                self._parse_turn_context(payload)
                return None

            # Handle token_count events for token usage
            if event_type == "event_msg" and payload.get("type") == "token_count":
                return self._parse_token_count(payload)

            # Handle function_call events for MCP tool calls
            if event_type == "response_item" and payload.get("type") == "function_call":
                return self._parse_function_call(payload)

            return None

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self.handle_unrecognized_line(f"Parse error: {e}")
            return None

    def _parse_turn_context(self, payload: Dict[str, Any]) -> None:
        """
        Parse turn_context event for model detection.

        Args:
            payload: The event payload containing model info
        """
        if self.detected_model:
            return None

        model_id = payload.get("model")
        if model_id:
            self.detected_model = model_id
            # Map to human-readable name (AC #15)
            self.model_name = MODEL_DISPLAY_NAMES.get(model_id, model_id)
            # Set on session object for persistence
            self.session.model = model_id

        return None

    def _parse_token_count(self, payload: Dict[str, Any]) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Parse token_count event for token usage.

        Codex CLI provides both total_token_usage (cumulative) and
        last_token_usage (delta). We use last_token_usage for incremental tracking.

        Args:
            payload: The event payload with token info

        Returns:
            Tuple of ("__session__", usage_dict) with token data
        """
        info = payload.get("info")
        if not info:
            return None

        # Use last_token_usage for incremental tracking (delta from last event)
        # Fall back to total_token_usage if last not available
        usage = info.get("last_token_usage") or info.get("total_token_usage", {})

        if not usage:
            return None

        # Codex CLI token field names
        usage_dict = {
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0)
            + usage.get("reasoning_output_tokens", 0),
            "cache_created_tokens": 0,  # Codex doesn't have cache creation
            "cache_read_tokens": usage.get("cached_input_tokens", 0),
        }

        total_tokens = sum(usage_dict.values())
        if total_tokens > 0:
            return ("__session__", usage_dict)

        return None

    def _parse_function_call(self, payload: Dict[str, Any]) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Parse function_call event for MCP tool calls.

        Only returns events for MCP tools (name starts with "mcp__").

        Args:
            payload: The event payload with tool call info

        Returns:
            Tuple of (tool_name, usage_dict) for MCP tool calls
        """
        tool_name = payload.get("name", "")

        # Only track MCP tools
        if not tool_name.startswith("mcp__"):
            return None

        # Parse arguments if available
        arguments_str = payload.get("arguments", "{}")
        try:
            tool_params = json.loads(arguments_str)
        except json.JSONDecodeError:
            tool_params = {}

        # MCP tool calls don't include token usage directly
        # Tokens are tracked separately via token_count events
        usage_dict = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_created_tokens": 0,
            "cache_read_tokens": 0,
            "tool_params": tool_params,
            "call_id": payload.get("call_id"),
        }

        return (tool_name, usage_dict)

    def get_platform_metadata(self) -> Dict[str, Any]:
        """
        Get Codex CLI platform metadata.

        Returns:
            Dictionary with platform-specific data
        """
        return {
            "model": self.detected_model,
            "model_name": self.model_name,
            "codex_args": self.codex_args,
            "process_id": self.process.pid if self.process else None,
        }

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _process_tool_call(self, tool_name: str, usage: Dict[str, Any]) -> None:
        """
        Process a single tool call or session event.

        Args:
            tool_name: MCP tool name or "__session__" for non-MCP events
            usage: Token usage dictionary
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

        # Extract tool parameters for duplicate detection
        tool_params = usage.get("tool_params", {})
        content_hash = None
        if tool_params:
            content_hash = self.compute_content_hash(tool_params)

        # Get platform metadata
        platform_data = {"model": self.detected_model, "model_name": self.model_name}

        # Record tool call using BaseTracker
        # BaseTracker will normalize the tool name (strip -mcp suffix)
        self.record_tool_call(
            tool_name=tool_name,
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
            cache_created_tokens=usage["cache_created_tokens"],
            cache_read_tokens=usage["cache_read_tokens"],
            duration_ms=0,  # Codex CLI doesn't provide duration
            content_hash=content_hash,
            platform_data=platform_data,
        )


# ============================================================================
# Standalone Execution
# ============================================================================


def main() -> int:
    """Main entry point for standalone execution"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Codex CLI MCP Tracker (BaseTracker Adapter)",
        epilog="All arguments after -- are passed to codex command",
    )
    parser.add_argument("--project", default="mcp-audit", help="Project name")
    parser.add_argument(
        "--output",
        default=str(Path.home() / ".mcp-audit" / "sessions"),
        help="Output directory for session logs (default: ~/.mcp-audit/sessions)",
    )

    # Parse known args, rest go to codex
    args, codex_args = parser.parse_known_args()

    # Create adapter
    print(f"Starting Codex CLI tracker for project: {args.project}")
    print(f"Codex arguments: {codex_args}")

    adapter = CodexCLIAdapter(project=args.project, codex_args=codex_args)

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

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
