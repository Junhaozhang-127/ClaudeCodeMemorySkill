# Codex 第二阶段独立核验报告

## 1. 核验日期

2026-06-03

## 2. 项目路径

`D:\SmartManufacturingWorkshop\program\ClaudeMeory`

## 3. 核验结论

**结论：基本通过。**

第二阶段“摘要与关键词增强”的核心声明大体真实：项目新增了可插拔摘要器模块，`memory_core.py` 增加了 `decisions/todos` 元数据、可选 `jieba` 关键词增强、结构化 Markdown、增强评分、增强上下文输出和新旧 Markdown 兼容重建；CLI 的 Windows UTF-8 stdout 处理已存在；测试从 12 项扩展到 49 项并全部通过。

未判定为“完全通过”的原因：

- `RuleBasedSummarizer` 的触发词规则偏宽，存在误判风险。例如英文触发词 `decision` 会匹配 `decisions`，导致包含字段名 `decisions` 的 TODO 也被识别为关键决策。
- 摘要长度控制存在 off-by-one：截断后追加省略号，实测摘要长度可到 501，而不是严格不超过 500。
- `format_context(max_chars_per_item=...)` 只近似限制主体内容，标题、文件路径、相关分等头部不计入，最终单条块长度可能超过该值。
- CLI subprocess 测试虽然会清理，但运行期间仍触碰真实 `memory/`；严格意义上不完全等同于临时目录隔离。
- `retrieve_memory()` 仍信任 `index.json` 中的 `file` 路径，手动篡改索引时仍有读取预期外路径的风险。

## 4. 第二阶段声明真实性判断

### 4.1 已证实的声明

| Claude Code 声明 | 核验结论 |
|---|---|
| `MemoryRecord` 新增 `decisions/todos` 字段 | 真实，字段位于 `scripts/memory_core.py` 的 `MemoryRecord` |
| `extract_keywords()` 集成 `jieba` + 停用词过滤，且无 jieba 时回退 | 真实；当前环境未安装 `jieba`，测试和手动断言均通过回退路径 |
| `save_memory()` 接入可插拔摘要器 | 真实，新增 `summarizer=None` 可选参数，默认懒加载 `RuleBasedSummarizer` |
| `score_record()` 支持多字段加权和时间加分 | 真实，覆盖 topic、keywords、summary、decisions、todos 和 7 天内更新加分 |
| `format_context()` 优先输出摘要、关键决策、待办事项 | 真实，普通检索输出已验证 |
| `rebuild_index()` 兼容新旧 Markdown 并解析 summary/keywords/decisions/todos | 真实，测试覆盖旧格式和新格式 |
| 新增 `scripts/summarizers.py` | 真实 |
| 存在 `SummaryResult`、`BaseSummarizer`、`RuleBasedSummarizer` | 真实 |
| RuleBasedSummarizer 不依赖外部 LLM/API | 真实，仅使用标准库和注入的关键词函数 |
| CLI 增加 Windows UTF-8 stdout 处理 | 真实，`retrieve_memory.py` 和 `summarize_session.py` 均调用 `sys.stdout.reconfigure(encoding="utf-8")` |
| `retrieve_memory.py --json` 包含 `decisions/todos` 且可 `json.loads()` | 真实，手动 UTF-8 捕获解析通过 |
| 测试扩展到 49 项 | 真实，`unittest` 和 `pytest` 均收集/运行 49 项 |
| 文档新增 `docs/SUMMARIZER_DESIGN.md` | 真实 |
| 未接入外部 LLM、数据库、向量库 | 真实，源码未导入相关库 |
| 核心接口向后兼容 | 基本真实，`save_memory(topic, text)`、`retrieve_memory(query)`、`rebuild_index()`、`format_context(results)` 均可按旧方式调用 |

### 4.2 存在偏差的声明

| 声明 | 偏差 |
|---|---|
| “测试使用临时目录隔离，不污染真实 memory/” | 大部分类通过 `IsolatedMemoryTest` 隔离，但 CLI subprocess 测试仍在真实项目 `memory/` 下创建 `CLI_` 文件再清理。测试通过后未残留 CLI 文件，但运行中确实触碰真实目录 |
| “摘要长度控制 500 字以内” | 实测长文本摘要长度为 501，因为截断后追加了省略号 |
| “决策/待办抽取质量增强” | 功能存在，但触发词偏宽，字段名 `decisions` 会触发 `decision`，存在误判 |
| “max_chars_per_item 限制每条记忆最大字符数” | 仅限制主体拼装时的剩余预算，不包含标题/文件/分数，最终块可超过该值 |

