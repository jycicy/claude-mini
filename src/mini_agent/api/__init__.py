"""
通信层 — 多 Provider API 适配

支持的 Provider：
- anthropic: Claude 系列（Anthropic 官方 API）
- openai: OpenAI 格式兼容（GPT、DeepSeek、MiMo、Qwen、Gemini via OpenRouter...）

设计思想：
- 上层只调用统一接口 send_message()
- 底层根据 provider 选择不同的 SDK
- 切换模型只需改配置，不改代码
"""

from mini_agent.api.base import BaseProvider, APIResponse, create_provider
from mini_agent.api.anthropic_provider import AnthropicProvider
from mini_agent.api.openai_provider import OpenAIProvider

__all__ = [
    "BaseProvider",
    "APIResponse",
    "AnthropicProvider",
    "OpenAIProvider",
    "create_provider",
]
