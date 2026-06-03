# Codex 第四阶段独立核验报告

## 1. 核验日期

- 核验日期：2026-06-03
- 核验环境：Windows / PowerShell
- Python：3.7.3

## 2. 项目路径

`D:\SmartManufacturingWorkshop\program\ClaudeMeory`

## 3. 核验结论

**结论：基本通过。**

第四阶段声明中的主要代码资产已经存在，核心 CLI、workspace 写入/检索、混合检索字段、安全路径校验、Markdown fence 转义、索引备份、日志文件和测试套件均有实际证据支撑。测试结果为 `78 tests OK (skipped=3)`，pytest 为 `75 passed, 3 skipped`。

但第四阶段不能判定为完全通过：`CLAUDE_MEMORY_WORKSPACE` 和 `CLAUDE_MEMORY_DIR` 在 CLI 默认路径中未生效；`EmbeddingRetriever` 作为 stub 静默返回空列表；部分 Phase 4 专项文档缺失；维护命令对中文 topic 的 dry-run 匹配在当前 Windows/PowerShell 环境下不稳定；文档中仍存在“向量检索属于第四阶段计划”的旧表述。建议先做 Phase 4.1 修补，再进入第五阶段或发布前验收。

## 4. 第四阶段声明真实性判断

| 声明 | 核验结果 | 说明 |
| --- | --- | --- |
| `scripts/memory_core.py` 集成 workspace、HybridRetriever、安全校验、fence 转义、备份、锁、score_breakdown | 基本通过 | 代码与实际 CLI 均可验证大部分能力；但环境变量路径未被 CLI 默认参数触发。 |
| 新增 `scripts/config.py` | 通过 | 存在 `MemoryConfig`，包含 workspace、memory_dir、log、backup、lock 等配置字段。 |
| 新增 `scripts/retrieval.py` | 基本通过 | 存在 `BaseRetriever`、`KeywordRetriever`、`HybridRetriever`、`EmbeddingRetriever`；但 `EmbeddingRetriever.retrieve()` 静默返回 `[]`。 |
| 新增 `scripts/memory_maintenance.py` | 部分通过 | 命令存在，默认 dry-run/`--apply` 设计存在；中文 topic 场景下 `compact`/`merge` 未匹配到实际文件。 |
| 新增 `scripts/logging_utils.py` | 通过 | 使用标准 logging 与 `RotatingFileHandler`，日志文件已生成。 |
| 新增 `scripts/workspace_manager.py` | 通过 | 支持 `init`、`list`、`status`、`migrate-legacy`。 |
| CLI 新增 `--workspace` | 通过 | `summarize_session.py`、`retrieve_memory.py`、`update_index.py` 均支持并实际可用。 |
| `CLAUDE_MEMORY_WORKSPACE` / `CLAUDE_MEMORY_DIR` 有效 | 未通过 | 实测设置环境变量后 CLI 仍写入默认 legacy `memory/topics/`。 |
| Phase 4 测试 17 项 | 通过 | 测试类统计显示 Phase 4 共 17 个测试。 |
| Phase 4 开发报告存在 | 未通过 | 未发现 `docs/PHASE4_DEVELOPMENT_REPORT.md`。 |

## 5. 项目结构核验结果

当前目录树摘要：

