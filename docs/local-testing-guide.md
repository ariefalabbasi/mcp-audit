# Local Testing Guide for Claude Code

> **Quick Start**: For automated testing, use the test harness scripts:
> ```bash
> ./scripts/test-harness.sh --platform claude-code --quick  # Single platform
> ./scripts/test-harness.sh --all                           # All platforms
> ./scripts/compare-results.sh --latest                     # Analyze results
> ```
> See `docs/automated-testing-plan.md` for full automation documentation.

This guide provides **detailed reference** for headless CLI execution and manual testing workflows.

## Overview

When developing mcp-audit, you can validate adapter changes by:
1. Installing mcp-audit from local source (editable install)
2. Running Claude Code, Gemini CLI, or Codex CLI in **headless/non-interactive mode**
3. Processing the generated session files with mcp-audit
4. Verifying token tracking, MCP tool detection, and cost calculations

This workflow enables rapid iteration without PyPI releases.

---

## Prerequisites

### Required Installations

| Tool | Version | Installation |
|------|---------|--------------|
| Claude Code CLI | 2.0.59+ | `npm install -g @anthropic/claude-code` |
| Gemini CLI | 0.19.1+ | `npm install -g @anthropic/gemini-cli` |
| Codex CLI | 0.64.0+ | `npm install -g @openai/codex` |
| Python | 3.10+ | System or pyenv |

### Verify Installations

```bash
# Check versions
claude --version   # Should show 2.0.59 or higher
gemini --version   # Should show 0.19.1 or higher
codex --version    # Should show codex-cli 0.64.0 or higher
python3 --version  # Should show 3.10+
```

### Authentication

All CLIs must be authenticated before headless execution:

```bash
# Claude Code CLI - Anthropic API key or Claude subscription
# Auth stored via: claude setup-token

# Gemini CLI - OAuth personal (already configured)
# Auth stored in: ~/.gemini/oauth_creds.json

# Codex CLI - OpenAI API key
# Auth stored in: ~/.codex/auth.json
```

---

## Quick Start: Editable Install

Install mcp-audit from local source for development testing:

```bash
cd /Users/nathanschram/claude-code-tools/lba/apps/devtools/mcp-audit/main

# Create/activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Verify installation
mcp-audit --version
```

Alternative: Use PYTHONPATH without installing:

```bash
cd /Users/nathanschram/claude-code-tools/lba/apps/devtools/mcp-audit/main
PYTHONPATH=src python -m mcp_audit --version
```

---

## Claude Code CLI Headless Testing

Claude Code can run **itself** in headless mode to test mcp-audit's Claude Code adapter. This is useful for testing the `claude_code_adapter.py` without user interaction.

### Basic Headless Execution

Use the `-p/--print` flag for non-interactive mode:

```bash
# Simple headless prompt (different directory to avoid conflicts)
cd /tmp
claude -p "What is 2 + 2?" --output-format json

# From a specific project directory
claude -p "List the Python files in this directory" \
  --output-format json \
  -C /Users/nathanschram/claude-code-tools/lba/apps/devtools/mcp-audit/main
```

### Full Test: MCP Tools + Token Tracking

Generate a session with MCP tool calls for comprehensive testing:

```bash
# Run headless with MCP tools from a test directory
cd /tmp

# This triggers MCP tools (brave-search, jina, etc.)
claude -p "Search the web for 'MCP protocol specification' and summarize" \
  --output-format json \
  --permission-mode acceptEdits \
  -C /Users/nathanschram/claude-code-tools/lba/apps/devtools/mcp-audit/main \
  > /tmp/claude-test-output.json

# Check the JSON output
cat /tmp/claude-test-output.json | jq '.total_cost_usd, .num_turns, .session_id'
```

### Testing from Different Directory

**IMPORTANT**: To test mcp-audit adapter changes, run Claude Code headlessly from a **different directory** to avoid conflicts with the current session:

```bash
# Option 1: Use -C flag to set working directory
cd /tmp
claude -p "Explain the mcp-audit architecture" \
  --output-format json \
  -C /Users/nathanschram/claude-code-tools/lba/apps/devtools/mcp-audit/main

# Option 2: Run from another project entirely
cd /Users/nathanschram/claude-code-tools/lba/marketing/brand-copilot/main
claude -p "What Python version is installed?" --output-format json
```

### Session File Location

Claude Code stores sessions per-project using path-based directory names:

```
~/.claude/projects/-Users-nathanschram-<path-with-dashes>/*.jsonl
```

**mcp-audit project sessions**:
```bash
# List mcp-audit sessions
ls -la ~/.claude/projects/-Users-nathanschram-claude-code-tools-lba-apps-devtools-mcp-audit-main/*.jsonl | tail -10
```

