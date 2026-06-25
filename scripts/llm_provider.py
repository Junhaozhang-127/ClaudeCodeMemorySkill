"""
llm_provider.py — 可配置的 LLM Provider 抽象层 (v0.6.0)

提供:
  - LLMProvider: 抽象基类
  - FakeLLMProvider: 确定性假 LLM（测试用）
  - OpenAILLMProvider: OpenAI-compatible API provider
  - get_llm_provider: 工厂函数

安全约束: API key 只从环境变量读取，不写入配置文件。
"""

from __future__ import annotations

import hashlib
import os
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """LLM Provider 抽象基类。

    所有 LLM 实现必须继承此类。
    """

    @abstractmethod
    def complete(self, prompt: str, task: str = "") -> str:
        """执行单次 completion。"""
        ...

    @abstractmethod
    def complete_batch(self, prompts: list[str], task: str = "") -> list[str]:
        """批量执行 completion。"""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """返回模型名。"""
        ...


# ═══════════════════════════════════════════════════════════════
# FakeLLMProvider — 确定性假 LLM（测试用）
# ═══════════════════════════════════════════════════════════════

class FakeLLMProvider(LLMProvider):
    """基于规则的假 LLM provider。

    不做真正的 LLM 调用，通过规则提取和重组输入内容来模拟摘要行为。
    输出是确定性的（相同输入产生相同输出）。
    """

    def __init__(self):
        self._model = "fake-llm-v1"

    @property
    def model_name(self) -> str:
        return self._model

    def complete(self, prompt: str, task: str = "") -> str:
        return self._fake_complete(prompt, task)

    def complete_batch(self, prompts: list[str], task: str = "") -> list[str]:
        return [self._fake_complete(p, task) for p in prompts]

    def _fake_complete(self, prompt: str, task: str) -> str:
        """从输入中提取关键信息作为"摘要"输出。

        策略:
          - 提取决策/结论性语句（含"决定""采用""结论""Phase"等词）
          - 提取待办/下一步（含"需要""TODO""待办"等词）
          - 保留技术实体（文件名、模块名、API名、版本号）
          - 对 summarize 任务生成结构化输出
        """
        import re

        if task == "summarize":
            lines = prompt.replace("\n", " ").split("。")
        else:
            lines = prompt.replace("\n", " ").split("。")

        # 决策关键词
        decision_keywords = ["决定", "采用", "选择", "确定", "结论", "最终",
                            "方案", "架构", "设计", "Phase", "v0."]
        # 待办关键词
        todo_keywords = ["需要", "TODO", "待办", "下一步", "修复", "补充",
                        "优化", "增加", "测试", "检查", "实现"]
        # 实体关键词
        entity_patterns = [
            r"\b\w+\.py\b", r"\b\w+\.json\b", r"\b\w+\.md\b",
            r"\b\w+\.sh\b", r"v\d+\.\d+\.\d+", r"Phase\s*\d+",
            r"\b[A-Z][a-z]+[A-Z]\w*\b",
        ]

        decisions = []
        todos = []
        entities = set()

        for line in lines:
            line = line.strip()
            if not line or len(line) < 3:
                continue
            for kw in decision_keywords:
                if kw in line and line not in decisions:
                    decisions.append(line[:120])
                    break
            for kw in todo_keywords:
                if kw in line and line not in todos:
                    todos.append(line[:120])
                    break
            for pat in entity_patterns:
                found = re.findall(pat, line)
                entities.update(found)

        parts = []
        if decisions:
            parts.append("关键决策: " + "; ".join(decisions[:3]))
        if todos:
            parts.append("待办事项: " + "; ".join(todos[:3]))
        if entities:
            parts.append("相关实体: " + ", ".join(sorted(entities)[:8]))
        if not parts:
            # fallback: 取前 3 句作为摘要
            parts.append("内容摘要: " + "。".join(
                l.strip() for l in lines[:5] if l.strip()
            )[:500])
        return "。".join(parts) + "。"


