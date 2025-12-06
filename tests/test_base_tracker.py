#!/usr/bin/env python3
"""
Test suite for base_tracker module

Tests BaseTracker abstract class and shared functionality.
"""

import pytest
from datetime import datetime
from pathlib import Path
from mcp_audit.base_tracker import (
    BaseTracker,
    Session,
    ServerSession,
    ToolStats,
    Call,
    TokenUsage,
    MCPToolCalls,
    SCHEMA_VERSION,
)


# ============================================================================
# Concrete Test Implementation of BaseTracker
# ============================================================================


class ConcreteTestTracker(BaseTracker):
    """Concrete implementation of BaseTracker for testing"""

    def __init__(self, project: str = "test-project", platform: str = "test-platform"):
        super().__init__(project, platform)
        self.events = []

    def start_tracking(self) -> None:
        """Test implementation - does nothing"""
        pass

    def parse_event(self, event_data):
        """Test implementation - returns None"""
        return None

    def get_platform_metadata(self):
        """Test implementation - returns test metadata"""
        return {"test_key": "test_value"}


# ============================================================================
# Data Structure Tests
# ============================================================================


class TestDataStructures:
    """Tests for core data structures (v1.1.0 schema)"""

    def test_call_creation(self) -> None:
        """Test Call dataclass creation (v1.1.0 - no schema_version on Call)"""
        call = Call(
            tool_name="mcp__zen__chat",
            server="zen",
            index=1,
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
        )

        assert call.tool_name == "mcp__zen__chat"
        assert call.server == "zen"  # v1.1.0: server name on Call
        assert call.index == 1  # v1.1.0: sequential index
        assert call.input_tokens == 100
        assert call.output_tokens == 50
        assert call.total_tokens == 150
        # v1.1.0: schema_version removed from Call (only at session level)

    def test_call_to_dict(self) -> None:
        """Test Call to_dict conversion (v1.1.0 format)"""
        from datetime import timezone

        timestamp = datetime(2025, 11, 24, 10, 30, 0, tzinfo=timezone.utc)
        call = Call(
            tool_name="mcp__zen__chat",
            server="zen",
            index=1,
            timestamp=timestamp,
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
        )

        data = call.to_dict()

        # v1.1.0: uses "tool" instead of "tool_name"
        assert data["tool"] == "mcp__zen__chat"
        assert data["server"] == "zen"
        assert data["index"] == 1
        assert data["input_tokens"] == 100
        # v1.1.0: ISO 8601 with timezone offset
        assert "2025-11-24T10:30:00" in data["timestamp"]

    def test_call_to_dict_v1_0(self) -> None:
        """Test Call to_dict_v1_0 for backward compatibility"""
        timestamp = datetime(2025, 11, 24, 10, 30, 0)
        call = Call(
            tool_name="mcp__zen__chat",
            timestamp=timestamp,
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
        )

        data = call.to_dict_v1_0()

        # v1.0.0 format includes schema_version and tool_name
        assert data["schema_version"] == "1.0.0"
        assert data["tool_name"] == "mcp__zen__chat"
        assert data["input_tokens"] == 100

    def test_tool_stats_creation(self) -> None:
        """Test ToolStats dataclass creation (v1.1.0 - no schema_version)"""
        stats = ToolStats(calls=5, total_tokens=1000, avg_tokens=200.0)

        assert stats.calls == 5
        assert stats.total_tokens == 1000
        assert stats.avg_tokens == 200.0
        # v1.1.0: schema_version removed from ToolStats

    def test_tool_stats_to_dict(self) -> None:
        """Test ToolStats to_dict with call history (v1.1.0)"""
        call = Call(tool_name="test", server="test-server", index=1, total_tokens=100)
        stats = ToolStats(calls=1, call_history=[call])

        data = stats.to_dict()

        assert data["calls"] == 1
        assert len(data["call_history"]) == 1
        # v1.1.0: uses "tool" instead of "tool_name"
        assert data["call_history"][0]["tool"] == "test"
        assert data["call_history"][0]["server"] == "test-server"

    def test_tool_stats_to_dict_v1_0(self) -> None:
        """Test ToolStats to_dict_v1_0 for backward compatibility"""
        call = Call(tool_name="test", total_tokens=100)
        stats = ToolStats(calls=1, call_history=[call])

        data = stats.to_dict_v1_0()

        # v1.0.0 format includes schema_version
        assert data["schema_version"] == "1.0.0"
        assert data["calls"] == 1
        assert data["call_history"][0]["tool_name"] == "test"

    def test_server_session_creation(self) -> None:
        """Test ServerSession dataclass creation"""
        session = ServerSession(server="zen", total_calls=10, total_tokens=5000)

        assert session.server == "zen"
        assert session.total_calls == 10
        assert session.total_tokens == 5000

    def test_session_creation(self) -> None:
        """Test Session dataclass creation"""
        session = Session(project="test-project", platform="test-platform", session_id="test-123")

        assert session.project == "test-project"
        assert session.platform == "test-platform"
        assert session.session_id == "test-123"
        assert session.schema_version == SCHEMA_VERSION


