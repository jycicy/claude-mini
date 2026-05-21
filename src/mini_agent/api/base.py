"""
Provider 基类 — 所有 LLM Provider 的统一接口

设计思想：
- 定义统一的 send_message() 接口
- 上层（Loop 层）永远只跟这个接口打交道
- 不同 Provider（Anthropic、OpenAI 兼容）各自实现细节
- 工厂函数 create_provider() 根据配置自动选择实现
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable

from mini_agent.types import (
    ContentBlock,
    Message,
    TokenUsage,
    ToolDefinition,
)


# ============================================================
# 统一响应类型
# ============================================================


@dataclass
class APIResponse:
    """
    统一的 API 响应格式

    无论底层用哪个 Provider，返回给 Loop 层的都是这个格式。
    """

    # AI 返回的内容块列表
    content: list[ContentBlock] = field(default_factory=list)
    # 停止原因: end_turn=主动结束, tool_use=需要调用工具, max_tokens=超长
    stop_reason: str = "end_turn"
    # 本次请求消耗的 token
    usage: TokenUsage = field(default_factory=TokenUsage)


# ============================================================
# Provider 基类
# ============================================================


class BaseProvider(ABC):
    """
    LLM Provider 基类

    所有 Provider 必须实现 send_message() 方法。
    上层代码只依赖这个抽象接口，不依赖具体 SDK。
    """

    @abstractmethod
    async def send_message(
        self,
        *,
        system_prompt: str,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        on_text_delta: Callable[[str], None] | None = None,
    ) -> APIResponse:
        """
        发送消息并获取响应

        Args:
            system_prompt: 系统提示词
            messages: 对话历史
            tools: 可用工具列表
            on_text_delta: 流式文本回调

        Returns:
            APIResponse: 统一格式的响应
        """
        ...

    @property
    @abstractmethod
    def model(self) -> str:
        """当前使用的模型名"""
        ...

    @model.setter
    @abstractmethod
    def model(self, value: str) -> None:
        """切换模型"""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider 标识名（用于日志和显示）"""
        ...


# ============================================================
# 工厂函数
# ============================================================


def create_provider(
    provider: str,
    *,
    api_key: str,
    model: str,
    max_tokens: int = 4096,
    base_url: str | None = None,
) -> BaseProvider:
    """
    工厂函数 — 根据 provider 名称创建对应的客户端

    Args:
        provider: "anthropic" 或 "openai"
        api_key: API 密钥
        model: 模型名称
        max_tokens: 最大输出 token 数
        base_url: 自定义 API 地址（用于 DeepSeek、MiMo 等）

    Returns:
        BaseProvider: 对应的 Provider 实例

    Examples:
        # Claude
        create_provider("anthropic", api_key="sk-ant-...", model="claude-sonnet-4-20250514")

        # DeepSeek
        create_provider("openai", api_key="sk-...", model="deepseek-v4-pro",
                        base_url="https://api.deepseek.com/v1")

        # MiMo
        create_provider("openai", api_key="sk-...", model="mimo-v2.5-pro",
                        base_url="https://api.mimo.xiaomi.com/v1")

        # GPT
        create_provider("openai", api_key="sk-...", model="gpt-4o")

        # OpenRouter（一个 key 调所有模型）
        create_provider("openai", api_key="sk-or-...", model="deepseek/deepseek-v4-pro",
                        base_url="https://openrouter.ai/api/v1")
    """
    if provider == "anthropic":
        from mini_agent.api.anthropic_provider import AnthropicProvider

        return AnthropicProvider(
            api_key=api_key,
            model=model,
            max_tokens=max_tokens,
            base_url=base_url,
        )
    elif provider == "openai":
        from mini_agent.api.openai_provider import OpenAIProvider

        return OpenAIProvider(
            api_key=api_key,
            model=model,
            max_tokens=max_tokens,
            base_url=base_url,
        )
    else:
        raise ValueError(
            f'Unknown provider: "{provider}". '
            f"Supported providers: anthropic, openai"
        )
