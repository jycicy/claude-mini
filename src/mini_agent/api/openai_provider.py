"""
OpenAI-Compatible Provider — 兼容 OpenAI 格式的所有模型

这是一个"万能适配器"，因为几乎所有模型都兼容 OpenAI 格式：
- OpenAI GPT 系列 (gpt-4o, gpt-4-turbo, ...)
- DeepSeek (deepseek-v4-pro, deepseek-v4-flash, deepseek-chat)
- MiMo / 小米 (mimo-v2.5-pro, mimo-v2-flash)
- Qwen / 通义千问 (qwen-max, qwen-plus)
- GLM / 智谱 (glm-4)
- Google Gemini (via OpenRouter)
- 本地模型 (Ollama, vLLM, LM Studio)
- 聚合平台 (OpenRouter, SiliconFlow, 硅基流动)

只需要换 base_url 和 model 名即可。
"""

from __future__ import annotations

import json
from typing import Any, Callable

from openai import OpenAI

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


# ============================================================
# 预设的 Provider 配置（方便用户快速使用）
# ============================================================

PROVIDER_PRESETS: dict[str, dict[str, str]] = {
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-v4-pro",
    },
    "mimo": {
        "base_url": "https://api.mimo.xiaomi.com/v1",
        "default_model": "mimo-v2.5-pro",
    },
    "qwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-max",
    },
    "glm": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "default_model": "glm-4",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "deepseek/deepseek-v4-pro",
    },
    "siliconflow": {
        "base_url": "https://api.siliconflow.cn/v1",
        "default_model": "deepseek-ai/DeepSeek-V3",
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "default_model": "llama3",
    },
}


class OpenAIProvider(BaseProvider):
    """
    OpenAI-Compatible Provider

    适用于所有兼容 OpenAI /v1/chat/completions 格式的模型。
    这是行业事实标准，几乎所有模型供应商都支持。

    使用方法：
        # GPT 官方
        provider = OpenAIProvider(api_key="sk-...", model="gpt-4o")

        # DeepSeek
        provider = OpenAIProvider(
            api_key="sk-...",
            model="deepseek-v4-pro",
            base_url="https://api.deepseek.com/v1",
        )

        # 本地 Ollama
        provider = OpenAIProvider(
            api_key="ollama",
            model="llama3",
            base_url="http://localhost:11434/v1",
        )
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-4o",
        max_tokens: int = 4096,
        base_url: str | None = None,
    ) -> None:
        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url

        self._client = OpenAI(**kwargs)
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
        """发送消息到 OpenAI 兼容 API"""
        api_messages = self._convert_messages(system_prompt, messages)

        # 构建请求参数
        request_params: dict[str, Any] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": api_messages,
            "stream": True,
        }

        # 添加工具定义（OpenAI 格式）
        if tools:
            request_params["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.input_schema,
                    },
                }
                for t in tools
            ]

        # 流式调用
        content_blocks: list[ContentBlock] = []
        full_text = ""
        tool_calls_data: dict[int, dict[str, Any]] = {}
        input_tokens = 0
        output_tokens = 0
        stop_reason = "end_turn"

        stream = self._client.chat.completions.create(**request_params)

        for chunk in stream:
            if not chunk.choices:
                # usage 信息可能在最后一个 chunk
                if hasattr(chunk, "usage") and chunk.usage:
                    input_tokens = chunk.usage.prompt_tokens or 0
                    output_tokens = chunk.usage.completion_tokens or 0
                continue

            choice = chunk.choices[0]
            delta = choice.delta

            # 文本流
            if delta and delta.content:
                full_text += delta.content
                if on_text_delta:
                    on_text_delta(delta.content)

            # 工具调用流
            if delta and delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_data:
                        tool_calls_data[idx] = {
                            "id": tc.id or "",
                            "name": "",
                            "arguments": "",
                        }
                    if tc.id:
                        tool_calls_data[idx]["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            tool_calls_data[idx]["name"] = tc.function.name
                        if tc.function.arguments:
                            tool_calls_data[idx]["arguments"] += tc.function.arguments

            # 停止原因
            if choice.finish_reason:
                if choice.finish_reason == "tool_calls":
                    stop_reason = "tool_use"
                elif choice.finish_reason == "length":
                    stop_reason = "max_tokens"
                else:
                    stop_reason = "end_turn"

            # usage（部分 provider 在 chunk 里带 usage）
            if hasattr(chunk, "usage") and chunk.usage:
                input_tokens = chunk.usage.prompt_tokens or 0
                output_tokens = chunk.usage.completion_tokens or 0

        # 组装内容块
        if full_text:
            content_blocks.append(TextContent(text=full_text))

        # 工具调用转为 ToolUseContent
        for _idx, tc_data in sorted(tool_calls_data.items()):
            try:
                arguments = json.loads(tc_data["arguments"]) if tc_data["arguments"] else {}
            except json.JSONDecodeError:
                arguments = {}

            content_blocks.append(
                ToolUseContent(
                    id=tc_data["id"],
                    name=tc_data["name"],
                    input=arguments,
                )
            )
            # 有工具调用时确保 stop_reason 正确
            stop_reason = "tool_use"

        return APIResponse(
            content=content_blocks,
            stop_reason=stop_reason,
            usage=TokenUsage(input_tokens=input_tokens, output_tokens=output_tokens),
        )

    def _convert_messages(
        self, system_prompt: str, messages: list[Message]
    ) -> list[dict[str, Any]]:
        """将内部消息格式转换为 OpenAI API 格式"""
        api_messages: list[dict[str, Any]] = []

        # OpenAI 格式：system prompt 作为第一条 system message
        api_messages.append({"role": "system", "content": system_prompt})

        for msg in messages:
            if msg.role == Role.SYSTEM:
                continue

            if isinstance(msg.content, str):
                api_messages.append({"role": msg.role.value, "content": msg.content})
            else:
                # 处理复杂内容（工具调用/结果）
                if msg.role == Role.ASSISTANT:
                    # assistant 消息可能包含 tool_calls
                    text_parts: list[str] = []
                    tool_calls: list[dict[str, Any]] = []

                    for block in msg.content:
                        if isinstance(block, TextContent):
                            text_parts.append(block.text)
                        elif isinstance(block, ToolUseContent):
                            tool_calls.append({
                                "id": block.id,
                                "type": "function",
                                "function": {
                                    "name": block.name,
                                    "arguments": json.dumps(block.input, ensure_ascii=False),
                                },
                            })

                    assistant_msg: dict[str, Any] = {"role": "assistant"}
                    if text_parts:
                        assistant_msg["content"] = "\n".join(text_parts)
                    else:
                        assistant_msg["content"] = None
                    if tool_calls:
                        assistant_msg["tool_calls"] = tool_calls

                    api_messages.append(assistant_msg)

                elif msg.role == Role.USER:
                    # user 消息中的 ToolResultContent → OpenAI 的 tool message
                    for block in msg.content:
                        if isinstance(block, ToolResultContent):
                            api_messages.append({
                                "role": "tool",
                                "tool_call_id": block.tool_use_id,
                                "content": block.content,
                            })
                        elif isinstance(block, TextContent):
                            api_messages.append({
                                "role": "user",
                                "content": block.text,
                            })

        return api_messages

    @property
    def model(self) -> str:
        return self._model

    @model.setter
    def model(self, value: str) -> None:
        self._model = value

    @property
    def provider_name(self) -> str:
        return "openai"