# ============================================================================
# BaseTracker Initialization Tests
# ============================================================================


class TestBaseTrackerInitialization:
    """Tests for BaseTracker initialization"""

    def test_initialization(self) -> None:
        """Test BaseTracker initialization"""
        tracker = ConcreteTestTracker(project="my-project", platform="my-platform")

        assert tracker.project == "my-project"
        assert tracker.platform == "my-platform"
        assert tracker.session.project == "my-project"
        assert tracker.session.platform == "my-platform"

    def test_session_id_generation(self) -> None:
        """Test session ID generation"""
        tracker = ConcreteTestTracker()

        session_id = tracker.session_id

        # Should be in format: project-YYYY-MM-DDTHH-MM-SS
        assert session_id.startswith("test-project-")
        assert "T" in session_id

    def test_server_sessions_initialized(self) -> None:
        """Test server sessions dictionary initialized"""
        tracker = ConcreteTestTracker()

        assert isinstance(tracker.server_sessions, dict)
        assert len(tracker.server_sessions) == 0

    def test_content_hashes_initialized(self) -> None:
        """Test content hashes dictionary initialized"""
        tracker = ConcreteTestTracker()

        assert isinstance(tracker.content_hashes, dict)


# ============================================================================
# Normalization Tests
# ============================================================================


class TestNormalization:
    """Tests for tool name normalization"""

    def test_normalize_server_name_claude_code(self) -> None:
        """Test server name extraction (Claude Code format)"""
        tracker = ConcreteTestTracker()

        server = tracker.normalize_server_name("mcp__zen__chat")

        assert server == "zen"

    def test_normalize_server_name_codex_cli(self) -> None:
        """Test server name extraction (Codex CLI format with -mcp)"""
        tracker = ConcreteTestTracker()

        server = tracker.normalize_server_name("mcp__zen-mcp__chat")

        assert server == "zen"

    def test_normalize_server_name_hyphenated(self) -> None:
        """Test server name with hyphens"""
        tracker = ConcreteTestTracker()

        server = tracker.normalize_server_name("mcp__brave-search__web")

        assert server == "brave-search"

    def test_normalize_tool_name_passthrough(self) -> None:
        """Test tool name normalization (Claude Code format)"""
        tracker = ConcreteTestTracker()

        normalized = tracker.normalize_tool_name("mcp__zen__chat")

        assert normalized == "mcp__zen__chat"

    def test_normalize_tool_name_codex_cli(self) -> None:
        """Test tool name normalization (Codex CLI -mcp suffix)"""
        tracker = ConcreteTestTracker()

        normalized = tracker.normalize_tool_name("mcp__zen-mcp__chat")

        assert normalized == "mcp__zen__chat"

    def test_normalize_invalid_tool_name(self) -> None:
        """Test normalization warns on invalid tool name"""
        tracker = ConcreteTestTracker()

        with pytest.warns(UserWarning):
            server = tracker.normalize_server_name("Read")

        assert server == "unknown"


