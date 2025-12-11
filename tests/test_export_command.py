"""
Tests for the export command (v1.5.0 - task-103.2).

Tests cover:
- AI prompt export in markdown format
- AI prompt export in JSON format
- Storage helper functions
"""

import json
import tempfile
from pathlib import Path

import pytest


# ============================================================================
# Storage Helper Tests
# ============================================================================


class TestStorageHelpers:
    """Tests for storage helper functions."""

    def test_load_session_file_valid(self) -> None:
        """Test loading a valid session JSON file."""
        from mcp_audit.storage import load_session_file

        session_data = {
            "session": {"platform": "claude-code", "project": "test"},
            "token_usage": {"total_tokens": 1000},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(session_data, f)
            f.flush()
            file_path = Path(f.name)

        try:
            loaded = load_session_file(file_path)
            assert loaded is not None
            assert loaded["session"]["platform"] == "claude-code"
            assert loaded["token_usage"]["total_tokens"] == 1000
        finally:
            file_path.unlink()

    def test_load_session_file_invalid_json(self) -> None:
        """Test loading an invalid JSON file returns None."""
        from mcp_audit.storage import load_session_file

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json")
            f.flush()
            file_path = Path(f.name)

        try:
            loaded = load_session_file(file_path)
            assert loaded is None
        finally:
            file_path.unlink()

    def test_load_session_file_missing(self) -> None:
        """Test loading a missing file returns None."""
        from mcp_audit.storage import load_session_file

        loaded = load_session_file(Path("/nonexistent/path.json"))
        assert loaded is None

    def test_get_latest_session_missing_dir(self) -> None:
        """Test get_latest_session with missing directory returns None."""
        from mcp_audit.storage import get_latest_session

        result = get_latest_session(Path("/nonexistent/directory"))
        assert result is None


# ============================================================================
# AI Prompt Generation Tests
# ============================================================================


class TestAIPromptGeneration:
    """Tests for AI prompt generation functions."""

    def test_generate_markdown_basic(self) -> None:
        """Test markdown generation with basic session data."""
        from mcp_audit.cli import generate_ai_prompt_markdown

        session_data = {
            "session": {
                "platform": "claude-code",
                "model": "claude-opus-4-5",
                "duration_seconds": 300,
                "project": "test-project",
            },
            "token_usage": {
                "input_tokens": 5000,
                "output_tokens": 2000,
                "cache_read_tokens": 1000,
                "cache_created_tokens": 500,
                "total_tokens": 8500,
            },
            "cost_estimate_usd": 0.15,
            "mcp_summary": {
                "total_calls": 10,
                "unique_tools": 3,
                "most_called": "mcp__zen__chat (5 calls)",
            },
            "server_sessions": {},
            "smells": [],
            "zombie_tools": {},
            "data_quality": {
                "accuracy_level": "exact",
                "token_source": "native",
                "confidence": 1.0,
            },
        }

        session_path = Path("/tmp/test-session.json")
        output = generate_ai_prompt_markdown(session_data, session_path)

        # Verify key sections exist
        assert "# MCP Session Analysis Request" in output
        assert "## Session Summary" in output
        assert "**Platform**: claude-code" in output
        assert "## Token Usage" in output
        assert "**Total Tokens**: 8,500" in output
        assert "## Cost" in output
        assert "$0.1500" in output
        assert "## MCP Tool Usage" in output
        assert "## Suggested Analysis Questions" in output

    def test_generate_markdown_with_smells(self) -> None:
        """Test markdown generation includes smells."""
        from mcp_audit.cli import generate_ai_prompt_markdown

        session_data = {
            "session": {"platform": "claude-code"},
            "token_usage": {"total_tokens": 1000},
            "cost_estimate_usd": 0.01,
            "mcp_summary": {},
            "server_sessions": {},
            "smells": [
                {
                    "pattern": "CHATTY",
                    "severity": "warning",
                    "tool": "mcp__zen__chat",
                    "description": "Called 25 times",
                    "evidence": {"call_count": 25, "threshold": 20},
                }
            ],
            "zombie_tools": {},
        }

        session_path = Path("/tmp/test-session.json")
        output = generate_ai_prompt_markdown(session_data, session_path)

        assert "## Detected Efficiency Issues" in output
        assert "CHATTY" in output
        assert "Called 25 times" in output

    def test_generate_json_basic(self) -> None:
        """Test JSON generation with basic session data."""
        from mcp_audit.cli import generate_ai_prompt_json

        session_data = {
            "session": {
                "platform": "codex-cli",
                "model": "gpt-5.1-codex",
                "duration_seconds": 180,
                "project": "my-project",
            },
            "token_usage": {"total_tokens": 5000},
            "cost_estimate_usd": 0.05,
            "mcp_summary": {"total_calls": 5},
            "server_sessions": {},
            "smells": [],
            "zombie_tools": {},
            "data_quality": {"accuracy_level": "estimated"},
        }

        session_path = Path("/tmp/test-session.json")
        output = generate_ai_prompt_json(session_data, session_path)

        # Parse and verify
        parsed = json.loads(output)
        assert "analysis_request" in parsed
        assert "session_summary" in parsed
        assert parsed["session_summary"]["platform"] == "codex-cli"
        assert "token_usage" in parsed
        assert "smells" in parsed
        assert "top_tools" in parsed


class TestFormatDuration:
    """Tests for duration formatting."""

    def test_seconds(self) -> None:
        """Test formatting duration in seconds."""
        from mcp_audit.cli import _format_duration

        assert _format_duration(45) == "45s"

    def test_minutes(self) -> None:
        """Test formatting duration in minutes."""
        from mcp_audit.cli import _format_duration

        assert _format_duration(125) == "2m 5s"

    def test_hours(self) -> None:
        """Test formatting duration in hours."""
        from mcp_audit.cli import _format_duration

        assert _format_duration(3725) == "1h 2m"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
