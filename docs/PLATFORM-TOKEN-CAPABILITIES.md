# Platform Token Capabilities

This document describes the token tracking capabilities and limitations for each platform supported by mcp-audit, along with our planned approach for MCP tool token estimation.

---

## Overview

mcp-audit tracks token usage and MCP server efficiency across multiple AI coding platforms. Each platform provides different levels of token attribution detail:

| Platform | Session Tokens | Per-Message Tokens | Per-Tool Tokens | Reasoning Tokens | MCP Tool Data | Built-in Tools |
|----------|---------------|-------------------|-----------------|-----------------|---------------|----------------|
| Claude Code | ✅ Native | ✅ Native | ✅ Native | ❌ Not exposed | Full attribution | ✅ Calls + Tokens |
| Codex CLI | ✅ Native | ✅ Native (turn-level) | ❌ Not available | ✅ `reasoning_output_tokens` | Args + results | ✅ Calls only |
| Gemini CLI | ✅ Native | ✅ Native | ❌ Not available | ✅ `thoughts` | Args + results | ✅ Calls only |

---

## Claude Code

### Token Capabilities

Claude Code provides **complete per-tool token attribution** through its JSONL session logs.

**What's tracked:**
- Input tokens (per tool call)
- Output tokens (per tool call)
- Cache read tokens
- Cache created tokens
- Tool call duration

**Session log format:**
```json
{
  "type": "assistant",
  "message": {
    "usage": {
      "input_tokens": 1234,
      "output_tokens": 567,
      "cache_read_input_tokens": 890,
      "cache_creation_input_tokens": 123
    },
    "content": [{
      "type": "tool_use",
      "name": "mcp__brave-search__brave_web_search",
      "input": {"query": "..."}
    }]
  }
}
```

### Built-in Tool Tracking (v1.2.0)

As of schema v1.2.0, mcp-audit tracks built-in tools (Bash, Read, Write, Edit, Glob, Grep, etc.) in session files:

```json
{
  "builtin_tool_summary": {
    "total_calls": 15,
    "total_tokens": 1250000,
    "tools": [
      {"tool": "Read", "calls": 5, "tokens": 450000},
      {"tool": "Bash", "calls": 4, "tokens": 350000}
    ]
  }
}
```

This enables post-session analysis of both MCP and built-in tool usage patterns.

### Limitations

None - Claude Code provides full MCP tool token attribution and built-in tool tracking.

---

## Codex CLI (OpenAI)

### Token Capabilities

Codex CLI provides **turn-level token tracking** but does NOT provide per-tool token attribution.

**What's available:**
- Cumulative session totals (`total_token_usage`) - **used by mcp-audit**
- Per-turn deltas (`last_token_usage`) - not used (causes double-counting)
- Input, output, cached, and reasoning tokens
- Full tool call arguments and results

**Session log format (JSONL):**
```json
// Token count event (turn-level)
{
  "timestamp": "2025-12-04T03:57:56.501Z",
  "type": "event_msg",
  "payload": {
    "type": "token_count",
    "info": {
      "total_token_usage": {
        "input_tokens": 18062,
        "cached_input_tokens": 8704,
        "output_tokens": 162,
        "reasoning_output_tokens": 64,
        "total_tokens": 18224
      },
      "last_token_usage": {
        "input_tokens": 9317,
        "cached_input_tokens": 8704,
        "output_tokens": 51,
        "reasoning_output_tokens": 0,
        "total_tokens": 9368
      }
    }
  }
}

// Tool call event (no token info)
{
  "timestamp": "2025-12-04T03:57:56.731Z",
  "type": "response_item",
  "payload": {
    "type": "function_call",
    "name": "mcp__brave-search__brave_web_search",
    "arguments": "{\"query\": \"...\"}",
    "call_id": "call_kvoLihUZg6LMYJU5nnYlIOJm"
  }
}

// Tool result event (no token info)
{
  "type": "response_item",
  "payload": {
    "type": "function_call_output",
    "call_id": "call_kvoLihUZg6LMYJU5nnYlIOJm",
    "output": "Search results: ..."
  }
}
```

### Event Timing Pattern

