# MCP Audit – GitHub Issues, Milestones & Documentation Integration Guide  
_For use inside the `mcp-audit` repository with Claude Code or other AI development agents._

This document explains **exactly how issues, milestones, the roadmap, CHANGELOG, and README** should connect.  
Claude Code must read and follow this guide before implementing tasks, modifying docs, or preparing releases.

---

# 1. Purpose of This Guide
This file defines:
- how **GitHub Issues** represent implementation tasks  
- how **Milestones** group issues into version releases  
- how **ROADMAP.md**, **CHANGELOG.md**, and **README.md** should reference (or avoid referencing) issues  
- how Claude Code should update each file  
- how tasks flow from idea → Issue → Milestone → PR → Changelog → Release  

It acts as the **canonical workflow** for development inside the `mcp-audit` project.

---

# 2. Core Principles

### ✔ Issues = Source of Truth for All Work  
Every implementation task MUST have an Issue:
- bugs  
- features  
- improvements  
- refactors  
- documentation tasks  
- roadmap items  
- milestone items  

### ✔ Milestones = Version Buckets  
Milestones represent:
- `v0.5.0`  
- `v0.6.0`  
- `v0.7.0`  
- `v0.8.0`  
- `v0.9.0`  
- `v1.0.0`  

An Issue MUST be assigned to one Milestone unless it is long-term backlog.

### ✔ README must NOT contain issues or milestones  
The README is **evergreen** and should never mention:
- Issue numbers  
- PR numbers  
- Milestones  

Only high‑level “What’s New” summary belongs in README.

### ✔ ROADMAP links to Milestones (not individual Issues)  
ROADMAP.md should:
- show high‑level version goals  
- link to GitHub Milestones  
- avoid listing Issue numbers  

### ✔ CHANGELOG references Issue numbers  
CHANGELOG.md is where all Issue numbers belong.  
Each release section must include:
- “Added”, “Changed”, “Fixed”, “Removed”  
- Issue numbers (e.g. `(#84)`)  

---

# 3. File‑by‑File Rules for Claude Code

## 3.1 README.md  
### Claude MUST NOT:
- add Issue numbers  
- add Milestone references  
- add implementation details  
- describe future versions  

### Claude MAY:
- update the “What’s New in vX.Y.Z” section with **high‑level** features only  
- update feature explanations  
- update supported agents, usage examples, tables, badges  

### NOTE  
If Claude thinks something belongs in README, it must confirm:
**“Is this evergreen? Is this onboarding content?”**

If not → it goes into MS, Roadmap, or Changelog.

---

## 3.2 ROADMAP.md  
ROADMAP.md contains:
- high‑level release themes  
- version purpose  
- links to Milestones  

### Claude MUST:
- keep ROADMAP.md human‑readable  
- update future version goals as Milestones evolve  
- link to Milestones at the bottom of each release section  

### Claude MUST NOT:
- list Issue numbers in ROADMAP.md  
- copy the entire Milestone contents into the file  

### Example (Correct):
```
## v0.6.0 — Platform Layer
- Multi-model token telemetry
- Minimal Ollama CLI adapter
- Static/dynamic payload metrics

➡️ Milestone: https://github.com/littlebearapps/mcp-audit/milestone/3
```

---

## 3.3 CHANGELOG.md  
CHANGELOG.md is the ONLY place that ties Issue numbers to releases.

### Claude MUST:
- add Issue numbers  
- add PR numbers (if applicable)  
- follow Keep-a-Changelog style  
- add changes under “Added / Changed / Fixed / Removed” headings  

### Claude MUST NOT:
- add vague descriptions  
- use marketing language  
- skip Issue numbers  

---

## 3.4 Issues (GitHub)  
### Claude MUST:
- create a GitHub Issue for ALL meaningful work  
- assign appropriate labels (`bug`, `feature`, `docs`, `enhancement`)  
- assign the Issue to a Milestone  
- write clear acceptance criteria  

### Claude MAY:
- link docs or code snippets inside Issues  
- propose design notes  
- refine tasks into smaller Issues  

### Claude MUST NOT:
- bypass Issues by working directly from Backlog.md  
- create PRs without an Issue reference  

---

## 3.5 Milestones  
Milestones represent version releases.

### Claude MUST:
- assign every Issue to a Milestone  
- update Milestone descriptions when needed  
- avoid overstuffing Milestones (move work to later versions if needed)  

### Claude MUST NOT:
- close Milestones prematurely  
- duplicate Milestones or create micro-versions

---

# 4. Workflow: Idea → Issue → Milestone → PR → Changelog → Release

## Step 1 — Idea captured  
- Backlog.md (optional local buffer)  
- or straight to GitHub Issue  

## Step 2 — Issue created  
Issue includes:
- title  
- description  
- acceptance criteria  
- labels  
- assigned Milestone  

## Step 3 — Development  
Claude Code uses the Issue as its plan.  
Claude MUST reference the Issue in all commits/PRs.

## Step 4 — PR  
PR title includes:
```
feat: <feature> (#issueNumber)
```

## Step 5 — Changelog update  
Claude updates CHANGELOG.md:
```
### Added
- Smell detection engine (#84)
```

## Step 6 — Release  
When Milestone is complete:
- Milestone is closed  
- GitHub Release Notes generated  
- CHANGELOG.md becomes final record  

---

# 5. Claude Code Operational Checklist

Before making any code or documentation changes, Claude MUST ask:

### 1. Does this require an Issue?
If yes → create or reference one.

### 2. Does this change belong in:
- README? → Only if evergreen & onboarding  
- ROADMAP? → Only if adjusting version goals  
- CHANGELOG? → Only for historical version notes  
- Docs? → If it changes user/developer behaviour  
- Milestone? → If it's part of planned work  

### 3. Have I updated all linked components?
For example:
- New feature → Issue + Milestone + CHANGELOG  
- Doc update → Issue + docs folder  
- New version release → CHANGELOG + README high‑level notes + Release Notes  

### 4. Am I avoiding README bloat?
README must stay clean.

---

# 6. How This Benefits AI Agents & Future Contributors

Using Issues + Milestones correctly allows:
- Claude Code to fully automate roadmap execution  
- precise PR generation  
- clean release notes  
- automatic GEO improvements (AIs love structured project metadata)  
- better onboarding for future contributors  
- consistent documentation changes  

This system turns MCP Audit into a **mature, professional OSS project**.

---

# 7. Summary (Rules in One Block)

```
README      → NO issues, NO milestones, high-level current version only  
ROADMAP     → Link to milestones, NO issue numbers  
CHANGELOG   → Issue numbers REQUIRED  
Issues      → Every task goes here  
Milestones  → Every Issue assigned to one milestone  
PRs         → MUST reference Issue numbers  
```

Claude Code must follow this framework for all future development inside mcp-audit.

---

If updates to this workflow are required, modify this file and notify Claude Code.
