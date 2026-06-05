<p align="right"><a href="README.zh-CN.md">中文</a> | <b>English</b></p>

# Claude Code Memory Skill

Lightweight local memory bank for Claude Code — automatically saves sessions as structured Markdown and retrieves historical context in new sessions.

## Why You Need It

Each Claude Code session is isolated. When you switch sessions, all prior project context, bug analyses, and design decisions are lost, forcing you to manually repeat yourself.

This skill automatically distills conversations into structured memories (summaries, key decisions, TODOs) at session end, and auto-retrieves relevant context based on your input in new sessions.

## Installation

```bash
git clone https://github.com/Junhaozhang-127/ClaudeMeory.git
cd ClaudeMeory
python scripts/install.py --interactive
```

On first run, you'll be prompted to choose a memory storage path — press Enter for the default.

**Requirements**: Python 3.7+, zero core dependencies. Optional: `pip install jieba` for enhanced Chinese word segmentation.

## Quick Start

```bash
# Save a memory
python scripts/summarize_session.py --topic "Architecture Discussion" --text "Decided to use microservices..."

# Retrieve relevant memories
python scripts/retrieve_memory.py --query "architecture plan"

# View JSON output (with score breakdown)
python scripts/retrieve_memory.py --query "architecture" --json

# Rebuild index
python scripts/update_index.py
```

## Core Capabilities

### Structured Memory
Automatically extracts summaries, key decisions, and TODOs from conversations into structured Markdown memory files.

### Hybrid Retrieval
Multi-signal weighted scoring (topic > keywords > decisions > TODOs > summary), returning interpretable `score_breakdown` results.

### Workspace Isolation
Memory directories are isolated per project — different projects never interfere.

```bash
python scripts/workspace_manager.py init --workspace my-project
python scripts/summarize_session.py --workspace my-project --topic "..." --text "..."
```

### Hook Automation
Auto-save at session end, auto-retrieve at session start. Features a **turn-based auto-save timer** that saves your conversation every N turns (default 10) — no need to wait until session end.

```bash
# Configure auto-save interval
export MEMORY_AUTO_SAVE_INTERVAL=5   # Save every 5 turns
export MEMORY_AUTO_SAVE_INTERVAL=0   # Disable turn-based auto-save
```

Supports bash / Windows CMD / PowerShell. See `docs/HOOK_SETUP.md` for details.

### Memory Maintenance
Deduplication, merging, compaction, archiving — all with dry-run protection.

```bash
python scripts/memory_maintenance.py detect-duplicates
python scripts/memory_maintenance.py compact --topic "..." --dry-run
python scripts/memory_maintenance.py archive-old --days 180 --dry-run
```

### Release Tools

| Command | Purpose |
|---------|---------|
| `install.py` | Installation & initialization |
| `uninstall.py` | Safe uninstallation |
| `upgrade.py` | Upgrade & migration |
| `health_check.py` | System health diagnostics |
| `memory_stats.py` | Memory bank statistics |
| `release_prepare.py` | Pre-release cleanup |
| `run_acceptance.py` | Acceptance tests |

## Project Structure

```text
ClaudeMeory/
├── scripts/          # Core Python scripts
├── hooks/            # Hook scripts (bash/bat/ps1)
│   ├── pre_prompt.*      # Retrieve on input
│   ├── post_conversation.* # Save on session end
│   └── auto_save.*       # Turn-based auto-save timer
├── memory/           # Memory storage directory
│   ├── index.json        # Topic index
│   ├── .turn_state.json  # Auto-save turn counter
│   └── topics/           # Markdown memory files
├── docs/             # Documentation
│   ├── CAPABILITY_MATRIX.md    # Capability matrix
│   ├── DEVELOPMENT_ROADMAP.md  # Development roadmap
│   ├── HOOK_SETUP.md           # Hook configuration guide
│   ├── PROJECT_STRUCTURE.md    # Architecture overview
│   └── SUMMARIZER_DESIGN.md    # Summarizer design
├── tests/            # Tests (78 items)
├── plugin.json       # Plugin Manifest
├── install.sh        # One-click install
├── CHANGELOG.md      # Changelog
└── LICENSE           # MIT
```

## Testing

```bash
python tests/test_memory_skill.py        # 78 unit tests
python scripts/run_acceptance.py --quick # 7 acceptance tests
```

## Configuration

Priority: CLI arguments > environment variables > config.json > defaults

```bash
# Environment variables
export CLAUDE_MEMORY_WORKSPACE=my-project
export CLAUDE_MEMORY_DIR=/path/to/memories
export MEMORY_AUTO_SAVE_INTERVAL=10   # Auto-save every N turns (default 10)

# Or use config.json
python scripts/install.py --interactive  # Interactive generation
```

## Documentation Index

| Document | Content |
|----------|---------|
| `SKILL.md` | Skill behavior rules & slash commands |
| `CHANGELOG.md` | Phase 1–5 changelog |
| `docs/CAPABILITY_MATRIX.md` | 40+ capability status table |
| `docs/HOOK_SETUP.md` | Hook configuration (bash/bat/ps1) |
| `docs/PROJECT_STRUCTURE.md` | Architecture & module overview |
| `docs/SUMMARIZER_DESIGN.md` | Pluggable summarizer design |
| `docs/DEVELOPMENT_ROADMAP.md` | Five-phase roadmap |
| `docs/settings.template.json` | Hook config template |
| `docs/config.example.json` | Config file example |

## Known Limitations

- **Plugin Manifest**: `plugin.json` is currently a manifest template, not yet validated against the official Claude Code plugin runtime.
- **Slash Commands**: Currently mapped declaratively to CLI scripts via SKILL.md / plugin.json, not a full official `commands/` directory implementation.
- **EmbeddingRetriever**: Currently a stub — does not provide true semantic vector retrieval. Retrieval primarily relies on keyword + multi-field weighted scoring.
- **Storage**: Local Markdown + JSON file storage, no multi-user concurrent database.

See `LIMITATIONS.md` for details.

## Security & Privacy

- All memories are stored locally by default and never uploaded to any remote service.
- Never expose API keys, passwords, tokens, or other sensitive information in conversations.
- Use `scripts/memory_maintenance.py` to maintain or clean up memories.
- Logs do not record full conversation transcripts.

## Repository Note

The current repository name is `ClaudeMeory` (for historical reasons). The project display name is **Claude Code Memory Skill**.

## License

MIT — see `LICENSE`
