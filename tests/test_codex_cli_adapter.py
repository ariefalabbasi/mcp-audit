#!/usr/bin/env python3
"""
Integration tests for Codex CLI adapter.

Tests the CodexCLIAdapter's ability to:
1. Parse JSONL events in the correct format
2. Detect model from turn_context events
3. Track tokens from token_count events
4. Handle MCP tool call events (response_item with function_call)
5. Normalize tool names (strip -mcp suffix)
"""

import json
from typing import Any, Dict, List

import pytest

from mcp_audit.codex_cli_adapter import CodexCLIAdapter, MODEL_DISPLAY_NAMES


@pytest.fixture
def sample_turn_context_event() -> Dict[str, Any]:
    """Sample turn_context event for model detection."""
    return {
        "timestamp": "2025-11-04T11:38:27.361Z",
        "type": "turn_context",
        "payload": {
            "cwd": "/test/project",
            "model": "gpt-5.1",
        },
    }


@pytest.fixture
def sample_token_count_event() -> Dict[str, Any]:
    """Sample token_count event for token tracking."""
    return {
        "timestamp": "2025-11-04T11:38:30.056Z",
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "info": {
                "total_token_usage": {
                    "input_tokens": 500,
                    "cached_input_tokens": 2000,
                    "output_tokens": 200,
                    "reasoning_output_tokens": 100,
                    "total_tokens": 2800,
                },
                "last_token_usage": {
                    "input_tokens": 300,
                    "cached_input_tokens": 1500,
                    "output_tokens": 150,
                    "reasoning_output_tokens": 50,
                    "total_tokens": 2000,
                },
            },
        },
    }


@pytest.fixture
def sample_mcp_tool_event() -> Dict[str, Any]:
    """Sample MCP tool call event (function_call)."""
    return {
        "timestamp": "2025-11-04T11:38:31.000Z",
        "type": "response_item",
        "payload": {
            "type": "function_call",
            "name": "mcp__zen-mcp__chat",
            "arguments": '{"prompt": "test query"}',
            "call_id": "call_abc123",
        },
    }


@pytest.fixture
def sample_builtin_tool_event() -> Dict[str, Any]:
    """Sample built-in tool call event (should be ignored)."""
    return {
        "timestamp": "2025-11-04T11:38:32.000Z",
        "type": "response_item",
        "payload": {
            "type": "function_call",
            "name": "read_file",
            "arguments": '{"path": "/test/file.py"}',
            "call_id": "call_def456",
        },
    }


@pytest.fixture
def sample_codex_events() -> List[Dict[str, Any]]:
    """Complete sample of Codex CLI JSONL events."""
    return [
        # turn_context event (model detection)
        {
            "timestamp": "2025-11-04T11:38:27.361Z",
            "type": "turn_context",
            "payload": {
                "cwd": "/test/project",
                "model": "gpt-5.1",
            },
        },
        # token_count event
        {
            "timestamp": "2025-11-04T11:38:30.056Z",
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {
                    "last_token_usage": {
                        "input_tokens": 300,
                        "cached_input_tokens": 1500,
                        "output_tokens": 150,
                        "reasoning_output_tokens": 50,
                        "total_tokens": 2000,
                    },
                },
            },
        },
        # MCP tool call (zen server)
        {
            "timestamp": "2025-11-04T11:38:31.000Z",
            "type": "response_item",
            "payload": {
                "type": "function_call",
                "name": "mcp__zen-mcp__chat",
                "arguments": '{"prompt": "test"}',
                "call_id": "call_abc123",
            },
        },
        # MCP tool call (brave-search server)
        {
            "timestamp": "2025-11-04T11:38:32.000Z",
            "type": "response_item",
            "payload": {
                "type": "function_call",
                "name": "mcp__brave-search-mcp__web",
                "arguments": '{"query": "search"}',
                "call_id": "call_def456",
            },
        },
    ]