## 5. 项目结构核验结果

### 5.1 当前目录树

```text
ClaudeMeory/
|-- .gitignore
|-- README.md
|-- requirements.txt
|-- SKILL.md
|-- .pytest_cache/
|-- docs/
|   |-- CODEX_PHASE2_VERIFICATION_REPORT.md
|   |-- CODEX_VERIFICATION_REPORT.md
|   |-- DEVELOPMENT_ROADMAP.md
|   |-- HOOK_SETUP.md
|   |-- PROJECT_STRUCTURE.md
|   `-- SUMMARIZER_DESIGN.md
|-- hooks/
|   |-- post_conversation_example.sh
|   `-- pre_prompt_example.sh
|-- memory/
|   |-- index.json
|   `-- topics/
|       |-- Phase2_Codex_核验_2026-06-03.md
|       `-- README.md
|-- scripts/
|   |-- __init__.py
|   |-- memory_core.py
|   |-- retrieve_memory.py
|   |-- summarizers.py
|   |-- summarize_session.py
|   |-- update_index.py
|   `-- __pycache__/
`-- tests/
    |-- test_memory_skill.py
    `-- __pycache__/
```

### 5.2 指定文件状态

| 文件 | 状态 | 说明 |
|---|---|---|
| `scripts/memory_core.py` | 存在 | Phase2 核心逻辑已修改 |
| `scripts/summarizers.py` | 存在 | Phase2 新增摘要器模块 |
| `scripts/summarize_session.py` | 存在 | Windows stdout UTF-8 处理已加入 |
| `scripts/retrieve_memory.py` | 存在 | Windows stdout UTF-8 处理已加入，JSON 输出包含新字段 |
| `scripts/update_index.py` | 存在 | 索引重建入口可用 |
| `tests/test_memory_skill.py` | 存在 | 49 项测试 |
| `requirements.txt` | 存在 | 标注 `jieba` 为可选依赖 |
| `README.md` | 存在 | 已更新 Phase2 能力说明 |
| `SKILL.md` | 存在 | 已更新注入优先级与规则 |
| `docs/DEVELOPMENT_ROADMAP.md` | 存在 | 标记 Phase2 已完成 |
| `docs/SUMMARIZER_DESIGN.md` | 存在 | Phase2 新增设计文档 |
| `docs/HOOK_SETUP.md` | 存在 | Phase1 Hook 文档仍在 |
| `docs/PROJECT_STRUCTURE.md` | 存在 | 项目结构文档仍在 |
| `docs/CODEX_VERIFICATION_REPORT.md` | 存在 | Phase1 核验报告仍在 |
| `.gitignore` | 存在 | 缓存与测试文件模式已忽略 |
| `memory/index.json` | 存在 | 当前为有效 JSON |
| `memory/topics/README.md` | 存在 | 重建索引时未被索引 |

## 6. 摘要器模块核验结果

核验文件：`scripts/summarizers.py`

| 核验项 | 结果 |
|---|---|
| 存在 `SummaryResult` 数据结构 | 通过 |
| `SummaryResult` 包含 `summary: str` | 通过 |
| `SummaryResult` 包含 `decisions: list[str]` | 通过 |
| `SummaryResult` 包含 `todos: list[str]` | 通过 |
| `SummaryResult` 包含 `keywords: list[str]` | 通过 |
| 存在 `BaseSummarizer` 抽象基类 | 通过 |
| `BaseSummarizer.summarize(text, topic="") -> SummaryResult` | 通过 |
| 存在 `RuleBasedSummarizer` | 通过 |
| 不依赖外部 LLM/API | 通过 |
| 可生成 summary | 通过 |
| 可抽取 decisions，最多 5 条 | 通过 |
| 可抽取 todos，最多 8 条 | 通过 |
| 可复用关键词抽取逻辑 | 通过，通过 `keyword_extractor` 注入 |
| 摘要有长度控制 | 部分通过，目标 500，但实测可能为 501 |
| 无明确决策/待办时返回空列表 | 通过，使用无触发词文本验证为空列表 |
| 是否存在循环导入风险 | 未发现直接循环导入。`memory_core` 懒加载 `RuleBasedSummarizer`，`summarizers.py` 不导入 `memory_core` |

额外评价：

- 决策触发词包含 `use`、`decision` 等英文短词或子串，容易误判。例如 `decisions` 包含 `decision`，导致 TODO 句子被识别为关键决策。
- 待办触发词包含“测试”“检查”“实现”等高频词，适合 MVP 召回，但误召回风险较高。
- 句子切分支持中文句号、问号、感叹号、分号、换行和部分英文标点；对 Markdown 列表的处理有限，因为 `_split_sentences()` 会合并空白，列表结构会被弱化。

## 7. 关键词增强核验结果

核验函数：`extract_keywords(text, topic="", max_keywords=10)`

| 核验项 | 结果 |
|---|---|
| 函数名和签名兼容 | 通过，`topic` 仍有默认值，旧调用可用 |
| 优先尝试 `jieba` | 通过，模块导入时设置 `_JIEBA_AVAILABLE` |
| 未安装 `jieba` 自动回退 | 通过，当前环境 `jieba_installed=False`，测试和手动断言通过 |
| 停用词过滤 | 通过，存在中英文停用词集合 |
| 中文关键词抽取 | 通过 |
| 英文技术 token 抽取 | 通过 |
| Python 函数名抽取 | 通过，实测包含 `save_memory`、`retrieve_memory` |
| 文件名/模块名抽取 | 部分通过，`memory_core.py` 被拆为 `memory_core`、`index.json` 被拆为 `index`、`json` |
| 去重且保持稳定顺序 | 通过 |
| 遵守 `max_keywords` | 通过 |
| `requirements.txt` 标注 `jieba` 为可选依赖 | 通过 |
| 未安装 `jieba` 时测试通过 | 通过 |

## 8. Markdown 与 index.json 元数据核验结果

### 8.1 `save_memory()` 核验

| 核验项 | 结果 |
|---|---|
| 接入默认摘要器 | 通过 |
| 支持可选 `summarizer` 参数 | 通过 |
| 旧调用 `save_memory(topic, text)` 不受影响 | 通过 |
| Markdown 包含 `# 主题` | 通过 |
| Markdown 包含更新时间 | 通过 |
| Markdown 包含 `## 摘要` | 通过 |
| Markdown 包含 `## 关键词` | 通过 |
| Markdown 包含 `## 关键决策` | 通过 |
| Markdown 包含 `## 待办事项` | 通过 |
| Markdown 包含 `## 原始对话摘录` | 通过 |
| 无决策时输出“无明确关键决策。” | 通过 |
| 无待办时输出“无明确待办事项。” | 通过 |
| append=True 追加 | 通过，测试覆盖 |
| append=False 覆盖 | 通过，测试覆盖 |
| 文件名安全处理 | 通过，沿用 `slugify_topic()` |