```text
D:\SmartManufacturingWorkshop\program\ClaudeMeory
|   .gitignore
|   install.sh
|   plugin.json
|   README.md
|   requirements.txt
|   SKILL.md
|
+---docs
|       CODEX_PHASE2_VERIFICATION_REPORT.md
|       CODEX_PHASE3_VERIFICATION_REPORT.md
|       CODEX_PHASE4_VERIFICATION_REPORT.md
|       CODEX_VERIFICATION_REPORT.md
|       DEVELOPMENT_ROADMAP.md
|       HOOK_SETUP.md
|       PROJECT_STRUCTURE.md
|       settings.template.json
|       SUMMARIZER_DESIGN.md
|
+---hooks
|       post_conversation.bat
|       post_conversation.ps1
|       post_conversation.sh
|       post_conversation_example.sh
|       pre_prompt.bat
|       pre_prompt.ps1
|       pre_prompt.sh
|       pre_prompt_example.sh
|
+---logs
|       claude_memory.log
|
+---memory
|   |   index.json
|   |
|   +---backups
|   +---topics
|   |       CustomDirCheck_2026-06-03.md
|   |       EnvWorkspaceCheck_2026-06-03.md
|   |       Phase4_Legacy_核验_2026-06-03.md
|   |       README.md
|   |
|   \---workspaces
|       +---Phase4BackupCheck
|       +---Phase4CodexCheck
|       +---Phase4FenceCheck
|       \---Phase4SecurityCheck
|
+---scripts
|   |   __init__.py
|   |   config.py
|   |   logging_utils.py
|   |   memory_core.py
|   |   memory_maintenance.py
|   |   retrieval.py
|   |   retrieve_memory.py
|   |   summarizers.py
|   |   summarize_session.py
|   |   update_index.py
|   |   workspace_manager.py
|   \---__pycache__
|
\---tests
    |   test_memory_skill.py
    \---__pycache__
```

文件存在性：

| 路径 | 状态 |
| --- | --- |
| `README.md` | 存在 |
| `SKILL.md` | 存在 |
| `requirements.txt` | 存在 |
| `.gitignore` | 存在 |
| `plugin.json` | 存在 |
| `scripts/memory_core.py` | 存在 |
| `scripts/summarizers.py` | 存在 |
| `scripts/config.py` | 存在 |
| `scripts/retrieval.py` | 存在 |
| `scripts/memory_maintenance.py` | 存在 |
| `scripts/logging_utils.py` | 存在 |
| `scripts/workspace_manager.py` | 存在 |
| `scripts/summarize_session.py` | 存在 |
| `scripts/retrieve_memory.py` | 存在 |
| `scripts/update_index.py` | 存在 |
| `hooks/post_conversation.sh` / `pre_prompt.sh` | 存在 |
| `hooks/post_conversation.ps1` / `pre_prompt.ps1` | 存在 |
| `hooks/post_conversation.bat` / `pre_prompt.bat` | 存在 |
| `memory/index.json` | 存在，JSON 有效 |
| `memory/topics/README.md` | 存在 |
| `memory/workspaces/` | 本次核验后存在 |
| `logs/` | 存在 |
| `tests/test_memory_skill.py` | 存在 |
| `docs/WORKSPACE_GUIDE.md` | 缺失 |
| `docs/RETRIEVAL_DESIGN.md` | 缺失 |
| `docs/MAINTENANCE.md` | 缺失 |
| `docs/SECURITY.md` | 缺失 |
| `docs/PHASE4_DEVELOPMENT_REPORT.md` | 缺失 |

残留文件：

- 存在 `.pytest_cache/`。
- 存在 `scripts/__pycache__/` 和 `tests/__pycache__/`。
- 存在 `logs/claude_memory.log`。
- 未发现残留 `*.lock` 文件。

## 6. 核心接口兼容性核验结果

接口签名如下：

```text
memory_core.save_memory(topic: str, conversation_text: str, append: bool = True, summarizer=None, workspace: str = '') -> Path
memory_core.retrieve_memory(query: str, top_k: int = 5, workspace: str = '', retriever=None) -> list[dict]
memory_core.rebuild_index(workspace: str = '') -> dict
memory_core.format_context(results: Iterable[dict], max_chars_per_item: int = 1200) -> str
memory_core.extract_keywords(text: str, topic: str = '', max_keywords: int = 10) -> list[str]
memory_core.score_record(query: str, record: dict) -> int
```

结论：