class TestCodexCLIAdapterInitialization:
    """Test adapter initialization."""

    def test_initialization(self) -> None:
        """Test adapter initializes correctly."""
        adapter = CodexCLIAdapter(project="test-project", codex_args=[])

        assert adapter.project == "test-project"
        assert adapter.platform == "codex-cli"
        assert adapter.detected_model is None
        assert adapter.model_name == "Unknown Model"
        assert adapter.codex_args == []

    def test_initialization_with_args(self) -> None:
        """Test adapter initializes with codex args."""
        adapter = CodexCLIAdapter(
            project="test-project",
            codex_args=["--model", "gpt-5.1"],
        )

        assert adapter.codex_args == ["--model", "gpt-5.1"]


class TestEventParsing:
    """Test JSONL event parsing for Codex CLI format."""

    def test_parse_turn_context_event(self, sample_turn_context_event: Dict[str, Any]) -> None:
        """turn_context events should set model and return None."""
        adapter = CodexCLIAdapter(project="test", codex_args=[])

        result = adapter.parse_event(json.dumps(sample_turn_context_event))

        assert result is None
        assert adapter.detected_model == "gpt-5.1"
        assert adapter.model_name == "GPT-5.1"
        assert adapter.session.model == "gpt-5.1"

    def test_parse_turn_context_only_sets_model_once(self) -> None:
        """turn_context should only set model on first occurrence."""
        adapter = CodexCLIAdapter(project="test", codex_args=[])

        # First turn_context
        event1 = {
            "type": "turn_context",
            "payload": {"model": "gpt-5.1"},
        }
        adapter.parse_event(json.dumps(event1))
        assert adapter.detected_model == "gpt-5.1"

        # Second turn_context (should be ignored)
        event2 = {
            "type": "turn_context",
            "payload": {"model": "gpt-4.1"},
        }
        adapter.parse_event(json.dumps(event2))
        assert adapter.detected_model == "gpt-5.1"  # Unchanged

    def test_parse_token_count_event(self, sample_token_count_event: Dict[str, Any]) -> None:
        """token_count events should return __session__ with usage data."""
        adapter = CodexCLIAdapter(project="test", codex_args=[])

        result = adapter.parse_event(json.dumps(sample_token_count_event))

        assert result is not None
        tool_name, usage = result
        assert tool_name == "__session__"
        # Uses last_token_usage (delta)
        assert usage["input_tokens"] == 300
        assert usage["output_tokens"] == 200  # 150 + 50 reasoning
        assert usage["cache_read_tokens"] == 1500
        assert usage["cache_created_tokens"] == 0  # Codex doesn't have cache creation

    def test_parse_token_count_fallback_to_total(self) -> None:
        """Should fallback to total_token_usage if last not available."""
        adapter = CodexCLIAdapter(project="test", codex_args=[])

        event = {
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {
                    "total_token_usage": {
                        "input_tokens": 500,
                        "cached_input_tokens": 2000,
                        "output_tokens": 200,
                        "reasoning_output_tokens": 0,
                    },
                },
            },
        }
        result = adapter.parse_event(json.dumps(event))

        assert result is not None
        tool_name, usage = result
        assert tool_name == "__session__"
        assert usage["input_tokens"] == 500
        assert usage["cache_read_tokens"] == 2000

    def test_parse_mcp_tool_event(self, sample_mcp_tool_event: Dict[str, Any]) -> None:
        """MCP function_call events should return tool name and params."""
        adapter = CodexCLIAdapter(project="test", codex_args=[])

        result = adapter.parse_event(json.dumps(sample_mcp_tool_event))

        assert result is not None
        tool_name, usage = result
        assert tool_name == "mcp__zen-mcp__chat"  # Raw name (normalization in record)
        assert usage["input_tokens"] == 0  # No tokens in MCP events
        assert usage["output_tokens"] == 0
        assert usage["tool_params"] == {"prompt": "test query"}
        assert usage["call_id"] == "call_abc123"

    def test_parse_builtin_tool_ignored(self, sample_builtin_tool_event: Dict[str, Any]) -> None:
        """Built-in tools (not mcp__) should return None."""
        adapter = CodexCLIAdapter(project="test", codex_args=[])

        result = adapter.parse_event(json.dumps(sample_builtin_tool_event))

        assert result is None

    def test_parse_invalid_json(self) -> None:
        """Invalid JSON should return None."""
        adapter = CodexCLIAdapter(project="test", codex_args=[])

        result = adapter.parse_event("not valid json")
        assert result is None

    def test_parse_empty_line(self) -> None:
        """Empty lines should return None."""
        adapter = CodexCLIAdapter(project="test", codex_args=[])

        assert adapter.parse_event("") is None
        assert adapter.parse_event("  ") is None
        assert adapter.parse_event("\n") is None

    def test_parse_unknown_event_type(self) -> None:
        """Unknown event types should return None."""
        adapter = CodexCLIAdapter(project="test", codex_args=[])

        event = {"type": "unknown_type", "payload": {}}
        result = adapter.parse_event(json.dumps(event))
        assert result is None