手动保存命令生成：

```text
memory/topics/Phase2_Codex_核验_2026-06-03.md
```

该文件包含摘要、关键词、关键决策、待办事项和原始对话摘录。

### 8.2 `index.json` 核验

| 核验项 | 结果 |
|---|---|
| `MemoryRecord` 新增 `decisions/todos` | 通过 |
| `save_memory()` 写入 `decisions/todos` | 通过 |
| `retrieve_memory()` 返回 `decisions/todos` | 通过 |
| `rebuild_index()` 可解析新格式 summary/keywords/decisions/todos | 通过 |
| `rebuild_index()` 兼容旧格式 Markdown | 通过，测试覆盖 |
| 旧 index 无 `decisions/todos` 时不报错 | 通过 |
| `index.json` 有效 JSON | 通过 |
| `ensure_ascii=False`、`indent=2` 可读性保持 | 通过 |
| `memory/topics/README.md` 不被索引 | 通过 |

注意：`save_memory()` 直接写入索引时 key 是 `slugify_topic(topic)`，而 `rebuild_index()` 使用 `slugify_topic(path.stem)`，会把日期也放入 key。当前不影响检索，但会导致索引 id 在保存后和重建后不一致。

## 9. score_record() 评分核验结果

核验函数：`score_record(query, record)`

| 核验项 | 结果 |
|---|---|
| 函数名和签名兼容 | 通过 |
| 主题命中权重最高或明显较高 | 通过，完整主题命中 +15，token 命中 +5 |
| keywords 命中有效召回 | 通过 |
| summary 命中加分 | 通过 |
| decisions/todos 命中加分 | 通过 |
| 英文大小写不敏感 | 通过，统一 lower |
| 过滤中文无效短词 | 通过，停用词和 2 字以下过滤 |
| 时间衰减/最近加分存在且不过度 | 通过，7 天内只加 2 分 |
| 评分逻辑简单可解释 | 通过 |
| 未引入向量检索或外部依赖 | 通过 |

