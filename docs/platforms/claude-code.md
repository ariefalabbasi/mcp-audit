# Claude Code Setup Guide

This guide explains how to use MCP Audit with [Claude Code](https://claude.ai/claude-code), Anthropic's AI coding assistant.

---

## Prerequisites

- **Claude Code** installed and configured
- **Python 3.8+** installed
- **MCP servers** configured in Claude Code (optional, but tracking is most useful with MCP)

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
mcp-audit collect --platform claude-code
```

You'll see a live display of your session:

```
MCP Audit - Claude Code Session
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Status: Tracking...
Project: my-project (auto-detected)

Tokens:      0 input │ 0 output │ 0 cached
Cost:        $0.00 (estimated)
MCP Tools:   0 calls │ 0 unique

Waiting for events... (Ctrl+C to stop)
```

### 2. Use Claude Code Normally

In a separate terminal, start Claude Code:

```bash
claude
```

Work as usual. MCP Audit will track:
- All model interactions (tokens used)
- All MCP tool calls (which tools, how many tokens)
- Cache efficiency (cache hits vs misses)

### 3. Stop Tracking

When done, press `Ctrl+C` in the MCP Audit terminal:

```
^C
Session complete!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Duration:    45 minutes
Tokens:      125,432 total (93% cached)
Cost:        $0.15 (estimated)
MCP Tools:   42 calls across 3 servers

Session saved to:
~/.mcp-audit/sessions/claude_code/2025-11-25/session-20251125T103045-abc123.jsonl
```

---

## How It Works

MCP Audit monitors Claude Code's debug log files located at:

```
~/.claude/cache/*/debug.log
```

It parses events in real-time to extract:
- Token usage (input, output, cache created, cache read)
- MCP tool calls (tool name, server, tokens per call)
- Model information (which Claude model variant)

### File Watcher Approach

```
Claude Code          MCP Audit
    │                    │
    │ writes events      │
    ▼                    │
~/.claude/cache/     watches
debug.log ──────────────►│
                         │ parses events
                         ▼
                   Tracking Data
```

---

## Configuration

### Auto-Detection

MCP Audit automatically detects:
- **Project name**: From your current working directory
- **Model**: From Claude Code's session metadata
- **MCP servers**: From tool call events

### Manual Configuration

Override auto-detection with CLI flags:

```bash
# Specify project name
mcp-audit collect --platform claude-code --project "my-feature"

# Custom output directory
mcp-audit collect --platform claude-code --output ./my-sessions/
```

### Pricing Configuration

Create `~/.mcp-audit/config/mcp-audit.toml`:

```toml
[pricing.claude]
# Prices are per 1M tokens
"claude-sonnet-4" = { input = 3.00, output = 15.00 }
"claude-opus-4" = { input = 15.00, output = 75.00 }
"claude-haiku" = { input = 0.25, output = 1.25 }
```

---

## MCP Server Tracking

### Supported MCP Servers

MCP Audit tracks all MCP servers configured in Claude Code:

| Server | Common Tools | Notes |
|--------|--------------|-------|
| zen | chat, thinkdeep, consensus | High token usage |
| brave-search | web, local, news | Variable by query |
| context7 | lookup | Documentation |
| mult-fetch | fetch | Web content |

### Tool Name Format

Claude Code uses this format for MCP tools:

```
mcp__<server>__<tool>
```

Examples:
- `mcp__zen__chat`
- `mcp__brave-search__web`
- `mcp__context7__lookup`

---

## Viewing Results

### Terminal Report

```bash
mcp-audit report
```

### JSON Export

```bash
mcp-audit report --format json --output report.json
```

### CSV for Spreadsheets

```bash
mcp-audit report --format csv --output report.csv
```

### Session Details

View raw session events:

```bash
cat ~/.mcp-audit/sessions/claude_code/2025-11-25/session-*.jsonl | head -20
```

---

## Troubleshooting

### No Events Detected

**Symptom**: Tracker shows "Waiting for events..." but nothing appears.

**Solutions**:
1. Ensure Claude Code is running in a separate terminal
2. Check that Claude Code's cache directory exists:
   ```bash
   ls ~/.claude/cache/
   ```
3. Verify debug logging is enabled (usually automatic)

### Missing MCP Data

**Symptom**: Model tokens tracked but no MCP tool calls.

**Solutions**:
1. Verify MCP servers are configured:
   ```bash
   cat ~/.config/claude/mcp.json
   ```
2. Use an MCP tool in Claude Code to trigger events
3. Check for parsing errors in MCP Audit output

### High Cache Miss Rate

**Symptom**: Low cache efficiency (<50%).

**Causes**:
- New conversation (no cache to hit)
- Rapidly changing context
- Large file edits

**Note**: High cache miss is normal for new sessions.

---

## Best Practices

### Session Organization

- Run one MCP Audit instance per Claude Code session
- Name projects descriptively: `--project "feature-auth-refactor"`
- Review sessions weekly to identify patterns

### Cost Optimization

Based on MCP Audit data:

1. **Reduce expensive tool calls**:
   - `thinkdeep`: Use for complex debugging only
   - `consensus`: Batch questions to minimize calls

2. **Leverage caching**:
   - Keep context consistent within sessions
   - Avoid frequent large file changes

3. **Use appropriate tools**:
   - `chat` for simple questions (lower tokens)
   - `thinkdeep` for complex analysis (higher tokens)

---

## Example Session

### Sample Output

```
Top 5 Most Expensive Tools
═══════════════════════════════════════════════════════════════
Tool                              Calls    Tokens    Avg/Call
mcp__zen__thinkdeep                   3   112,345      37,448
mcp__zen__chat                       15    45,678       3,045
mcp__brave-search__web                8    23,456       2,932
mcp__context7__lookup                 5    12,345       2,469
Read (built-in)                      45     8,765         195

Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total tokens:     202,589
Cache efficiency: 87%
Estimated cost:   $0.23
```

---

## See Also

- [Architecture](../architecture.md) - How MCP Audit works internally
- [Privacy & Security](../privacy-security.md) - What data is collected
- [Contributing](../contributing.md) - Adding platform adapters