### Process Session with mcp-audit

```bash
cd /Users/nathanschram/claude-code-tools/lba/apps/devtools/mcp-audit/main
source .venv/bin/activate

# Process the latest Claude Code session
mcp-audit collect --platform claude-code --batch --latest

# Or specify a session file directly
mcp-audit collect --platform claude-code --batch \
  --session-file ~/.claude/projects/-Users-nathanschram-claude-code-tools-lba-apps-devtools-mcp-audit-main/<session-id>.jsonl
```

### Claude Code CLI Headless Flags Reference

| Flag | Purpose | Example |
|------|---------|---------|
| `-p, --print` | Run in non-interactive mode | `claude -p "query"` |
| `--output-format` | Output format: text, json, stream-json | `--output-format json` |
| `-C` | Set working directory | `-C /path/to/project` |
| `--permission-mode` | Permission handling: acceptEdits, bypassPermissions, default | `--permission-mode acceptEdits` |
| `--allowedTools` | Whitelist specific tools | `--allowedTools "Bash,Read,mcp__jina"` |
| `--disallowedTools` | Blacklist specific tools | `--disallowedTools "Write"` |
| `-c, --continue` | Continue most recent conversation | `claude -c -p "follow up"` |
| `-r, --resume` | Resume by session ID | `claude -r <session-id> -p "continue"` |
| `--model` | Specify model (sonnet, opus, etc.) | `--model sonnet` |
| `--append-system-prompt` | Add custom instructions | `--append-system-prompt "Be concise"` |

### Multi-Turn Headless Sessions

```bash
# Start a session and capture the session ID
result=$(claude -p "Analyze the mcp-audit codebase structure" \
  --output-format json \
  -C /Users/nathanschram/claude-code-tools/lba/apps/devtools/mcp-audit/main)

session_id=$(echo "$result" | jq -r '.session_id')
echo "Session ID: $session_id"

# Continue the session with follow-up prompts
claude -p "Now explain the adapter pattern used" \
  --resume "$session_id" \
  --output-format json

# Or continue the most recent session
claude -p "What MCP servers are configured?" \
  --continue \
  --output-format json
```

### JSON Output Schema

The `--output-format json` returns:

```json
{
  "type": "result",
  "subtype": "success",
  "total_cost_usd": 0.003,
  "is_error": false,
  "duration_ms": 1234,
  "duration_api_ms": 800,
  "num_turns": 6,
  "result": "The response text here...",
  "session_id": "abc123-def456-..."
}
```

---

## Gemini CLI Headless Testing

### Basic Headless Execution

Run a simple prompt to generate session data:

```bash
# From any project directory
cd /Users/nathanschram/claude-code-tools/lba/apps/devtools/mcp-audit/main

# Simple headless prompt (creates session file)
gemini "What version of Python is installed?" --output-format json

# With auto-approve for tool usage
gemini "List the files in this directory" --yolo --output-format json
```

### Full Test: MCP Tools + Token Tracking

Generate a session with MCP tool calls for comprehensive testing:

```bash
# Run headless with MCP tools (uses configured servers)
cd /Users/nathanschram/claude-code-tools/lba/apps/devtools/mcp-audit/main

# This prompt triggers web search (MCP tool)
gemini "Search the web for 'MCP protocol specification' and summarize the first result" \
  --yolo \
  --output-format json \
  > /tmp/gemini-test-output.json

# Check the JSON output for stats
cat /tmp/gemini-test-output.json | jq '.stats'
```

### Session File Location

Gemini CLI stores sessions per-project using a SHA256 hash of the working directory:

```
~/.gemini/tmp/<project_hash>/chats/session-*.json
```

**mcp-audit project hash**: `76c62a47a1287071d52c32065e26834b212bf4df1e1551d71ebc39403d65d37b`

```bash
# List mcp-audit sessions
ls -la ~/.gemini/tmp/76c62a47a1287071d52c32065e26834b212bf4df1e1551d71ebc39403d65d37b/chats/
```

### Process Session with mcp-audit

```bash
cd /Users/nathanschram/claude-code-tools/lba/apps/devtools/mcp-audit/main
source .venv/bin/activate

# Process the latest Gemini session (auto-detects project hash from CWD)
mcp-audit collect --platform gemini-cli --batch --latest

# Or specify a session file directly
mcp-audit collect --platform gemini-cli --batch \
  --session-file ~/.gemini/tmp/76c62a47a1287071d52c32065e26834b212bf4df1e1551d71ebc39403d65d37b/chats/session-2025-12-05T04-48-cb0c81ca.json
```

### Gemini CLI Headless Flags Reference

