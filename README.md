<p align="right"><a href="README.zh-CN.md">中文</a> | <b>English</b></p>

# Claude Code Memory Skill

Lightweight local memory & session workspace for Claude Code — semantic retrieval, LLM summarization, session management, interactive TUI.

**v0.7.0** — 352 tests, zero failures.

## Why You Need It

Claude Code sessions are isolated. When you switch sessions, project context, bug analyses, and design decisions are lost.

This skill saves conversations as structured memories, retrieves them via semantic/hybrid search, manages session workspaces, and provides an interactive TUI for session navigation.

## Installation

```bash
git clone https://github.com/Junhaozhang-127/ClaudeCodeMemorySkill.git
cd ClaudeCodeMemorySkill
pip install jieba              # optional: enhanced Chinese word segmentation
```

**Requirements**: Python 3.7+. Zero core dependencies. Optional: `jieba` for Chinese NLP.

## Quick Start

```bash
# Save a memory (auto-detects current session)
python scripts/summarize_session.py --topic "Architecture Discussion" --text "Decided to use microservices..."

# Retrieve with keyword mode
python scripts/retrieve_memory.py --query "architecture plan"

# Retrieve with semantic search (requires EMBEDDING_API_KEY)
python scripts/retrieve_memory.py --query "architecture" --mode semantic --json

# Retrieve with hybrid mode (keyword + semantic)
python scripts/retrieve_memory.py --query "architecture" --mode hybrid

# Retrieve from all sessions
python scripts/retrieve_memory.py --query "architecture" --all-sessions

# Retrieve with linked sessions
python scripts/retrieve_memory.py --query "architecture" --include-linked-sessions

# Session management
python scripts/session_cli.py create --title "Project Alpha" --use
python scripts/session_cli.py list
python scripts/session_cli.py current
python scripts/session_cli.py tui       # Interactive session selector
```

## Core Capabilities (v0.7.0)

### Semantic & Hybrid Retrieval (v0.6.0)
Three retrieval modes: `keyword`, `semantic`, `hybrid`. Embedding vector similarity search with automatic fallback. Supports OpenAI-compatible API (set `EMBEDDING_API_KEY`) or zero-config fake provider.

```bash
python scripts/retrieve_memory.py --query "..." --mode hybrid
```

### LLM Summarization (v0.6.0)
Three summary types: `brief`, `semantic`, `memory`. Chunk-merge for long texts. Fallback to rule-based summarizer when no LLM key is configured.

```bash
python scripts/summarize_session.py --topic "..." --text "..." --summary-mode llm
```

### Slash Command System (v0.6.0)
CommandRegistry with 5 slash commands: `memory:save`, `memory:retrieve`, `memory:rebuild`, `memory:manage`, `memory:session`. Argument validation, structured results, edit-distance suggestions.

```bash
/memory save "Architecture" --text "We decided to use microservices"
/memory retrieve "architecture" --mode hybrid --all-sessions
/memory session create --title "Book Review" --use
/memory session tui     # Interactive TUI
```

### Memory Lifecycle (v0.6.0)
Extended MemoryRecord schema (23 fields). Status state machine: `active` → `archived` / `expired` / `merged` / `deleted`. TTL-based auto-expiry, content-hash dedup, quality reports.

```bash
python scripts/memory_maintenance.py detect-duplicates
python -c "from memory_lifecycle import generate_quality_report; print(generate_quality_report())"
```

### Session Workspace Manager (v0.7.0)
Per-session directories with manifest, memories, links, events. Full lifecycle: create, list, rename, archive, soft-delete, restore.

```bash
python scripts/session_cli.py create --title "Paper Review" --use
python scripts/session_cli.py list
python scripts/session_cli.py info --session-id <id>
python scripts/session_cli.py delete --session-id <id>
python scripts/session_cli.py restore --session-id <id>
```

### Session-Aware Memory (v0.7.0)
`save_memory` auto-detects current session. `retrieve_memory` defaults to current session scope. Supports `--session-id`, `--all-sessions`, `--include-archived-sessions`, `--include-linked-sessions`.

### Linked Sessions (v0.7.0)
Explicit session linking via `links.json`. Retrieval with `include_linked_sessions=True` expands scope to linked sessions.

```bash
python scripts/session_cli.py link --to <target_session_id> --reason "related"
python scripts/session_cli.py unlink --to <target_session_id>
python scripts/session_cli.py links
```

### Interactive Session TUI (v0.7.0)
Terminal-based session selector with keyboard navigation: UP/DOWN, Enter, Delete, N, R, A, L, Q. Soft-delete with double-press confirmation.

```bash
python scripts/session_cli.py tui
python scripts/session_cli.py tui --include-archived
```

### Structured Memory & Auto-Save
Auto-extracts summaries, decisions, and TODOs. Turn-based auto-save (every N turns). Intelligent merge on same topic. Hook scripts for bash/bat/ps1.

### Memory Maintenance
Dedup, merge, compact, archive — all with dry-run protection.