手动断言结果：

```text
topic score: 67
summary score: 22
keyword score: 6
decision score: 32
todo score: 20
stop-words-only score: 0
```

结论：主题命中明显高于仅命中摘要；关键词、决策、待办均能召回；纯停用词不会大量召回。

## 10. format_context() 输出核验结果

核验函数：`format_context(results, max_chars_per_item=1200)`

| 核验项 | 结果 |
|---|---|
| 输出主题 | 通过 |
| 输出文件路径 | 通过 |
| 输出相关分 | 通过 |
| 优先输出摘要 | 通过 |
| 优先输出关键决策 | 通过 |
| 优先输出待办事项 | 通过 |
| 必要时输出内容片段 | 通过 |
| 无结果时输出明确提示 | 通过 |
| 中文输出正常 | 通过 |
| 不无节制注入完整原文 | 基本通过 |
| `max_chars_per_item` 有效 | 部分通过，主体内容有效，但最终块长度可超过该值 |

手动普通检索输出已包含：

- `**摘要**`
- `**关键决策**`
- `**待办事项**`
- `**内容**`

## 11. CLI 手动验证结果

### 11.1 保存结构化记忆

命令：

```bash
python scripts/summarize_session.py --topic "Phase2 Codex 核验" --text "团队决定使用规则摘要器完成第二阶段开发。下一步需要补充 Codex 核验报告。TODO: 检查 decisions 和 todos 是否写入 index.json。"
```

结果：成功，输出：

```text
Memory saved: D:\SmartManufacturingWorkshop\program\ClaudeMeory\memory\topics\Phase2_Codex_核验_2026-06-03.md
```

### 11.2 普通检索

命令：

```bash
python scripts/retrieve_memory.py --query "规则摘要器 Codex 核验"
```

结果：成功，输出包含摘要、关键决策、待办事项和内容片段。中文 stdout 正常。

### 11.3 JSON 检索

命令：

```bash
python scripts/retrieve_memory.py --query "规则摘要器 Codex 核验" --json
```

结果：成功。

验证：

- `json.loads()` 可按 UTF-8 解析。
- JSON 结果包含 `decisions` 和 `todos`。
- `decisions`、`todos` 均为 list。

### 11.4 重建索引

命令：

```bash
python scripts/update_index.py
```

结果：

```text
Index rebuilt. Total topics: 1
```

验证：

- `memory/index.json` 有效。
- Phase2 核验记忆被索引。
- `README.md` 未被索引。

## 12. 测试执行结果

### 12.1 unittest

命令：

```bash
python tests/test_memory_skill.py
```

结果：

```text
Ran 49 tests in 0.890s
OK
```

通过数：49  
失败数：0

### 12.2 pytest

命令：

```bash
python -m pytest
```

结果：

```text
collected 49 items
49 passed, 196 warnings in 1.00s
```

通过数：49  
失败数：0  
警告：196 条，来自当前 Anaconda 环境中的 pytest 插件弃用警告，不是项目逻辑失败。

### 12.3 测试覆盖类别

| 类别 | 状态 |
|---|---|
| `TestSummarizer` | 存在，7 项 |
| `TestKeywords` | 存在，7 项 |
| `TestStructuredMarkdown` | 存在，3 项 |
| `TestIndexMetadata` | 存在，3 项 |
| `TestScoring` | 存在，6 项 |
| `TestFormatContextEnhanced` | 存在，3 项 |
| `TestRebuildCompatibility` | 存在，3 项 |
| `TestBackwardsCompat` | 存在，4 项 |
| `TestPhase1Regression` | 存在，9 项 |
| `TestCLIJsonEnhanced` | 存在，4 项 |

特别核验：

- 第一阶段回归测试仍存在。
- 大多数核心测试使用临时目录隔离。
- CLI subprocess 测试覆盖 `--json`。
- CLI subprocess 测试覆盖 `summarize_session.py --no-append`。
- CLI subprocess 测试覆盖 `update_index.py`。
- 测试覆盖旧格式 Markdown 兼容。
- CLI subprocess 测试运行期间使用真实项目 `memory/`，但清理逻辑会删除 `CLI_`、`测试_`、`test_` 前缀文件并恢复索引。

## 13. 文档完整性核验结果

### 13.1 README.md

结果：基本通过。

已包含：