| Flag | Purpose | Example |
|------|---------|---------|
| `"prompt"` | Positional prompt (preferred) | `gemini "What is Python?"` |
| `-p, --prompt` | Prompt flag (deprecated) | `gemini -p "What is Python?"` |
| `-o, --output-format` | Output format: text, json, stream-json | `--output-format json` |
| `-y, --yolo` | Auto-approve all tool actions | `gemini "..." --yolo` |
| `--approval-mode` | Control approval: default, auto_edit, yolo | `--approval-mode yolo` |
| `-m, --model` | Specify model | `-m gemini-2.5-flash` |

---

## Codex CLI Headless Testing

### Basic Headless Execution

Use `codex exec` for non-interactive mode:

```bash
# Simple headless prompt
codex exec "What version of Python is installed on this system?"

# With JSON output for structured data
codex exec "List the Python files in the current directory" --json
```

### Full Test: MCP Tools + Token Tracking

```bash
cd /Users/nathanschram/claude-code-tools/lba/apps/devtools/mcp-audit/main

# Run with MCP tools (uses configured servers in ~/.codex/config.toml)
# This triggers brave-search-mcp
codex exec "Search the web for 'OpenAI Codex CLI documentation' and summarize" \
  --json \
  > /tmp/codex-test-output.jsonl

# Check output
cat /tmp/codex-test-output.jsonl | head -20
```

### Session File Location

Codex CLI stores sessions by date:

```
~/.codex/sessions/YYYY/MM/DD/*.jsonl
```

```bash
# List recent sessions
ls -la ~/.codex/sessions/2025/12/

# Find sessions from today
find ~/.codex/sessions/2025/12 -name "*.jsonl" -mtime -1
```

### Process Session with mcp-audit

```bash
cd /Users/nathanschram/claude-code-tools/lba/apps/devtools/mcp-audit/main
source .venv/bin/activate

# Process the latest Codex session
mcp-audit collect --platform codex-cli --batch --latest

# Or specify a session file directly
mcp-audit collect --platform codex-cli --batch \
  --session-file ~/.codex/sessions/2025/12/04/rollout-2025-12-04T16-33-30-019ae7d9-eca0-7cd2-bca1-a544afaa55ef.jsonl
```

### Codex CLI Headless Flags Reference

| Flag | Purpose | Example |
|------|---------|---------|
| `exec` | Non-interactive subcommand | `codex exec "prompt"` |
| `--json` | JSONL output to stdout | `codex exec "..." --json` |
| `-m, --model` | Specify model | `-m gpt-5.1` |
| `-s, --sandbox` | Sandbox mode: read-only, workspace-write, danger-full-access | `-s workspace-write` |
| `--full-auto` | Convenience for auto execution | `codex exec "..." --full-auto` |
| `-C, --cd` | Set working directory | `--cd /path/to/project` |

---

## Complete Test Workflow for Claude Code

### Step 1: Make Code Changes

Edit adapter files in `src/mcp_audit/`:
- `claude_code_adapter.py` - Claude Code session parsing
- `gemini_cli_adapter.py` - Gemini CLI parsing
- `codex_cli_adapter.py` - Codex CLI parsing
- `base_tracker.py` - Shared tracking logic

### Step 2: Install Local Changes

```bash
cd /Users/nathanschram/claude-code-tools/lba/apps/devtools/mcp-audit/main
source .venv/bin/activate
pip install -e ".[dev]"
```

### Step 3: Generate Test Sessions

**Claude Code CLI Test** (run from /tmp to avoid conflicts):
```bash
cd /tmp

# Simple test (token tracking)
claude -p "Explain what mcp-audit does in one sentence" \
  --output-format json \
  -C /Users/nathanschram/claude-code-tools/lba/apps/devtools/mcp-audit/main

# MCP tool test
claude -p "Search the web for 'Claude MCP protocol' and summarize" \
  --output-format json \
  --permission-mode acceptEdits \
  -C /Users/nathanschram/claude-code-tools/lba/apps/devtools/mcp-audit/main
```

**Gemini CLI Test**:
```bash
cd /Users/nathanschram/claude-code-tools/lba/apps/devtools/mcp-audit/main

# Simple test (token tracking)
gemini "Explain what mcp-audit does in one sentence" --output-format json

# MCP tool test (if jina/brave MCP servers configured)
gemini "Search the web for 'Claude MCP protocol' and list 3 key features" \
  --yolo --output-format json
```

**Codex CLI Test**:
```bash
cd /Users/nathanschram/claude-code-tools/lba/apps/devtools/mcp-audit/main

# Simple test
codex exec "What is the purpose of mcp-audit?"

# MCP tool test
codex exec "Use brave-search to find 'OpenAI function calling' and summarize" --json
```