```
TOKEN_CNT (before decision)
    ↓
FUNC_CALL (tool invocation)
    ↓
FUNC_CALL_OUTPUT (tool result)
    ↓
TOKEN_CNT (same values - confirmation/duplicate)
    ↓
[Model processes result]
    ↓
TOKEN_CNT (new cumulative total)
```

**Important**: Codex CLI native logs contain **duplicate `token_count` events** - the same values often appear twice consecutively (e.g., Event 2 duplicates Event 1 with identical cumulative totals).

### How mcp-audit Handles Duplicates (v0.3.14+)

mcp-audit uses `total_token_usage` (cumulative totals) and **replaces** session values instead of summing:

| Field | Strategy | Why |
|-------|----------|-----|
| `total_token_usage` | REPLACE | Cumulative - last event has final totals |
| `last_token_usage` | IGNORED | Summing would cause double-counting |

This ensures token counts match native Codex CLI values exactly, regardless of duplicate events.

### Limitations

1. **No `call_id` in token events**: Cannot link `token_count` events to specific `function_call` events
2. **Turn-level granularity**: Token deltas include model thinking, not just tool I/O
3. **Multiple tools per turn**: When multiple tools are called in one turn, tokens cannot be separated
4. **No official API**: OpenAI has not documented per-tool token attribution for Codex CLI

### What We CAN Extract

Despite limitations, Codex CLI logs contain:
- Full tool arguments (JSON string)
- Full tool results (string)
- Tool call timing (timestamps)
- Tool names and call IDs

This data enables **token estimation** based on content size.

### Built-in Tool Tracking (v1.2.0)

As of schema v1.2.0, mcp-audit tracks built-in tools (shell, read_file, apply_patch, etc.) in session files:

```json
{
  "builtin_tool_summary": {
    "total_calls": 8,
    "total_tokens": 0,
    "tools": [
      {"tool": "shell", "calls": 5, "tokens": 0},
      {"tool": "read_file", "calls": 3, "tokens": 0}
    ]
  }
}
```

**Note**: Codex CLI doesn't provide per-tool token attribution, so `tokens` is always 0. Call counts are tracked accurately.

---

## Gemini CLI (Google)

### Token Capabilities

Gemini CLI provides **per-message token tracking** with a dedicated `tool` field (currently unused).

**What's available:**
- Per-message token breakdown
- Input, output, cached, and thoughts tokens
- A `tool` token field (always 0 currently)
- Full tool call arguments and results

**Session log format (JSON):**
```json
{
  "sessionId": "16b12454-dd91-4cc8-a69f-eb5ff9049a4a",
  "messages": [
    {
      "id": "msg_001",
      "type": "gemini",
      "tokens": {
        "input": 10323,
        "output": 16,
        "cached": 0,
        "thoughts": 218,
        "tool": 0,
        "total": 10557
      },
      "toolCalls": [
        {
          "name": "read_file",
          "args": {"file_path": "example.txt"},
          "result": [{"functionResponse": {...}}]
        }
      ]
    }
  ]
}
```

### Token Fields Explained

| Field | Description | Status |
|-------|-------------|--------|
| `input` | Input tokens for the message | ✅ Populated |
| `output` | Output tokens for the response | ✅ Populated |
| `cached` | Cached/reused tokens | ✅ Populated |
| `thoughts` | Thinking/reasoning tokens | ✅ Populated |
| `tool` | Tool-specific tokens | ❌ Always 0 |
| `total` | Sum of all token types | ✅ Populated |

### Limitations

1. **`tool` field unused**: Despite having a dedicated field, it's always 0
2. **Message-level only**: Tokens are per-message, not per-tool-call
3. **Multiple tools per message**: When a message has multiple tool calls, tokens cannot be separated
4. **No official documentation**: Google has not documented per-tool token plans

### What We CAN Extract

Gemini CLI logs contain:
- Full tool arguments (in `args` object)
- Full tool results (in `result` array)
- Message-level tokens (can be correlated to tools)
- Tool names and timing

This data enables **token estimation** based on content size.

### Built-in Tool Tracking (v1.2.0)

As of schema v1.2.0, mcp-audit tracks built-in tools (read_file, list_directory, google_web_search, etc.) in session files:

```json
{
  "builtin_tool_summary": {
    "total_calls": 12,
    "total_tokens": 0,
    "tools": [
      {"tool": "read_file", "calls": 6, "tokens": 0},
      {"tool": "google_web_search", "calls": 4, "tokens": 0},
      {"tool": "list_directory", "calls": 2, "tokens": 0}
    ]
  }
}
```

**Note**: Gemini CLI doesn't provide per-tool token attribution. Tokens are reported at message level only, so `tokens` is always 0. Call counts are tracked accurately.

---

## Reasoning/Thinking Tokens (v1.3.0)

Starting with schema v1.3.0, mcp-audit tracks reasoning/thinking tokens separately from output tokens. This provides more accurate cost analysis for models that include thinking tokens.

### Platform Support

| Platform | Field Name | Schema v1.3.0 Field | Notes |
|----------|------------|---------------------|-------|
| Claude Code | N/A | `reasoning_tokens: 0` | Claude doesn't expose thinking tokens |
| Codex CLI | `reasoning_output_tokens` | `reasoning_tokens` | Present in o1, o3-mini, and similar models |
| Gemini CLI | `thoughts` | `reasoning_tokens` | Present in Gemini 2.0+ responses |

### Impact on Token Counts

**Before v1.3.0:**
- `output_tokens` = output + reasoning (combined)
- Reasoning tokens hidden inside output total

**After v1.3.0:**
- `output_tokens` = output only
- `reasoning_tokens` = thinking/reasoning tokens separately
- `total_tokens` = input + output + reasoning + cache_read (for TUI display)

### TUI Display Behavior

The reasoning tokens row is displayed conditionally:

```
# When reasoning_tokens > 0 (Codex CLI, Gemini CLI):
╭─ Token Usage ────────────────────╮
│  Input:      10,000              │
│  Output:     2,000               │
│  Reasoning:  500                 │
│  Cache Read: 50,000              │
│  Total:      62,500              │
╰──────────────────────────────────╯

# When reasoning_tokens == 0 (Claude Code):
╭─ Token Usage ────────────────────╮
│  Input:      10,000              │
│  Output:     2,000               │
│  Cache Read: 50,000              │
│  Total:      62,000              │
╰──────────────────────────────────╯
```

This auto-hiding behavior ensures the TUI remains clean for platforms that don't support thinking tokens.

---

## Token Estimation Plan

Since Codex CLI and Gemini CLI don't provide native per-tool token attribution, mcp-audit can **estimate** MCP tool token usage using tokenizer libraries.

### Approach

Use the actual tool call content (arguments and results) to estimate token counts:

```
Estimated MCP Tokens = tokenize(tool_arguments) + tokenize(tool_results)
```

### Implementation

#### 1. Token Estimator Module

```python
# src/mcp_audit/estimation.py

import json
from typing import Optional, Tuple

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False


class TokenEstimator:
    """Estimate token counts for MCP tool calls.

    Uses tiktoken when available, falls back to character-based
    approximation otherwise.
    """

    def __init__(self, model: str = "gpt-4"):
        """Initialize estimator.

        Args:
            model: Model name for tokenizer selection.
                   Uses cl100k_base encoding for GPT-4/GPT-5 models.
        """
        self._encoding = None
        if TIKTOKEN_AVAILABLE:
            try:
                self._encoding = tiktoken.encoding_for_model(model)
            except KeyError:
                # Fall back to cl100k_base for unknown models
                self._encoding = tiktoken.get_encoding("cl100k_base")

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.

        Args:
            text: Text to tokenize.

        Returns:
            Estimated token count.
        """
        if not text:
            return 0

        if self._encoding:
            return len(self._encoding.encode(text))

        # Fallback: ~4 characters per token (rough approximation)
        return len(text) // 4

    def estimate_tool_call(
        self,
        args: Optional[dict],
        result: Optional[str]
    ) -> Tuple[int, int]:
        """Estimate input and output tokens for a tool call.

        Args:
            args: Tool call arguments (dict or None).
            result: Tool call result (string or None).

        Returns:
            Tuple of (estimated_input_tokens, estimated_output_tokens).
        """
        # Serialize arguments to JSON string
        args_text = json.dumps(args) if args else ""
        result_text = str(result) if result else ""

        input_tokens = self.estimate_tokens(args_text)
        output_tokens = self.estimate_tokens(result_text)

        return input_tokens, output_tokens
```