class TestTokenAccumulation:
    """Test token accumulation via _process_tool_call."""

    def test_process_session_event(self) -> None:
        """Session events should accumulate tokens without recording tool call."""
        adapter = CodexCLIAdapter(project="test", codex_args=[])

        usage = {
            "input_tokens": 100,
            "output_tokens": 50,
            "cache_created_tokens": 0,
            "cache_read_tokens": 500,
        }
        adapter._process_tool_call("__session__", usage)

        assert adapter.session.token_usage.input_tokens == 100
        assert adapter.session.token_usage.output_tokens == 50
        assert adapter.session.token_usage.cache_read_tokens == 500
        assert adapter.session.token_usage.total_tokens == 650
        assert adapter.session.mcp_tool_calls.total_calls == 0  # Not a tool call

    def test_process_mcp_tool_call(self) -> None:
        """MCP tool calls should be recorded."""
        adapter = CodexCLIAdapter(project="test", codex_args=[])

        usage = {
            "input_tokens": 0,  # MCP events don't have tokens
            "output_tokens": 0,
            "cache_created_tokens": 0,
            "cache_read_tokens": 0,
            "tool_params": {"prompt": "test"},
        }
        adapter._process_tool_call("mcp__zen-mcp__chat", usage)

        # Server session created with normalized name
        assert "zen" in adapter.server_sessions
        assert adapter.server_sessions["zen"].total_calls == 1

        # mcp_tool_calls populated after finalize_session()
        session = adapter.finalize_session()
        assert session.mcp_tool_calls.total_calls == 1

    def test_multiple_events(self, sample_codex_events: List[Dict[str, Any]]) -> None:
        """Multiple events should accumulate correctly."""
        adapter = CodexCLIAdapter(project="test", codex_args=[])

        mcp_calls = 0
        for event in sample_codex_events:
            result = adapter.parse_event(json.dumps(event))
            if result:
                tool_name, usage = result
                if tool_name == "__session__":
                    adapter._process_tool_call(tool_name, usage)
                else:
                    adapter._process_tool_call(tool_name, usage)
                    mcp_calls += 1

        # Model detected
        assert adapter.detected_model == "gpt-5.1"

        # Tokens from token_count event
        assert adapter.session.token_usage.input_tokens == 300
        assert adapter.session.token_usage.output_tokens == 200  # 150 + 50
        assert adapter.session.token_usage.cache_read_tokens == 1500

        # MCP calls recorded (counted during processing)
        assert mcp_calls == 2

        # Server sessions tracked
        assert len(adapter.server_sessions) == 2
        assert "zen" in adapter.server_sessions
        assert "brave-search" in adapter.server_sessions

        # mcp_tool_calls populated after finalize_session()
        session = adapter.finalize_session()
        assert session.mcp_tool_calls.total_calls == 2


