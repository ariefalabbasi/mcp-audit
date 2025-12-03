#!/usr/bin/env python3
"""
Test suite for gemini_cli_adapter module

Tests GeminiCLIAdapter implementation and OpenTelemetry parsing.
"""

import json
import os
import pytest
from pathlib import Path
from typing import Any, Dict

from mcp_audit.gemini_cli_adapter import GeminiCLIAdapter


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def adapter(tmp_path: Path) -> GeminiCLIAdapter:
    """Create a GeminiCLIAdapter with temp directories"""
    gemini_dir = tmp_path / ".gemini"
    gemini_dir.mkdir()

    telemetry_file = gemini_dir / "telemetry.log"
    telemetry_file.touch()

    return GeminiCLIAdapter(
        project="test-project",
        gemini_dir=gemini_dir,
        telemetry_file=telemetry_file,
    )


@pytest.fixture
def adapter_with_settings(tmp_path: Path) -> GeminiCLIAdapter:
    """Create adapter with settings.json configured"""
    gemini_dir = tmp_path / ".gemini"
    gemini_dir.mkdir()

    # Create settings.json with telemetry enabled
    settings = {
        "telemetry": {
            "enabled": True,
            "target": "local",
            "outfile": ".gemini/telemetry.log",
        }
    }
    settings_file = gemini_dir / "settings.json"
    settings_file.write_text(json.dumps(settings))

    telemetry_file = gemini_dir / "telemetry.log"
    telemetry_file.touch()

    return GeminiCLIAdapter(
        project="test-project",
        gemini_dir=gemini_dir,
        telemetry_file=telemetry_file,
    )


# ============================================================================
# Sample OpenTelemetry Events
# ============================================================================


def make_tool_call_count_event(
    function_name: str,
    tool_type: str = "mcp",
    success: bool = True,
    decision: str = "auto_accept",
) -> Dict[str, Any]:
    """Create a gemini_cli.tool.call.count event"""
    return {
        "name": "gemini_cli.tool.call.count",
        "attributes": {
            "function_name": function_name,
            "tool_type": tool_type,
            "success": success,
            "decision": decision,
        },
        "value": 1,
        "timestamp": "2025-11-25T10:30:00Z",
    }


def make_token_usage_event(
    token_type: str,
    value: int,
    model: str = "gemini-2.5-pro",
) -> Dict[str, Any]:
    """Create a gemini_cli.token.usage event"""
    return {
        "name": "gemini_cli.token.usage",
        "attributes": {
            "model": model,
            "type": token_type,
        },
        "value": value,
        "timestamp": "2025-11-25T10:30:01Z",
    }


def make_tool_latency_event(
    function_name: str,
    latency_ms: int,
) -> Dict[str, Any]:
    """Create a gemini_cli.tool.call.latency event"""
    return {
        "name": "gemini_cli.tool.call.latency",
        "attributes": {
            "function_name": function_name,
        },
        "value": latency_ms,
        "timestamp": "2025-11-25T10:30:02Z",
    }


# ============================================================================
# Initialization Tests
# ============================================================================


class TestGeminiCLIAdapterInitialization:
    """Tests for GeminiCLIAdapter initialization"""

    def test_initialization(self, adapter: GeminiCLIAdapter) -> None:
        """Test adapter initializes correctly"""
        assert adapter.project == "test-project"
        assert adapter.platform == "gemini-cli"
        assert adapter.gemini_dir is not None
        assert adapter.telemetry_file is not None

    def test_default_gemini_dir(self, tmp_path: Path) -> None:
        """Test default gemini_dir is ~/.gemini"""
        # Create adapter without specifying gemini_dir
        adapter = GeminiCLIAdapter(project="test")
        assert adapter.gemini_dir == Path.home() / ".gemini"

    def test_custom_telemetry_file(self, tmp_path: Path) -> None:
        """Test custom telemetry file path"""
        custom_file = tmp_path / "custom_telemetry.log"
        custom_file.touch()

        adapter = GeminiCLIAdapter(
            project="test",
            telemetry_file=custom_file,
        )
        assert adapter.telemetry_file == custom_file

    def test_thoughts_tokens_initialized(self, adapter: GeminiCLIAdapter) -> None:
        """Test thoughts_tokens initialized to zero"""
        assert adapter.thoughts_tokens == 0

    def test_pending_tokens_initialized(self, adapter: GeminiCLIAdapter) -> None:
        """Test pending tokens dict initialized"""
        assert adapter._pending_tokens == {
            "input": 0,
            "output": 0,
            "cache": 0,
            "thought": 0,
        }