# ============================================================================
# Tool Call Recording Tests
# ============================================================================


class TestToolCallRecording:
    """Tests for recording tool calls"""

    def test_record_tool_call_basic(self) -> None:
        """Test recording a basic tool call"""
        tracker = ConcreteTestTracker()

        tracker.record_tool_call(
            tool_name="mcp__zen__chat",
            input_tokens=100,
            output_tokens=50,
            cache_created_tokens=20,
            cache_read_tokens=500,
        )

        # Check session token usage
        assert tracker.session.token_usage.input_tokens == 100
        assert tracker.session.token_usage.output_tokens == 50
        assert tracker.session.token_usage.cache_created_tokens == 20
        assert tracker.session.token_usage.cache_read_tokens == 500
        assert tracker.session.token_usage.total_tokens == 670

    def test_record_tool_call_creates_server_session(self) -> None:
        """Test tool call creates server session"""
        tracker = ConcreteTestTracker()

        tracker.record_tool_call(tool_name="mcp__zen__chat", input_tokens=100, output_tokens=50)

        assert "zen" in tracker.server_sessions
        assert tracker.server_sessions["zen"].server == "zen"

    def test_record_tool_call_creates_tool_stats(self) -> None:
        """Test tool call creates tool stats"""
        tracker = ConcreteTestTracker()

        tracker.record_tool_call(tool_name="mcp__zen__chat", input_tokens=100, output_tokens=50)

        zen_session = tracker.server_sessions["zen"]
        assert "mcp__zen__chat" in zen_session.tools
        tool_stats = zen_session.tools["mcp__zen__chat"]
        assert tool_stats.calls == 1
        assert tool_stats.total_tokens == 150

    def test_record_multiple_tool_calls(self) -> None:
        """Test recording multiple tool calls"""
        tracker = ConcreteTestTracker()

        # First call
        tracker.record_tool_call(tool_name="mcp__zen__chat", input_tokens=100, output_tokens=50)

        # Second call
        tracker.record_tool_call(tool_name="mcp__zen__chat", input_tokens=200, output_tokens=100)

        tool_stats = tracker.server_sessions["zen"].tools["mcp__zen__chat"]
        assert tool_stats.calls == 2
        assert tool_stats.total_tokens == 450  # 150 + 300
        assert tool_stats.avg_tokens == 225.0  # 450 / 2

    def test_record_tool_call_normalizes_codex_name(self) -> None:
        """Test Codex CLI tool names are normalized"""
        tracker = ConcreteTestTracker()

        tracker.record_tool_call(
            tool_name="mcp__zen-mcp__chat", input_tokens=100, output_tokens=50  # Codex format
        )

        # Should be normalized to Claude Code format
        zen_session = tracker.server_sessions["zen"]
        assert "mcp__zen__chat" in zen_session.tools

    def test_record_tool_call_with_duration(self) -> None:
        """Test recording tool call with duration"""
        tracker = ConcreteTestTracker()

        tracker.record_tool_call(
            tool_name="mcp__zen__chat", input_tokens=100, output_tokens=50, duration_ms=1500
        )

        tool_stats = tracker.server_sessions["zen"].tools["mcp__zen__chat"]
        assert tool_stats.total_duration_ms == 1500
        assert tool_stats.avg_duration_ms == 1500.0
        assert tool_stats.max_duration_ms == 1500
        assert tool_stats.min_duration_ms == 1500

    def test_record_tool_call_duration_stats(self) -> None:
        """Test duration statistics across multiple calls"""
        tracker = ConcreteTestTracker()

        # Three calls with different durations
        tracker.record_tool_call(
            tool_name="mcp__zen__chat", input_tokens=100, output_tokens=50, duration_ms=1000
        )
        tracker.record_tool_call(
            tool_name="mcp__zen__chat", input_tokens=100, output_tokens=50, duration_ms=2000
        )
        tracker.record_tool_call(
            tool_name="mcp__zen__chat", input_tokens=100, output_tokens=50, duration_ms=1500
        )

        tool_stats = tracker.server_sessions["zen"].tools["mcp__zen__chat"]
        assert tool_stats.total_duration_ms == 4500
        assert tool_stats.avg_duration_ms == 1500.0
        assert tool_stats.max_duration_ms == 2000
        assert tool_stats.min_duration_ms == 1000

    def test_record_tool_call_with_content_hash(self) -> None:
        """Test recording tool call with content hash (duplicate detection)"""
        tracker = ConcreteTestTracker()

        tracker.record_tool_call(
            tool_name="mcp__zen__chat", input_tokens=100, output_tokens=50, content_hash="abc123"
        )

        assert "abc123" in tracker.content_hashes
        assert len(tracker.content_hashes["abc123"]) == 1

    def test_cache_efficiency_calculation(self) -> None:
        """Test cache efficiency calculation"""
        tracker = ConcreteTestTracker()

        tracker.record_tool_call(
            tool_name="mcp__zen__chat",
            input_tokens=100,
            output_tokens=50,
            cache_created_tokens=20,
            cache_read_tokens=500,
        )

        # cache_efficiency = cache_read / total_input
        # total_input = input_tokens + cache_created + cache_read = 100 + 20 + 500 = 620
        # 500 / 620 = 0.8064...
        assert tracker.session.token_usage.cache_efficiency > 0.80
        assert tracker.session.token_usage.cache_efficiency < 0.81


