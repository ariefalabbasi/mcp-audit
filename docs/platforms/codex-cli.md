# Codex CLI Setup Guide

This guide explains how to use MCP Audit with [Codex CLI](https://github.com/openai/codex), OpenAI's terminal-based coding assistant.

---

## Prerequisites

- **Codex CLI** installed and configured
- **Python 3.8+** installed
- **OpenAI API key** configured for Codex

---

## Installation

```bash
pip install mcp-audit
```

---

## Quick Start

### 1. Start Tracking

Open a new terminal and run:

```bash
mcp-audit collect --platform codex_cli
```

You'll see a live display:

```
MCP Audit - Codex CLI Session
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Status: Tracking...
Project: my-project (auto-detected)

Tokens:      0 input │ 0 output │ 0 cached
Cost:        $0.00 (estimated)
MCP Tools:   0 calls │ 0 unique

Waiting for events... (Ctrl+C to stop)
```

### 2. Use Codex CLI Normally

In a separate terminal, start Codex:

```bash
codex
```

Work as usual. MCP Audit will track all model interactions and MCP tool calls.

### 3. Stop Tracking

Press `Ctrl+C` to end the session:

```
^C
Session complete!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Duration:    30 minutes
Tokens:      85,432 total
Cost:        $0.21 (estimated)
MCP Tools:   28 calls across 2 servers

Session saved to:
~/.mcp-audit/sessions/codex_cli/2025-11-25/session-20251125T143022-def456.jsonl
```

---

## How It Works

MCP Audit monitors Codex CLI by wrapping the process and capturing stdout/stderr events.

### Process Wrapper Approach

```
MCP Audit
    │
    │ spawns & monitors
    ▼
Codex CLI ───────────► stdout/stderr
    │                       │
    │ API calls             │ captured
    ▼                       ▼
OpenAI API          Tracking Data
```

### Event Sources

- **stdout**: Response messages, tool outputs
- **stderr**: Debug information, warnings
- **API responses**: Token usage, model info

---

## Tool Name Normalization

Codex CLI uses a slightly different format for MCP tools:

| Codex CLI Format | Normalized Format |
|------------------|-------------------|
| `mcp__zen-mcp__chat` | `mcp__zen__chat` |
| `mcp__brave-search-mcp__web` | `mcp__brave-search__web` |

MCP Audit automatically normalizes the `-mcp` suffix for consistent tracking across platforms.

---

## Configuration

### Auto-Detection

MCP Audit automatically detects:
- **Project name**: From current working directory
- **Model**: From Codex session metadata
- **Working directory**: For session context

### Manual Configuration

```bash
# Specify project name
mcp-audit collect --platform codex_cli --project "api-refactor"

# Custom output directory
mcp-audit collect --platform codex_cli --output ./codex-sessions/
```

### Pricing Configuration

Create `~/.mcp-audit/config/mcp-audit.toml`:

```toml
[pricing.openai]
# Prices are per 1M tokens
"gpt-4o" = { input = 2.50, output = 10.00 }
"gpt-4o-mini" = { input = 0.15, output = 0.60 }
"o1" = { input = 15.00, output = 60.00 }
"o1-mini" = { input = 3.00, output = 12.00 }
"o3-mini" = { input = 1.10, output = 4.40 }
```

---

## MCP Server Tracking

### Supported MCP Servers

All MCP servers configured in Codex CLI are tracked:

| Server | Common Tools | Notes |
|--------|--------------|-------|
| zen | chat, thinkdeep | Custom thinking tools |
| brave-search | web, local | Search capabilities |
| filesystem | read, write | File operations |

### Built-in vs MCP Tools

MCP Audit differentiates between:

**Built-in Tools** (Codex native):
- `execute_zsh`
- `read_file`
- `write_to_file`
- `list_directory`
- `glob_search`

**MCP Tools** (tracked separately):
- `mcp__zen__chat`
- `mcp__brave-search__web`
- etc.

---

## Viewing Results

### Terminal Report

```bash
mcp-audit report --platform codex_cli
```

### Filter by Date

```bash
mcp-audit report --platform codex_cli --start 2025-11-20 --end 2025-11-25
```

### Export Options

```bash
# JSON
mcp-audit report --format json --output codex-report.json

# CSV
mcp-audit report --format csv --output codex-report.csv

# Markdown
mcp-audit report --format markdown --output codex-report.md
```

---

## Troubleshooting

### No Events Captured

**Symptom**: Tracker starts but no events appear.

**Solutions**:
1. Ensure Codex CLI is running and active
2. Make a request to trigger output
3. Check that Codex CLI is outputting to stdout:
   ```bash
   codex --verbose
   ```

### Tool Names Not Normalized

**Symptom**: Same tool appears twice with different names.

**Cause**: Older version of MCP Audit without normalization.

**Solution**: Update to latest version:
```bash
pip install --upgrade mcp-audit
```

### Missing Token Counts

**Symptom**: Tool calls tracked but token counts are 0.

**Cause**: Codex CLI version may not output token usage.

**Workaround**: Use `--verbose` flag with Codex:
```bash
codex --verbose
```

---

## Comparison with Claude Code

| Aspect | Claude Code | Codex CLI |
|--------|-------------|-----------|
| Interception | File watcher | Process wrapper |
| MCP Format | `mcp__server__tool` | `mcp__server-mcp__tool` |
| Token Format | Native | Requires normalization |
| Cache Tracking | Yes | Limited |
| Session Recovery | events.jsonl | events.jsonl |

Both platforms produce compatible session data for cross-platform analysis.

---

## Best Practices

### Parallel Tracking

Run MCP Audit before starting Codex CLI to capture all events:

```bash
# Terminal 1
mcp-audit collect --platform codex_cli

# Terminal 2 (after tracker starts)
codex
```

### Project Organization

Use descriptive project names for easier analysis:

```bash
mcp-audit collect --platform codex_cli --project "feature-auth"
```

### Cost Comparison

Compare costs between Claude Code and Codex CLI:

```bash
# Claude Code sessions
mcp-audit report --platform claude_code --last 7

# Codex CLI sessions
mcp-audit report --platform codex_cli --last 7
```

---

## Example Session

### Sample Output

```
Codex CLI Session Summary
═══════════════════════════════════════════════════════════════

Top 5 Most Expensive Tools
──────────────────────────────────────────────────────────────
Tool                              Calls    Tokens    Avg/Call
mcp__zen__thinkdeep                   2    78,234      39,117
execute_zsh (built-in)               12    23,456       1,955
mcp__zen__chat                        8    18,765       2,346
read_file (built-in)                 25    12,345         494
mcp__brave-search__web                3     8,765       2,922

Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total tokens:     141,565
Estimated cost:   $0.35

Anomalies Detected:
⚠️  mcp__zen__thinkdeep: High average tokens (39,117 per call)
```

---

## See Also

- [Claude Code Guide](claude-code.md) - Compare with Claude Code tracking
- [Architecture](../architecture.md) - Technical details
- [Contributing](../contributing.md) - Adding platform adapters