- 旧调用方式仍兼容，`save_memory(topic, text)`、`retrieve_memory(query)`、`rebuild_index()`、`format_context(results)` 均有测试覆盖。
- `workspace` 参数都有默认值，不传时仍使用 legacy `memory/index.json` 和 `memory/topics/`。
- `summary`、`keywords`、`decisions`、`todos` 字段仍存在。
- Phase 3 的 CLI、Hook、`plugin.json`、settings 模板文件未被删除。
- `jieba` 仍为可选依赖，当前环境 `jieba_available=False`，测试仍通过。
- 未发现强制接入外部 LLM、数据库、向量库或联网依赖。

## 7. Workspace 隔离核验结果

执行命令：

```powershell
python scripts\workspace_manager.py init --workspace Phase4CodexCheck
python scripts\summarize_session.py --workspace Phase4CodexCheck --topic "Phase4 Workspace 核验" --text "..."
python scripts\retrieve_memory.py --workspace Phase4CodexCheck --query "workspace 混合检索 score_breakdown" --json
python scripts\update_index.py --workspace Phase4CodexCheck
python scripts\workspace_manager.py status --workspace Phase4CodexCheck
python scripts\workspace_manager.py list
```

结果：

- `memory/workspaces/Phase4CodexCheck/` 被创建。
- workspace 记忆写入 `memory/workspaces/Phase4CodexCheck/topics/`。
- `retrieve_memory.py --workspace ... --json` 可解析。
- JSON 中包含 `score_breakdown` 和 `matched_fields`。
- `update_index.py --workspace Phase4CodexCheck` 只重建该 workspace 索引。
- `workspace_manager.py status` 显示该 workspace 有 1 个 index entry 和 1 个 Markdown 文件。
- legacy 与 workspace 路径分离成立。

不通过项：

- 设置 `CLAUDE_MEMORY_WORKSPACE=Phase4EnvCheck` 后运行 `summarize_session.py --topic EnvWorkspaceCheck ...`，实际仍写入 `memory/topics/`，没有写入 `memory/workspaces/Phase4EnvCheck/`。
- 设置 `CLAUDE_MEMORY_DIR=<custom path>` 后运行 CLI，实际仍写入默认 `memory/topics/`，自定义目录未生效。

这说明 `MemoryConfig` 支持环境变量的代码存在，但 CLI 到 `memory_core._resolve_paths()` 的实际路径没有采用该配置。

## 8. Hybrid Retrieval 核验结果

文件与类：

- `BaseRetriever`：存在。
- `KeywordRetriever`：存在。
- `HybridRetriever`：存在。
- `EmbeddingRetriever`：存在。

实际检索结果：

- workspace 检索返回 `score`、`score_breakdown`、`matched_fields`。
- `score_breakdown` 是 dict。
- `matched_fields` 是 list。
- 主题命中时 `score_breakdown.topic > 0`。
- TODO 查询可命中 `todos`。
- 路径越界记录不会被读取。
- `format_context()` 能展示匹配字段和评分明细。

偏差：

- `EmbeddingRetriever().retrieve(...)` 实测返回 `[]`，没有抛出 `NotImplementedError`，也没有返回明确提示，属于静默失败。
- 查询 `HybridRetriever` 时，部分场景 `matched_fields` 只显示 `recency`，没有稳定体现关键词命中，混合检索解释性仍需增强。
- 同一主题连续保存后，重建索引前检索可能出现同一 Markdown 文件的重复结果；执行 `update_index.py --workspace` 后会收敛为 1 条。

## 9. 记忆维护命令核验结果

命令存在：

- `detect-duplicates`
- `merge`
- `compact`
- `archive-old`

执行结果：

```powershell
python scripts\memory_maintenance.py detect-duplicates --workspace Phase4CodexCheck
python scripts\memory_maintenance.py compact --workspace Phase4CodexCheck --topic "Phase4 Workspace 核验" --dry-run
python scripts\memory_maintenance.py archive-old --workspace Phase4CodexCheck --days 1 --dry-run
python scripts\memory_maintenance.py merge --workspace Phase4CodexCheck --topic "Phase4 Workspace 核验" --dry-run
```