class TestModelDetection:
    """Test model detection from turn_context events."""

    def test_model_display_names(self) -> None:
        """Test all model display name mappings."""
        # GPT-5 series
        assert MODEL_DISPLAY_NAMES["gpt-5.1"] == "GPT-5.1"
        assert MODEL_DISPLAY_NAMES["gpt-5-mini"] == "GPT-5 Mini"
        assert MODEL_DISPLAY_NAMES["gpt-5-nano"] == "GPT-5 Nano"
        assert MODEL_DISPLAY_NAMES["gpt-5-pro"] == "GPT-5 Pro"

        # GPT-4.1 series
        assert MODEL_DISPLAY_NAMES["gpt-4.1"] == "GPT-4.1"
        assert MODEL_DISPLAY_NAMES["gpt-4.1-mini"] == "GPT-4.1 Mini"

        # O-series
        assert MODEL_DISPLAY_NAMES["o4-mini"] == "O4 Mini"
        assert MODEL_DISPLAY_NAMES["o3-mini"] == "O3 Mini"

    def test_unknown_model_uses_id(self) -> None:
        """Unknown models should use the raw ID as display name."""
        adapter = CodexCLIAdapter(project="test", codex_args=[])

        event = {
            "type": "turn_context",
            "payload": {"model": "gpt-99-turbo"},
        }
        adapter.parse_event(json.dumps(event))

        assert adapter.detected_model == "gpt-99-turbo"
        assert adapter.model_name == "gpt-99-turbo"  # Uses ID as fallback


class TestToolNameNormalization:
    """Test Codex CLI tool name normalization (-mcp suffix stripping)."""

    def test_mcp_suffix_stripped_in_server_name(self) -> None:
        """Server names should have -mcp suffix stripped."""
        adapter = CodexCLIAdapter(project="test", codex_args=[])

        # Record tool call with -mcp suffix
        adapter.record_tool_call(
            tool_name="mcp__zen-mcp__chat",
            input_tokens=0,
            output_tokens=0,
            cache_created_tokens=0,
            cache_read_tokens=0,
        )

        # Server name should be normalized (no -mcp)
        assert "zen" in adapter.server_sessions
        assert "zen-mcp" not in adapter.server_sessions

    def test_tool_name_normalized_in_server_session(self) -> None:
        """Tool names in server sessions should be normalized."""
        adapter = CodexCLIAdapter(project="test", codex_args=[])

        adapter.record_tool_call(
            tool_name="mcp__brave-search-mcp__web",
            input_tokens=0,
            output_tokens=0,
            cache_created_tokens=0,
            cache_read_tokens=0,
        )

        assert "brave-search" in adapter.server_sessions
        brave_session = adapter.server_sessions["brave-search"]
        # Normalized tool name
        assert "mcp__brave-search__web" in brave_session.tools


class TestCacheAnalysis:
    """Test cache analysis for Codex CLI platform."""

    def test_cache_analysis_no_creation(self) -> None:
        """Codex CLI has no cache creation, only reads."""
        adapter = CodexCLIAdapter(project="test", codex_args=[])

        # Process token event with cache read
        adapter._process_tool_call(
            "__session__",
            {
                "input_tokens": 100,
                "output_tokens": 50,
                "cache_created_tokens": 0,
                "cache_read_tokens": 10000,
            },
        )

        session = adapter.finalize_session()
        analysis = session._build_cache_analysis()

        # Codex CLI only has cache reads
        assert analysis.creation_tokens == 0
        assert analysis.read_tokens == 10000
        # All reads, no creation = efficient
        assert analysis.status == "efficient"

    def test_cache_analysis_in_session_dict(self) -> None:
        """Test cache_analysis included in session.to_dict() for Codex CLI."""
        adapter = CodexCLIAdapter(project="test", codex_args=[])

        adapter._process_tool_call(
            "__session__",
            {
                "input_tokens": 100,
                "output_tokens": 50,
                "cache_created_tokens": 0,
                "cache_read_tokens": 5000,
            },
        )

        session = adapter.finalize_session()
        session_dict = session.to_dict()

        assert "cache_analysis" in session_dict


class TestSourceFilesTracking:
    """Test source_files population for Codex CLI adapter."""

    def test_source_tracking_initialized(self) -> None:
        """Test _has_received_events flag initialized."""
        adapter = CodexCLIAdapter(project="test", codex_args=[])
        assert hasattr(adapter, "_has_received_events")
        assert adapter._has_received_events is False

    def test_source_files_empty_initially(self) -> None:
        """Test session.source_files is empty list by default."""
        adapter = CodexCLIAdapter(project="test", codex_args=[])
        assert adapter.session.source_files == []