#### 2. Adapter Integration

```python
# In codex_cli_adapter.py

class CodexCLIAdapter(BaseTracker):
    def __init__(self, ...):
        # ...
        self._estimator = TokenEstimator(model="gpt-4")

    def _process_tool_call(self, tool_name: str, args: dict, result: str):
        # Get native tokens (will be 0 for Codex)
        native_tokens = 0  # Not available

        # Estimate tokens from content
        estimated_input, estimated_output = self._estimator.estimate_tool_call(
            args=args,
            result=result
        )
        estimated_total = estimated_input + estimated_output

        # Track with estimation flag
        self._track_mcp_tool(
            tool_name=tool_name,
            tokens=estimated_total,
            is_estimated=True
        )
```

#### 3. Display Integration

```python
# In rich_display.py

def _build_tools(self, snapshot: DisplaySnapshot) -> Panel:
    # Build title with estimation indicator
    title = f"MCP Servers Usage ({num_servers} servers, {total_calls} calls)"
    if snapshot.has_estimated_tokens:
        title += " - Estimated*"

    # ... existing display code ...

    # Add footnote for estimated tokens
    if snapshot.has_estimated_tokens:
        content.append(
            "\n  * Tokens estimated from tool arguments and results",
            style="dim italic"
        )

    return Panel(content, title=title, border_style="yellow")
```

#### 4. User-Facing Display

**With estimation enabled:**
```
╭─ MCP Servers Usage (2 servers, 5 calls) - Estimated* ─╮
│                                                        │
│  brave-search       2 calls    ~1.2K  (avg ~600/call) │
│    └─ brave_web_search   2 calls    ~1.2K             │
│                                                        │
│  context7           3 calls    ~2.5K  (avg ~833/call) │
│    └─ resolve-library-id   3 calls    ~2.5K           │
│                                                        │
│  ────────────────────────────────────────────────────  │
│  Total MCP: 5 calls  (~3.7K estimated tokens)          │
│                                                        │
│  * Tokens estimated from tool arguments and results    │
╰────────────────────────────────────────────────────────╯
```

### What Estimation Measures

| Metric | Meaning | Use Case |
|--------|---------|----------|
| Estimated Input | Tokens in tool arguments | How much context sent to tool |
| Estimated Output | Tokens in tool results | How much context returned from tool |
| Total Estimated | Combined tool I/O | Overall MCP context load |

### What Estimation Does NOT Measure

- Actual model billing tokens
- System prompt overhead
- Model reasoning about tool calls
- Internal formatting tokens
- Cache efficiency

### Accuracy Considerations

**tiktoken (when available):**
- Very accurate for OpenAI models (GPT-4, GPT-5, Codex)
- Reasonable approximation for other models
- Uses cl100k_base encoding by default

**Fallback (without tiktoken):**
- Uses ~4 characters per token heuristic
- Less accurate but still useful for relative comparisons
- No additional dependencies required

### Value Proposition

Even as estimates, MCP tool token tracking provides:

1. **Relative comparisons**: Which MCP servers use the most context?
2. **Efficiency insights**: Are tool results excessively large?
3. **Optimization targets**: Which tools should be optimized?
4. **Cross-session trends**: Is MCP usage growing over time?

This is **unique functionality** - competitors like ccusage only track session-level tokens.

---

## Future Possibilities

### Platform Improvements

We're monitoring these platforms for native per-tool token support:

- **Codex CLI**: OpenAI could add `tokens` field to `function_call` events
- **Gemini CLI**: Google could populate the existing `tool` token field

If these become available, mcp-audit will automatically use native values.

### Feature Requests

Consider filing feature requests:
- OpenAI Codex: Request per-tool token attribution in JSONL output
- Google Gemini: Request population of the `tool` token field

---

## References

- [tiktoken](https://github.com/openai/tiktoken) - OpenAI's fast BPE tokenizer
- [Codex CLI Reference](https://developers.openai.com/codex/cli/reference) - Official Codex documentation
- [ccusage Codex Guide](https://ccusage.com/guide/codex/) - Third-party usage tracking
