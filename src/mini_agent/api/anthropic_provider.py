"""
Anthropic Provider — Claude 系列模型

使用 Anthropic 官方 SDK 通信。
支持通过 base_url 连接兼容 Anthropic 协议的第三方服务（如 DeepSeek 的 /anthropic 端点）。
"""

from __future__ import annotations

from typing import Any, Callable

import anthropic

from mini_agent.api.base import APIResponse, BaseProvider
from mini_agent.types import (
    ContentBlock,
    Message,
    Role,
    TextContent,
    TokenUsage,
    ToolDefinition,
    ToolResultContent,
    ToolUseContent,
)


class AnthropicProvider(BaseProvider):
    """
    Anthropic Provider

    适用于：
    - Claude 官方 API (https://api.anthropic.com)
    - 兼容 Anthropic 协议的第三方（如 DeepSeek /anthropic 端点）
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096,
        base_url: str | None = None,
    ) -> None:
        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url

        self._client = anthropic.Anthropic(**kwargs)
        self._model = model
        self._max_tokens = max_tokens
        self._base_url = base_url

    async def send_message(
        self,
        *,
        system_prompt: str,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        on_text_delta: Callable[[str], None] | None = None,
    ) -> APIResponse:
        """发送消息到 Anthropic API"""
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

        # 流式调用
        content_blocks: list[ContentBlock] = []

        with self._client.messages.stream(**request_params) as stream:
            for text in stream.text_stream:
                if on_text_delta:
                    on_text_delta(text)
            response = stream.get_final_message()

        # 解析响应
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
        """将内部消息格式转换为 Anthropic API 格式"""
        api_messages: list[dict[str, Any]] = []

        for msg in messages:
            if msg.role == Role.SYSTEM:
                continue

            if isinstance(msg.content, str):
                api_messages.append({"role": msg.role.value, "content": msg.content})
            else:
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
                    elif isinstance(block, ToolResultContent):
                        content_list.append({
                            "type": "tool_result",
                            "tool_use_id": block.tool_use_id,
                            "content": block.content,
                            **({"is_error": True} if block.is_error else {}),
                        })
                api_messages.append({"role": msg.role.value, "content": content_list})

        return api_messages

    @property
    def model(self) -> str:
        return self._model

    @model.setter
    def model(self, value: str) -> None:
        self._model = value

    @property
    def provider_name(self) -> str:
        return "anthropic"