结果：

- `detect-duplicates` 成功执行，输出未发现重复文件。
- `archive-old --dry-run` 成功执行，未移动文件。
- `compact --dry-run` 未修改文件，但没有匹配到中文 topic 对应 Markdown 文件。
- `merge --dry-run` 未修改文件，但没有匹配到中文 topic 对应 Markdown 文件。

判断：

- 默认 dry-run 与 `--apply` 显式生效的设计存在。
- 维护命令对中文 topic、文件名 slug 或当前 Windows 参数编码的兼容性不足。
- 本次未执行任何 `--apply` 破坏性操作。

## 10. 日志系统核验结果

核验结果：

- `scripts/logging_utils.py` 使用 Python 标准 `logging`。
- 使用 `RotatingFileHandler`。
- `logs/claude_memory.log` 已生成。
- 保存记忆、检索、索引恢复、安全越界 warning 均有日志记录。
- 日志记录 topic、workspace、query 摘要、top_k、hits、文件路径等摘要信息。
- 日志未记录完整长原始对话。
- `_sanitize()` 会过滤 `api_key`、`token`、`password`、`secret` 等敏感片段，并截断长文本。

偏差：

- `CLAUDE_MEMORY_LOG_LEVEL` 存在读取逻辑，但日志 handler 初始化后复用，测试/多次调用场景下动态调整效果有限。
- 当前 Windows 控制台/文件读取显示存在中文编码错位现象，日志可读性受影响。

## 11. 索引备份、文件锁与恢复核验结果

已验证：

- `save_index()` 仍使用临时文件 + `os.replace()`。
- 覆盖已有 `index.json` 前会生成备份。
- 备份目录为 legacy `memory/backups/` 或 workspace 下的 `backups/`。
- 备份数量有上限配置，默认 10。
- 写入期间使用 `index.json.lock`。
- 写入完成后 lock 文件会清理，本次未发现残留 `*.lock`。
- `load_index()` 在 index 损坏时会尝试读取最近备份。
- 无备份时会降级返回空 dict 并记录 warning。

验证细节：

- 在 `Phase4BackupCheck` 中故意损坏 `index.json` 后，`load_index()` 返回了备份内容。
- 随后已将该临时 workspace 的 `index.json` 修复为有效 JSON。

偏差：

- `load_index()` 返回备份内容后不会自动把恢复内容写回损坏的 `index.json`；调用方若不显式 `save_index()`，磁盘上的 index 仍可能保持损坏状态。
- lock 获取失败时当前实现倾向于跳过写入并记录 warning，这能避免阻塞，但也可能造成调用者误以为保存成功。

## 12. 安全性增强核验结果

已验证：

- 恶意 index 记录将 `file` 指向 `..\..\README.md` 时，`retrieve_memory()` 返回空结果，没有读取越界文件。
- 保存包含三反引号的原始文本时，Markdown 使用四反引号 fenced block，结构未被三反引号破坏。
- `format_context()` 对长内容有截断控制。
- 日志只记录摘要，不记录完整原始对话。
- 日志敏感字段过滤逻辑存在。
- 文档中有不要保存密码、API Key、Token 等敏感信息的安全提示。

仍需增强：

- `format_context(max_chars_per_item)` 的预算语义仍不是严格的整个 block 总长度上限。
- Hook 自动保存的敏感信息风险主要依赖文档说明，缺少运行时确认或过滤策略。
- 环境变量支持声明与实际 CLI 行为不一致，可能导致用户误以为已隔离但实际写入 legacy。

## 13. 归档与时间衰减核验结果

已验证：

- `HybridRetriever` 的 `score_breakdown` 包含 `recency`。
- 最近记录有 recency 加分，且没有压过主题/关键词等主相关信号。
- `archive-old` 支持 `--days`、`--dry-run`、`--apply`、`--workspace`。
- `archive-old --dry-run` 没有移动文件。