# ============================================================================
# Session Finalization Tests
# ============================================================================


class TestSessionFinalization:
    """Tests for session finalization"""

    def test_finalize_session_basic(self) -> None:
        """Test basic session finalization"""
        tracker = ConcreteTestTracker()

        # Record some calls
        tracker.record_tool_call(tool_name="mcp__zen__chat", input_tokens=100, output_tokens=50)

        session = tracker.finalize_session()

        assert session.end_timestamp is not None
        assert session.duration_seconds is not None
        assert session.duration_seconds >= 0

    def test_finalize_session_mcp_summary(self) -> None:
        """Test MCP tool calls summary"""
        tracker = ConcreteTestTracker()

        # Record multiple calls
        tracker.record_tool_call(tool_name="mcp__zen__chat", input_tokens=100, output_tokens=50)
        tracker.record_tool_call(tool_name="mcp__zen__chat", input_tokens=100, output_tokens=50)
        tracker.record_tool_call(tool_name="mcp__zen__debug", input_tokens=200, output_tokens=100)

        session = tracker.finalize_session()

        assert session.mcp_tool_calls.total_calls == 3
        assert session.mcp_tool_calls.unique_tools == 2
        assert "mcp__zen__chat (2 calls)" in session.mcp_tool_calls.most_called

    def test_finalize_session_server_sessions(self) -> None:
        """Test server sessions added to session"""
        tracker = ConcreteTestTracker()

        tracker.record_tool_call(tool_name="mcp__zen__chat", input_tokens=100, output_tokens=50)

        session = tracker.finalize_session()

        assert "zen" in session.server_sessions
        assert session.server_sessions["zen"].server == "zen"

    def test_analyze_redundancy(self) -> None:
        """Test redundancy analysis (duplicate detection)"""
        tracker = ConcreteTestTracker()

        # Same content hash = duplicate
        tracker.record_tool_call(
            tool_name="mcp__zen__chat", input_tokens=100, output_tokens=50, content_hash="abc123"
        )
        tracker.record_tool_call(
            tool_name="mcp__zen__chat",
            input_tokens=100,
            output_tokens=50,
            content_hash="abc123",  # Duplicate
        )
        tracker.record_tool_call(
            tool_name="mcp__zen__chat",
            input_tokens=100,
            output_tokens=50,
            content_hash="def456",  # Different
        )

        session = tracker.finalize_session()

        assert session.redundancy_analysis is not None
        assert session.redundancy_analysis["duplicate_calls"] == 1
        assert session.redundancy_analysis["potential_savings"] == 150

    def test_detect_anomalies_high_frequency(self) -> None:
        """Test anomaly detection for high frequency"""
        tracker = ConcreteTestTracker()

        # 15 calls (threshold is 10)
        for _ in range(15):
            tracker.record_tool_call(tool_name="mcp__zen__chat", input_tokens=100, output_tokens=50)

        session = tracker.finalize_session()

        # Should detect high frequency anomaly
        assert len(session.anomalies) > 0
        anomaly = session.anomalies[0]
        assert anomaly["type"] == "high_frequency"
        assert anomaly["tool"] == "mcp__zen__chat"
        assert anomaly["calls"] == 15

    def test_detect_anomalies_high_avg_tokens(self) -> None:
        """Test anomaly detection for high average tokens"""
        tracker = ConcreteTestTracker()

        # 600K tokens (threshold is 500K - raised for Claude Code context accumulation)
        tracker.record_tool_call(
            tool_name="mcp__zen__thinkdeep", input_tokens=400000, output_tokens=200000
        )

        session = tracker.finalize_session()

        # Should detect high avg tokens anomaly
        assert len(session.anomalies) > 0
        anomaly = session.anomalies[0]
        assert anomaly["type"] == "high_avg_tokens"
        assert anomaly["tool"] == "mcp__zen__thinkdeep"
        assert anomaly["avg_tokens"] == 600000


