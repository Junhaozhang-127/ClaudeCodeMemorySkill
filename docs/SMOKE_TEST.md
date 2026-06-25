# Real Provider Smoke Test Guide (v0.6.0)

本文档说明如何在不依赖真实 API key 的环境下手工验证 Embedding / LLM Provider。

**核心设计原则:** 所有 Provider 遵循 "有 Key 走真实 API，无 Key 自动降级 Fake，不崩溃" 的策略。

---

## 1. 环境变量

### Embedding Provider

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `EMBEDDING_API_KEY` | OpenAI-compatible API key | (空，使用 Fake) |
| `EMBEDDING_API_BASE` | API base URL | `https://api.openai.com/v1` |
| `EMBEDDING_MODEL` | 模型名 | `text-embedding-3-small` |

### LLM Provider

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LLM_API_KEY` | OpenAI-compatible API key | (空，使用 Fake) |
| `LLM_API_BASE` | API base URL | `https://api.openai.com/v1` |
| `LLM_MODEL` | 模型名 | `gpt-4o-mini` |

### 设置方式 (Windows Git Bash / WSL)

```bash
export EMBEDDING_API_KEY="sk-..."
export EMBEDDING_API_BASE="https://api.openai.com/v1"
export LLM_API_KEY="sk-..."
export LLM_API_BASE="https://api.openai.com/v1"
```

### 设置方式 (Windows PowerShell)

```powershell
$env:EMBEDDING_API_KEY="sk-..."
$env:LLM_API_KEY="sk-..."
```

---

## 2. Embedding 手工 Smoke Test

### 2.1 准备: 保存两条语义相近但词语不同的记忆

```bash
cd D:/SmartManufacturingWorkshop/program/Skill/ClaudeMeory

python scripts/summarize_session.py \
  --topic "语义测试_记忆系统架构" \
  --text "我们设计了一套基于本地 Markdown 文件的会话记忆系统，支持自动保存和关键词检索。"

python scripts/summarize_session.py \
  --topic "语义测试_上下文持久化" \
  --text "团队实现了一个对话持久化方案，将 Claude Code 会话内容存储为结构化 Markdown，并支持在新会话中检索历史上下文。"
```

### 2.2 验证: 语义检索 (semantic mode)

```bash
python scripts/retrieve_memory.py \
  --query "对话历史持久化" \
  --top-k 3 \
  --json
```

**预期:** 两条记忆都应命中，且 "语义测试_上下文持久化" 得分应高于 "语义测试_记忆系统架构"。

### 2.3 验证: 混合检索 (hybrid mode)

```bash
python -c "
from memory_core import retrieve_memory, format_context
results = retrieve_memory('Markdown 存储会话', mode='hybrid', top_k=3)
print(format_context(results))
"
```

**预期:** 至少命中一条记忆，score_breakdown 包含 keyword + semantic 两个分数。

### 2.4 验证: 降级行为 (不配置 key)

```bash
# 确保未设置 API key
export EMBEDDING_API_KEY=""

python -c "
from memory_core import retrieve_memory
results = retrieve_memory('对话持久化', mode='semantic', top_k=3)
if results:
    print(f'降级成功: mode={results[0].get(\"retrieval_mode\", \"?\")}')
    print(f'结果数: {len(results)}')
else:
    print('降级成功: 0 结果（非崩溃）')
"
```

**预期:** 输出 "降级成功: mode=keyword"，程序不崩溃。

---

## 3. LLM Summarizer 手工 Smoke Test

### 3.1 准备: 一段含决策和待办的长文本

```bash
python -c "
text = '''
今天团队开了项目周会。会议讨论了三个核心议题：
1. 记忆检索性能优化 —— 决定引入 embedding 语义检索作为 hybrid 模式的一部分。
2. LLM 摘要集成 —— 确认使用 OpenAI-compatible API，支持 DeepSeek 和 OpenAI。
   约束：API key 只通过环境变量配置，不写入配置文件。
3. 测试覆盖率 —— 目前 59 个新测试全部通过，但缺少真实 API 的 E2E 测试。
   下一步需要补充 smoke test 文档。
遗留问题：session workspace 隔离方案仍在设计中，预计下个版本完成。
'''
with open('smoke_test_input.txt', 'w', encoding='utf-8') as f:
    f.write(text)
"
```

### 3.2 验证: LLM 语义摘要