# ═══════════════════════════════════════════════════════════════
# OpenAILLMProvider — OpenAI-compatible API
# ═══════════════════════════════════════════════════════════════

class OpenAILLMProvider(LLMProvider):
    """OpenAI-compatible Chat Completions API provider。

    支持 OpenAI / DeepSeek / 任何兼容 /v1/chat/completions 端点。

    Config (all from env vars):
      LLM_API_KEY — required
      LLM_API_BASE — defaults to https://api.openai.com/v1
      LLM_MODEL — defaults to gpt-4o-mini
    """

    def __init__(
        self,
        api_key: str = "",
        api_base: str = "",
        model: str = "",
        timeout: float = 60.0,
    ):
        self._api_key = api_key or os.environ.get("LLM_API_KEY", "")
        self._api_base = api_base or os.environ.get(
            "LLM_API_BASE", "https://api.openai.com/v1"
        )
        self._model = model or os.environ.get("LLM_MODEL", "gpt-4o-mini")
        self._timeout = timeout

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    def complete(self, prompt: str, task: str = "") -> str:
        results = self.complete_batch([prompt], task)
        return results[0] if results else ""

    def complete_batch(self, prompts: list[str], task: str = "") -> list[str]:
        if not self._api_key:
            raise ValueError(
                "LLM_API_KEY 未设置。请设置环境变量 LLM_API_KEY 或"
                " 使用 FakeLLMProvider 进行测试。"
            )
        import json
        import urllib.request
        import urllib.error

        results = []
        for prompt in prompts:
            system_msg = self._system_prompt_for_task(task)
            payload = json.dumps({
                "model": self._model,
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 800,
            }).encode("utf-8")

            url = self._api_base.rstrip("/") + "/chat/completions"
            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._api_key}",
                },
            )
            try:
                resp = urllib.request.urlopen(req, timeout=self._timeout)
                body = json.loads(resp.read().decode("utf-8"))
                content = body["choices"][0]["message"]["content"]
                results.append(content.strip())
            except urllib.error.HTTPError as e:
                raise RuntimeError(
                    f"LLM API 请求失败 ({e.code}): {e.reason}"
                ) from e
            except Exception as e:
                raise RuntimeError(f"LLM API 请求失败: {e}") from e

        return results

    def _system_prompt_for_task(self, task: str) -> str:
        if task == "summarize":
            return (
                "你是一个专业的文本摘要助手。请从对话中提取关键信息，"
                "以结构化方式输出：摘要、关键决策、待办事项、实体列表。"
                "只输出原文中存在的内容，不要编造。不确定的地方标记为[不确定]。"
            )
        if task == "memory":
            return (
                "你是一个记忆压缩助手。从对话中提取可复用的信息："
                "用户偏好、项目状态、关键决策、待办线索。"
                "保留文件名、模块名、版本号、接口名等技术实体。"
            )
        return "你是一个有帮助的助手。请简洁准确地回答。"


# ═══════════════════════════════════════════════════════════════
# 工厂函数
# ═══════════════════════════════════════════════════════════════

def get_llm_provider(provider: str = "auto") -> LLMProvider:
    """获取 LLMProvider 实例。

    Args:
        provider: "auto" / "openai" / "fake"
            - auto: 优先使用 OpenAI（若 LLM_API_KEY 已设），否则回退到 Fake
            - openai: 强制 OpenAI，无 key 时抛异常
            - fake: 使用 FakeLLMProvider

    Returns:
        LLMProvider 实例。
    """
    if provider == "fake":
        return FakeLLMProvider()

    if provider == "openai":
        p = OpenAILLMProvider()
        if not p.is_configured:
            raise ValueError(
                "LLM_API_KEY 环境变量未设置。请设置后重试，或使用 provider='fake'。"
            )
        return p

    # auto: 优先 OpenAI
    openai_p = OpenAILLMProvider()
    if openai_p.is_configured:
        return openai_p
    return FakeLLMProvider()
