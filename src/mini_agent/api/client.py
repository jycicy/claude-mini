"""
通信层 — LLM API 客户端

对应 Claude Code 的 src/services/api/client.ts + claude.ts

职责：
1. 封装 Anthropic SDK 调用
2. 流式接收响应
3. 统一输出格式（无论底层用什么 Provider）

设计思想：
- 上层（Loop 层）不需要知道 API 的具体细节
- 流式优先：逐 token 返回，让 UI 可以实时展示
- 错误分类：区分可重试/不可重试错误
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import anthropic

from mini_agent.types import (
    ContentBlock,
    Message,
    Role,
    TextContent,
    ToolDefinition,
    ToolUseContent,
    TokenUsage,
)


# ============================================================
# 配置
# ============================================================


@dataclass
class APIClientConfig:
    """API 客户端配置"""

    api_key: str
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    base_url: str | None = None


# ============================================================
# 响应类型
# ============================================================


@dataclass
class APIResponse:
    """API 响应"""

    # AI 返回的内容块列表
    content: list[ContentBlock] = field(default_factory=list)
    # 停止原因: end_turn=主动结束, tool_use=需要调用工具, max_tokens=超长
    stop_reason: str = "end_turn"
    # 本次请求消耗的 token
    usage: TokenUsage = field(default_factory=TokenUsage)


# ============================================================
# API 客户端
# ============================================================


class APIClient:
    """
    Anthropic API 客户端

    封装所有与 LLM 的通信。整个框架的"网络出口"——
    所有与大模型的交互都经过这里。
    """

    def __init__(self, config: APIClientConfig) -> None:
        kwargs: dict[str, Any] = {"api_key": config.api_key}
        if config.base_url:
            kwargs["base_url"] = config.base_url

        self._client = anthropic.Anthropic(**kwargs)
        self._model = config.model
        self._max_tokens = config.max_tokens

    async def send_message(
        self,
        *,
        system_prompt: str,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        on_text_delta: Callable[[str], None] | None = None,
    ) -> APIResponse:
        """
        发送消息并流式接收响应

        这是整个框架的"网络出口"——所有与 LLM 的通信都经过这里

        Args:
            system_prompt: 系统提示词（动态组装的）
            messages: 对话历史
            tools: 可用工具列表（AI 根据这个决定调用哪些工具）
            on_text_delta: 文本流回调（用于实时展示）

        Returns:
            APIResponse: 包含内容块、停止原因和 token 使用量
        """
        # 转换消息格式为 Anthropic SDK 要求的格式
        api_messages = self._convert_messages(messages)

        # 构建请求参数
        request_params: dict[str, Any] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "system": system_prompt,
            "messages": api_messages,
        }

        # 添加工具定义
        if tools:
            request_params["tools"] = [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.input_schema,
                }
                for t in tools
            ]

        # 使用流式 API
        content_blocks: list[ContentBlock] = []

        with self._client.messages.stream(**request_params) as stream:
            for text in stream.text_stream:
                if on_text_delta:
                    on_text_delta(text)

            # 获取最终完整消息
            response = stream.get_final_message()

        # 解析响应内容
        for block in response.content:
            if block.type == "text":
                content_blocks.append(TextContent(text=block.text))
            elif block.type == "tool_use":
                content_blocks.append(
                    ToolUseContent(
                        id=block.id,
                        name=block.name,
                        input=block.input if isinstance(block.input, dict) else {},
                    )
                )

        return APIResponse(
            content=content_blocks,
            stop_reason=response.stop_reason or "end_turn",
            usage=TokenUsage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            ),
        )

    def _convert_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        """将内部 Message 格式转换为 Anthropic API 格式"""
        api_messages: list[dict[str, Any]] = []

        for msg in messages:
            if msg.role == Role.SYSTEM:
                continue  # system 消息通过 system 参数传递

            if isinstance(msg.content, str):
                api_messages.append({
                    "role": msg.role.value,
                    "content": msg.content,
                })
            else:
                # 转换 ContentBlock 列表为 API 格式
                content_list: list[dict[str, Any]] = []
                for block in msg.content:
                    if isinstance(block, TextContent):
                        content_list.append({"type": "text", "text": block.text})
                    elif isinstance(block, ToolUseContent):
                        content_list.append({
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input,
                        })
                    elif hasattr(block, "tool_use_id"):
                        # ToolResultContent
                        content_list.append({
                            "type": "tool_result",
                            "tool_use_id": block.tool_use_id,
                            "content": block.content,
                            **({"is_error": True} if block.is_error else {}),
                        })

                api_messages.append({
                    "role": msg.role.value,
                    "content": content_list,
                })

        return api_messages

    @property
    def model(self) -> str:
        """获取当前模型名称"""
        return self._model

    @model.setter
    def model(self, value: str) -> None:
        """动态切换模型（用于子代理场景或 fallback）"""
        self._model = value