未充分验证：

- 未执行 `archive-old --apply`，因为该操作会移动文件。
- 未发现 `access_count` / `last_accessed_at` 的实际写入证据。
- `CLAUDE_MEMORY_TRACK_ACCESS` 有配置读取逻辑，但未发现完整访问计数落盘行为。

## 14. CLI 回归验证结果

执行并通过的命令：

```powershell
python scripts\summarize_session.py --topic "Phase4 Legacy 核验" --text "这是默认 legacy memory 核验。"
python scripts\retrieve_memory.py --query "Phase4 Legacy 核验" --json
python scripts\update_index.py
python scripts\workspace_manager.py init --workspace Phase4CodexCheck
python scripts\summarize_session.py --workspace Phase4CodexCheck --topic "Phase4 Workspace 核验" --text "..."
python scripts\retrieve_memory.py --workspace Phase4CodexCheck --query "workspace HybridRetriever 日志 备份" --json
python scripts\update_index.py --workspace Phase4CodexCheck
python scripts\workspace_manager.py status --workspace Phase4CodexCheck
python scripts\memory_maintenance.py detect-duplicates --workspace Phase4CodexCheck
python scripts\memory_maintenance.py compact --workspace Phase4CodexCheck --topic "Phase4 Workspace 核验" --dry-run
python scripts\memory_maintenance.py archive-old --workspace Phase4CodexCheck --days 1 --dry-run
```

结论：

- JSON 输出可被 `json.loads()` 解析。
- legacy 与 workspace 目录隔离基本成立。
- workspace JSON 包含 `score_breakdown` 和 `matched_fields`。
- dry-run 未删除、移动或重写 Markdown 文件。
- index.json 均保持有效 JSON。
- 日志文件产生合理记录。

注意：

- 本次 CLI 验证按要求产生了 legacy 记忆文件、workspace、backups 和日志。
- 环境变量路径验证失败，且额外产生了 `EnvWorkspaceCheck`、`CustomDirCheck` legacy 记忆，用于证明环境变量未生效。

## 15. 测试执行结果

### unittest

```text
Ran 78 tests in 2.062s
OK (skipped=3)
```

### pytest

```text
collected 78 items
75 passed, 3 skipped, 312 warnings in 2.43s
```

测试分布：

| 测试类 | 数量 |
| --- | ---: |
| Phase 1 regression | 9 |
| Phase 2 相关增强测试 | 37 |
| Phase 3 Hook / Manifest / settings / install | 15 |
| Phase 4 workspace / retrieval / security / backup / logging / maintenance | 17 |

覆盖判断：

- workspace：有覆盖。
- retrieval：有覆盖。
- security：有覆盖。
- backup：有覆盖。
- logging：有覆盖。
- maintenance：有覆盖，但只覆盖 duplicate 检测，不覆盖 CLI dry-run 的完整中文 topic 场景。
- 仍有真实 `memory/` 被 CLI 回归污染的风险，本次按用户要求实际运行 CLI，确实产生了样例记忆。
- 3 个 skipped 仍与 Windows 上 Bash 权限/语法检查有关。
- 312 warnings 主要来自当前 pytest 插件/Anaconda 环境的弃用警告，不是业务失败。

## 16. 文档完整性核验结果

`README.md`：

- 包含 Phase 4 能力说明。
- 包含 Workspace、混合检索、记忆维护、日志、备份、安全等概念。
- 包含 CLI 示例和当前限制。
- 但 `matched_fields`、`CLAUDE_MEMORY_*` 环境变量说明不足。
- 仍存在“检索非语义，计划第四阶段解决”的旧限制描述，与当前第四阶段状态冲突。

`SKILL.md`：

- 保留基础 Skill 使用说明、失败降级、安全注意和不应做的事情。
- 未充分覆盖多 workspace 使用规则、跨 workspace 注入边界、检索注入优先级、日志边界和记忆冲突处理。