- 第二阶段新增能力说明
- 规则摘要器说明
- 中文关键词增强说明
- 关键决策抽取说明
- 待办事项抽取说明
- 检索评分优化说明
- `jieba` 可选依赖说明
- 新 `index.json` 示例
- 新 Markdown 记忆文件格式示例
- 当前能力边界说明：规则摘要，不是 LLM 语义摘要

备注：未出现精确短语“规则法摘要”，但文档表达了规则摘要器和非 LLM 的边界。

### 13.2 SKILL.md

结果：基本通过。

已包含：

- 优先注入摘要、关键决策、待办事项
- 原始对话作为低优先级补充
- 无决策/无待办时的处理规则
- 检索不到记忆时不要编造历史的等价约束

备注：未出现精确短语“不要编造”，但语义要求存在。

### 13.3 docs/DEVELOPMENT_ROADMAP.md

结果：通过。

已标记第二阶段相关任务完成，包含摘要、关键词、关键决策和待办事项增强。

### 13.4 docs/SUMMARIZER_DESIGN.md

结果：基本通过。

已包含：

- 摘要器架构
- `SummaryResult`
- `BaseSummarizer`
- `RuleBasedSummarizer`
- 处理流程
- 如何替换为 LLM 摘要器
- 设计原则与限定条件

备注：标题使用“限定条件”而不是“当前限制”，使用“如何替换为 LLM 摘要器”而不是精确短语 “LLM Summarizer”，语义覆盖。

## 14. 依赖与边界核验结果

| 核验项 | 结果 |
|---|---|
| 未接入 OpenAI / Claude / Ollama 等外部 LLM API | 通过，源码未导入相关 SDK 或 HTTP 客户端 |
| 未引入向量数据库 | 通过 |
| 未引入数据库 | 通过 |
| `jieba` 为可选依赖 | 通过 |
| `requirements.txt` 表述准确 | 通过 |
| 第一阶段 Hook 未破坏 | 通过 |
| 第一阶段 CLI 未破坏 | 通过 |
| 第一阶段原子写入能力未破坏 | 通过 |
| 测试隔离能力 | 基本通过，但 CLI subprocess 测试仍触碰真实 memory |
| 不无节制注入大段原文 | 基本通过，format_context 有主体截断 |
| 未扩大明显路径穿越风险 | 基本通过，保存路径安全；检索路径信任旧风险仍在 |

源码导入检查显示 `scripts/` 顶层只使用标准库；`jieba` 是动态可选导入。

## 15. 安全性与可靠性问题

| 核验项 | 结果 |
|---|---|
| summarizer 处理超长文本有长度控制 | 部分通过，摘要目标 500，但可产生 501 字符 |
| Markdown 原始对话三反引号风险 | 存在风险，原始对话未转义三反引号，可能破坏 Markdown code fence |
| JSON 输出中 `decisions/todos` 始终为 list | 通过，`_safe_get_list()` 兼容旧索引 |
| `rebuild_index()` 格式异常容错 | 基本通过，缺失段落会回退或空列表；严重 malformed Markdown 不保证完整解析 |
| `retrieve_memory()` file 路径信任问题 | 仍存在，继承 Phase1 风险 |
| 循环导入风险 | 未发现直接循环导入 |
| Windows / 中文路径问题 | 基本通过，CLI stdout UTF-8 处理有效，中文文件名可显示 |
| 缓存目录残留 | 存在 `.pytest_cache/` 和 `__pycache__/`，已被 `.gitignore` 覆盖 |

## 16. 发现的问题清单

### P0：必须立即修复

无。

### P1：建议尽快修复

1. **规则触发词存在明显误判**
   - 现象：`decision` 会匹配 `decisions`，导致 `TODO: 检查 decisions 和 todos...` 同时进入关键决策和待办事项。
   - 影响：结构化记忆中的关键决策可能混入待办或字段名。
   - 建议：英文触发词使用单词边界，如 `\bdecision\b`，中文触发词也可区分“决定/确定”与“检查/测试”等动作。

2. **CLI subprocess 测试仍触碰真实 `memory/`**
   - 现象：`TestCLIJsonEnhanced` 在真实项目目录下创建 `CLI_增强测试`、`CLI_覆盖增强` 记忆再清理。
   - 影响：测试中断时可能残留真实记忆或临时索引。
   - 建议：CLI 测试也通过临时项目目录或环境变量重定向 memory 路径。

### P2：后续优化

1. **摘要长度 off-by-one**
   - 现象：目标 500 字符，实测可为 501。
   - 建议：追加省略号前预留 1 字符。