```bash
python scripts/memory_maintenance.py detect-duplicates
python scripts/memory_maintenance.py compact --topic "..." --dry-run
python scripts/memory_maintenance.py archive-old --days 180 --dry-run
```

## Project Structure (v0.7.0)

```text
ClaudeMeory/
├── scripts/                # Core Python (20+ modules)
│   ├── memory_core.py          # Memory save/retrieve/format core
│   ├── retrieval.py            # Keyword/Hybrid/Semantic retrievers
│   ├── summarizers.py          # RuleBased/LLM summarizers
│   ├── embedding_provider.py   # EmbeddingProvider ABC + Fake/OpenAI
│   ├── llm_provider.py         # LLMProvider ABC + Fake/OpenAI
│   ├── memory_lifecycle.py     # Lifecycle state machine + quality report
│   ├── session_manager.py      # Session CRUD + link + events
│   ├── session_tui.py          # Interactive session selector
│   ├── session_cli.py          # Session CLI entry
│   └── ...
├── commands/               # Slash command handlers (v0.6.0)
│   ├── base.py                 # Command + CommandResult
│   ├── registry.py             # CommandRegistry
│   ├── memory_save.py          # /memory save
│   ├── memory_retrieve.py      # /memory retrieve
│   ├── memory_rebuild.py       # /memory rebuild
│   ├── memory_manage.py        # /memory manage
│   └── memory_session.py       # /memory session (12 actions)
├── hooks/                  # Hook scripts (bash/bat/ps1)
├── .claude-plugin/         # Plugin manifest + marketplace
├── memory/                 # Memory storage
│   ├── index.json              # Topic index
│   ├── .memory/sessions/       # Session workspaces (v0.7.0)
│   └── topics/                 # Markdown memory files
├── docs/                   # Documentation
│   ├── SESSION_WORKSPACE.md    # Session workspace guide
│   ├── SMOKE_TEST.md           # Real API smoke test guide
│   ├── releases/               # Release summaries
│   └── ...
├── tests/                  # 352 tests, 0 failures
├── CHANGELOG.md
└── LICENSE
```

## Testing

```bash
python -m pytest -q                        # 352 tests (0 failed)
python -m pytest tests/test_session_manager.py -v     # 52 session tests
python -m pytest tests/test_session_tui.py -v         # 47 TUI tests
python scripts/run_acceptance.py --quick              # Acceptance tests
```

## Configuration

Priority: CLI arguments > environment variables > config.json > defaults

```bash
# Session workspace (v0.7.0)
export SESSION_ENABLED=true

# Retrieval mode: keyword / semantic / hybrid
export CLAUDE_MEMORY_RETRIEVAL_MODE=hybrid

# Embedding provider (v0.6.0)
export EMBEDDING_API_KEY=sk-...
export EMBEDDING_API_BASE=https://api.openai.com/v1
export EMBEDDING_MODEL=text-embedding-3-small

# LLM provider (v0.6.0)
export LLM_API_KEY=sk-...
export LLM_API_BASE=https://api.openai.com/v1
export LLM_MODEL=gpt-4o-mini

# Auto-save
export MEMORY_AUTO_SAVE_INTERVAL=10
```

## Documentation Index

| Document | Content |
|----------|---------|
| `README.zh-CN.md` | Chinese README |
| `SKILL.md` | Skill behavior rules & slash commands |
| `CHANGELOG.md` | v0.1.0 – v0.7.0 changelog |
| `docs/SESSION_WORKSPACE.md` | Session workspace guide |
| `docs/SMOKE_TEST.md` | Real API provider smoke test |
| `docs/CAPABILITY_MATRIX.md` | Capability status table |
| `docs/HOOK_SETUP.md` | Hook configuration (bash/bat/ps1) |
| `docs/PROJECT_STRUCTURE.md` | Architecture overview |
| `docs/SUMMARIZER_DESIGN.md` | Summarizer design |
| `docs/DEVELOPMENT_ROADMAP.md` | Development roadmap |
| `docs/config.example.json` | Config file example |
| `docs/settings.template.json` | Hook config template |

## Known Limitations

- **Plugin Manifest**: `.claude-plugin/plugin.json` is a manifest template, not yet validated against the official Claude Code plugin runtime.
- **Real API E2E**: Embedding/LLM providers tested with fake providers in CI. Real API smoke test documented in `docs/SMOKE_TEST.md` but not automated.
- **Storage**: Local Markdown + JSON + JSONL file storage, no multi-user concurrent database.
- **Session TUI**: Tested via controller/renderer unit tests; real terminal interaction not part of automated CI.

## Security & Privacy

- All memories stored locally; never uploaded to remote services.
- Never expose API keys, passwords, or tokens in conversations.
- Embedding/LLM API keys configured via environment variables only.
- Logs do not record full conversation transcripts.

## Repository

Repository: `ClaudeCodeMemorySkill` (GitHub name `ClaudeMeory` for historical reasons).

## License

MIT — see `LICENSE`
