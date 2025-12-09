# Changelog

All notable changes to MCP Audit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Note:** Starting with v0.5.0, all entries reference GitHub Issues (e.g., `[#16](url)`).
> Earlier versions reference internal task IDs (e.g., `Task 69`).

## [0.4.2] - 2025-12-09

### Changed
- **README overhaul for better onboarding**
  - New "What mcp-audit Does (At a Glance)" section with categorized features
  - Highlighted platform Getting Started guides in Documentation section
  - Renamed FAQ sections: "MCP Problems mcp-audit Helps Solve" and "Usage & Support FAQ"
  - Consolidated Compatibility section (Python + Platform support)
  - Dynamic version badge in "What's New" section
- **PyPI page improvements**
  - All relative links converted to full GitHub URLs for PyPI compatibility
  - Fixed GitHub-only `[!TIP]` alert syntax for cross-platform rendering
  - Converted HTML table to Markdown for consistent rendering
  - Added `Source` and `Discussions` project URLs

### Fixed
- **PyPI URL verification** - Publish workflow now runs from public repo
  - OIDC token originates from `littlebearapps/mcp-audit` (public)
  - All GitHub URLs now eligible for PyPI "Verified" status
  - New `publish-pypi.yml` workflow for Trusted Publishing

## [0.4.1] - 2025-12-08

### Fixed
- **Demo GIF display on PyPI** - Use absolute URL for cross-platform compatibility

## [0.4.0] - 2025-12-08

### Added
- **MCP tool token estimation for Codex CLI and Gemini CLI** (Task 69)
  - `TokenEstimator` class with platform-specific tokenizers
  - Codex CLI: tiktoken o200k_base (~99-100% accuracy)
  - Gemini CLI: SentencePiece/Gemma (100%) or tiktoken fallback (~95%)
  - Per-tool estimated tokens shown in TUI and session logs
  - `FUNCTION_CALL_OVERHEAD` constant (25 tokens) for API formatting
- **Schema v1.4.0** - Per-call estimation metadata
  - `is_estimated` field indicates estimated vs native tokens
  - `estimation_method` field (tiktoken/sentencepiece/character)
  - `estimation_encoding` field (o200k_base/gemma/cl100k_base)
- **Theme system with Catppuccin support** (Task 83)
  - Catppuccin Mocha (dark) and Latte (light) color palettes
  - High-contrast themes (hc-dark, hc-light) meeting WCAG AAA
  - Auto-detection of terminal background color
  - `--theme` CLI option: auto, dark, light, hc-dark, hc-light
  - `MCP_AUDIT_THEME` environment variable
- **ASCII mode** for terminals without unicode support
  - `--ascii` flag or `MCP_AUDIT_ASCII=1` environment variable
  - Box-drawing with ASCII characters, no emoji
