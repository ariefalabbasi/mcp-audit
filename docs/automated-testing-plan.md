# Automated Testing Plan for mcp-audit

**Last Updated**: 2025-12-06
**Status**: Implementation Ready

---

## Overview

This document outlines an automated testing workflow that enables Claude Code to test mcp-audit changes across all three CLI platforms (Claude Code, Codex CLI, Gemini CLI) without requiring manual intervention or large backlog tasks.

**Goals**:
1. Test specific adapter changes or full mcp-audit functionality
2. Run real CLI sessions with real API calls ("testing in production")
3. Capture and store TUI snapshots, session files, and comparison data
4. Enable rapid iteration without PyPI releases
5. Provide analyzable, comparable outputs across test runs

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Test Harness (scripts/test-harness.sh)          │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                │
│  │ Claude Code  │   │  Gemini CLI  │   │  Codex CLI   │                │
│  │  Headless    │   │  Headless    │   │   Headless   │                │
│  │  (-p flag)   │   │  (positional)│   │  (exec cmd)  │                │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘                │
│         │                  │                  │                         │
│         ▼                  ▼                  ▼                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                     mcp-audit (editable install)                  │  │
│  │  - Collects session from each CLI                                 │  │
│  │  - Runs TUI in tmux for snapshot capture                          │  │
│  │  - Saves session files to ~/.mcp-audit/sessions/                  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                  │                                      │
│                                  ▼                                      │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │              Test Artifacts (tests/artifacts/<run-id>/)           │  │
│  │  - TUI snapshots (tmux capture-pane)                              │  │
│  │  - CLI JSON outputs                                               │  │
│  │  - mcp-audit session files (copied)                               │  │
│  │  - Comparison reports                                             │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Quick Start Commands

### For Claude Code to Run

```bash
# === Setup (run once per session) ===
cd /Users/nathanschram/claude-code-tools/lba/apps/devtools/mcp-audit/main
source .venv/bin/activate
pip install -e ".[dev]"

# === Quick Test: Single Platform ===
./scripts/test-harness.sh --platform claude-code --quick
./scripts/test-harness.sh --platform gemini-cli --quick
./scripts/test-harness.sh --platform codex-cli --quick

# === Full Test: All Platforms ===
./scripts/test-harness.sh --all

# === Targeted Test: Specific Component ===
./scripts/test-harness.sh --platform claude-code --test token-tracking
./scripts/test-harness.sh --platform gemini-cli --test mcp-tools
./scripts/test-harness.sh --platform codex-cli --test tui-display

# === Compare Latest Results ===
./scripts/compare-results.sh --latest
```

---

## Test Harness Design

### File: `scripts/test-harness.sh`