### Step 4: Process and Validate

```bash
cd /Users/nathanschram/claude-code-tools/lba/apps/devtools/mcp-audit/main
source .venv/bin/activate

# Process Claude Code session
mcp-audit collect --platform claude-code --batch --latest

# Process Gemini session
mcp-audit collect --platform gemini-cli --batch --latest

# Process Codex session
mcp-audit collect --platform codex-cli --batch --latest

# Check the generated session logs
ls -la ~/.mcp-audit/sessions/
cat ~/.mcp-audit/sessions/claude-code/*.json | jq '.token_usage'
cat ~/.mcp-audit/sessions/gemini-cli/*.json | jq '.token_usage'
cat ~/.mcp-audit/sessions/codex-cli/*.json | jq '.token_usage'
```

### Step 5: Verify Key Metrics

Check these fields in session logs:

| Field | Expected | Notes |
|-------|----------|-------|
| `schema_version` | `"1.6.0"` | Current schema version |
| `token_usage.input_tokens` | > 0 | Should match CLI output |
| `token_usage.output_tokens` | > 0 | Model response tokens |
| `token_usage.cache_read_tokens` | >= 0 | Cache hits (may be 0) |
| `model` | Detected correctly | `claude-sonnet-4-*`, `gemini-2.5-pro`, or `gpt-5.1-codex-max` |
| `models_used` | Array | v0.6.0: List of models used in session |
| `model_usage` | Object or null | v0.6.0: Per-model breakdown (if multi-model) |
| `static_cost` | Object or null | v0.6.0: MCP schema context tax |
| `tool_calls` | Array | MCP tools with `mcp__` prefix |
| `cost_usd` | Calculated | Based on token counts |
| `data_quality.accuracy_level` | Platform-specific | See table below |
| `data_quality.pricing_source` | String | `litellm_api`, `cache`, or `toml_fallback` |

### Platform Accuracy Levels

Each platform has different token tracking capabilities:

| Platform | `accuracy_level` | Token Source | Expected Variance |
|----------|-----------------|--------------|-------------------|
| Claude Code | `exact` | Native API tokens | < 5% vs native |
| Gemini CLI | `estimated` | tiktoken approximation | 10-20% vs native |
| Codex CLI | `estimated` | tiktoken (o200k_base) | ~99% vs native session totals |

---

## Macbook Configuration Reference

### Claude Code CLI

| Item | Location |
|------|----------|
| Config | `~/.claude/settings.json` |
| Global CLAUDE.md | `~/.claude/CLAUDE.md` |
| Sessions | `~/.claude/projects/-Users-nathanschram-<path>/*.jsonl` |
| History | `~/.claude/history.jsonl` |
| Version | 2.0.59 |

### Gemini CLI

| Item | Location |
|------|----------|
| Config | `~/.gemini/settings.json` |
| Auth | `~/.gemini/oauth_creds.json` |
| Sessions | `~/.gemini/tmp/<project_hash>/chats/session-*.json` |
| Version | 0.19.1 |

### Codex CLI

| Item | Location |
|------|----------|
| Config | `~/.codex/config.toml` |
| Auth | `~/.codex/auth.json` |
| Sessions | `~/.codex/sessions/YYYY/MM/DD/*.jsonl` |
| Model | `gpt-5.1-codex-max` (reasoning_effort: high) |
| Version | 0.64.0 |

### MCP Servers (Codex CLI)

Configured in `~/.codex/config.toml`:

| Server | Purpose |
|--------|---------|
| brave-search-mcp | Web search |
| context7-mcp | Library documentation |
| fs-mcp | File system operations |
| github-mcp | GitHub API |
| mdfmt-mcp | Markdown formatting |
| rg-mcp | Ripgrep search |
| secrets-mcp | Secrets management |
| testrun-mcp | Test execution |

---

## Troubleshooting

### Claude Code CLI: Session conflicts

When testing from the same directory as your current Claude Code session, the headless instance may conflict. Always run from a different directory:

```bash
# WRONG: Running from the same mcp-audit directory
cd /Users/nathanschram/claude-code-tools/lba/apps/devtools/mcp-audit/main
claude -p "Test" --output-format json  # May conflict with current session

# CORRECT: Run from /tmp and use -C flag
cd /tmp
claude -p "Test" --output-format json \
  -C /Users/nathanschram/claude-code-tools/lba/apps/devtools/mcp-audit/main
```

### Claude Code CLI: Permission errors

Use `--permission-mode` to control tool approval:

```bash
# Accept all file edits automatically
claude -p "Edit README.md" --permission-mode acceptEdits --output-format json

# Bypass all permissions (use with caution!)
claude -p "Run tests" --permission-mode bypassPermissions --output-format json
```