```bash
python -c "
from summarizers import LLMSummarizer
from llm_provider import get_llm_provider

with open('smoke_test_input.txt', 'r', encoding='utf-8') as f:
    text = f.read()

prov = get_llm_provider(provider='auto')
summarizer = LLMSummarizer(provider=prov)
result = summarizer.summarize(text, '项目周会', summary_type='semantic')

print(f'Summary: {result.summary[:200]}...')
print(f'Mode: {result.metadata.get(\"mode\")}')
print(f'Model: {result.metadata.get(\"model\")}')
print(f'Decisions: {len(result.decisions)}')
print(f'Todos: {len(result.todos)}')
"
```

**预期 (有 key):**
- Mode: `llm`
- Model: `gpt-4o-mini` (或配置的模型)
- 摘要含 "embedding"、"DeepSeek"、"OpenAI" 等关键词
- decisions = 2-3 条
- todos 包含 "smoke test" 相关项

### 3.3 验证: Memory 压缩摘要

```bash
python -c "
from summarizers import LLMSummarizer
from llm_provider import get_llm_provider

text = '''项目状态: ClaudeMeory v0.5.2，78 tests passing。
用户偏好: 中文交互，Keep code minimal。
关键文件: memory_core.py, retrieval.py。
遗留问题: EmbeddingRetriever stub 未实现。'''

prov = get_llm_provider(provider='auto')
summarizer = LLMSummarizer(provider=prov)
result = summarizer.summarize(text, '项目记忆', summary_type='memory')

print(f'Summary: {result.summary[:200]}...')
print(f'Key Points: {result.key_points}')
print(f'Entities: {result.entities}')
"
```

**预期:** 摘要保留 "v0.5.2"、"memory_core.py"、"EmbeddingRetriever" 等技术实体。

### 3.4 验证: 长文本分块 (chunk-merge)

```bash
python -c "
from summarizers import LLMSummarizer
from llm_provider import get_llm_provider

# 构造 ~10000 字符的长文本
long_text = ''
for i in range(200):
    long_text += f'第{i}段：团队讨论了记忆系统的第{i}个优化方向，确定采用方案{i%5}。需要在下个迭代中完成。\n'

prov = get_llm_provider(provider='auto')
summarizer = LLMSummarizer(provider=prov)
result = summarizer.summarize(long_text, '长文本分块测试', summary_type='brief')

print(f'Partial: {result.partial}')
print(f'Metadata: {result.metadata}')
"
```

**预期:**
- `partial: True` (长文本触发分块)
- `mode: llm_chunked`
- `chunks >= 3`

### 3.5 验证: 降级行为 (无 LLM key)

```bash
# 确保未设置 API key
export LLM_API_KEY=""

python -c "
from summarizers import LLMSummarizer
from llm_provider import get_llm_provider

prov = get_llm_provider(provider='auto')
summarizer = LLMSummarizer(provider=prov)
result = summarizer.summarize('决定使用 jieba 分词。TODO: 补充测试。', '测试')

print(f'Mode: {result.metadata.get(\"mode\")}')
print(f'Summary: {result.summary[:100]}...')
print(f'Decisions: {result.decisions}')
print(f'Todos: {result.todos}')
"
```

**预期:**
- `mode: rule_fallback`
- Summary 非空
- 程序不崩溃

---

## 4. 端到端验证: Command → Provider 串联

```bash
# 不带 key: 全链路降级验证
python -c "
from commands.registry import get_registry
reg = get_registry()

# save with rule fallback
r1 = reg.dispatch('memory:save', {'topic': 'E2E_Demo', 'text': 'Claude Code 记忆系统设计：Markdown + JSON 存储方案。决定使用 embedding 做语义检索。需要补充 LLM 摘要功能。'})
print(f'Save: {r1.ok}')

# retrieve hybrid (will fallback to keyword)
r2 = reg.dispatch('memory:retrieve', {'query': '语义检索 embedding 存储', 'mode': 'hybrid', 'top_k': 3, 'json': False})
print(f'Retrieve: {r2.ok}, hits={r2.data.get(\"hit_count\", 0)}, mode={r2.data.get(\"mode\", \"?\")}')

# quality report
r3 = reg.dispatch('memory:manage', {'action': 'quality'})
print(f'Quality: {r3.ok}, total={r3.data.get(\"total\", 0)}')

print('E2E smoke test: ALL PASSED')
"
```

**预期:** 三个 dispatch 全部 `ok=True`，无异常。

---

## 5. 检查清单

- [ ] 不配置任何 API key: 全链路降级，不崩溃
- [ ] 只配置 EMBEDDING_API_KEY: semantic 检索可用
- [ ] 只配置 LLM_API_KEY: LLM 摘要可用
- [ ] 两项都配置: 全链路真实 API
- [ ] 长文本触发 chunk-merge
- [ ] memory 类型摘要保留技术实体
- [ ] Command dispatch 端到端可用
- [ ] 降级时有 warning/log 输出