```bash
#!/bin/bash
# mcp-audit Test Harness
# Runs automated tests across CLI platforms with real API calls

set -euo pipefail

# === Configuration ===
MCP_AUDIT_DIR="/Users/nathanschram/claude-code-tools/lba/apps/devtools/mcp-audit/main"
ARTIFACTS_DIR="$MCP_AUDIT_DIR/tests/artifacts"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
RUN_ID="run-$TIMESTAMP"

# === Test Prompts (designed to trigger different features) ===
declare -A TEST_PROMPTS
TEST_PROMPTS[quick]="What is 2 + 2? Reply with just the number."
TEST_PROMPTS[token-tracking]="List the Python files in src/mcp_audit/ and show the first 5 lines of cli.py"
TEST_PROMPTS[mcp-tools]="Search the web for 'MCP protocol Anthropic' and summarize in one sentence"
TEST_PROMPTS[multi-tool]="Find all files containing 'DisplaySnapshot' and show the class definition"
TEST_PROMPTS[cache-test]="Read pyproject.toml and tell me the Python version requirement"

# === Parse Arguments ===
PLATFORM=""
TEST_TYPE="quick"
RUN_ALL=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --platform) PLATFORM="$2"; shift 2 ;;
        --test) TEST_TYPE="$2"; shift 2 ;;
        --all) RUN_ALL=true; shift ;;
        --quick) TEST_TYPE="quick"; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# === Setup Artifact Directory ===
mkdir -p "$ARTIFACTS_DIR/$RUN_ID"
echo "Run ID: $RUN_ID"
echo "Artifacts: $ARTIFACTS_DIR/$RUN_ID"

# === Logging ===
log() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$ARTIFACTS_DIR/$RUN_ID/test.log"; }

# === Run Claude Code Test ===
run_claude_code_test() {
    local prompt="${TEST_PROMPTS[$TEST_TYPE]}"
    log "Testing Claude Code with prompt type: $TEST_TYPE"

    # Run headless from /tmp to avoid session conflicts
    cd /tmp

    # Execute headless Claude Code
    local output_file="$ARTIFACTS_DIR/$RUN_ID/claude-code-output.json"
    claude -p "$prompt" \
        --output-format json \
        -C "$MCP_AUDIT_DIR" \
        > "$output_file" 2>&1 || true

    log "Claude Code output saved to: $output_file"

    # Return to mcp-audit dir
    cd "$MCP_AUDIT_DIR"

    # Start mcp-audit TUI in tmux and capture
    capture_tui "claude-code"

    # Process with mcp-audit
    source .venv/bin/activate
    mcp-audit collect --platform claude-code --batch --latest \
        > "$ARTIFACTS_DIR/$RUN_ID/claude-code-collect.log" 2>&1 || true

    # Copy session file
    copy_latest_session "claude-code"
}

# === Run Gemini CLI Test ===
run_gemini_cli_test() {
    local prompt="${TEST_PROMPTS[$TEST_TYPE]}"
    log "Testing Gemini CLI with prompt type: $TEST_TYPE"

    cd "$MCP_AUDIT_DIR"
    source .venv/bin/activate

    # Execute headless Gemini CLI
    local output_file="$ARTIFACTS_DIR/$RUN_ID/gemini-cli-output.json"
    gemini "$prompt" --yolo --output-format json \
        > "$output_file" 2>&1 || true

    log "Gemini CLI output saved to: $output_file"

    # Capture TUI
    capture_tui "gemini-cli"

    # Process with mcp-audit
    mcp-audit collect --platform gemini-cli --batch --latest \
        > "$ARTIFACTS_DIR/$RUN_ID/gemini-cli-collect.log" 2>&1 || true

    # Copy session file
    copy_latest_session "gemini-cli"
}

# === Run Codex CLI Test ===
run_codex_cli_test() {
    local prompt="${TEST_PROMPTS[$TEST_TYPE]}"
    log "Testing Codex CLI with prompt type: $TEST_TYPE"

    cd "$MCP_AUDIT_DIR"
    source .venv/bin/activate

    # Execute headless Codex CLI
    local output_file="$ARTIFACTS_DIR/$RUN_ID/codex-cli-output.jsonl"
    codex exec "$prompt" --json \
        > "$output_file" 2>&1 || true

    log "Codex CLI output saved to: $output_file"

    # Capture TUI
    capture_tui "codex-cli"

    # Process with mcp-audit
    mcp-audit collect --platform codex-cli --batch --latest \
        > "$ARTIFACTS_DIR/$RUN_ID/codex-cli-collect.log" 2>&1 || true

    # Copy session file
    copy_latest_session "codex-cli"
}

# === TUI Capture Function ===
capture_tui() {
    local platform="$1"
    local session_name="mcp-test-$platform"

    log "Capturing TUI for $platform"

    # Kill any existing session
    tmux kill-session -t "$session_name" 2>/dev/null || true

    # Start mcp-audit TUI in tmux
    tmux new-session -d -s "$session_name" -x 120 -y 40 \
        "cd $MCP_AUDIT_DIR && source .venv/bin/activate && mcp-audit collect --platform $platform --batch --latest 2>&1"

    # Wait for TUI to render
    sleep 3

    # Capture TUI snapshots
    for i in 1 2 3; do
        tmux capture-pane -t "$session_name" -p \
            > "$ARTIFACTS_DIR/$RUN_ID/$platform-tui-snapshot-$i.txt" 2>/dev/null || true
        sleep 1
    done

    # Final capture
    tmux capture-pane -t "$session_name" -p \
        > "$ARTIFACTS_DIR/$RUN_ID/$platform-tui-final.txt" 2>/dev/null || true

    # Kill session
    tmux kill-session -t "$session_name" 2>/dev/null || true

    log "TUI snapshots saved for $platform"
}

# === Copy Latest Session File ===
copy_latest_session() {
    local platform="$1"
    local session_base="$HOME/.mcp-audit/sessions/$platform"

    # Find the latest session file
    local latest_session=$(find "$session_base" -name "*.json" -type f 2>/dev/null | sort -r | head -1)

    if [[ -n "$latest_session" ]]; then
        cp "$latest_session" "$ARTIFACTS_DIR/$RUN_ID/$platform-session.json"
        log "Session file copied: $platform-session.json"
    else
        log "WARNING: No session file found for $platform"
    fi
}

# === Main Execution ===
log "=== mcp-audit Test Harness ==="
log "Test type: $TEST_TYPE"

if $RUN_ALL; then
    log "Running all platform tests..."
    run_claude_code_test
    run_gemini_cli_test
    run_codex_cli_test
elif [[ -n "$PLATFORM" ]]; then
    case $PLATFORM in
        claude-code) run_claude_code_test ;;
        gemini-cli) run_gemini_cli_test ;;
        codex-cli) run_codex_cli_test ;;
        *) log "Unknown platform: $PLATFORM"; exit 1 ;;
    esac
else
    log "No platform specified. Use --platform or --all"
    exit 1
fi

# === Generate Summary ===
log "=== Test Complete ==="
log "Artifacts saved to: $ARTIFACTS_DIR/$RUN_ID"

# List generated files
echo ""
echo "Generated Files:"
ls -la "$ARTIFACTS_DIR/$RUN_ID/"

echo ""
echo "To compare with previous runs:"
echo "  ./scripts/compare-results.sh --run $RUN_ID"
```