### Claude Code CLI: Finding session files

Session files use path-based naming with dashes:

```bash
# Find all Claude Code sessions for mcp-audit
ls ~/.claude/projects/-Users-nathanschram-claude-code-tools-lba-apps-devtools-mcp-audit-main/

# Find recent sessions (modified in last day)
find ~/.claude/projects/ -name "*.jsonl" -mtime -1
```

### Gemini CLI: "No sessions found"

1. Verify project hash matches CWD:
   ```bash
   python3 -c "import hashlib; print(hashlib.sha256(str('$(pwd)').encode()).hexdigest())"
   ```

2. Check sessions exist:
   ```bash
   ls ~/.gemini/tmp/*/chats/
   ```

3. Run a headless prompt to create a session:
   ```bash
   gemini "Hello" --output-format json
   ```

### Codex CLI: "exec" command not found

Ensure you're using `codex exec` (subcommand), not `codex --exec`:

```bash
# Correct
codex exec "prompt here"

# Incorrect
codex --exec "prompt here"
```

### Token counts are 0

For Codex CLI, per-tool token attribution is not available (platform limitation). Session-level totals should still be accurate.

For Gemini CLI, check the `--output-format json` output includes `stats.models` with token counts.

### MCP tools not detected

1. Verify MCP servers are configured:
   ```bash
   # Gemini
   gemini mcp list

   # Codex
   grep -A2 "\[mcp_servers" ~/.codex/config.toml
   ```

2. Ensure tools are invoked with `mcp__` prefix in prompts:
   ```bash
   gemini "Use mcp__jina__search_web to find 'Claude API'" --yolo
   ```

---

## TUI Testing with tmux

The mcp-audit TUI (Terminal User Interface) uses Rich's `Live` display for real-time updates. Testing the TUI programmatically requires capturing terminal output. This section explains how Claude Code can test the TUI without user interaction.

### Why TUI Testing is Challenging

The mcp-audit TUI uses `rich.live.Live` which:
- Requires a real terminal (PTY) for proper rendering
- Updates in place (no scrolling output)
- Cannot be captured with standard stdout redirection

**Solution**: Use tmux to run the CLI in a virtual terminal and capture the display buffer.

### tmux-based TUI Capture

tmux provides a virtual terminal that can be controlled and captured programmatically.

#### Basic TUI Capture

```bash
# 1. Start mcp-audit in a detached tmux session
tmux new-session -d -s mcp-test -x 120 -y 40 \
  "cd /Users/nathanschram/claude-code-tools/lba/apps/devtools/mcp-audit/main && \
   source .venv/bin/activate && \
   mcp-audit collect --platform claude-code"

# 2. Wait for TUI to initialize
sleep 3

# 3. Capture the current TUI display
tmux capture-pane -t mcp-test -p > /tmp/mcp-audit-tui-capture.txt

# 4. View the captured TUI
cat /tmp/mcp-audit-tui-capture.txt

# 5. Kill the session when done
tmux kill-session -t mcp-test
```

#### Full TUI Test Workflow

```bash
#!/bin/bash
# tui-test.sh - Test mcp-audit TUI rendering

set -e

MCP_AUDIT_DIR="/Users/nathanschram/claude-code-tools/lba/apps/devtools/mcp-audit/main"
SESSION_NAME="mcp-tui-test-$$"
CAPTURE_FILE="/tmp/mcp-tui-capture-$$.txt"

# Clean up on exit
trap "tmux kill-session -t $SESSION_NAME 2>/dev/null || true" EXIT

# 1. Start mcp-audit in background tmux session
echo "Starting mcp-audit TUI in tmux..."
tmux new-session -d -s "$SESSION_NAME" -x 120 -y 40 \
  "cd $MCP_AUDIT_DIR && source .venv/bin/activate && mcp-audit collect --platform gemini-cli 2>&1"

# 2. Wait for TUI to render
sleep 5

# 3. Capture TUI output
echo "Capturing TUI display..."
tmux capture-pane -t "$SESSION_NAME" -p -S - > "$CAPTURE_FILE"

# 4. Verify TUI elements are present
echo "Verifying TUI elements..."
if grep -q "MCP Audit" "$CAPTURE_FILE"; then
    echo "✓ Header present"
else
    echo "✗ Missing header"
    exit 1
fi

if grep -q "Token Usage" "$CAPTURE_FILE"; then
    echo "✓ Token panel present"
else
    echo "✗ Missing token panel"
    exit 1
fi

if grep -q "MCP Servers" "$CAPTURE_FILE"; then
    echo "✓ MCP Servers panel present"
else
    echo "✗ Missing MCP Servers panel"
    exit 1
fi

if grep -q "Recent Activity" "$CAPTURE_FILE"; then
    echo "✓ Activity panel present"
else
    echo "✗ Missing activity panel"
    exit 1
fi

echo ""
echo "TUI capture saved to: $CAPTURE_FILE"
echo "All TUI elements verified successfully!"
```

