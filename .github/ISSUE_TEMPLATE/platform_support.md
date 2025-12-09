---
name: Platform Support Request
about: Request support for a new platform or CLI tool
title: '[PLATFORM] Add support for '
labels: enhancement, needs-triage
assignees: ''
---

## Platform Information

> **Privacy Note**: Do not include API keys, tokens, or sensitive file paths in your report.

**Platform Name**:
<!-- e.g., Aider, Cursor, Custom CLI -->

**Official Website**:
<!-- Link to project homepage -->

**GitHub Repository** (if applicable):
<!-- Link to repository -->

**Documentation**:
<!-- Link to relevant documentation -->

## Platform Details

**Type**:
- [ ] AI coding assistant CLI
- [ ] IDE with MCP support
- [ ] Custom tool/framework
- [ ] Other (please specify)

**MCP Integration**:
- [ ] Native MCP support
- [ ] MCP via plugin/extension
- [ ] No MCP support (requires investigation)
- [ ] Unknown

**Debug/Log Output**:
<!-- How does this platform expose session data? -->

**Typical Log Location**:
<!-- e.g., ~/.platform/logs/debug.log -->

## Use Case

**Why do you need support for this platform?**

**How many users would benefit?**
- [ ] Just me
- [ ] Small team (2-5)
- [ ] Organization (6+)
- [ ] Large community

## Technical Information

### Sample Output

<!-- If possible, provide sample debug log or output from this platform -->

```
Paste sample output here
```

### Session Format

<!-- How does this platform structure session data? -->

**Known data format**:
- [ ] JSON
- [ ] JSONL
- [ ] Plain text
- [ ] Custom format
- [ ] Unknown

### Interception Strategy

<!-- How would MCP Audit capture data from this platform? -->

- [ ] File watcher (monitor log file)
- [ ] Process wrapper (wrap CLI execution)
- [ ] API integration (if available)
- [ ] Stdin/stdout capture
- [ ] Unknown (needs investigation)

## Research Completed

<!-- Have you investigated how to integrate with this platform? -->

**Documentation reviewed**:
- [ ] Platform documentation
- [ ] MCP integration docs
- [ ] Debug/logging capabilities
- [ ] Not yet

**Findings**:
<!-- Share any relevant findings or challenges discovered -->

## Implementation Willingness

**Would you be willing to help implement this?**
- [ ] Yes - I can contribute code
- [ ] Yes - I can test and provide feedback
- [ ] Yes - I can provide sample data/logs
- [ ] No - Requesting as feature only

## Additional Context

<!-- Any other information that would help with implementation -->

## Related Issues

<!-- Link any related issues or discussions -->