`docs/DEVELOPMENT_ROADMAP.md`：

- 有第四阶段相关内容，但部分条目仍以未来规划方式描述向量检索、混合检索、归档、并发安全、日志系统。
- 未清晰标记哪些 Phase 4 能力已完成、哪些只是 stub 或未来工作。

专项文档：

- `docs/WORKSPACE_GUIDE.md`：缺失。
- `docs/RETRIEVAL_DESIGN.md`：缺失。
- `docs/MAINTENANCE.md`：缺失。
- `docs/SECURITY.md`：缺失。

结论：文档覆盖了总体能力，但 Phase 4 专项文档不完整，且部分描述与实现状态不完全一致。

## 17. 依赖与边界核验结果

已确认：

- 未强制引入外部 LLM。
- 未强制引入向量数据库。
- 未替换 Markdown 存储为数据库。
- 未强制联网。
- `jieba` 仍是可选依赖。
- `EmbeddingRetriever` 是 stub，不应被描述为已实现向量检索。
- `memory_maintenance` 的破坏性操作默认 dry-run，需要显式 `--apply`。
- legacy `memory/` 兼容仍存在。
- Plugin / Hook 文件未被删除。

边界偏差：

- `docs/DEVELOPMENT_ROADMAP.md` 中仍提到 OpenAI Embeddings、Anthropic SDK、sentence-transformers 等未来方向；这些不是当前运行依赖，但需要明确标注为未来可选设计。

## 18. 当前工作区变化说明

本次核验生成或修改了以下内容：

- 新增 `docs/CODEX_PHASE4_VERIFICATION_REPORT.md`。
- 修改 `memory/index.json`。
- 新增 `memory/backups/`。
- 新增 `memory/topics/Phase4_Legacy_核验_2026-06-03.md`。
- 新增 `memory/topics/EnvWorkspaceCheck_2026-06-03.md`。
- 新增 `memory/topics/CustomDirCheck_2026-06-03.md`。
- 新增 `memory/workspaces/Phase4CodexCheck/`。
- 新增 `memory/workspaces/Phase4SecurityCheck/`。
- 新增 `memory/workspaces/Phase4FenceCheck/`。
- 新增 `memory/workspaces/Phase4BackupCheck/`。
- 更新或追加 `logs/claude_memory.log`。
- 存在 `.pytest_cache/`、`scripts/__pycache__/`、`tests/__pycache__/`。

未发现残留 `index.json.lock`。

是否需要清理：

- 如果这些核验样例不希望进入提交，应清理 `memory/topics/` 中的核验样例、`memory/workspaces/Phase4*`、`memory/backups/`、日志和缓存。
- 如果希望保留审计证据，可保留 `Phase4CodexCheck` 等 workspace 作为核验样例，但不建议发布包中携带。

## 19. 问题清单

### P0：必须立即修复

无。

未发现导致核心记忆写入、检索、索引重建和测试套件完全不可用的问题。

### P1：建议尽快修复

1. **环境变量声明与实际 CLI 行为不一致。**  
   `CLAUDE_MEMORY_WORKSPACE` 和 `CLAUDE_MEMORY_DIR` 有配置读取代码，但实测 CLI 默认调用未生效，仍写入 legacy `memory/topics/`。

2. **EmbeddingRetriever stub 静默返回空结果。**  
   未实现能力应明确抛出 `NotImplementedError` 或返回显式状态，避免用户误以为向量检索已正常工作。

3. **维护命令对中文 topic 匹配不稳定。**  
   `compact --topic "Phase4 Workspace 核验"` 与 `merge --topic ...` 在当前环境没有匹配到实际 Markdown 文件，需修复 topic、slug、编码或索引匹配策略。

4. **同一主题连续保存后索引可出现重复结果。**  
   重建索引可收敛，但重建前检索返回同一文件多条结果，影响检索质量。

