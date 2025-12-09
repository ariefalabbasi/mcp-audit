# GitHub Issues Integration Investigation

**Date**: 2025-12-09
**Status**: Complete
**Decision**: **ENABLE GitHub Issues** on public repo with specific configuration

---

## Executive Summary

### Recommendation: Enable GitHub Issues on Public Repo

After investigating the dual-repo architecture, Claude Code gh CLI capabilities, documentation impacts, and workflow integration options, the recommendation is to **enable GitHub Issues on the public repository** (`littlebearapps/mcp-audit`) with the following configuration:

| Aspect | Decision |
|--------|----------|
| **Where to enable** | Public repo only |
| **Issue types** | Bug reports and platform support requests |
| **Feature requests** | Keep in Discussions (Ideas category) |
| **Questions** | Keep in Discussions (Q&A category) |
| **Backlog.md sync** | Manual, one-way (public Issues → Backlog.md tasks when triaged) |
| **Label taxonomy** | Platform-specific + severity + type labels |

### Why Enable Issues?

1. **Standard contributor expectation** - Most open-source projects use Issues for bug reports
2. **Better triage workflow** - Issues have assignments, milestones, projects
3. **Claude Code integration** - `gh` CLI provides full Issue CRUD from terminal
4. **Template support** - Issue templates already exist (bug_report.md, feature_request.md, platform_support.md)
5. **Separation of concerns** - Bug reports (actionable) vs Discussions (exploratory)

### Why NOT Sync Bidirectionally?

1. **252 internal tasks** - Backlog.md has extensive internal tracking not suitable for public
2. **Privacy** - Internal task details, implementation notes shouldn't be public
3. **Duplication overhead** - Maintaining sync would add friction without clear benefit
4. **Different lifecycles** - Internal tasks have sprints/versions; public issues have community timing

---

## Part 1: Repository Architecture Analysis

### Current State

| Repository | Visibility | Issues | Discussions | Purpose |
|------------|------------|--------|-------------|---------|
| `littlebearapps/mcp-audit-master` | Private | Enabled (unused) | Enabled | Internal development |
| `littlebearapps/mcp-audit` | Public | Enabled (redirected) | Enabled | PyPI distribution, community |

**Key Finding**: Both repos have Issues enabled, but the public repo's `.github/ISSUE_TEMPLATE/config.yml` redirects all issue creation to Discussions:

```yaml
blank_issues_enabled: false
contact_links:
  - name: Feature Request
    url: https://github.com/littlebearapps/mcp-audit/discussions/new?category=ideas
  - name: Question or Help
    url: https://github.com/littlebearapps/mcp-audit/discussions/new?category=q-a
```

### Existing Issue Templates

Three well-designed templates exist but are currently unused:

1. **Bug Report** (`bug_report.md`) - Comprehensive with environment, reproduction steps, session data
2. **Feature Request** (`feature_request.md`) - Includes platform relevance, priority self-assessment
3. **Platform Support** (`platform_support.md`) - Detailed template for new CLI platform requests

### Recommendation: Enable Issues on Public Only

**Rationale**:
- Public repo is the community touchpoint
- Master repo uses Backlog.md for internal tracking
- Issue numbers won't conflict (different repos, different sequences)
- Commits referencing `#123` in master won't auto-link to public Issues (intentional separation)

---

## Part 2: Claude Code + gh CLI Integration

### Capabilities Verified

The `gh` CLI (v2.78.0) provides full GitHub Issues management from Claude Code:

| Operation | Command | Status |
|-----------|---------|--------|
| List issues | `gh issue list --repo littlebearapps/mcp-audit` | ✅ Works |
| View issue | `gh issue view 123 --repo littlebearapps/mcp-audit` | ✅ Works |
| Create issue | `gh issue create --title "..." --body "..." --label bug` | ✅ Works |
| Close issue | `gh issue close 123` | ✅ Works |
| Add comment | `gh issue comment 123 --body "..."` | ✅ Works |
| Edit issue | `gh issue edit 123 --title "..." --add-label "..."` | ✅ Works |
| Search issues | `gh issue list --search "query"` | ✅ Works |
| Transfer issue | `gh issue transfer 123 other-repo` | ✅ Works |

### Workflow Integration Points

Claude Code can effectively:

1. **Triage incoming issues** - Read issue, assess severity, add labels
2. **Create issues from findings** - During testing, create bug reports
3. **Link commits to issues** - Include `Fixes #123` in commit messages
4. **Update issue status** - Close with resolution, add comments for progress
5. **Cross-reference** - Link to Discussions or external resources

### Example Claude Code Workflow

```bash
# View new issues needing triage
gh issue list --repo littlebearapps/mcp-audit --label "needs-triage"

# Add labels after investigation
gh issue edit 42 --add-label "bug,platform:claude-code,priority:medium" --remove-label "needs-triage"

# Create issue from test failure
gh issue create --repo littlebearapps/mcp-audit \
  --title "[BUG] TUI shows incorrect token count for nested MCP tools" \
  --body "..." \
  --label "bug,platform:claude-code"

# Close with reference
gh issue close 42 --comment "Fixed in v0.4.1 via commit abc123"
```

