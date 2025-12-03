# Changelog

All notable changes to MCP Audit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.11] - 2025-12-02

### Added
- **Collapsible table of contents** - README now has expandable TOC for easier navigation
- **GIF caption** - Demo GIF has descriptive caption like competitor ccusage
- **Lightweight badge** - Added <500KB install size feature highlight

### Changed
- **README overhaul** - Complete restructuring with competitor comparison, better messaging, and improved layout
  - Side-by-side audience cards for MCP developers and power users
  - Collapsible FAQ section with accordions
  - Enhanced "Why mcp-audit?" section with ccusage distinction
  - SEO improvements for discoverability
- **Repository hygiene** - Internal development files now gitignored (CLAUDE.md, quickref/, backlog/, etc.)

## [0.3.10] - 2025-12-01

### Added
- **Version display** - TUI header now shows mcp-audit version and session logs include `mcp_audit_version` field
- **Comprehensive adapter tests** - Added `test_codex_cli_adapter.py` with 28 tests for Codex CLI format

### Fixed
- **Codex CLI adapter** - Rewrote `parse_event()` to handle actual JSONL format correctly (#24)
  - `turn_context` events for model detection
  - `event_msg` with `token_count` for usage tracking
  - `response_item` with `function_call` for MCP tool calls
- **FAQ section** - Added common questions to README

## [0.3.9] - 2025-11-30

### Fixed
- **Claude Code tracking** - Fixed critical bug where new session files created during monitoring were missed
  - Root cause: `_find_jsonl_files()` filtered out empty files (`st_size > 0`)
  - When Claude Code creates a new session file (initially empty), mcp-audit excluded it
  - Once Claude Code wrote content, mcp-audit found the file but set position to END, missing all events
  - Fix: Include all .jsonl files, check file creation time for new files discovered during monitoring
  - If file created after tracking started, read from beginning (position 0)
  - If file created before, read only new content (position at END)

## [0.3.8] - 2025-11-30

### Fixed
- **Session token tracking** - Track session tokens for all assistant messages, not just MCP calls (#21)

## [0.3.7] - 2025-11-30

### Changed
- **Single source version** - Version now defined only in `pyproject.toml`, read dynamically via `importlib.metadata`
- **Email update** - Changed contact email from contact@ to help@littlebearapps.com
- **Release docs** - Added Releasing section to CLAUDE.md with version flow and checklist

### Fixed
- **Version mismatch** - CLI `--version` now always matches PyPI package version (was showing 0.3.4 when package was 0.3.5)

## [0.3.6] - 2025-11-30

### Fixed
- **Version sync** - Synced `__version__` in `__init__.py` with `pyproject.toml` (both now 0.3.6)

## [0.3.5] - 2025-11-30

### Added
- **Auto GitHub Releases** - Version bumps now auto-create GitHub Releases with generated notes
- **Dependencies badge** - Added libraries.io badge to README

### Changed
- **Model pricing** - Updated mcp-audit.toml with all current models (Claude, OpenAI, Gemini) with USD labels
- **TUI display** - Cost now shows "Cost (USD):" for clarity

### Removed
- **Legacy files** - Removed COMMANDS.md, model-pricing.json, usage-wp-nav.sh, live-session-tracker.sh
- **TestPyPI** - Removed unused TestPyPI job from publish workflow

## [0.3.4] - 2025-11-29

### Changed
- **Codebase cleanup** - Removed 12 legacy Python scripts from root directory (now in src/mcp_audit/)
- **Documentation updates** - Updated all docs to use `mcp-audit` CLI instead of npm scripts
- **PyPI keywords** - Updated keywords for better discoverability (context-window, token-tracking, llm-cost)

### Fixed
- **Type annotations** - Fixed all mypy strict mode errors in session_manager.py, cli.py, and storage.py
- **Project name detection** - Now correctly detects git worktree setups (project-name/main → project-name)
- **Troubleshooting docs** - Complete rewrite to use `mcp-audit` CLI commands

## [0.3.2] - 2025-11-25

### Added
- **CodeQL workflow** - Explicit `codeql.yml` for badge compatibility and consistent security scanning
- **Auto-tag workflow** - Automatic git tagging on version bumps for seamless PyPI publishing
- **Release documentation** - Added Releasing section to CONTRIBUTING.md

## [0.3.1] - 2025-11-25

### Added
- **GitHub topics** - 10 topics for discoverability (mcp, claude-code, codex-cli, etc.)
- **CONTRIBUTING.md** - Root-level contributing guide (GitHub standard location)
- **Makefile** - Build targets for gpm verify (lint, typecheck, test, build)

### Changed
- **README badges** - Updated to shields.io format with PyPI version/downloads
- **Installation docs** - Added pipx as installation option
- **CLAUDE.md** - Added explicit PR merge approval requirement

### Fixed
- **CI workflow** - Hardened publish.yml to require CI pass before PyPI publish
- **gpm integration** - Fixed mypy verification to only check src/ directory

## [0.3.0] - 2025-11-25

### Added
- **PyPI distribution** - Now installable via `pip install mcp-audit` or `pipx install mcp-audit`
- **Rich TUI display** - Beautiful terminal dashboard with live updating panels
  - Auto TTY detection (TUI for terminals, plain text for CI)
  - Display modes: `--tui`, `--plain`, `--quiet`
  - Configurable refresh rate with `--refresh-rate`
- **Gemini CLI adapter** - Full support for tracking Gemini CLI sessions via OpenTelemetry
- **Display adapter pattern** - Modular display system (RichDisplay, PlainDisplay, NullDisplay)
- **CLI command** - `mcp-audit` command with `collect` and `report` subcommands
- **Proper package structure** - Modern `src/` layout following Python packaging best practices
- **Type hints** - Full type annotations with `py.typed` marker for editor support
- **GitHub Actions** - Automated CI/CD pipeline with PyPI publishing on releases
- **JSONL storage system** - Efficient session storage with indexing for fast queries
- **Platform adapters** - Modular architecture for adding new platform support

### Changed
- Restructured project from flat files to `src/mcp_audit/` package
- Updated from Phase 1 (Foundation) to Phase 2 (Public Beta)
- Improved test organization with dedicated `tests/` directory
- Enhanced pyproject.toml with modern Python packaging standards

### Fixed
- License deprecation warnings in setuptools
- Test imports for new package structure

## [0.2.0] - 2025-11-24

### Added
- **BaseTracker abstraction** - Platform-agnostic tracker base class
- **Schema v1.0.0** - Locked data schema with backward compatibility guarantees
- **Pricing configuration** - TOML-based model pricing with Claude and OpenAI support
- **CI/CD pipeline** - GitHub Actions with pytest, mypy, ruff, and black
- **JSONL storage** - Session persistence with 57 comprehensive tests
- **Complete documentation** - Architecture docs, data contract, contributing guide

### Changed
- Migrated from single-file scripts to modular architecture
- Added strict mypy type checking
- Standardized code formatting with black

## [0.1.0] - 2025-11-18

### Added
- Initial implementation
- Claude Code session tracking
- Codex CLI session tracking
- Real-time token usage display
- Cross-session analysis
- Duplicate detection
- Anomaly detection