# ============================================================================
# Persistence Tests
# ============================================================================


class TestPersistence:
    """Tests for session persistence (v1.1.0 single-file format)"""

    def test_save_session(self, tmp_path) -> None:
        """Test saving session to disk (v1.1.0 format)"""
        tracker = ConcreteTestTracker()

        tracker.record_tool_call(tool_name="mcp__zen__chat", input_tokens=100, output_tokens=50)

        tracker.finalize_session()
        tracker.save_session(tmp_path)

        # v1.1.0: session_dir points to date subdirectory
        assert tracker.session_dir is not None
        assert tracker.session_dir.exists()

        # v1.1.0: single file per session, named <project>-<timestamp>.json
        # File is in date subdirectory (session_dir)
        session_files = list(tracker.session_dir.glob("*.json"))
        assert len(session_files) == 1

        # v1.1.0: no more separate mcp-*.json files
        mcp_files = list(tracker.session_dir.glob("mcp-*.json"))
        assert len(mcp_files) == 0

        # Verify file contents
        import json

        with open(session_files[0]) as f:
            data = json.load(f)

        # v1.1.0: has _file header
        assert "_file" in data
        assert data["_file"]["schema_version"] == SCHEMA_VERSION
        assert data["_file"]["type"] == "mcp_audit_session"

        # v1.1.0: has session block
        assert "session" in data
        assert data["session"]["project"] == "test-project"
        assert data["session"]["platform"] == "test-platform"

        # v1.1.0: has flat tool_calls array
        assert "tool_calls" in data
        assert len(data["tool_calls"]) == 1
        assert data["tool_calls"][0]["tool"] == "mcp__zen__chat"


# ============================================================================
# Utility Methods Tests
# ============================================================================


class TestUtilityMethods:
    """Tests for utility methods"""

    def test_compute_content_hash(self) -> None:
        """Test content hash computation"""
        input_data = {"query": "test", "options": {"verbose": True}}

        hash1 = BaseTracker.compute_content_hash(input_data)
        hash2 = BaseTracker.compute_content_hash(input_data)

        # Same input = same hash
        assert hash1 == hash2

        # Different input = different hash
        input_data2 = {"query": "different"}
        hash3 = BaseTracker.compute_content_hash(input_data2)
        assert hash3 != hash1

    def test_handle_unrecognized_line(self) -> None:
        """Test unrecognized line handling"""
        tracker = ConcreteTestTracker()

        # Should not crash, just warn
        with pytest.warns(UserWarning):
            tracker.handle_unrecognized_line("invalid line format")