#### Continuous TUI Monitoring

Capture TUI snapshots over time:

```bash
# Start mcp-audit in tmux
tmux new-session -d -s mcp-monitor -x 120 -y 40 \
  "cd /Users/nathanschram/claude-code-tools/lba/apps/devtools/mcp-audit/main && \
   source .venv/bin/activate && \
   mcp-audit collect --platform claude-code"

# Capture snapshots every 2 seconds for 30 seconds
for i in $(seq 1 15); do
    sleep 2
    tmux capture-pane -t mcp-monitor -p > "/tmp/tui-snapshot-$i.txt"
    echo "Snapshot $i captured"
done

# Compare first and last snapshots
diff /tmp/tui-snapshot-1.txt /tmp/tui-snapshot-15.txt
```

### Display Adapter Pattern for Testing

mcp-audit uses a Display Adapter Pattern that enables testing without the TUI:

```
src/mcp_audit/display/
├── base.py          # DisplayAdapter abstract class
├── rich_display.py  # Full TUI (Rich Live)
├── plain_display.py # Plain text output
├── null_display.py  # Silent mode (no output)
└── snapshot.py      # DisplaySnapshot data structure
```

#### Using NullDisplay for Programmatic Testing

For adapter logic testing (without visual output):

```python
from mcp_audit.display.null_display import NullDisplay
from mcp_audit.display.snapshot import DisplaySnapshot
from datetime import datetime

# Create a null display (no terminal output)
display = NullDisplay()

# Create a test snapshot
snapshot = DisplaySnapshot.create(
    project="test-project",
    platform="claude-code",
    start_time=datetime.now(),
    duration_seconds=60.0,
    input_tokens=1000,
    output_tokens=500,
    total_tokens=1500,
)

# Lifecycle won't produce output
display.start(snapshot)
display.update(snapshot)
display.stop(snapshot)

# Verify the snapshot data directly
assert snapshot.total_tokens == 1500
assert snapshot.platform == "claude-code"
```

#### Capturing Rich Console Output

For testing Rich rendering without `Live`:

```python
import io
from rich.console import Console
from rich.table import Table

# Create a console that writes to StringIO
buffer = io.StringIO()
console = Console(file=buffer, width=120, force_terminal=True)

# Build a table (similar to TUI)
table = Table(title="Token Usage")
table.add_column("Type")
table.add_column("Count", justify="right")
table.add_row("Input", "1,234")
table.add_row("Output", "567")

# Render to buffer
console.print(table)

# Get captured output
output = buffer.getvalue()
print(output)

# Verify content
assert "Token Usage" in output
assert "1,234" in output
```

### Testing CLI Platforms with TUI

#### Test Claude Code Adapter + TUI

```bash
# 1. Run Claude Code headlessly to generate session data
cd /tmp
claude -p "Explain what Python is in one sentence" \
  --output-format json \
  -C /Users/nathanschram/claude-code-tools/lba/apps/devtools/mcp-audit/main

# 2. Start mcp-audit TUI in tmux to process the session
cd /Users/nathanschram/claude-code-tools/lba/apps/devtools/mcp-audit/main
tmux new-session -d -s claude-tui -x 120 -y 40 \
  "source .venv/bin/activate && mcp-audit collect --platform claude-code --batch --latest"

# 3. Capture final summary
sleep 3
tmux capture-pane -t claude-tui -p > /tmp/claude-tui-output.txt

# 4. Verify session was processed
grep -q "Session Complete" /tmp/claude-tui-output.txt && echo "✓ Session processed"

# Clean up
tmux kill-session -t claude-tui
```

#### Test Gemini CLI Adapter + TUI

```bash
# 1. Run Gemini headlessly
cd /Users/nathanschram/claude-code-tools/lba/apps/devtools/mcp-audit/main
gemini "What is 2+2?" --output-format json

# 2. Process with TUI in tmux
tmux new-session -d -s gemini-tui -x 120 -y 40 \
  "source .venv/bin/activate && mcp-audit collect --platform gemini-cli --batch --latest"

sleep 3
tmux capture-pane -t gemini-tui -p > /tmp/gemini-tui-output.txt

# 3. Verify
grep -q "Session Complete" /tmp/gemini-tui-output.txt && echo "✓ Gemini session processed"

tmux kill-session -t gemini-tui
```

#### Test Codex CLI Adapter + TUI