5. **Phase 4 文档状态不准确。**  
   README / ROADMAP 中仍有“第四阶段计划解决向量检索”等旧描述，容易误导验收判断。

### P2：后续优化

1. 补充 `docs/WORKSPACE_GUIDE.md`、`docs/RETRIEVAL_DESIGN.md`、`docs/MAINTENANCE.md`、`docs/SECURITY.md`。
2. 在 `SKILL.md` 中补充多 workspace 注入边界、记忆冲突处理和日志边界。
3. `load_index()` 从备份恢复后可选择自动写回磁盘或明确提示调用方。
4. lock 获取失败时应向调用方返回更明确的失败状态。
5. `format_context(max_chars_per_item)` 建议定义并测试严格总长度语义。
6. 日志中文编码在 Windows 环境下需要验证和规范。
7. `CLAUDE_MEMORY_TRACK_ACCESS` 若暂未实现访问计数，应在文档中标注为预留。
8. 发布前清理核验样例、日志、backups、`.pytest_cache` 与 `__pycache__`。

## 20. 被证实的 Claude Code 声明

以下声明被证实：

- Phase 4 新增脚本文件存在。
- `MemoryConfig` 存在。
- `--workspace` 参数在三个核心 CLI 中存在并可用。
- legacy memory 默认路径仍可用。
- workspace 路径 `memory/workspaces/<workspace>/index.json` 与 `topics/` 可用。
- `HybridRetriever` 存在并返回 `score_breakdown` / `matched_fields`。
- 路径越界读取被阻止。
- Markdown fence 转义已实现。
- 索引备份与 lock 文件机制存在。
- `load_index()` 可从备份读取恢复内容。
- 维护命令存在，且破坏性操作默认 dry-run。
- 日志系统存在，使用 `RotatingFileHandler`。
- Phase 4 测试确实为 17 项。
- 测试总数确实为 78 项，且本次全部通过或跳过。

## 21. 存在偏差的 Claude Code 声明

以下声明存在偏差：

- `CLAUDE_MEMORY_WORKSPACE` 有效：实测 CLI 未生效。
- `CLAUDE_MEMORY_DIR` 有效：实测 CLI 未生效。
- `EmbeddingRetriever` 是清晰占位：实测静默返回空列表，不够清晰。
- 记忆维护命令完全可用：中文 topic dry-run 匹配失败。
- Phase 4 文档完整：专项文档缺失，README/ROADMAP 有旧表述。
- 混合检索解释性完全稳定：部分查询的 `matched_fields` 不符合预期。

## 22. 是否建议进入第五阶段或发布前验收

**不建议直接进入第五阶段。**

建议先做 Phase 4.1 修补，至少关闭 P1 问题后，再进入第五阶段。

**不建议直接进入发布前验收。**

原因是环境变量路径隔离、维护命令中文 topic 匹配和文档准确性都属于验收时容易被用户立即遇到的问题。发布前还应清理测试样例、缓存、日志和 backups，保证包内容干净。

## 23. 下一步建议

建议按以下顺序处理：

1. 修复 CLI 与 `MemoryConfig` 的接入，让 `CLAUDE_MEMORY_WORKSPACE` 和 `CLAUDE_MEMORY_DIR` 在不传 `--workspace` 时真实生效。
2. 修改 `EmbeddingRetriever.retrieve()`，未实现时明确抛出 `NotImplementedError` 或返回结构化未实现状态。
3. 修复 `memory_maintenance.py` 对中文 topic、slug 文件名和 index key 的匹配策略。
4. 对同一 topic 追加保存后的 index 记录做去重，避免重建前重复检索。
5. 更新 README、SKILL、ROADMAP，准确区分“已实现”“stub”“未来计划”。
6. 补齐 workspace、retrieval、maintenance、security 四份专项文档。
7. 发布前清理核验样例数据、日志、缓存和备份目录。

完成以上修复后，可以进入发布前验收；第五阶段应在发布前验收通过后再开始。