# ============================================================================
# Integration Tests
# ============================================================================


class TestBaseTrackerIntegration:
    """Integration tests for complete tracker workflow (v1.1.0)"""

    def test_complete_workflow(self, tmp_path) -> None:
        """Test complete tracking workflow (v1.1.0 format)"""
        import json

        tracker = ConcreteTestTracker()

        # Record multiple tools across multiple servers
        tracker.record_tool_call(
            tool_name="mcp__zen__chat", input_tokens=100, output_tokens=50, duration_ms=1000
        )
        tracker.record_tool_call(
            tool_name="mcp__zen__debug", input_tokens=200, output_tokens=100, duration_ms=2000
        )
        tracker.record_tool_call(
            tool_name="mcp__brave-search__web", input_tokens=150, output_tokens=75, duration_ms=500
        )

        # Finalize and save
        session = tracker.finalize_session()
        tracker.save_session(tmp_path)

        # Verify session data
        assert session.mcp_tool_calls.total_calls == 3
        assert session.mcp_tool_calls.unique_tools == 3
        assert len(tracker.server_sessions) == 2  # zen + brave-search

        # v1.1.0: single session file in date subdirectory
        session_files = list(tracker.session_dir.glob("*.json"))
        assert len(session_files) == 1

        # Load and verify the session file
        with open(session_files[0]) as f:
            data = json.load(f)

        # v1.1.0: verify _file header
        assert data["_file"]["schema_version"] == SCHEMA_VERSION

        # v1.1.0: verify flat tool_calls array has all 3 calls
        assert len(data["tool_calls"]) == 3

        # Verify sequential indices
        indices = [c["index"] for c in data["tool_calls"]]
        assert indices == [1, 2, 3]

        # Verify all servers captured in tool_calls
        servers = {c["server"] for c in data["tool_calls"]}
        assert servers == {"zen", "brave-search"}

        # v1.1.0: verify mcp_summary
        assert data["mcp_summary"]["total_calls"] == 3
        assert data["mcp_summary"]["unique_tools"] == 3
        assert data["mcp_summary"]["unique_servers"] == 2
        assert set(data["mcp_summary"]["servers_used"]) == {"zen", "brave-search"}


# ============================================================================
# Cache Analysis Tests (task-47)
# ============================================================================