```bash
# 1. Run Codex headlessly
cd /Users/nathanschram/claude-code-tools/lba/apps/devtools/mcp-audit/main
codex exec "What is 2+2?"

# 2. Process with TUI in tmux
tmux new-session -d -s codex-tui -x 120 -y 40 \
  "source .venv/bin/activate && mcp-audit collect --platform codex-cli --batch --latest"

sleep 3
tmux capture-pane -t codex-tui -p > /tmp/codex-tui-output.txt

# 3. Verify
grep -q "Session Complete" /tmp/codex-tui-output.txt && echo "✓ Codex session processed"

tmux kill-session -t codex-tui
```

### TUI Testing Limitations

| What CAN Be Tested | What CANNOT Be Tested |
|--------------------|----------------------|
| TUI element presence (headers, panels) | Real-time animation smoothness |
| Token/cost values in display | Color rendering (ANSI codes) |
| MCP server hierarchy layout | Cursor positioning |
| Final summary content | Keyboard interaction |
| Panel borders and structure | Live refresh rate |

### TUI Verification Checklist

When testing the TUI, verify these elements are present:

```bash
# Capture TUI
tmux capture-pane -t mcp-test -p > /tmp/tui.txt

# Check required elements
grep -q "MCP Audit" /tmp/tui.txt         # Header
grep -q "Token Usage" /tmp/tui.txt       # Token panel
grep -q "MCP Servers" /tmp/tui.txt       # MCP panel
grep -q "Recent Activity" /tmp/tui.txt   # Activity feed
grep -q "Press Ctrl+C" /tmp/tui.txt      # Footer

# Check for data
grep -E "Input:|Output:" /tmp/tui.txt    # Token metrics
grep -E "Cost w/" /tmp/tui.txt           # Cost display
```

---

## Live Monitoring vs Batch Mode

mcp-audit supports two modes of operation. Understanding when to use each is critical for testing.

### Mode Comparison

| Mode | Command | Use Case | Captures |
|------|---------|----------|----------|
| **Live** | `mcp-audit collect --platform xxx` | Real-time monitoring | Active sessions as they happen |
| **Batch** | `mcp-audit collect --platform xxx --batch --latest` | Post-processing | Existing session files |

### Live Monitoring (Recommended for Integration Testing)

**Key insight**: mcp-audit must be running BEFORE the AI session starts to capture live data.

```bash
# Step 1: Start mcp-audit in tmux FIRST (live mode)
tmux new-session -d -s mcp-live -x 140 -y 50 \
  "cd /Users/nathanschram/claude-code-tools/lba/apps/devtools/mcp-audit/main && \
   source .venv/bin/activate && \
   mcp-audit collect --platform claude-code --project my-test"

# Step 2: Run AI CLI (in separate terminal or after tmux starts)
cd /tmp
claude -p "Test prompt with MCP tools" \
  --output-format json \
  --permission-mode acceptEdits \
  -C /Users/nathanschram/claude-code-tools/lba/apps/devtools/mcp-audit/main

# Step 3: Capture TUI snapshots
sleep 5
tmux capture-pane -t mcp-live -p -S - > /tmp/live-tui-capture.txt

# Step 4: Stop mcp-audit
tmux send-keys -t mcp-live C-c
sleep 2
tmux kill-session -t mcp-live
```

### Batch Mode (For Processing Existing Sessions)

Use batch mode when you already have session files and want to process them:

```bash
# Process the most recent session
mcp-audit collect --platform claude-code --batch --latest

# Process a specific session file
mcp-audit collect --platform claude-code --batch \
  --session-file ~/.claude/projects/-Users-nathanschram-.../session-id.jsonl
```

---

## Comparing Native vs mcp-audit Metrics

For accuracy testing, compare mcp-audit session logs against native AI CLI logs.

### Claude Code: Native Session Comparison

```bash
# Find the mcp-audit session log
MCP_LOG=$(ls -t ~/.mcp-audit/sessions/claude-code/*.json | head -1)

# Find the native Claude Code session
NATIVE_LOG=$(ls -t ~/.claude/projects/-Users-nathanschram-claude-code-tools-lba-apps-devtools-mcp-audit-main/*.jsonl | head -1)

# Extract mcp-audit metrics
echo "=== mcp-audit metrics ==="
cat "$MCP_LOG" | jq '{
  cost_usd,
  input_tokens: .token_usage.input_tokens,
  output_tokens: .token_usage.output_tokens,
  accuracy_level: .data_quality.accuracy_level
}'

# Extract native metrics (last summary line)
echo "=== Native metrics ==="
tail -1 "$NATIVE_LOG" | jq '{costUSD, totalTokensIn, totalTokensOut}' 2>/dev/null || \
  echo "Check native session format"
```