---

## Comparison Script

### File: `scripts/compare-results.sh`

```bash
#!/bin/bash
# Compare test results across runs or platforms

set -euo pipefail

MCP_AUDIT_DIR="/Users/nathanschram/claude-code-tools/lba/apps/devtools/mcp-audit/main"
ARTIFACTS_DIR="$MCP_AUDIT_DIR/tests/artifacts"

# Parse arguments
RUN_ID=""
COMPARE_TO=""
LATEST=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --run) RUN_ID="$2"; shift 2 ;;
        --compare-to) COMPARE_TO="$2"; shift 2 ;;
        --latest) LATEST=true; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# Find latest run if requested
if $LATEST; then
    RUN_ID=$(ls -1 "$ARTIFACTS_DIR" | grep "^run-" | sort -r | head -1)
    echo "Using latest run: $RUN_ID"
fi

if [[ -z "$RUN_ID" ]]; then
    echo "Available runs:"
    ls -1 "$ARTIFACTS_DIR" | grep "^run-" | sort -r | head -10
    exit 0
fi

RUN_DIR="$ARTIFACTS_DIR/$RUN_ID"

echo "=== Test Run Analysis: $RUN_ID ==="
echo ""

# Analyze each platform
for platform in claude-code gemini-cli codex-cli; do
    session_file="$RUN_DIR/$platform-session.json"
    tui_file="$RUN_DIR/$platform-tui-final.txt"

    if [[ -f "$session_file" ]]; then
        echo "--- $platform ---"

        # Extract key metrics from session file
        echo "Session Metrics:"
        jq -r '
            "  Input tokens:     " + (.token_usage.input_tokens // 0 | tostring) + "\n" +
            "  Output tokens:    " + (.token_usage.output_tokens // 0 | tostring) + "\n" +
            "  Cache read:       " + (.token_usage.cache_read_tokens // 0 | tostring) + "\n" +
            "  Total tokens:     " + (.token_usage.total_tokens // 0 | tostring) + "\n" +
            "  Cost estimate:    $" + (.cost_estimate // 0 | tostring) + "\n" +
            "  Model:            " + (.model // "unknown") + "\n" +
            "  MCP calls:        " + (.mcp_tool_calls.total_calls // 0 | tostring) + "\n" +
            "  Duration:         " + (.duration_seconds // 0 | tostring) + "s"
        ' "$session_file" 2>/dev/null || echo "  (Could not parse session file)"

        # Check TUI capture
        if [[ -f "$tui_file" ]]; then
            echo ""
            echo "TUI Verification:"
            grep -q "Token Usage" "$tui_file" && echo "  [✓] Token Usage panel" || echo "  [✗] Token Usage panel missing"
            grep -q "MCP Servers" "$tui_file" && echo "  [✓] MCP Servers panel" || echo "  [✗] MCP Servers panel missing"
            grep -q "Recent Activity" "$tui_file" && echo "  [✓] Activity panel" || echo "  [✗] Activity panel missing"
        fi

        echo ""
    fi
done

# Cross-platform comparison
echo "=== Cross-Platform Comparison ==="
for platform in claude-code gemini-cli codex-cli; do
    session_file="$RUN_DIR/$platform-session.json"
    if [[ -f "$session_file" ]]; then
        total=$(jq -r '.token_usage.total_tokens // 0' "$session_file" 2>/dev/null)
        cost=$(jq -r '.cost_estimate // 0' "$session_file" 2>/dev/null)
        printf "%-15s %10s tokens  \$%.4f\n" "$platform:" "$total" "$cost"
    fi
done
```

---

## Test Types and Prompts

| Test Type | Purpose | Expected Tools | Validates |
|-----------|---------|----------------|-----------|
| `quick` | Fast smoke test | None | Token tracking, model detection |
| `token-tracking` | Token counting accuracy | Glob, Read | Input/output/cache tokens |
| `mcp-tools` | MCP server detection | brave-search/jina | MCP hierarchy, tool attribution |
| `multi-tool` | Multiple tool calls | Grep, Read | Tool aggregation, activity feed |
| `cache-test` | Cache efficiency | Read | Cache read/created tokens |

---

## Artifact Structure

Each test run creates:

```
tests/artifacts/run-YYYYMMDD-HHMMSS/
├── test.log                      # Execution log
├── claude-code-output.json       # Raw CLI JSON output
├── claude-code-collect.log       # mcp-audit collect output
├── claude-code-session.json      # mcp-audit session file (copied)
├── claude-code-tui-snapshot-1.txt
├── claude-code-tui-snapshot-2.txt
├── claude-code-tui-snapshot-3.txt
├── claude-code-tui-final.txt     # Final TUI state
├── gemini-cli-output.json
├── gemini-cli-collect.log
├── gemini-cli-session.json
├── gemini-cli-tui-*.txt
├── codex-cli-output.jsonl
├── codex-cli-collect.log
├── codex-cli-session.json
└── codex-cli-tui-*.txt
```

---

## Integration with Claude Code Workflow

### Inline Test Commands

Claude Code can run these commands directly during development:

```bash
# Quick validation after code changes
cd /Users/nathanschram/claude-code-tools/lba/apps/devtools/mcp-audit/main
source .venv/bin/activate && pip install -e ".[dev]"
./scripts/test-harness.sh --platform claude-code --quick

# Full validation before commit
./scripts/test-harness.sh --all --test token-tracking
./scripts/compare-results.sh --latest

# Targeted testing for specific bug
./scripts/test-harness.sh --platform gemini-cli --test mcp-tools
cat tests/artifacts/$(ls tests/artifacts | grep run- | sort -r | head -1)/gemini-cli-session.json | jq '.mcp_summary'
```

### pytest Integration

```python
# tests/test_live_cli.py (optional - for CI validation)
import subprocess
import json
from pathlib import Path

def test_harness_claude_code():
    """Run live Claude Code test (requires API key)"""
    result = subprocess.run(
        ["./scripts/test-harness.sh", "--platform", "claude-code", "--quick"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    assert result.returncode == 0

    # Find latest artifact
    artifacts = sorted(Path("tests/artifacts").glob("run-*"), reverse=True)
    assert len(artifacts) > 0

    session_file = artifacts[0] / "claude-code-session.json"
    if session_file.exists():
        data = json.loads(session_file.read_text())
        assert data.get("platform") == "claude-code"
        assert data.get("token_usage", {}).get("total_tokens", 0) > 0
```

---

## TUI Verification Checklist

When analyzing TUI captures, verify:

| Element | grep Pattern | Notes |
|---------|--------------|-------|
| Header | `mcp-audit` | Version and session type |
| Token panel | `Token Usage` | All token counts |
| Cost display | `Cost w/` | Cost with/without cache |
| MCP panel | `MCP Servers` | Server hierarchy |
| Activity feed | `Recent Activity` | Tool call history |
| Footer | `Press Ctrl+C` | Session controls |
| Model | Platform-specific | Claude Opus 4.5, Gemini 2.5, gpt-5.1 |

---

## Troubleshooting

### Claude Code Session Conflicts

Run from `/tmp` with `-C` flag:
```bash
cd /tmp
claude -p "test" --output-format json -C /path/to/mcp-audit
```

### Gemini CLI Auth Issues

Verify OAuth:
```bash
ls -la ~/.gemini/oauth_creds.json
gemini "hello" --output-format json  # Should not prompt for auth
```

### Codex CLI API Key

Verify authentication:
```bash
cat ~/.codex/auth.json | jq '.api_key'
codex exec "test" --json
```

### tmux Capture Failures

Check tmux is available and session exists:
```bash
tmux list-sessions
tmux capture-pane -t mcp-test-claude-code -p
```

---

## Session File Locations Reference

| Platform | Native Sessions | mcp-audit Sessions |
|----------|-----------------|-------------------|
| Claude Code | `~/.claude/projects/-Users-nathanschram-*/*.jsonl` | `~/.mcp-audit/sessions/claude-code/<date>/*.json` |
| Gemini CLI | `~/.gemini/tmp/<hash>/chats/session-*.json` | `~/.mcp-audit/sessions/gemini-cli/<date>/*.json` |
| Codex CLI | `~/.codex/sessions/YYYY/MM/DD/*.jsonl` | `~/.mcp-audit/sessions/codex-cli/<date>/*.json` |

---

## Future Enhancements

1. **Baseline Comparison**: Store "golden" test outputs for regression detection
2. **CI Integration**: GitHub Actions workflow for automated testing on PR
3. **Cost Tracking**: Track API costs per test run for budget management
4. **Parallel Execution**: Run platform tests concurrently
5. **HTML Reports**: Generate rich comparison reports

---

## Related Documentation

- [Local Testing Guide](local-testing-guide.md) - Detailed CLI reference
- [Platform Token Capabilities](PLATFORM-TOKEN-CAPABILITIES.md) - What each platform supports
- [Architecture](architecture.md) - System design
- [Data Contract](data-contract.md) - Session file format