---

## Part 3: Documentation Impact Assessment

### README.md Changes Required

The README already has an Issues link at the bottom:

```markdown
[Issues](https://github.com/littlebearapps/mcp-audit/issues) · [Discussions](https://github.com/littlebearapps/mcp-audit/discussions) · [Roadmap](ROADMAP.md)
```

**Recommendation**: Add clarity in the "Contributing" section:

```markdown
## 🤝 Contributing

- **Bug reports**: [Open an Issue](https://github.com/littlebearapps/mcp-audit/issues/new?template=bug_report.md)
- **Feature ideas**: [Start a Discussion](https://github.com/littlebearapps/mcp-audit/discussions/new?category=ideas)
- **Questions**: [Ask in Discussions](https://github.com/littlebearapps/mcp-audit/discussions/new?category=q-a)
```

### CONTRIBUTING.md Changes Required

Section "Pull Request Workflow" mentions:

> 2. **Open an issue first** - For significant changes, discuss before coding

This is correct behavior. Additional clarification:

```markdown
### Before You Start

1. **Bug fixes**: Check if an [Issue](https://github.com/littlebearapps/mcp-audit/issues) already exists
2. **New features**: Start a [Discussion](https://github.com/littlebearapps/mcp-audit/discussions/new?category=ideas) first
```

### ROADMAP.md - No Changes Needed

ROADMAP already links to Discussions for feature requests. This is correct:
- **Ideas** → Discussions (exploratory, community input)
- **Bugs** → Issues (actionable, trackable)

### CHANGELOG.md Integration

When closing issues that are bug fixes, CHANGELOG entries should reference:

```markdown
## [0.4.2] - 2025-12-15

### Fixed
- TUI shows incorrect token count for nested MCP tools ([#42](https://github.com/littlebearapps/mcp-audit/issues/42))
```

---

## Part 4: Label Taxonomy

### Proposed Labels

| Category | Labels | Purpose |
|----------|--------|---------|
| **Type** | `bug`, `enhancement`, `documentation`, `question` | Issue classification |
| **Platform** | `platform:claude-code`, `platform:codex-cli`, `platform:gemini-cli` | Platform-specific |
| **Priority** | `priority:critical`, `priority:high`, `priority:medium`, `priority:low` | Triage |
| **Status** | `needs-triage`, `confirmed`, `in-progress`, `blocked`, `wontfix` | Workflow |
| **Special** | `good first issue`, `help wanted`, `duplicate` | Community |

### Default GitHub Labels to Remove

The default labels are too generic. Remove:
- `invalid` (use `wontfix` with explanation)
- `question` (redirect to Discussions)

---

## Part 5: Backlog.md ↔ GitHub Issues Strategy

### Current State

- **Backlog.md**: 252 tasks across internal development
- **GitHub Issues**: 0 public issues (template redirect active)

### Recommended Strategy: Manual One-Way Sync

```
Public Issue Created → Maintainer Triages → Creates Backlog.md Task (if valid)
                                         → Closes with "wontfix" (if invalid)
                                         → Redirects to Discussion (if feature request)
```

**Why not bidirectional?**

1. **Privacy**: Internal tasks contain implementation details not for public
2. **Scale**: 252 internal tasks would flood public Issues
3. **Noise**: Not all internal tasks are community-relevant
4. **Automation complexity**: Sync scripts add maintenance burden

### Workflow

1. **New Issue arrives** → Gets `needs-triage` label automatically
2. **Claude Code triages** → Read issue, understand problem, add appropriate labels
3. **If valid bug**:
   - Create corresponding Backlog.md task: `task-XXX - [GH#42] Bug description`
   - Add `confirmed` label to Issue
   - Add comment: "Thanks for reporting! Tracked internally."
4. **If feature request**:
   - Transfer to Discussions (Ideas category)
   - Close Issue with redirect link
5. **When fixed**:
   - Close Issue with `Fixes #42` in commit
   - Update Backlog.md task to Done
   - Add to CHANGELOG with Issue reference

### Issue → Backlog.md Task Naming Convention

```
task-XXX - [GH#42] Short description from issue title
```

This makes it easy to:
- Search Backlog.md for GitHub Issue references
- Link back from Issue to internal task (in private comments/notes)

---

## Part 6: Security and Privacy Considerations

### Sensitive Information in Bug Reports

The bug report template requests:
- Python version
- OS version
- mcp-audit version
- Session data (JSON snippet)

**Risk**: Users might paste full session logs containing:
- File paths (reveals system structure)
- Project names (reveals work context)
- Tool call parameters (may contain prompts)

**Mitigation**:
1. Template already says "redact sensitive info"
2. Add explicit warning about what NOT to include
3. Maintainer can edit issues to redact if needed