### Gemini CLI: Native Session Comparison

```bash
# mcp-audit session
MCP_LOG=$(ls -t ~/.mcp-audit/sessions/gemini-cli/*.json | head -1)

# Native Gemini session (project hash for mcp-audit)
GEMINI_HASH="76c62a47a1287071d52c32065e26834b212bf4df1e1551d71ebc39403d65d37b"
NATIVE_LOG=$(ls -t ~/.gemini/tmp/$GEMINI_HASH/chats/*.json | head -1)

# Compare
echo "=== mcp-audit ==="
cat "$MCP_LOG" | jq '.token_usage'

echo "=== Native (message-level tokens) ==="
cat "$NATIVE_LOG" | jq '[.messages[].tokenCount // 0] | add'
```

### Codex CLI: Native Session Comparison

```bash
# mcp-audit session
MCP_LOG=$(ls -t ~/.mcp-audit/sessions/codex-cli/*.json | head -1)

# Native Codex session
NATIVE_LOG=$(find ~/.codex/sessions/2025/12 -name "*.jsonl" -mmin -30 | head -1)

# Tool call count comparison (Codex doesn't provide per-call tokens)
echo "=== mcp-audit tool calls ==="
cat "$MCP_LOG" | jq '.tool_calls | length'

echo "=== Native tool calls ==="
grep -c '"type":"tool_call"' "$NATIVE_LOG" || echo "0"
```

### Expected Accuracy by Platform

| Platform | Metric | Expected Match |
|----------|--------|----------------|
| Claude Code | Cost USD | Within 5% |
| Claude Code | Input/Output tokens | Exact match |
| Gemini CLI | Token counts | Within 20% (tiktoken estimation) |
| Codex CLI | Tool call count | Exact match |
| Codex CLI | Token counts | N/A (no native reference) |

---

## Related Documentation

- [Claude Code Headless Docs](https://code.claude.com/docs/en/headless) - Official headless mode documentation
- [Gemini CLI Setup](gemini-cli-setup.md) - Full Gemini CLI configuration
- [Codex CLI Setup](codex-cli-setup.md) - Full Codex CLI configuration
- [Platform Token Capabilities](PLATFORM-TOKEN-CAPABILITIES.md) - Token tracking limitations
- [Architecture](architecture.md) - System design

---

## Quick Reference Commands

```bash
# === Setup ===
cd /Users/nathanschram/claude-code-tools/lba/apps/devtools/mcp-audit/main
source .venv/bin/activate
pip install -e ".[dev]"

# === Live Monitoring Test (Recommended) ===
# Step 1: Start mcp-audit FIRST
tmux new-session -d -s mcp-live -x 140 -y 50 \
  "source .venv/bin/activate && mcp-audit collect --platform claude-code --project test"
# Step 2: Run AI CLI
cd /tmp && claude -p "Test prompt" --output-format json \
  -C /Users/nathanschram/claude-code-tools/lba/apps/devtools/mcp-audit/main
# Step 3: Capture and stop
sleep 5 && tmux capture-pane -t mcp-live -p -S - > /tmp/live-capture.txt
tmux send-keys -t mcp-live C-c && sleep 2 && tmux kill-session -t mcp-live

# === Batch Processing (Existing Sessions) ===
mcp-audit collect --platform claude-code --batch --latest
mcp-audit collect --platform gemini-cli --batch --latest
mcp-audit collect --platform codex-cli --batch --latest

# === Claude Code CLI Headless Test ===
cd /tmp
claude -p "Test prompt for mcp-audit" \
  --output-format json \
  -C /Users/nathanschram/claude-code-tools/lba/apps/devtools/mcp-audit/main

# === Gemini CLI Headless Test ===
cd /Users/nathanschram/claude-code-tools/lba/apps/devtools/mcp-audit/main
gemini "Test prompt for mcp-audit" --yolo --output-format json

# === Codex CLI Headless Test ===
codex exec "Test prompt for mcp-audit" --json

# === Verify Results ===
ls -la ~/.mcp-audit/sessions/

# === Verify v0.6.0 Schema Fields ===
LATEST=$(ls -t ~/.mcp-audit/sessions/claude-code/*.json | head -1)
cat "$LATEST" | jq '{schema_version, models_used, data_quality}'

# === TUI Testing with tmux ===
tmux new-session -d -s mcp-test -x 140 -y 50 \
  "source .venv/bin/activate && mcp-audit collect --platform claude-code"
sleep 3
tmux capture-pane -t mcp-test -p -S - > /tmp/tui-capture.txt
cat /tmp/tui-capture.txt
tmux kill-session -t mcp-test
```