- **NO_COLOR standard compliance** - [no-color.org](https://no-color.org/)
  - Set `NO_COLOR=1` to disable all color output
- **GitHub Release download for Gemma tokenizer** (Task 96)
  - `mcp-audit tokenizer download` fetches from GitHub Releases (no signup)
  - `--source` flag (github/huggingface)
  - `--release` flag to download specific version
  - SHA256 checksum verification
  - Version tracking via `tokenizer.meta.json`
- **"Noisy fallback" pattern** - Users informed when using approximate accuracy
  - One-time hint during Gemini CLI collection about tokenizer download
  - `mcp-audit tokenizer status` shows accuracy implications
- **Manual installation guide** - `docs/manual-tokenizer-install.md` for corporate networks

### Changed
- **Package size reduced from ~5MB to <500KB** - Gemma tokenizer now optional download
  - Pip package no longer bundles the 4MB tokenizer
  - Tokenizer available via `mcp-audit tokenizer download`
  - Gemini CLI works immediately with ~95% accuracy (tiktoken fallback)
- **TUI enhancements**
  - Token panel title shows estimation method when applicable
  - Final summary shows estimation stats (e.g., "5 calls with tiktoken estimation")
  - Theme-aware colors throughout
- **Improved `mcp-audit tokenizer status` output** - Clearer terminology
  - Shows "Downloaded (persistent)" instead of "cached"
  - Displays version and download timestamp

### Security
- **Path traversal protection** for tarball extraction (`_validate_tarball_member()`)
- **SHA256 checksum verification** for downloaded tokenizer integrity

### Notes
- **Gemini CLI users**: Run `mcp-audit tokenizer download` for 100% token accuracy
- **Claude Code users**: No action needed - has native per-tool token attribution
- **Codex CLI users**: No action needed - uses tiktoken (~99-100% accuracy)
- Corporate network users: See `docs/manual-tokenizer-install.md`

## [0.3.14] - 2025-12-06

### Added
- **Schema v1.3.0: Reasoning tokens** - Track thinking/reasoning tokens separately from output
  - `reasoning_tokens` field in `token_usage` block
  - Codex CLI: maps to `reasoning_output_tokens` (o-series models)
  - Gemini CLI: maps to `thoughts` (Gemini 2.0+ responses)
  - Claude Code: always 0 (no thinking tokens exposed)
  - TUI displays "Reasoning" row only when > 0 (auto-hides for Claude Code)
- **Schema v1.2.0: Built-in tool tracking** - Persist built-in tool stats to session files
  - `builtin_tool_summary` block with per-tool calls and tokens
  - Claude Code: Full token attribution per built-in tool
  - Codex CLI / Gemini CLI: Call counts only (no per-tool tokens)
- **BUILTIN_TOOLS documentation** - Official tool names from upstream sources
  - `CLAUDE_CODE_BUILTIN_TOOLS` (18 tools) from anthropics/claude-code
  - `CODEX_BUILTIN_TOOLS` (11 tools) from openai/codex
  - `GEMINI_BUILTIN_TOOLS` (12 tools) from google-gemini/gemini-cli
- **Automated test harness** - Cross-platform testing scripts
  - `scripts/test-harness.sh` - Automated testing with `--platform` and `--quick` flags
  - `scripts/compare-results.sh` - Test result analysis and regression detection
  - `docs/automated-testing-plan.md` - Complete test strategy documentation
  - `docs/local-testing-guide.md` - Manual testing procedures
- **Comprehensive platform validation** - Tasks 75-77 completed
  - Claude Code, Codex CLI, and Gemini CLI thoroughly validated
  - Evidence directories with TUI captures and session analysis

### Changed
- **Data contract** - Updated to schema v1.3.0 with full backward compatibility
  - Added `reasoning_tokens` field documentation
  - Added `builtin_tool_summary` block documentation (v1.2.0)
  - Updated platform-specific behavior tables
- **Platform documentation** - Updated PLATFORM-TOKEN-CAPABILITIES.md
  - Documented reasoning token support per platform
  - Documented built-in tool tracking differences

### Fixed
- **Codex CLI token double-counting** (Task 79) - Critical bug fix
  - Root cause: Codex CLI native logs contain duplicate `token_count` events
  - Old behavior: Summing `last_token_usage` (delta) caused double-counting
  - New behavior: Use cumulative `total_token_usage` and REPLACE session totals
  - Accurate token tracking regardless of duplicate events in logs

## [0.3.13] - 2025-12-03

### Added
- **Gemini CLI adapter rewrite** - Complete rewrite to parse native JSON session files
  - No OTEL/telemetry setup required - reads `~/.gemini/tmp/<hash>/chats/session-*.json` directly
  - Project hash auto-detection from working directory (SHA256)
  - Per-message token tracking: input, output, cached, thoughts, tool, total
  - Thinking tokens tracked separately (`thoughts_tokens` field)
  - Tool call detection via `toolCalls` array with `mcp__` prefix filtering
  - Model detection from session data
- **Codex CLI adapter enhancements** - File-based session reading without subprocess wrapping
  - Session auto-discovery with `--latest` flag
  - Date range filtering with `--since` and `--until` options
  - File watcher for live session monitoring
- **Platform-aware reports** - New `--platform` filter for `mcp-audit report`
  - Multi-platform aggregation in reports
  - Platform breakdown in summary statistics
- **Unified cost comparison** - Cross-platform cost efficiency analysis
  - Cost per 1M tokens by platform
  - Cost per session by platform
  - "Most efficient platform" indicator
- **Setup guides** - Comprehensive documentation for each platform
  - `docs/codex-cli-setup.md` - Codex CLI installation and usage
  - `docs/gemini-cli-setup.md` - Gemini CLI installation and usage
- **Gemini model pricing** - Added Gemini 2.0, 2.5, and 3.0 series to `mcp-audit.toml`
- **Codex model pricing** - Added GPT-5 series and Codex-specific models

### Changed
- **Gemini CLI** - Removed OTEL telemetry dependency entirely
- **Documentation** - Updated architecture.md, ROADMAP.md, platform docs for new adapters
- **Examples** - Updated gemini-cli-session example with new JSON format

### Fixed
- **Gemini CLI tracking** - Now works out-of-the-box without any telemetry configuration

## [0.3.12] - 2025-12-02

### Fixed
- **Public sync workflow** - Fixed sync to include hidden files (.github/)
- **GitHub topics** - Synced 14 repository topics to public repo

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
