# Gemini CLI Setup Guide

This guide explains how to use MCP Audit with [Gemini CLI](https://github.com/google-gemini/gemini-cli), Google's AI coding assistant for the terminal.

---

## Prerequisites

- **Gemini CLI** installed and configured (`npm install -g @google/gemini-cli`)
- **Python 3.8+** installed
- **Google account** authenticated with Gemini CLI
- **MCP servers** configured in Gemini CLI (optional, but tracking is most useful with MCP)

---

## Installation

```bash
pip install mcp-audit
```

---

## Quick Start

### 1. Enable Telemetry

MCP Audit uses Gemini CLI's built-in OpenTelemetry system. Enable it with one of these methods:

**Option A: Environment Variables (Recommended)**

```bash
export GEMINI_TELEMETRY_ENABLED=true
export GEMINI_TELEMETRY_OUTFILE=~/.gemini/telemetry.log
```

Add to your `~/.bashrc` or `~/.zshrc` for persistence.

**Option B: Settings File**

Add to `~/.gemini/settings.json`:

```json
{
  "telemetry": {
    "enabled": true,
    "target": "local",
    "outfile": ".gemini/telemetry.log"
  }
}
```

### 2. Start Tracking

Open a new terminal and run:

```bash
mcp-audit collect --platform gemini_cli
```

You'll see a live display of your session:

```
MCP Audit - Gemini CLI Session
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Status: Tracking...
Project: my-project (auto-detected)

Tokens:      0 input │ 0 output │ 0 thought │ 0 cached
Cost:        $0.00 (estimated)
MCP Tools:   0 calls │ 0 unique

Waiting for events... (Ctrl+C to stop)
```

### 3. Use Gemini CLI Normally

In a separate terminal, start Gemini CLI:

```bash
gemini
```

Work as usual. MCP Audit will track:
- All model interactions (tokens used)
- All MCP tool calls (which tools, how many tokens)
- Thinking/reasoning tokens (Gemini-specific)
- Per-tool execution latency
- Cache efficiency

### 4. Stop Tracking

When done, press `Ctrl+C` in the MCP Audit terminal:

```
^C
Session complete!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Duration:    30 minutes
Tokens:      98,432 total (45% cached)
Thinking:    12,345 tokens
Cost:        $0.12 (estimated)
MCP Tools:   28 calls across 2 servers

Session saved to:
~/.mcp-audit/sessions/gemini_cli/2025-11-25/session-20251125T103045-abc123.jsonl
```

---

## How It Works

MCP Audit monitors Gemini CLI's OpenTelemetry telemetry file (default: `~/.gemini/telemetry.log`).

It parses these metrics in real-time:
- `gemini_cli.token.usage` - Token counts by type (input, output, thought, cache)
- `gemini_cli.tool.call.count` - Tool invocations with `tool_type` attribute
- `gemini_cli.tool.call.latency` - Per-tool execution duration

### Key Discovery: Native MCP Tracking

Gemini CLI's telemetry includes a `tool_type` attribute:
- `"mcp"` - MCP server tools (what we track)
- `"native"` - Built-in tools (file ops, shell, etc.)

This native distinction means MCP Audit can accurately separate MCP tool usage from built-in tools without heuristics.

### File Watcher Approach

```
Gemini CLI           MCP Audit
    │                    │
    │ writes metrics     │
    ▼                    │
~/.gemini/           watches
telemetry.log ───────────►│
                         │ parses OTEL events
                         ▼
                   Tracking Data
```

---

## Configuration

### Auto-Detection

MCP Audit automatically detects:
- **Telemetry file**: From `GEMINI_TELEMETRY_OUTFILE` or settings.json
- **Project name**: From your current working directory
- **Model**: From token usage events (e.g., `gemini-2.5-pro`)
- **MCP servers**: From tool call events

### Manual Configuration

Override auto-detection with CLI flags:

```bash
# Specify project name
mcp-audit collect --platform gemini_cli --project "my-feature"

# Custom telemetry file location
mcp-audit collect --platform gemini_cli --telemetry-file /path/to/custom.log

# Custom output directory
mcp-audit collect --platform gemini_cli --output ./my-sessions/
```

### Pricing Configuration

Add Gemini models to `~/.mcp-audit/config/mcp-audit.toml`:

```toml
[pricing.gemini]
# Prices are per 1M tokens
"gemini-2.5-pro" = { input = 1.25, output = 10.0, cache_read = 0.3125 }
"gemini-2.5-flash" = { input = 0.075, output = 0.30, cache_read = 0.01875 }
"gemini-2.0-flash" = { input = 0.075, output = 0.30, cache_read = 0.01875 }
```

---

## MCP Server Tracking

### Supported MCP Servers

MCP Audit tracks all MCP servers configured in Gemini CLI:

| Server | Common Tools | Notes |
|--------|--------------|-------|
| zen | chat, thinkdeep, consensus | High token usage |
| brave-search | web, local, news | Variable by query |
| context7 | lookup | Documentation |
| mult-fetch | fetch | Web content |

### Tool Name Format

Gemini CLI uses the same format as Claude Code for MCP tools:

```
mcp__<server>__<tool>
```

Examples:
- `mcp__zen__chat`
- `mcp__brave-search__brave_web_search`
- `mcp__context7__lookup`

**No normalization required** - unlike Codex CLI's `-mcp` suffix.

### MCP Configuration

Configure MCP servers in `~/.gemini/settings.json`:

```json
{
  "mcpServers": {
    "zen": {
      "command": "node",
      "args": ["/path/to/zen-server/index.js"],
      "trust": false,
      "timeout": 600000
    },
    "brave-search": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-brave-search"],
      "env": {
        "BRAVE_API_KEY": "${BRAVE_API_KEY}"
      }
    }
  }
}
```

---

## Gemini-Specific Features

### Thinking Tokens

Gemini models have a unique "thinking" or "reasoning" token type. MCP Audit tracks these separately:

```
Session Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Input tokens:     50,000
Output tokens:    25,000
Thinking tokens:  12,345  ← Gemini-specific
Cache tokens:     45,000
```

### Per-Tool Latency

Gemini CLI provides execution latency for each tool call:

```
Tool Performance
═══════════════════════════════════════════════════════════════
Tool                              Calls    Latency (avg)
mcp__zen__thinkdeep                   3       2,345ms
mcp__zen__chat                       15         456ms
mcp__brave-search__web                8       1,234ms
```

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
cat ~/.mcp-audit/sessions/gemini_cli/2025-11-25/session-*.jsonl | head -20
```

---

## Troubleshooting

### No Events Detected

**Symptom**: Tracker shows "Waiting for events..." but nothing appears.

**Solutions**:
1. Verify telemetry is enabled:
   ```bash
   echo $GEMINI_TELEMETRY_ENABLED
   # Should output: true
   ```
2. Check telemetry file exists and grows:
   ```bash
   ls -la ~/.gemini/telemetry.log
   tail -f ~/.gemini/telemetry.log
   ```
3. Ensure Gemini CLI is running in a separate terminal
4. Use an MCP tool to trigger events:
   ```
   gemini> @zen analyze this file
   ```

### Telemetry Not Enabled Warning

**Symptom**: "Warning: Telemetry does not appear to be enabled"

**Solution**: Enable telemetry with environment variables or settings.json (see Quick Start section).

### Missing MCP Data

**Symptom**: Model tokens tracked but no MCP tool calls.

**Solutions**:
1. Verify MCP servers are configured in `~/.gemini/settings.json`
2. Use an MCP tool in Gemini CLI to trigger events
3. Check that tool calls have `tool_type: "mcp"` in telemetry

### Thinking Tokens Not Tracked

**Symptom**: Thinking tokens show as 0.

**Solutions**:
1. Ensure you're using a Gemini model that supports thinking (e.g., gemini-2.5-pro)
2. Enable thinking mode in your Gemini CLI session
3. Verify `gemini_cli.token.usage` events include `type: "thought"`

---

## Best Practices

### Session Organization

- Run one MCP Audit instance per Gemini CLI session
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

3. **Monitor thinking tokens**:
   - Thinking tokens add to cost on Gemini models
   - Use flash models for simpler tasks

4. **Use appropriate tools**:
   - `chat` for simple questions (lower tokens)
   - `thinkdeep` for complex analysis (higher tokens)

---

## Example Session

### Sample Output

```
Top 5 Most Expensive Tools
═══════════════════════════════════════════════════════════════
Tool                              Calls    Tokens    Avg/Call    Latency
mcp__zen__thinkdeep                   3   112,345      37,448    2,345ms
mcp__zen__chat                       15    45,678       3,045      456ms
mcp__brave-search__web                8    23,456       2,932    1,234ms
mcp__context7__lookup                 5    12,345       2,469      234ms
read_file (built-in)                 45     8,765         195       45ms

Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total tokens:     202,589
Thinking tokens:   15,432
Cache efficiency: 45%
Estimated cost:   $0.25
```

---

## Telemetry Format Reference

### OpenTelemetry Events

MCP Audit parses these JSON lines from telemetry:

**MCP Tool Call**:
```json
{
  "name": "gemini_cli.tool.call.count",
  "attributes": {
    "function_name": "mcp__zen__chat",
    "tool_type": "mcp",
    "success": true,
    "decision": "auto_accept"
  },
  "value": 1
}
```

**Token Usage**:
```json
{
  "name": "gemini_cli.token.usage",
  "attributes": {
    "model": "gemini-2.5-pro",
    "type": "input"
  },
  "value": 1234
}
```

**Tool Latency**:
```json
{
  "name": "gemini_cli.tool.call.latency",
  "attributes": {
    "function_name": "mcp__zen__chat"
  },
  "value": 456
}
```

---

## See Also

- [Architecture](../architecture.md) - How MCP Audit works internally
- [Privacy & Security](../privacy-security.md) - What data is collected
- [Contributing](../contributing.md) - Adding platform adapters
- [Gemini CLI Docs](https://github.com/google-gemini/gemini-cli) - Official documentation
