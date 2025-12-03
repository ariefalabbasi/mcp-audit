# Example Gemini CLI Session

This directory contains example session data from a Gemini CLI MCP tracking session.

## Files

- `telemetry-sample.jsonl` - Sample OpenTelemetry events from Gemini CLI

## Session Details

- **Platform**: Gemini CLI
- **Model**: gemini-2.5-pro
- **Duration**: ~5 minutes
- **MCP Tools Used**: zen (chat, thinkdeep), brave-search (web)

## Telemetry Format

Gemini CLI exports OpenTelemetry metrics in JSON Lines format. Each line is a metric event:

```json
{"name": "gemini_cli.token.usage", "attributes": {"model": "gemini-2.5-pro", "type": "input"}, "value": 1234}
{"name": "gemini_cli.tool.call.count", "attributes": {"function_name": "mcp__zen__chat", "tool_type": "mcp", "success": true}, "value": 1}
{"name": "gemini_cli.tool.call.latency", "attributes": {"function_name": "mcp__zen__chat"}, "value": 456}
```

## Key Attributes

- `tool_type: "mcp"` - Distinguishes MCP tools from native tools
- `type: "thought"` - Gemini-specific thinking/reasoning tokens
- `model` - Auto-detected model identifier

## Usage

```bash
# To track your own Gemini CLI sessions:
mcp-audit collect --platform gemini-cli

# To generate a report:
mcp-audit report ~/.mcp-audit/sessions/gemini_cli/
```

See [Gemini CLI Setup Guide](../../docs/platforms/gemini-cli.md) for detailed instructions.