class TestCacheAnalysis:
    """Tests for cache analysis functionality (task-47.3, task-47.4)"""

    def test_tool_stats_cache_tracking(self) -> None:
        """Test per-tool cache token tracking (task-47.4)"""
        tracker = ConcreteTestTracker()

        tracker.record_tool_call(
            tool_name="mcp__zen__thinkdeep",
            input_tokens=100,
            output_tokens=50,
            cache_created_tokens=50000,
            cache_read_tokens=10000,
        )
        tracker.record_tool_call(
            tool_name="mcp__zen__chat",
            input_tokens=50,
            output_tokens=25,
            cache_created_tokens=5000,
            cache_read_tokens=100000,
        )

        # Check per-tool cache tracking
        thinkdeep_stats = tracker.server_sessions["zen"].tools["mcp__zen__thinkdeep"]
        assert thinkdeep_stats.cache_created_tokens == 50000
        assert thinkdeep_stats.cache_read_tokens == 10000

        chat_stats = tracker.server_sessions["zen"].tools["mcp__zen__chat"]
        assert chat_stats.cache_created_tokens == 5000
        assert chat_stats.cache_read_tokens == 100000

    def test_tool_stats_cache_aggregation(self) -> None:
        """Test cache tokens aggregate across multiple calls"""
        tracker = ConcreteTestTracker()

        # Multiple calls to same tool
        tracker.record_tool_call(
            tool_name="mcp__zen__chat",
            input_tokens=50,
            output_tokens=25,
            cache_created_tokens=10000,
            cache_read_tokens=5000,
        )
        tracker.record_tool_call(
            tool_name="mcp__zen__chat",
            input_tokens=50,
            output_tokens=25,
            cache_created_tokens=15000,
            cache_read_tokens=8000,
        )

        tool_stats = tracker.server_sessions["zen"].tools["mcp__zen__chat"]
        assert tool_stats.cache_created_tokens == 25000  # 10000 + 15000
        assert tool_stats.cache_read_tokens == 13000  # 5000 + 8000

    def test_cache_analysis_efficient(self) -> None:
        """Test cache analysis with efficient caching (positive savings)"""
        tracker = ConcreteTestTracker()

        tracker.record_tool_call(
            tool_name="mcp__zen__chat",
            input_tokens=100,
            output_tokens=50,
            cache_created_tokens=10000,
            cache_read_tokens=200000,  # High cache read = efficient
        )

        # Set cache savings (positive = efficient)
        tracker.session.cache_savings_usd = 0.50

        session = tracker.finalize_session()
        cache_analysis = session._build_cache_analysis(0.50)

        assert cache_analysis.status == "efficient"
        assert cache_analysis.creation_tokens == 10000
        assert cache_analysis.read_tokens == 200000
        assert cache_analysis.ratio == 20.0  # 200000 / 10000
        assert cache_analysis.net_savings_usd == 0.50
        assert "Cache saved" in cache_analysis.summary
        assert "efficiently" in cache_analysis.recommendation.lower()

    def test_cache_analysis_inefficient_no_reuse(self) -> None:
        """Test cache analysis with no reuse (high creation, zero read)"""
        tracker = ConcreteTestTracker()

        tracker.record_tool_call(
            tool_name="mcp__zen__thinkdeep",
            input_tokens=100,
            output_tokens=50,
            cache_created_tokens=100000,
            cache_read_tokens=0,  # No cache reuse
        )

        session = tracker.finalize_session()
        cache_analysis = session._build_cache_analysis(-0.25)

        assert cache_analysis.status == "inefficient"
        assert cache_analysis.read_tokens == 0
        assert "no reuse" in cache_analysis.summary.lower()
        assert "batching" in cache_analysis.recommendation.lower()

    def test_cache_analysis_inefficient_low_reuse(self) -> None:
        """Test cache analysis with low reuse (ratio < 0.1)"""
        tracker = ConcreteTestTracker()

        tracker.record_tool_call(
            tool_name="mcp__zen__thinkdeep",
            input_tokens=100,
            output_tokens=50,
            cache_created_tokens=100000,
            cache_read_tokens=5000,  # Low reuse: 5000/100000 = 0.05
        )

        session = tracker.finalize_session()
        cache_analysis = session._build_cache_analysis(-0.15)

        assert cache_analysis.status == "inefficient"
        assert cache_analysis.ratio < 0.1
        assert "low reuse" in cache_analysis.summary.lower()

    def test_cache_analysis_neutral(self) -> None:
        """Test cache analysis with no cache activity"""
        tracker = ConcreteTestTracker()

        tracker.record_tool_call(
            tool_name="mcp__zen__chat",
            input_tokens=100,
            output_tokens=50,
            cache_created_tokens=0,
            cache_read_tokens=0,
        )

        session = tracker.finalize_session()
        cache_analysis = session._build_cache_analysis(0.0)

        assert cache_analysis.status == "neutral"
        assert "No cache activity" in cache_analysis.summary
        assert cache_analysis.recommendation == ""

    def test_cache_analysis_top_creators(self) -> None:
        """Test cache analysis identifies top cache creators"""
        tracker = ConcreteTestTracker()

        tracker.record_tool_call(
            tool_name="mcp__zen__thinkdeep",
            input_tokens=100,
            output_tokens=50,
            cache_created_tokens=80000,
            cache_read_tokens=10000,
        )
        tracker.record_tool_call(
            tool_name="mcp__zen__chat",
            input_tokens=50,
            output_tokens=25,
            cache_created_tokens=20000,
            cache_read_tokens=50000,
        )

        session = tracker.finalize_session()
        cache_analysis = session._build_cache_analysis(-0.10)

        assert len(cache_analysis.top_cache_creators) == 2
        # thinkdeep should be first (80000 > 20000)
        assert cache_analysis.top_cache_creators[0]["tool"] == "mcp__zen__thinkdeep"
        assert cache_analysis.top_cache_creators[0]["tokens"] == 80000
        assert cache_analysis.top_cache_creators[0]["pct"] == 80.0

    def test_cache_analysis_top_readers(self) -> None:
        """Test cache analysis identifies top cache readers"""
        tracker = ConcreteTestTracker()

        tracker.record_tool_call(
            tool_name="mcp__zen__thinkdeep",
            input_tokens=100,
            output_tokens=50,
            cache_created_tokens=50000,
            cache_read_tokens=10000,
        )
        tracker.record_tool_call(
            tool_name="mcp__zen__chat",
            input_tokens=50,
            output_tokens=25,
            cache_created_tokens=5000,
            cache_read_tokens=90000,
        )

        session = tracker.finalize_session()
        cache_analysis = session._build_cache_analysis(0.20)

        assert len(cache_analysis.top_cache_readers) == 2
        # chat should be first (90000 > 10000)
        assert cache_analysis.top_cache_readers[0]["tool"] == "mcp__zen__chat"
        assert cache_analysis.top_cache_readers[0]["tokens"] == 90000
        assert cache_analysis.top_cache_readers[0]["pct"] == 90.0

    def test_cache_analysis_in_session_dict(self) -> None:
        """Test cache_analysis is included in session.to_dict() (task-47.3)"""
        tracker = ConcreteTestTracker()

        tracker.record_tool_call(
            tool_name="mcp__zen__chat",
            input_tokens=100,
            output_tokens=50,
            cache_created_tokens=10000,
            cache_read_tokens=50000,
        )

        tracker.session.cache_savings_usd = 0.15
        session = tracker.finalize_session()
        data = session.to_dict()

        # Verify cache_analysis section exists
        assert "cache_analysis" in data
        assert data["cache_analysis"]["status"] in ["efficient", "inefficient", "neutral"]
        assert "summary" in data["cache_analysis"]
        assert "creation_tokens" in data["cache_analysis"]
        assert "read_tokens" in data["cache_analysis"]
        assert "ratio" in data["cache_analysis"]
        assert "net_savings_usd" in data["cache_analysis"]
        assert "top_cache_creators" in data["cache_analysis"]
        assert "top_cache_readers" in data["cache_analysis"]
        assert "recommendation" in data["cache_analysis"]

    def test_session_cost_fields(self) -> None:
        """Test session has cost_no_cache and cache_savings_usd fields"""
        session = Session(project="test", platform="test", session_id="test-123")

        # Should have default values
        assert session.cost_no_cache == 0.0
        assert session.cache_savings_usd == 0.0

        # Should be settable
        session.cost_no_cache = 1.50
        session.cache_savings_usd = 0.25
        assert session.cost_no_cache == 1.50
        assert session.cache_savings_usd == 0.25

    def test_session_to_dict_includes_cost_fields(self) -> None:
        """Test session.to_dict() includes cost_no_cache_usd and cache_savings_usd"""
        tracker = ConcreteTestTracker()

        tracker.record_tool_call(
            tool_name="mcp__zen__chat",
            input_tokens=100,
            output_tokens=50,
        )

        tracker.session.cost_estimate = 1.00
        tracker.session.cost_no_cache = 1.25
        tracker.session.cache_savings_usd = 0.25

        session = tracker.finalize_session()
        data = session.to_dict()

        assert data["cost_estimate_usd"] == 1.00
        assert data["cost_no_cache_usd"] == 1.25
        assert data["cache_savings_usd"] == 0.25


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