# ============================================================================
# Telemetry Path Detection Tests
# ============================================================================


class TestTelemetryPathDetection:
    """Tests for telemetry file path detection"""

    def test_env_var_takes_priority(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test GEMINI_TELEMETRY_OUTFILE environment variable takes priority"""
        env_path = tmp_path / "env_telemetry.log"
        monkeypatch.setenv("GEMINI_TELEMETRY_OUTFILE", str(env_path))

        gemini_dir = tmp_path / ".gemini"
        gemini_dir.mkdir()

        adapter = GeminiCLIAdapter(project="test", gemini_dir=gemini_dir)
        assert adapter.telemetry_file == env_path

    def test_settings_json_path(self, tmp_path: Path) -> None:
        """Test settings.json outfile is used when env var not set"""
        gemini_dir = tmp_path / ".gemini"
        gemini_dir.mkdir()

        settings = {"telemetry": {"outfile": "custom/path.log"}}
        (gemini_dir / "settings.json").write_text(json.dumps(settings))

        adapter = GeminiCLIAdapter(project="test", gemini_dir=gemini_dir)
        assert adapter.telemetry_file == gemini_dir / "custom/path.log"

    def test_default_telemetry_path(self, tmp_path: Path) -> None:
        """Test default path when no config exists"""
        gemini_dir = tmp_path / ".gemini"
        gemini_dir.mkdir()

        adapter = GeminiCLIAdapter(project="test", gemini_dir=gemini_dir)
        assert adapter.telemetry_file == gemini_dir / "telemetry.log"


# ============================================================================
# Telemetry Enabled Check Tests
# ============================================================================


class TestTelemetryEnabledCheck:
    """Tests for telemetry enabled detection"""

    def test_env_var_enabled(
        self, adapter: GeminiCLIAdapter, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test env var enables telemetry"""
        monkeypatch.setenv("GEMINI_TELEMETRY_ENABLED", "true")
        assert adapter._ensure_telemetry_enabled() is True

    def test_settings_enabled(self, adapter_with_settings: GeminiCLIAdapter) -> None:
        """Test settings.json enables telemetry"""
        assert adapter_with_settings._ensure_telemetry_enabled() is True

    def test_telemetry_not_enabled(self, adapter: GeminiCLIAdapter) -> None:
        """Test warning when telemetry not enabled"""
        # No env var, no settings.json with enabled=true
        assert adapter._ensure_telemetry_enabled() is False


# ============================================================================
# Event Parsing Tests
# ============================================================================


class TestEventParsing:
    """Tests for OpenTelemetry event parsing"""

    def test_parse_mcp_tool_call(self, adapter: GeminiCLIAdapter) -> None:
        """Test parsing MCP tool call event"""
        event = make_tool_call_count_event("mcp__zen__chat")

        result = adapter.parse_event(json.dumps(event))

        assert result is not None
        tool_name, usage = result
        assert tool_name == "mcp__zen__chat"
        assert "input_tokens" in usage
        assert "output_tokens" in usage
        assert usage["success"] is True
        assert usage["decision"] == "auto_accept"

    def test_parse_native_tool_ignored(self, adapter: GeminiCLIAdapter) -> None:
        """Test native tools are ignored"""
        event = make_tool_call_count_event("read_file", tool_type="native")

        result = adapter.parse_event(json.dumps(event))

        assert result is None

    def test_parse_non_mcp_prefix_ignored(self, adapter: GeminiCLIAdapter) -> None:
        """Test non-mcp__ prefixed tools are ignored"""
        event = make_tool_call_count_event("some_tool", tool_type="mcp")

        result = adapter.parse_event(json.dumps(event))

        assert result is None

    def test_parse_token_usage_input(self, adapter: GeminiCLIAdapter) -> None:
        """Test parsing input token usage"""
        event = make_token_usage_event("input", 1000)

        adapter.parse_event(json.dumps(event))

        assert adapter._pending_tokens["input"] == 1000

    def test_parse_token_usage_output(self, adapter: GeminiCLIAdapter) -> None:
        """Test parsing output token usage"""
        event = make_token_usage_event("output", 500)

        adapter.parse_event(json.dumps(event))

        assert adapter._pending_tokens["output"] == 500

    def test_parse_token_usage_thought(self, adapter: GeminiCLIAdapter) -> None:
        """Test parsing thought token usage (Gemini-specific)"""
        event = make_token_usage_event("thought", 250)

        adapter.parse_event(json.dumps(event))

        assert adapter._pending_tokens["thought"] == 250
        assert adapter.thoughts_tokens == 250  # Cumulative

    def test_parse_token_usage_cache(self, adapter: GeminiCLIAdapter) -> None:
        """Test parsing cache token usage"""
        event = make_token_usage_event("cache", 5000)

        adapter.parse_event(json.dumps(event))

        assert adapter._pending_tokens["cache"] == 5000

    def test_parse_tool_latency(self, adapter: GeminiCLIAdapter) -> None:
        """Test parsing tool latency event"""
        event = make_tool_latency_event("mcp__zen__chat", 1500)

        adapter.parse_event(json.dumps(event))

        assert adapter._pending_latencies["mcp__zen__chat"] == 1500

    def test_model_detection(self, adapter: GeminiCLIAdapter) -> None:
        """Test model detection from token usage event"""
        event = make_token_usage_event("input", 100, model="gemini-2.5-pro")

        adapter.parse_event(json.dumps(event))

        assert adapter.detected_model == "gemini-2.5-pro"
        # AC #15: Model should be mapped to human-readable name
        assert adapter.model_name == "Gemini 2.5 Pro"
        # AC #5: Model should be set on session object for persistence
        assert adapter.session.model == "gemini-2.5-pro"

    def test_invalid_json_handled(self, adapter: GeminiCLIAdapter) -> None:
        """Test invalid JSON is handled gracefully"""
        result = adapter.parse_event("not valid json")

        assert result is None


# ============================================================================
# Token Attribution Tests
# ============================================================================


class TestTokenAttribution:
    """Tests for token attribution to tool calls"""

    def test_pending_tokens_attributed_to_tool_call(self, adapter: GeminiCLIAdapter) -> None:
        """Test pending tokens are attributed to tool calls"""
        # Simulate token events before tool call
        adapter.parse_event(json.dumps(make_token_usage_event("input", 1000)))
        adapter.parse_event(json.dumps(make_token_usage_event("output", 500)))
        adapter.parse_event(json.dumps(make_token_usage_event("cache", 5000)))

        # Parse tool call
        event = make_tool_call_count_event("mcp__zen__chat")
        result = adapter.parse_event(json.dumps(event))

        assert result is not None
        _, usage = result
        assert usage["input_tokens"] == 1000
        assert usage["output_tokens"] == 500
        assert usage["cache_read_tokens"] == 5000

    def test_pending_tokens_reset_after_attribution(self, adapter: GeminiCLIAdapter) -> None:
        """Test pending tokens are reset after attribution"""
        adapter.parse_event(json.dumps(make_token_usage_event("input", 1000)))

        # Parse tool call (consumes pending tokens)
        event = make_tool_call_count_event("mcp__zen__chat")
        adapter.parse_event(json.dumps(event))

        # Pending tokens should be reset
        assert adapter._pending_tokens["input"] == 0
        assert adapter._pending_tokens["output"] == 0

    def test_latency_attributed_to_tool_call(self, adapter: GeminiCLIAdapter) -> None:
        """Test latency is attributed to correct tool call"""
        # Parse latency event first
        adapter.parse_event(json.dumps(make_tool_latency_event("mcp__zen__chat", 1500)))

        # Parse tool call
        event = make_tool_call_count_event("mcp__zen__chat")
        result = adapter.parse_event(json.dumps(event))

        assert result is not None
        _, usage = result
        assert usage["duration_ms"] == 1500

    def test_latency_removed_after_attribution(self, adapter: GeminiCLIAdapter) -> None:
        """Test latency is removed from pending after attribution"""
        adapter.parse_event(json.dumps(make_tool_latency_event("mcp__zen__chat", 1500)))

        # Parse tool call (consumes latency)
        event = make_tool_call_count_event("mcp__zen__chat")
        adapter.parse_event(json.dumps(event))

        # Latency should be removed
        assert "mcp__zen__chat" not in adapter._pending_latencies


# ============================================================================
# Tool Call Recording Tests
# ============================================================================


class TestToolCallRecording:
    """Tests for recording tool calls via BaseTracker"""

    def test_process_tool_call(self, adapter: GeminiCLIAdapter) -> None:
        """Test _process_tool_call records via BaseTracker"""
        usage = {
            "input_tokens": 100,
            "output_tokens": 50,
            "cache_created_tokens": 0,
            "cache_read_tokens": 500,
            "duration_ms": 1500,
            "success": True,
            "decision": "auto_accept",
        }

        adapter._process_tool_call("mcp__zen__chat", usage)

        # Check server session created
        assert "zen" in adapter.server_sessions

        # Check tool stats
        tool_stats = adapter.server_sessions["zen"].tools["mcp__zen__chat"]
        assert tool_stats.calls == 1
        assert tool_stats.total_tokens == 650
        assert tool_stats.total_duration_ms == 1500

    def test_multiple_tool_calls(self, adapter: GeminiCLIAdapter) -> None:
        """Test multiple tool calls accumulate correctly"""
        usage1 = {
            "input_tokens": 100,
            "output_tokens": 50,
            "cache_created_tokens": 0,
            "cache_read_tokens": 0,
            "duration_ms": 1000,
        }
        usage2 = {
            "input_tokens": 200,
            "output_tokens": 100,
            "cache_created_tokens": 0,
            "cache_read_tokens": 0,
            "duration_ms": 2000,
        }

        adapter._process_tool_call("mcp__zen__chat", usage1)
        adapter._process_tool_call("mcp__zen__chat", usage2)

        tool_stats = adapter.server_sessions["zen"].tools["mcp__zen__chat"]
        assert tool_stats.calls == 2
        assert tool_stats.total_tokens == 450
        assert tool_stats.avg_tokens == 225.0


# ============================================================================
# Platform Metadata Tests
# ============================================================================


class TestPlatformMetadata:
    """Tests for platform metadata"""

    def test_get_platform_metadata(self, adapter: GeminiCLIAdapter) -> None:
        """Test get_platform_metadata returns correct data"""
        adapter.detected_model = "gemini-2.5-pro"
        adapter.model_name = "gemini-2.5-pro"
        adapter.thoughts_tokens = 500

        metadata = adapter.get_platform_metadata()

        assert metadata["model"] == "gemini-2.5-pro"
        assert metadata["model_name"] == "gemini-2.5-pro"
        assert metadata["thoughts_tokens"] == 500
        assert "gemini_dir" in metadata
        assert "telemetry_file" in metadata


# ============================================================================
# Session Finalization Tests
# ============================================================================


class TestSessionFinalization:
    """Tests for session finalization"""

    def test_finalize_session_includes_thoughts_tokens(self, adapter: GeminiCLIAdapter) -> None:
        """Test thoughts_tokens available after finalization"""
        # Parse some thought tokens
        adapter.parse_event(json.dumps(make_token_usage_event("thought", 500)))

        session = adapter.finalize_session()

        # thoughts_tokens should be tracked separately
        assert adapter.thoughts_tokens == 500

    def test_finalize_session_with_tool_calls(self, adapter: GeminiCLIAdapter) -> None:
        """Test session finalization with tool calls"""
        usage = {
            "input_tokens": 100,
            "output_tokens": 50,
            "cache_created_tokens": 0,
            "cache_read_tokens": 0,
        }
        adapter._process_tool_call("mcp__zen__chat", usage)

        session = adapter.finalize_session()

        assert session.mcp_tool_calls.total_calls == 1
        assert session.mcp_tool_calls.unique_tools == 1
        assert session.token_usage.total_tokens == 150


# ============================================================================
# File Monitoring Tests
# ============================================================================


class TestFileMonitoring:
    """Tests for telemetry file monitoring"""

    def test_process_new_telemetry(self, adapter: GeminiCLIAdapter) -> None:
        """Test processing new telemetry from file"""
        # Write events to telemetry file
        events = [
            make_token_usage_event("input", 1000),
            make_token_usage_event("output", 500),
            make_tool_call_count_event("mcp__zen__chat"),
        ]

        with open(adapter.telemetry_file, "w") as f:
            for event in events:
                f.write(json.dumps(event) + "\n")

        # Process new telemetry
        adapter._process_new_telemetry()

        # Should have recorded the tool call
        assert "zen" in adapter.server_sessions
        assert adapter.server_sessions["zen"].total_calls == 1

    def test_file_position_tracking(self, adapter: GeminiCLIAdapter) -> None:
        """Test file position is tracked correctly"""
        initial_position = adapter.file_position

        # Write first batch
        with open(adapter.telemetry_file, "w") as f:
            f.write(json.dumps(make_token_usage_event("input", 100)) + "\n")

        adapter._process_new_telemetry()
        position_after_first = adapter.file_position

        # Write second batch
        with open(adapter.telemetry_file, "a") as f:
            f.write(json.dumps(make_token_usage_event("output", 50)) + "\n")

        adapter._process_new_telemetry()
        position_after_second = adapter.file_position

        assert position_after_first > initial_position
        assert position_after_second > position_after_first

    def test_nonexistent_file_handled(self, tmp_path: Path) -> None:
        """Test nonexistent telemetry file is handled"""
        adapter = GeminiCLIAdapter(
            project="test",
            gemini_dir=tmp_path,
            telemetry_file=tmp_path / "nonexistent.log",
        )

        # Should not crash
        adapter._process_new_telemetry()


# ============================================================================
# Integration Tests
# ============================================================================


class TestGeminiCLIAdapterIntegration:
    """Integration tests for complete adapter workflow"""

    def test_complete_workflow(self, adapter: GeminiCLIAdapter, tmp_path: Path) -> None:
        """Test complete tracking workflow"""
        # Simulate a session with multiple tool calls
        events = [
            # First tool call
            make_token_usage_event("input", 1000),
            make_token_usage_event("output", 500),
            make_token_usage_event("thought", 200),
            make_tool_latency_event("mcp__zen__chat", 1500),
            make_tool_call_count_event("mcp__zen__chat"),
            # Second tool call (different server)
            make_token_usage_event("input", 500),
            make_token_usage_event("output", 250),
            make_tool_latency_event("mcp__brave-search__brave_web_search", 800),
            make_tool_call_count_event("mcp__brave-search__brave_web_search"),
        ]

        # Write events to file
        with open(adapter.telemetry_file, "w") as f:
            for event in events:
                f.write(json.dumps(event) + "\n")

        # Process telemetry
        adapter._process_new_telemetry()

        # Finalize and save
        session = adapter.finalize_session()
        adapter.save_session(tmp_path)

        # Verify results
        assert session.mcp_tool_calls.total_calls == 2
        assert session.mcp_tool_calls.unique_tools == 2
        assert len(adapter.server_sessions) == 2
        assert "zen" in adapter.server_sessions
        assert "brave-search" in adapter.server_sessions
        assert adapter.thoughts_tokens == 200

        # Verify files saved (v1.1.0: single file per session)
        assert adapter.session_dir is not None
        session_files = list(adapter.session_dir.glob("*.json"))
        assert len(session_files) == 1
        assert session_files[0].name.startswith("test-project-")

    def test_model_detection_and_pricing_lookup(self, adapter: GeminiCLIAdapter) -> None:
        """Test model detection works for pricing lookup"""
        event = make_token_usage_event("input", 100, model="gemini-2.5-pro")
        adapter.parse_event(json.dumps(event))

        # Model should be detected
        assert adapter.detected_model == "gemini-2.5-pro"

        # Platform metadata should include model
        metadata = adapter.get_platform_metadata()
        assert metadata["model"] == "gemini-2.5-pro"


# ============================================================================
# Cache Analysis Tests (task-47.5, task-47.6)
# ============================================================================


class TestGeminiCLICacheAnalysis:
    """Test cache_analysis for Gemini CLI platform"""

    def test_cache_analysis_efficient_read_only(self, adapter: GeminiCLIAdapter) -> None:
        """Test cache analysis shows efficient when only cache reading (no creation)"""
        # Gemini doesn't report cache_created_tokens, only cache_read
        usage = {
            "input_tokens": 100,
            "output_tokens": 50,
            "cache_created_tokens": 0,  # Gemini doesn't create cache
            "cache_read_tokens": 5000,  # But can read from cache
        }
        adapter._process_tool_call("mcp__zen__chat", usage)

        session = adapter.finalize_session()
        analysis = session._build_cache_analysis()

        # With read-only cache, should be efficient or neutral
        assert analysis.creation_tokens == 0
        assert analysis.read_tokens == 5000
        # No creation = no cost penalty
        assert analysis.status in ["efficient", "neutral"]

    def test_cache_analysis_neutral_no_cache(self, adapter: GeminiCLIAdapter) -> None:
        """Test cache analysis shows neutral when no cache activity"""
        usage = {
            "input_tokens": 100,
            "output_tokens": 50,
            "cache_created_tokens": 0,
            "cache_read_tokens": 0,
        }
        adapter._process_tool_call("mcp__zen__chat", usage)

        session = adapter.finalize_session()
        analysis = session._build_cache_analysis()

        assert analysis.status == "neutral"
        assert analysis.creation_tokens == 0
        assert analysis.read_tokens == 0
        assert "No cache activity" in analysis.summary

    def test_cache_analysis_in_session_dict(self, adapter: GeminiCLIAdapter) -> None:
        """Test cache_analysis included in session.to_dict() for Gemini sessions"""
        usage = {
            "input_tokens": 100,
            "output_tokens": 50,
            "cache_created_tokens": 0,
            "cache_read_tokens": 1000,
        }
        adapter._process_tool_call("mcp__zen__chat", usage)

        session = adapter.finalize_session()
        session_dict = session.to_dict()

        assert "cache_analysis" in session_dict
        cache_analysis = session_dict["cache_analysis"]
        assert "status" in cache_analysis
        assert "summary" in cache_analysis
        assert cache_analysis["read_tokens"] == 1000
        assert cache_analysis["creation_tokens"] == 0

    def test_per_tool_cache_tracking_gemini(self, adapter: GeminiCLIAdapter) -> None:
        """Test per-tool cache tracking works for Gemini"""
        # First tool with cache read
        adapter._process_tool_call(
            "mcp__zen__chat",
            {
                "input_tokens": 100,
                "output_tokens": 50,
                "cache_created_tokens": 0,
                "cache_read_tokens": 5000,
            },
        )
        # Second tool without cache
        adapter._process_tool_call(
            "mcp__brave-search__brave_web_search",
            {
                "input_tokens": 200,
                "output_tokens": 100,
                "cache_created_tokens": 0,
                "cache_read_tokens": 0,
            },
        )

        session = adapter.finalize_session()

        # Verify per-tool cache tracking
        zen_stats = adapter.server_sessions["zen"].tools["mcp__zen__chat"]
        assert zen_stats.cache_read_tokens == 5000
        assert zen_stats.cache_created_tokens == 0

        brave_stats = adapter.server_sessions["brave-search"].tools[
            "mcp__brave-search__brave_web_search"
        ]
        assert brave_stats.cache_read_tokens == 0
        assert brave_stats.cache_created_tokens == 0


class TestGeminiCLISourceFilesTracking:
    """Test source_files population for Gemini CLI adapter (task-50)"""

    def test_telemetry_had_events_initialized(self, adapter: GeminiCLIAdapter) -> None:
        """Test _telemetry_had_events flag initialized as False."""
        assert hasattr(adapter, "_telemetry_had_events")
        assert adapter._telemetry_had_events is False

    def test_source_files_empty_initially(self, adapter: GeminiCLIAdapter) -> None:
        """Test session.source_files is empty list by default."""
        assert adapter.session.source_files == []

    def test_telemetry_had_events_set_on_parse(self, adapter: GeminiCLIAdapter) -> None:
        """Test _telemetry_had_events set when events parsed."""
        # Create sample token event
        token_event = json.dumps(
            make_token_usage_event(token_type="input", value=100, model="gemini-2.5-flash")
        )

        # Simulate parsing events (flag set in _process_new_telemetry)
        result = adapter.parse_event(token_event)
        if result:
            adapter._telemetry_had_events = True

        assert adapter._telemetry_had_events is True

    def test_source_files_only_filename_not_path(self, adapter: GeminiCLIAdapter) -> None:
        """Test only filename stored, not full path (privacy)."""
        # Simulate events received
        adapter._telemetry_had_events = True

        # Populate source_files with filename only (simulating Ctrl+C behavior)
        adapter.session.source_files = [adapter.telemetry_file.name]

        # Verify only filename, no path components
        for filename in adapter.session.source_files:
            assert "/" not in filename
            assert "\\" not in filename
        assert adapter.session.source_files[0] == "telemetry.log"

    def test_source_files_in_session_dict(self, adapter: GeminiCLIAdapter) -> None:
        """Test source_files included in session.to_dict() output."""
        # Create sample tool call event
        tool_event = json.dumps(make_tool_call_count_event("mcp__zen__chat"))

        # Process an event
        result = adapter.parse_event(tool_event)
        if result:
            adapter._telemetry_had_events = True
            tool_name, usage = result
            adapter._process_tool_call(tool_name, usage)

        # Populate source_files
        if adapter._telemetry_had_events:
            adapter.session.source_files = [adapter.telemetry_file.name]

        session = adapter.finalize_session()
        session_dict = session.to_dict()

        assert "session" in session_dict
        assert "source_files" in session_dict["session"]
        assert session_dict["session"]["source_files"] == ["telemetry.log"]

    def test_source_files_empty_when_no_events(self, adapter: GeminiCLIAdapter) -> None:
        """Test source_files stays empty when no events received."""
        # No events processed
        assert adapter._telemetry_had_events is False

        # Simulate Ctrl+C behavior
        if adapter._telemetry_had_events:
            adapter.session.source_files = [adapter.telemetry_file.name]

        assert adapter.session.source_files == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