2. **`format_context()` 的 `max_chars_per_item` 不是严格总长度限制**
   - 现象：小 limit 下最终块长度可超过限制，因为标题、文件、分数等头部不计入。
   - 建议：明确参数语义为“主体内容限制”，或改为完整块级限制。

3. **原始对话中的三反引号可能破坏 Markdown**
   - 现象：`save_memory()` 直接把原始文本放入 ```text fence。
   - 建议：对原文中的 ``` 做转义，或使用更长 fence。

4. **`retrieve_memory()` 仍信任索引文件路径**
   - 现象：`PROJECT_ROOT / record["file"]` 未限制必须位于 `memory/topics/`。
   - 建议：resolve 后校验路径在 `TOPICS_DIR` 内。

5. **重建索引后 id/key 不稳定**
   - 现象：`save_memory()` 使用主题 slug 作为 key，`rebuild_index()` 使用文件 stem，重建后 key 会带日期。
   - 建议：统一 key 策略，或在索引中显式区分 stable id 与 file id。

6. **文档部分术语不是精确匹配**
   - 现象：`SUMMARIZER_DESIGN.md` 使用“限定条件”而非“当前限制”，使用“LLM 摘要器”而非 “LLM Summarizer”。
   - 影响：不影响实际使用，但自动检查时可能误判。

## 17. 被证实的 Claude Code 声明

- 新增 `scripts/summarizers.py`。
- 存在 `SummaryResult`、`BaseSummarizer`、`RuleBasedSummarizer`。
- `RuleBasedSummarizer` 能生成摘要、决策、待办和关键词。
- `RuleBasedSummarizer` 不依赖外部 LLM/API。
- `memory_core.py` 新增 `decisions/todos` 元数据。
- `extract_keywords()` 支持可选 `jieba` 和规则回退。
- `score_record()` 支持 topic、keywords、summary、decisions、todos 和时间加分。
- `format_context()` 优先输出摘要、关键决策、待办事项。
- `rebuild_index()` 兼容新旧 Markdown。
- CLI JSON 输出包含 `decisions/todos` 且可 UTF-8 解析。
- 测试数量为 49，全部通过。
- 未引入数据库、向量库或外部 LLM。
- 核心接口保持向后兼容。

## 18. 存在偏差的 Claude Code 声明

- “测试隔离不污染真实 memory”：核心测试隔离成立，但 CLI subprocess 测试仍触碰真实 `memory/` 后清理。
- “摘要长度控制 500 字以内”：存在 501 字符边界情况。
- “结构化抽取增强”：功能存在，但当前规则误判风险较明显。
- “max_chars_per_item 限制每条记忆最大字符数”：实际是近似主体限制，不是完整块长度限制。

## 19. 是否建议进入第三阶段

**建议：可以进入第三阶段，但建议先处理 P1 问题。**

第二阶段功能主体已经完成，测试和 CLI 都可运行，未发现阻断性 P0 问题。进入第三阶段 Claude Code 生态接入前，最好先修复触发词误判和 CLI 测试真实目录污染，以免 Hook/Skill 接入后放大错误记忆和测试副作用。

## 20. 下一步建议

1. 修复英文触发词边界，避免 `decisions` 被 `decision` 命中。
2. 将 CLI subprocess 测试也迁移到临时 workspace 或可配置 memory 目录。
3. 修复摘要长度 off-by-one。
4. 明确 `format_context(max_chars_per_item)` 的语义，或改为严格限制完整块长度。
5. 为原始对话中的 Markdown fence 做转义。
6. 在 `retrieve_memory()` 中限制索引路径必须位于 `memory/topics/`。
7. 统一 `save_memory()` 与 `rebuild_index()` 的索引 key 策略。
8. 进入第三阶段前，清理 `.pytest_cache/`、`__pycache__/` 等缓存目录，并决定是否保留 `Phase2_Codex_核验_2026-06-03.md` 作为核验样例。

## 21. 当前工作区变化说明

本次核验实际执行了保存和索引重建命令，因此当前工作区包含：

```text
 M memory/index.json
?? docs/CODEX_PHASE2_VERIFICATION_REPORT.md
?? memory/topics/Phase2_Codex_核验_2026-06-03.md
```

这些变化来源：

- `memory/index.json`：Phase2 CLI 保存与 `update_index.py` 重建产生。
- `memory/topics/Phase2_Codex_核验_2026-06-03.md`：手动 CLI 保存验证产生。
- `docs/CODEX_PHASE2_VERIFICATION_REPORT.md`：本报告。
