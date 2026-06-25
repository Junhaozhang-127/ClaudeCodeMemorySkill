<p align="right"><a href="README.zh-CN.md">中文</a> | <b>English</b></p>

# Claude Code Memory Skill

A production-grade local memory system and session workspace manager for Claude Code. Transforms ephemeral chat sessions into a persistent, searchable, and manageable knowledge base.

**v0.7.0** — 352 tests, zero failures. MIT licensed.

---

## Table of Contents

1. [What Problems This Solves](#what-problems-this-solves)
2. [Architecture Overview](#architecture-overview)
3. [Installation](#installation)
4. [Quick Start](#quick-start)
5. [Feature Guide](#feature-guide)
   - [Memory Persistence & Auto-Save](#1-memory-persistence--auto-save)
   - [Retrieval — Keyword, Semantic & Hybrid](#2-retrieval--keyword-semantic--hybrid)
   - [LLM Summarization](#3-llm-summarization)
   - [Slash Command System](#4-slash-command-system)
   - [Memory Lifecycle Management](#5-memory-lifecycle-management)
   - [Session Workspace Manager](#6-session-workspace-manager)
   - [Linked Session Retrieval](#7-linked-session-retrieval)
   - [Interactive Session TUI](#8-interactive-session-tui)
6. [Project Structure](#project-structure)
7. [Configuration Reference](#configuration-reference)
8. [Testing](#testing)
9. [Documentation Index](#documentation-index)
10. [Known Limitations](#known-limitations)
11. [Security & Privacy](#security--privacy)

---

## What Problems This Solves

### Problem 1: Session Isolation

Every Claude Code session starts with a blank slate. When you switch sessions — or start a new one tomorrow — all prior project context, bug root causes, architectural decisions, and pending TODOs are gone. You end up re-explaining the same things or re-discovering the same conclusions.

**How this solves it**: Auto-saves every session as structured Markdown memory. On your next session, your first prompt triggers a retrieval that injects the top 5 most relevant historical memories directly into Claude's context.

### Problem 2: Keyword Search Can't Find "Similar but Different"

You remember discussing "how to handle multi-user memory isolation" but your keyword search for "isolation" returns nothing because the original discussion used the term "workspace separation." Keyword matching fails when vocabulary differs.

**How this solves it**: Embedding-based semantic retrieval understands meaning, not just words. A query for "memory isolation" finds "workspace separation" discussions. When an embedding API key is unavailable, it gracefully falls back to keyword search with logging.

### Problem 3: Too Many Unrelated Memories

As your memory bank grows, sifting through hundreds of memories from different projects becomes noise. You need a way to organize memories by project context.

**How this solves it**: Session Workspace Manager gives each project its own isolated memory space. Save memories to the right session. Retrieve memories only from the sessions you care about. Link related sessions together.

### Problem 4: Memory Rot

Old memories accumulate. You don't know which ones are still relevant, which are stale, or which are duplicates.

**How this solves it**: Built-in lifecycle management — TTL-based auto-expiry, content-hash exact dedup, similarity-based near-duplicate detection, quality reports, and archive/merge/compact tools.

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────────┐
│                    Claude Code Session                      │
│                                                             │
│  /memory save ───┐               ┌── /memory retrieve       │
│  /memory manage ─┤               ├── /memory session        │
│  Hook: Stop ─────┘               └── Hook: PrePrompt ───────│
└──────────┬──────────────────────────────┬───────────────────┘
           │ save                          │ retrieve + inject
           ▼                               ▼
┌─────────────────────────────────────────────────────────────┐
│                   CommandRegistry Layer                      │
│                                                              │
│  commands/memory_save.py    commands/memory_retrieve.py      │
│  commands/memory_manage.py  commands/memory_session.py       │
│  commands/memory_rebuild.py                                  │
└──────────┬──────────────────────────────┬───────────────────┘
           │                              │
           ▼                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Core Engine                             │
│                                                              │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────────┐  │
│  │ memory_core  │  │ retrieval.py  │  │ summarizers.py   │  │
│  │ save/retrieve│  │ Keyword/Hybrid│  │ RuleBased/LLM    │  │
│  │ format/index │  │ Semantic      │  │ SummaryResult    │  │
│  └──────┬───────┘  └───────┬───────┘  └────────┬─────────┘  │
│         │                  │                    │            │
│  ┌──────┴──────────────────┴────────────────────┴─────────┐  │
│  │              Pluggable Providers                        │  │
│  │  embedding_provider.py  │  llm_provider.py              │  │
│  │  Fake ↔ OpenAI-compatible API                            │  │
│  └─────────────────────────────────────────────────────────┘  │
└──────────┬───────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│                  Session Workspace Layer                     │
│                                                              │
│  session_manager.py     session_tui.py    session_cli.py     │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  .memory/sessions/                                     │  │
│  │    index.json          ← Global session registry       │  │
│  │    current.json        ← Current session pointer       │  │
│  │    <session_id>/                                       │  │
│  │      manifest.json     ← Session metadata              │  │
│  │      memories.jsonl    ← Memory records mirror         │  │
│  │      links.json        ← Linked session graph          │  │
│  │      events.jsonl      ← Operation audit log           │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

The system is layered: **Command handlers** receive user input → **Core engine** processes save/retrieve/summarize → **Session workspace** organizes by context → **Pluggable providers** handle embedding/LLM (auto-fallback to rule-based when unconfigured).

---

## Installation

```bash
git clone https://github.com/Junhaozhang-127/ClaudeCodeMemorySkill.git
cd ClaudeCodeMemorySkill

# Zero mandatory dependencies — runs on Python 3.7+ stdlib
pip install jieba              # Optional: enhanced Chinese word segmentation
pip install httpx              # Optional: faster HTTP for OpenAI-compatible APIs
```

**Requirements**: Python 3.7+. All core functionality works with standard library alone.

---

## Quick Start

### Save and Retrieve (30 seconds)

```bash
# 1. Save your first memory
python scripts/summarize_session.py \
  --topic "Architecture Decision" \
  --text "Decided to use Redis for caching. Key constraint: max 256MB per instance."

# 2. Retrieve it back
python scripts/retrieve_memory.py --query "caching architecture" --json

# 3. Check what's in your memory bank
python scripts/memory_stats.py
```

### Create a Session Workspace

```bash
# Create a project workspace and switch to it
python scripts/session_cli.py create --title "My Project" --use

# Now all saves go to this session automatically
python scripts/summarize_session.py --topic "Bug #42" --text "Root cause: race condition in worker pool"

# List all sessions
python scripts/session_cli.py list

# Open the interactive session selector
python scripts/session_cli.py tui
```

---

## Feature Guide

### 1. Memory Persistence & Auto-Save

Every conversation is distilled into structured Markdown with five semantic sections:

| Section | Content | Extraction Method |
|---------|---------|-------------------|
| **摘要** (Summary) | Concise overview, first 3-5 sentences | Sentence segmentation + length cap |
| **关键词** (Keywords) | 10 most salient terms | jieba + regex fallback, stop-word filtered |
| **关键决策** (Decisions) | Architectural choices, confirmed approaches | Trigger-word matching (决定/采用/确认/finalize) |
| **待办事项** (TODOs) | Action items, pending fixes | Trigger-word matching (需要/TODO/FIXME/implement) |
| **原始对话** (Raw Text) | Full conversation excerpt | Verbatim, code-fence escaped |

**Auto-save behavior**: A turn counter tracks conversation rounds. Every N turns (default 10), the hook `auto_save.sh` triggers `summarize_session.py`. You can configure the interval:

```bash
export MEMORY_AUTO_SAVE_INTERVAL=5   # Save every 5 turns
export MEMORY_AUTO_SAVE_INTERVAL=0   # Disable turn-based auto-save
```

Three hook events are registered in `plugin.json`:

| Hook Event | Trigger | Action |
|------------|---------|--------|
| `UserPromptSubmit` (auto_save) | Every N turns | Save current conversation |
| `UserPromptSubmit` (pre_prompt) | Before each response | Retrieve + inject related memories |
| `Stop` (post_conversation) | Session end | Final save of all unsaved content |

**Intelligent merge**: Saving to the same topic doesn't create duplicate files. It appends to the existing Markdown, merges keywords/decisions/todos with deduplication, preserves the original `created_at`, and refreshes `updated_at`.

### 2. Retrieval — Keyword, Semantic & Hybrid

Three retrieval backends, selected via `--mode`:

| Mode | Mechanism | Best For | Requires |
|------|-----------|----------|----------|
| `keyword` | Multi-field weighted token matching (topic ≥ keywords > decisions ≥ todos > summary) + recency boost | Exact term lookup, fast, zero deps | Nothing |
| `semantic` | Embedding vector cosine similarity | Finding conceptually related but differently-worded content | `EMBEDDING_API_KEY` or Fake provider |
| `hybrid` | keyword (40%) + semantic (60%) weighted merge | Best of both — precision + recall | `EMBEDDING_API_KEY` or Fake provider |

**Scoring breakdown**: Every result includes `score_breakdown` showing exactly which fields contributed to the score and by how much. This makes retrieval decisions auditable.

**Graceful degradation**: If `EMBEDDING_API_KEY` is not set and you request `semantic` or `hybrid` mode, the system automatically falls back to `keyword` with a clear log warning. No crash, no error.

**Session-aware retrieval** (v0.7.0): By default, `retrieve_memory` only searches the current session's memories. You can expand scope:

```python
# Current session only (default)
retrieve_memory("architecture")

# Specific session
retrieve_memory("architecture", session_id="abc123")

# All active sessions
retrieve_memory("architecture", all_sessions=True)

# Current session + linked sessions
retrieve_memory("architecture", include_linked_sessions=True)
```

### 3. LLM Summarization

Two summarizer implementations implementing the `BaseSummarizer` interface:

| Summarizer | Mechanism | Quality | Requires |
|------------|-----------|---------|----------|
| `RuleBasedSummarizer` | Sentence segmentation + trigger-word extraction | Structured but mechanical | Nothing |
| `LLMSummarizer` | LLM API (OpenAI-compatible) | Context-aware, semantic | `LLM_API_KEY` |

Three summary types for different use cases:

| Type | What It Produces | Use Case |
|------|-----------------|----------|
| `brief` | 2-3 sentence gist | List previews, quick scanning |
| `semantic` | Goals, constraints, decisions, conclusions | Deep understanding of a discussion |
| `memory` | Reusable facts, user preferences, project state, pending leads | Memory compression for future retrieval |

**Long text handling**: Texts exceeding ~4000 characters are automatically split at sentence boundaries, each chunk summarized independently, then merged with deduplication. Results are marked `partial: True` and `mode: llm_chunked`.

**Fallback chain**: `LLMSummarizer` with API key → `LLMSummarizer` with FakeProvider → `RuleBasedSummarizer`. Fallback results carry `mode: rule_fallback` metadata. The system never crashes due to a missing API key.

### 4. Slash Command System

Five slash commands registered in `CommandRegistry`, each with argument validation, structured `CommandResult`, and edit-distance suggestions for typos:

```
/memory save       <topic> --text <content> [--session-id <id>] [--summary-mode rule|llm|auto]
/memory retrieve   <query> [--mode keyword|semantic|hybrid] [--session-id <id>] [--all-sessions] [--include-linked-sessions]
/memory rebuild    [--workspace <name>]
/memory manage     <action>   actions: quality / dedup / expire / merge / archive
/memory session    <action>   actions: list / create / current / use / rename / archive / delete / restore / info / link / unlink / links / tui
```

Commands are discoverable through both `commands/*.md` frontmatter (Claude Code auto-discovery) and `plugin.json` `commands` section (manifest-based). Both paths coexist.

**Command propagation**:
```
User types "/memory retrieve architecture"
  → Claude Code reads commands/memory-retrieve.md frontmatter
  → Dispatches to CommandRegistry.get("memory:retrieve")
  → Validates args against args_schema
  → Calls handler → memory_core.retrieve_memory()
  → Returns structured CommandResult
```

### 5. Memory Lifecycle Management

Every memory record carries 23 metadata fields including lifecycle state:

```
MemoryRecord:
  Core:    topic, file, keywords, summary, created_at, updated_at
  Extract: decisions, todos
  v0.6.0:  memory_id, tags, source, last_accessed_at, access_count,
           confidence, importance, status, expires_at, merged_into,
           content_hash, embedding_hash, embedding_model, ttl_days,
           lifecycle_reason
  v0.7.0:  session_id, session_title
```

**Status state machine**:

```
active ──→ archived ──→ expired
  │            │
  ├── merged ──┘
  └── deleted
```

All state transitions are logged with reason and timestamp. The `lifecycle_reason` field records why a state change occurred.

**Quality report** (`memory:manage quality`): Returns a diagnostic summary:

```json
{
  "total": 41,
  "active": 38, "archived": 0, "expired": 0, "merged": 2, "deleted": 1,
  "duplicate_candidates": 3,
  "near_duplicate_candidates": 5,
  "expired_candidates": 12,
  "low_quality_count": 7,
  "recommended_actions": [
    "过期 12 条: 运行 /memory manage expire --apply",
    "重复 3 对: 运行 /memory manage dedup"
  ]
}
```

**Maintenance tools**:

| Command | Function |
|---------|----------|
| `detect-duplicates` | Find memory pairs with Jaccard keyword similarity ≥ threshold |
| `merge --topic` | Combine 2+ duplicate records into one, backing up originals |
| `compact --topic` | Trim old conversation blocks, keep summary + recent N blocks |
| `archive-old --days` | Move memories older than N days to `memory/archive/` |

All destructive operations default to `--dry-run`. Add `--apply` to execute.

### 6. Session Workspace Manager

Each session is a self-contained directory under `.memory/sessions/`:

```
.memory/sessions/
├── index.json               # Global registry: {"version":"0.7.0","sessions":[...]}
├── current.json             # Pointer: {"current_session_id":"abc123"}
├── default/                 # Auto-created default session
│   ├── manifest.json        # SessionManifest metadata
│   ├── memories.jsonl       # Memory records (append-only JSON lines)
│   ├── summaries.jsonl      # Summary records
│   ├── embeddings.jsonl     # Embedding vectors
│   ├── links.json           # Linked sessions graph
│   ├── events.jsonl         # Audit log (create/rename/delete/restore/set_current...)
│   └── trash/               # Soft-delete staging
└── <session_id>/            # User-created sessions (same structure)
```

**Session lifecycle** (12 operations via `/memory session`):

| Action | Example | Behavior |
|--------|---------|----------|
| `create` | `create --title "Book Review" --use` | Creates directory + all files, optionally switches |
| `list` | `list --include-archived` | Lists sessions with status/memory count/linked count |
| `current` | `current` | Shows current session ID, title, path |
| `use` | `use --session-id abc123` | Switches current session (writes `current.json`) |
| `rename` | `rename --session-id abc123 --title "New"` | Updates manifest + index |
| `archive` | `archive --session-id abc123` | Sets status=archived (default session protected) |
| `delete` | `delete --session-id abc123` | Soft delete — status change only, directory preserved |
| `restore` | `restore --session-id abc123 --use` | Restores deleted→active, optionally switches |
| `info` | `info --session-id abc123` | Full manifest + file status + events count |
| `link` | `link --to abc123 --reason "related"` | Links current session to another |
| `unlink` | `unlink --to abc123` | Removes link |
| `links` | `links --session-id abc123` | Lists linked sessions with status/memory count |

**Default session protection**: The `default` session (session_id=`"default"`) is auto-created on first init. It cannot be archived or deleted. If somehow corrupted, `ensure_default_session()` forcibly restores it.

**Soft delete**: `delete_session()` sets `status = "deleted"` and logs the event. The directory and all files remain intact. `restore_session()` sets `status = "active"` again. Physical deletion never happens without explicit user action.

**Event audit trail**: Every operation on a session appends a JSON line to `events.jsonl`:

```json
{"event_id":"uuid","event_type":"session_linked","session_id":"abc","timestamp":"...","details":{"target_session_id":"xyz","reason":"related project"}}
```

### 7. Linked Session Retrieval

Sessions can be explicitly linked to form a retrieval graph. When you query with `include_linked_sessions=True`, the system searches not just your current session, but all sessions it's linked to.

**Use case**: You have a "Book Review" session and a "Format Fixer" session. They contain related work. Link them:

```bash
/memory session link --to <format-fixer-session-id> --reason "shared manuscript processing"
```

Now when you retrieve from "Book Review" with `--include-linked-sessions`, results from "Format Fixer" also appear — each marked with `[linked]` in the output.

**Link data model** (`links.json`):

```json
{
  "version": "0.7.0",
  "linked_sessions": [
    {
      "session_id": "abc123",
      "title": "Format Fixer",
      "linked_at": "2026-06-25 12:00:00",
      "link_type": "manual",
      "reason": "shared manuscript processing"
    }
  ],
  "updated_at": "2026-06-25 12:00:00"
}
```

**Retrieval scopes summary**:

| Parameters | Searches |
|------------|----------|
| *(default)* | Current session only |
| `session_id=X` | Session X only |
| `all_sessions=True` | All active sessions (overrides linked) |
| `include_linked_sessions=True` | Current + linked sessions |
| `include_archived_sessions=True` | Expands scope to include archived |

### 8. Interactive Session TUI

A terminal-based session browser invoked via `python scripts/session_cli.py tui` or `/memory session tui`.

```
——————————————————————————————————————————————————————————————————————————
Session Workspace Manager — v0.7.0

Current: Project Alpha / abc123

UP/DOWN:move ENTER:use DEL:delete N:new R:rename A:archive L:links V:archived D:deleted H:help Q:quit

> * Project Alpha         active    mem: 42   linked:  2   [default]
  ○ Book Review Phase 5   active    mem: 31   linked:  1
  ○ Format Fixer Dev      active    mem: 15   linked:  0
  ○ Old Migration Test    archived  mem:  3   linked:  0

Message: Switched to Project Alpha
——————————————————————————————————————————————————————————————————————————
```

**Keyboard controls**:

| Key | Action | Notes |
|-----|--------|-------|
| ↑/↓ | Navigate list | Bounded; stays within range |
| Enter | Switch to selected session | Blocks archived/deleted; shows message |
| Delete | Soft delete | Double-press to confirm; default session blocked |
| N | Create new session | Prompts for title; Enter to confirm, Esc to cancel |
| R | Rename selected | Pre-fills current title; edit in place |
| A | Archive selected | Default session blocked |
| L | Show linked sessions | Displays linked session IDs and titles |
| V | Toggle archived visibility | Shows/hides archived sessions in list |
| D | Toggle deleted visibility | Shows/hides deleted sessions in list |
| H / ? | Show help overlay | Lists all shortcuts |
| Q / Esc | Quit TUI | Session unchanged unless you pressed Enter |

**Architecture**: The TUI is built in three decoupled layers — `SessionTUIState` (data), `SessionTUIController` (business logic), `SessionTUIRenderer` (pure text output). Controller and renderer have zero terminal I/O dependencies, making them fully unit-testable (47 tests). Cross-platform input uses `msvcrt` on Windows and `termios` on Unix.

---

## Project Structure

```
ClaudeMeory/
│
├── scripts/                         # Core engine (22 modules)
│   │
│   ├── memory_core.py               # Central: save_memory, retrieve_memory, format_context,
│   │                                  rebuild_index, MemoryRecord dataclass (25 fields)
│   │
│   ├── retrieval.py                 # BaseRetriever ABC, KeywordRetriever (multi-field weighted),
│   │                                  SemanticRetriever (embedding cosine sim),
│   │                                  HybridRetriever (keyword + semantic merge, 3 modes)
│   │
│   ├── summarizers.py               # BaseSummarizer ABC, SummaryResult, EnhancedSummaryResult,
│   │                                  RuleBasedSummarizer (trigger-word extraction),
│   │                                  LLMSummarizer (3 summary types, chunk-merge pipeline)
│   │
│   ├── embedding_provider.py        # EmbeddingProvider ABC, FakeEmbeddingProvider (ngram-based
│   │                                  deterministic vectors), OpenAIEmbeddingProvider (urllib)
│   │
│   ├── embedding_cache.py           # JSON-file embedding cache with SHA256 content-hash keys,
│   │                                  model-change auto-invalidation
│   │
│   ├── llm_provider.py              # LLMProvider ABC, FakeLLMProvider (rule-based extraction
│   │                                  for testing), OpenAILLMProvider (urllib)
│   │
│   ├── memory_lifecycle.py          # Status state machine (5 states, 8 transitions),
│   │                                  TTL auto-expiry, generate_quality_report
│   │
│   ├── memory_maintenance.py        # CLI: detect-duplicates (Jaccard), merge, compact, archive-old
│   │
│   ├── session_manager.py           # SessionManager (~800 lines): CRUD, link, unlink, events,
│   │                                  SessionManifest/SessionIndex/CurrentSession/SessionEvent
│   │
│   ├── session_tui.py               # Interactive TUI: SessionTUIState, SessionTUIController,
│   │                                  SessionTUIRenderer, cross-platform key input
│   │
│   ├── session_cli.py               # argparse CLI: 12 subcommands (create/list/use/.../tui)
│   │
│   ├── config.py                    # MemoryConfig dataclass, config.json read/write,
│   │                                  env var override chain (CLI > env > config > default)
│   │
│   ├── logging_utils.py             # Rotating file logger, sanitized (no full transcripts)
│   │
│   ├── workspace_manager.py         # Project-level workspace isolation (legacy→v0.5.0)
│   │
│   ├── memory_stats.py              # Memory bank statistics (count, size, top keywords)
│   │
│   ├── version.py                   # Version info + capability status
│   │
│   ├── health_check.py              # System health: structure, Python env, memory integrity
│   ├── install.py / uninstall.py    # Installation management
│   ├── upgrade.py                   # Legacy → workspace migration
│   ├── release_prepare.py           # Pre-release cleanup
│   ├── run_acceptance.py            # Acceptance test suite
│   ├── turn_counter.py              # Turn-based auto-save counter
│   ├── auto_save_memory.py          # Auto-save orchestrator
│   └── summarize_session.py         # CLI: save memory from --text or --file
│       retrieve_memory.py           # CLI: retrieve memory with --query
│       update_index.py              # CLI: rebuild index.json from Markdown files
│
├── commands/                        # Slash command handlers (v0.6.0)
│   ├── base.py                      # Command dataclass, CommandResult dataclass
│   ├── registry.py                  # CommandRegistry: register, get (by name/alias), dispatch,
│   │                                  edit-distance suggestions for typos
│   ├── memory_save.py               # /memory save handler (session-aware)
│   ├── memory_retrieve.py           # /memory retrieve handler (session + linked aware)
│   ├── memory_rebuild.py            # /memory rebuild handler
│   ├── memory_manage.py             # /memory manage handler (quality/dedup/expire/merge/archive)
│   ├── memory_session.py            # /memory session handler (12 actions)
│   ├── memory-save.md               # Slash command declaration (YAML frontmatter)
│   ├── memory-retrieve.md           # Slash command declaration
│   ├── memory-rebuild.md            # Slash command declaration
│   └── session.md                   # Slash command declaration
│
├── hooks/                           # Cross-platform hook scripts
│   ├── post_conversation.sh/.bat/.ps1    # Stop hook: save on session end
│   ├── pre_prompt.sh/.bat/.ps1           # UserPromptSubmit: retrieve before response
│   └── auto_save.sh/.bat/.ps1            # UserPromptSubmit: turn-based auto-save
│
├── .claude-plugin/                  # Claude Code plugin metadata
│   ├── plugin.json                  # Manifest: name, version, hooks, commands, userConfig
│   └── marketplace.json             # Self-hosted marketplace entry
│
├── memory/                          # Storage (gitignored)
│   ├── index.json                   # Primary topic index
│   ├── .memory/sessions/            # Session workspaces (v0.7.0)
│   │   ├── index.json               # Global session registry
│   │   ├── current.json             # Current session pointer
│   │   └── <id>/                    # Per-session directory
│   └── topics/                      # Markdown memory files
│
├── docs/                            # Documentation
│   ├── SESSION_WORKSPACE.md         # Session workspace full guide
│   ├── SMOKE_TEST.md                # Real API provider manual verification
│   ├── CAPABILITY_MATRIX.md         # ~50 capability status items
│   ├── PROJECT_STRUCTURE.md         # Architecture deep-dive
│   ├── SUMMARIZER_DESIGN.md         # Pluggable summarizer design
│   ├── DEVELOPMENT_ROADMAP.md       # 5-phase development roadmap
│   ├── HOOK_SETUP.md                # Hook configuration guide
│   ├── FAQ.md                       # Frequently asked questions
│   ├── config.example.json          # Config file template
│   ├── settings.template.json       # Hook settings template
│   └── releases/                    # Per-version release summaries
│       ├── v0.6.0-release-summary.md
│       └── v0.7.0-release-summary.md
│
├── tests/                           # 352 tests, 0 failures
│   ├── test_memory_skill.py         # v0.5.0–v0.6.0: 153 tests (core, summarizer, CLI, hooks)
│   ├── test_session_manager.py      # v0.7.0 Phase 1: 52 tests
│   ├── test_session_commands.py     # v0.7.0 Phase 2: 38 tests
│   ├── test_memory_session_integration.py # v0.7.0 Phase 3: 33 tests
│   ├── test_linked_session_retrieval.py   # v0.7.0 Phase 4: 29 tests
│   └── test_session_tui.py          # v0.7.0 Phase 5: 47 tests
│
├── SKILL.md                         # Skill behavior rules (Claude Code)
├── CHANGELOG.md                     # v0.1.0 → v0.7.0 full changelog
├── README.md                        # This file (English)
├── README.zh-CN.md                  # Chinese README
├── LICENSE                          # MIT
├── LIMITATIONS.md                   # Known limitations (detailed)
├── RELEASE_CHECKLIST.md             # Release procedure
├── requirements.txt                 # Optional deps
├── install.sh                       # One-click install script
└── .gitignore
```

---

## Configuration Reference

**Priority chain**: CLI arguments > environment variables > `config.json` > built-in defaults

### Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `CLAUDE_MEMORY_WORKSPACE` | `""` | Workspace name for project isolation |
| `CLAUDE_MEMORY_DIR` | `memory` | Memory storage root directory |
| `MEMORY_AUTO_SAVE_INTERVAL` | `10` | Auto-save every N turns (0 = disable) |
| `CLAUDE_MEMORY_LOG_LEVEL` | `INFO` | Log level: DEBUG / INFO / WARNING / ERROR |

### Retrieval Settings (v0.6.0)

| Variable | Default | Description |
|----------|---------|-------------|
| `CLAUDE_MEMORY_RETRIEVAL_MODE` | `hybrid` | Default mode: keyword / semantic / hybrid |

### Embedding Provider (v0.6.0)

| Variable | Default | Description |
|----------|---------|-------------|
| `EMBEDDING_API_KEY` | `""` | OpenAI-compatible API key (unset → FakeProvider) |
| `EMBEDDING_API_BASE` | `https://api.openai.com/v1` | API base URL |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Model name |

### LLM Provider (v0.6.0)

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_API_KEY` | `""` | OpenAI-compatible API key (unset → FakeProvider) |
| `LLM_API_BASE` | `https://api.openai.com/v1` | API base URL |
| `LLM_MODEL` | `gpt-4o-mini` | Model name |

### Session Settings (v0.7.0)

| Variable | Default | Description |
|----------|---------|-------------|
| `SESSION_ENABLED` | `true` | Enable session workspace |
| `SESSION_ROOT` | `.memory/sessions` | Session directory root |
| `DEFAULT_SESSION_ID` | `"default"` | Default session ID |

### Lifecycle Settings (v0.6.0)

| Variable | Default | Description |
|----------|---------|-------------|
| `DEFAULT_TTL_DAYS` | `365` | Default time-to-live for memories |
| `SHORT_TERM_TTL_DAYS` | `30` | Short-term memory TTL |
| `AUTO_EXPIRE_ENABLED` | `false` | Auto-expire memories on save |

---

## Testing

```bash
# Full test suite (352 tests, 0 failures)
python -m pytest -q

# By phase
python -m pytest tests/test_memory_skill.py -v            # v0.6.0 core: 153 tests
python -m pytest tests/test_session_manager.py -v          # Phase 1: 52 tests
python -m pytest tests/test_session_commands.py -v         # Phase 2: 38 tests
python -m pytest tests/test_memory_session_integration.py -v # Phase 3: 33 tests
python -m pytest tests/test_linked_session_retrieval.py -v   # Phase 4: 29 tests
python -m pytest tests/test_session_tui.py -v              # Phase 5: 47 tests

# By feature
python -m pytest -v -k "Embedding or Semantic or HybridMode"  # Retrieval
python -m pytest -v -k "LLM or Summarizer"                    # Summarization
python -m pytest -v -k "Command"                              # Commands
python -m pytest -v -k "Lifecycle or Dedup or Quality"        # Lifecycle
python -m pytest -v -k "Session"                              # Sessions

# Acceptance tests
python scripts/run_acceptance.py --quick
```

---

## Documentation Index

| Document | Contents |
|----------|----------|
| `README.md` / `README.zh-CN.md` | This document — overview, architecture, feature guide |
| `SKILL.md` | Slash command definitions, save/retrieve rules, fallback strategies |
| `CHANGELOG.md` | Full changelog: v0.1.0 (MVP) through v0.7.0 (Session Workspace) |
| `docs/SESSION_WORKSPACE.md` | Session workspace: setup, commands, TUI, linked retrieval, migration |
| `docs/SMOKE_TEST.md` | Manual verification: real API embedding + LLM, fallback scenarios |
| `docs/CAPABILITY_MATRIX.md` | ~50 capability status items across storage/summary/keyword/retrieval/workspace/maintenance/security/ecosystem/tools |
| `docs/PROJECT_STRUCTURE.md` | Module-by-module architecture deep-dive, data flow diagrams |
| `docs/HOOK_SETUP.md` | Hook configuration: bash/bat/ps1, settings.json template |
| `docs/SUMMARIZER_DESIGN.md` | Pluggable summarizer design with `BaseSummarizer` interface |
| `docs/DEVELOPMENT_ROADMAP.md` | Five-phase roadmap (all phases completed as of v0.7.0) |
| `docs/FAQ.md` | Frequently asked questions |
| `docs/config.example.json` | Config file template with all keys |
| `docs/settings.template.json` | Hook config template for Claude Code settings.json |
| `docs/releases/` | Per-version release summaries (v0.6.0, v0.7.0) |
| `LIMITATIONS.md` | Detailed known limitations and design boundaries |
| `RELEASE_CHECKLIST.md` | Release procedure checklist |
| `LICENSE` | MIT |

---

## Known Limitations

- **Plugin Runtime**: `.claude-plugin/plugin.json` has not been validated against the live Claude Code plugin runtime. The manifest is structurally correct but untested in production plugin loading.
- **API Testing**: Embedding and LLM providers are tested with deterministic `FakeProvider` implementations in CI. Real API behavior is documented in `docs/SMOKE_TEST.md` for manual verification, not automated.
- **Storage Model**: Local file-based storage (Markdown + JSON + JSONL). No multi-user concurrency, no distributed locking beyond simple file locks. Suitable for single-user local use.
- **TUI Coverage**: Session TUI controller and renderer are fully unit-tested. Actual terminal rendering and key input are not part of automated CI and depend on terminal capability detection.
- **No Automatic Recommendations**: Sessions must be explicitly linked. The system does not automatically suggest related sessions based on content similarity.

---

## Security & Privacy

- **Local-first**: All memories stored on disk. No data leaves your machine unless you explicitly configure a remote API provider.
- **API keys via environment**: `EMBEDDING_API_KEY` and `LLM_API_KEY` are only read from environment variables. They are never written to config files, logs, or committed to git.
- **Sanitized logging**: The logging system (`logging_utils.py`) truncates content and strips paths. Full conversation transcripts are never written to logs.
- **Path traversal protection**: `_validate_file_path()` rejects index entries with `..` or absolute paths that escape the memory directory.
- **Atomic writes**: `index.json`, `manifest.json`, `links.json` all use temp-file + `os.replace()` for crash-safe writes.

---

## Repository

GitHub: [`Junhaozhang-127/ClaudeCodeMemorySkill`](https://github.com/Junhaozhang-127/ClaudeCodeMemorySkill) (display name `ClaudeMeory` for historical reasons).

## License

MIT — see [`LICENSE`](LICENSE)
