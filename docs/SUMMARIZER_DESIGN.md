# 摘要器架构设计

## 概述

`scripts/summarizers.py` 实现了一个**可插拔摘要器架构**，允许在不同摘要策略之间切换而不修改 `memory_core` 的核心逻辑。

当前 Phase 2 使用基于规则的本地摘要器（`RuleBasedSummarizer`），未来可无缝替换为 LLM 摘要器。

## 架构

```
┌──────────────────────────────────────────────┐
│                save_memory()                  │
│                                               │
│   summarizer: BaseSummarizer (optional)       │
│        │                                      │
│        ▼                                      │
│   summarizer.summarize(text, topic)           │
│        │                                      │
│        ▼                                      │
│   SummaryResult                               │
│   ├── summary: str                            │
│   ├── decisions: list[str]                    │
│   ├── todos: list[str]                        │
│   └── keywords: list[str]                     │
└──────────────────────────────────────────────┘
```

## 核心接口

### SummaryResult

```python
@dataclass
class SummaryResult:
    summary: str = ""           # 摘要文本
    decisions: list[str] = []   # 关键决策列表
    todos: list[str] = []       # 待办事项列表
    keywords: list[str] = []    # 关键词列表
```

### BaseSummarizer

```python
class BaseSummarizer(ABC):
    @abstractmethod
    def summarize(self, text: str, topic: str = "") -> SummaryResult:
        ...
```

任何实现 `BaseSummarizer.summarize()` 的类都可以作为摘要器传入 `save_memory()`。

## RuleBasedSummarizer 工作方式

当前默认实现，**不依赖任何外部 API 或模型**。

### 处理流程

1. **句子分割**（`_split_sentences`）
   - 按中文/英文标点分割文本为句子
   - 移除代码块和行内代码噪声
   - 合并过短片段

2. **摘要生成**（`_generate_summary`）
   - 取前 3~5 个有效句子
   - 控制在 500 字符以内
   - 去除多余空白和换行

3. **关键决策抽取**（`_extract_decisions`）
   - 匹配触发词：决定、确定、采用、选择、保持、不再、改为、结论、同意、确认、最终、方案、confirmed、decided、decision、use、choose、finalize、agree、conclusion
   - 最多返回 5 条
   - 无匹配时返回空列表

4. **待办事项抽取**（`_extract_todos`）
   - 匹配触发词：需要、下一步、待办、修复、补充、优化、增加、测试、检查、实现、完善、TODO、FIXME、fix、add、test、check、implement、update、remove
   - 也检测列表项（`- * 1.` 开头）
   - 最多返回 8 条
   - 无匹配时返回空列表

5. **关键词生成**
   - 调用注入的 `keyword_extractor` 函数
   - 默认为 `memory_core.extract_keywords`
   - jieba 可用时优先使用 jieba 分词

### 限定条件

- **不发送任何网络请求**
- **不调用任何外部 API**
- **不访问文件系统**（除 keyword_extractor 间接访问外）
- 所有处理均在内存中完成

## 如何替换为 LLM 摘要器

### 步骤 1：实现新摘要器

```python
# scripts/llm_summarizer.py
from summarizers import BaseSummarizer, SummaryResult

class LLMSummarizer(BaseSummarizer):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        self.api_key = api_key
        self.model = model

    def summarize(self, text: str, topic: str = "") -> SummaryResult:
        # 调用 Claude API 或本地模型
        prompt = f"""请从以下对话中提取结构化信息。
主题：{topic}

请返回 JSON 格式：
{{
    "summary": "简要摘要",
    "decisions": ["决策1", "决策2"],
    "todos": ["待办1", "待办2"],
    "keywords": ["关键词1", "关键词2"]
}}

对话内容：
{text}
"""
        # response = call_llm_api(prompt)
        # return parse_response(response)
        ...
```

### 步骤 2：注入到 save_memory()

```python
from llm_summarizer import LLMSummarizer

summarizer = LLMSummarizer(api_key="...")
path = save_memory("主题", "内容", summarizer=summarizer)
```

### 步骤 3：（可选）设为默认

修改 `memory_core._get_default_summarizer()` 以返回 `LLMSummarizer`。

## 设计原则

1. **开闭原则**：对扩展开放（新增摘要器），对修改关闭（不改变 memory_core 接口）
2. **依赖注入**：摘要器通过参数传入 `save_memory()`，不在内部硬编码
3. **向后兼容**：`summarizer=None` 时使用默认 RuleBasedSummarizer，旧代码无需修改
4. **优雅降级**：LLM 不可用时自动回退到 RuleBasedSummarizer