### Internal Task References

**DO NOT** include in public Issues:
- Backlog.md task IDs (reveals internal numbering)
- Internal implementation details
- Release timing information
- Private quickref documentation

**OK to include**:
- General acknowledgment ("tracked internally")
- Version target ("planned for v0.5.0")
- Technical approach (high-level)

---

## Part 7: Implementation Plan

### Phase 1: Enable Issues (Immediate)

1. Update `.github/ISSUE_TEMPLATE/config.yml`:
   ```yaml
   blank_issues_enabled: false
   contact_links:
     - name: Feature Request
       url: https://github.com/littlebearapps/mcp-audit/discussions/new?category=ideas
       about: Suggest new features. We use Discussions to gather community input.
     - name: Question or Help
       url: https://github.com/littlebearapps/mcp-audit/discussions/new?category=q-a
       about: Ask questions about usage, troubleshooting, or best practices.
   ```
   (Remove "Show and Tell" redirect - not needed in Issue templates)

2. Verify issue templates are active:
   - Bug Report → Creates Issue
   - Feature Request → Redirects to Discussions
   - Platform Support → Creates Issue

### Phase 2: Label Setup

Create labels via gh CLI:
```bash
# Platform labels
gh label create "platform:claude-code" --color "D97757" --description "Claude Code specific"
gh label create "platform:codex-cli" --color "412991" --description "Codex CLI specific"
gh label create "platform:gemini-cli" --color "8E75B2" --description "Gemini CLI specific"

# Priority labels
gh label create "priority:critical" --color "B60205" --description "Blocking issue"
gh label create "priority:high" --color "D93F0B" --description "Important"
gh label create "priority:medium" --color "FBCA04" --description "Normal priority"
gh label create "priority:low" --color "0E8A16" --description "Minor issue"

# Status labels
gh label create "needs-triage" --color "EDEDED" --description "Awaiting maintainer review"
gh label create "confirmed" --color "0E8A16" --description "Bug confirmed"
gh label create "in-progress" --color "0075CA" --description "Being worked on"
gh label create "blocked" --color "B60205" --description "Blocked by external factor"

# Delete defaults that don't fit
gh label delete "invalid" --yes
```

### Phase 3: Documentation Updates

1. Update README.md Contributing section
2. Update CONTRIBUTING.md "Before You Start" section
3. Add security/privacy guidance to bug report template

### Phase 4: Workflow Activation

1. Create GitHub Action for auto-labeling new issues with `needs-triage`
2. Document triage workflow for maintainers
3. Test end-to-end: Issue → Triage → Backlog.md → Fix → Close

---

## Appendix A: Files to Modify

| File | Change |
|------|--------|
| `.github/ISSUE_TEMPLATE/config.yml` | Remove redirect, enable Bug Report + Platform Support |
| `.github/ISSUE_TEMPLATE/bug_report.md` | Add privacy warning |
| `README.md` | Add contribution type guidance |
| `CONTRIBUTING.md` | Clarify Issue vs Discussion usage |
| `CLAUDE.md` | Add Issue triage workflow reference |

---

## Appendix B: Decision Log

| Question | Decision | Rationale |
|----------|----------|-----------|
| Enable Issues on master repo? | No | Use Backlog.md for internal |
| Enable Issues on public repo? | Yes | Standard open-source practice |
| Bidirectional sync? | No | Privacy, scale, complexity |
| Feature requests in Issues? | No | Keep in Discussions for community input |
| Questions in Issues? | No | Keep in Discussions for async Q&A |
| Bug reports in Issues? | Yes | Actionable, trackable |
| Platform support in Issues? | Yes | Structured input needed |

---

## Appendix C: gh CLI Commands Reference

### Triage Workflow

```bash
# List new issues needing triage
gh issue list -R littlebearapps/mcp-audit -l "needs-triage"

# View issue details
gh issue view 42 -R littlebearapps/mcp-audit

# Add labels after triage
gh issue edit 42 -R littlebearapps/mcp-audit \
  --add-label "bug,platform:claude-code,priority:medium,confirmed" \
  --remove-label "needs-triage"

# Comment on issue
gh issue comment 42 -R littlebearapps/mcp-audit \
  --body "Thanks for reporting! I can reproduce this. Tracking internally."

# Close issue
gh issue close 42 -R littlebearapps/mcp-audit \
  --comment "Fixed in v0.4.2. See CHANGELOG for details."

# Transfer to Discussions (feature requests)
gh issue close 42 -R littlebearapps/mcp-audit \
  --comment "Thanks for the suggestion! I've moved this to [Discussions](link) where we gather community input on new features."
```

### Create Issue (from test findings)

```bash
gh issue create -R littlebearapps/mcp-audit \
  --template "bug_report.md" \
  --title "[BUG] Description" \
  --label "bug,priority:medium"
```

---

**Document Prepared By**: Claude Code
**Approved By**: Pending maintainer review
**Last Updated**: 2025-12-09