class TestPlatformMetadata:
    """Test platform metadata generation."""

    def test_get_platform_metadata(self) -> None:
        """Test platform metadata includes correct fields."""
        adapter = CodexCLIAdapter(
            project="test",
            codex_args=["--model", "gpt-5.1"],
        )

        # Set model
        adapter.detected_model = "gpt-5.1"
        adapter.model_name = "GPT-5.1"

        metadata = adapter.get_platform_metadata()

        assert metadata["model"] == "gpt-5.1"
        assert metadata["model_name"] == "GPT-5.1"
        assert metadata["codex_args"] == ["--model", "gpt-5.1"]
        assert metadata["process_id"] is None  # No process started


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_token_count_with_zero_tokens(self) -> None:
        """Token count events with all zeros should return None."""
        adapter = CodexCLIAdapter(project="test", codex_args=[])

        event = {
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {
                    "last_token_usage": {
                        "input_tokens": 0,
                        "cached_input_tokens": 0,
                        "output_tokens": 0,
                        "reasoning_output_tokens": 0,
                    },
                },
            },
        }
        result = adapter.parse_event(json.dumps(event))
        assert result is None

    def test_token_count_missing_info(self) -> None:
        """Token count events without info should return None."""
        adapter = CodexCLIAdapter(project="test", codex_args=[])

        event = {
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                # No 'info' field
            },
        }
        result = adapter.parse_event(json.dumps(event))
        assert result is None

    def test_function_call_invalid_arguments(self) -> None:
        """Function calls with invalid JSON arguments should still work."""
        adapter = CodexCLIAdapter(project="test", codex_args=[])

        event = {
            "type": "response_item",
            "payload": {
                "type": "function_call",
                "name": "mcp__zen-mcp__chat",
                "arguments": "not valid json",
                "call_id": "call_123",
            },
        }
        result = adapter.parse_event(json.dumps(event))

        assert result is not None
        tool_name, usage = result
        assert tool_name == "mcp__zen-mcp__chat"
        assert usage["tool_params"] == {}  # Empty dict on parse failure

    def test_turn_context_missing_model(self) -> None:
        """turn_context without model should not crash."""
        adapter = CodexCLIAdapter(project="test", codex_args=[])

        event = {
            "type": "turn_context",
            "payload": {"cwd": "/test"},  # No model field
        }
        result = adapter.parse_event(json.dumps(event))

        assert result is None
        assert adapter.detected_model is None


class TestCompleteWorkflow:
    """Test complete end-to-end workflow."""

    def test_complete_session_tracking(self, sample_codex_events: List[Dict[str, Any]]) -> None:
        """Test complete session from events to finalization."""
        adapter = CodexCLIAdapter(project="test-codex", codex_args=[])

        # Process all events
        for event in sample_codex_events:
            result = adapter.parse_event(json.dumps(event))
            if result:
                tool_name, usage = result
                if tool_name == "__session__":
                    # Update session tokens directly
                    adapter.session.token_usage.input_tokens += usage["input_tokens"]
                    adapter.session.token_usage.output_tokens += usage["output_tokens"]
                    adapter.session.token_usage.cache_read_tokens += usage["cache_read_tokens"]
                else:
                    # Record MCP tool call
                    adapter.record_tool_call(
                        tool_name=tool_name,
                        input_tokens=usage["input_tokens"],
                        output_tokens=usage["output_tokens"],
                        cache_created_tokens=usage["cache_created_tokens"],
                        cache_read_tokens=usage["cache_read_tokens"],
                    )

        # Finalize
        session = adapter.finalize_session()

        # Verify session data
        assert session.project == "test-codex"
        assert session.platform == "codex-cli"
        assert session.model == "gpt-5.1"

        # Verify tokens
        assert session.token_usage.input_tokens == 300
        assert session.token_usage.output_tokens == 200
        assert session.token_usage.cache_read_tokens == 1500

        # Verify MCP calls (2 tool calls)
        assert session.mcp_tool_calls.total_calls == 2
        assert session.mcp_tool_calls.unique_tools == 2

        # Verify servers tracked (normalized names)
        assert "zen" in session.server_sessions
        assert "brave-search" in session.server_sessions
