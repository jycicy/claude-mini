"""
Mini Agent Framework — 基于 Claude Code 架构的精简版 AI Agent 框架 (Python 版)

支持多模型：Claude、GPT、DeepSeek、MiMo、Qwen、Gemini、本地模型...

用法:
    from mini_agent import QueryEngine
    from mini_agent.types import EngineConfig

    # Claude
    engine = QueryEngine(EngineConfig(api_key="sk-ant-..."))

    # DeepSeek
    engine = QueryEngine(EngineConfig(
        provider="openai",
        api_key="sk-...",
        model="deepseek-v4-pro",
        base_url="https://api.deepseek.com/v1",
    ))

    result = await engine.chat("帮我列出所有 Python 文件")
    print(result.final_text)
"""

from mini_agent.engine.engine import QueryEngine
from mini_agent.loop.loop import AgenticLoop
from mini_agent.api.base import BaseProvider, create_provider
from mini_agent.context.builder import ContextBuilder
from mini_agent.tools.base import Tool, ToolRegistry
from mini_agent.permissions.manager import PermissionManager
from mini_agent.types import (
    Message,
    ToolResult,
    ToolDefinition,
    EngineConfig,
    PermissionRule,
    PermissionDecision,
)

__all__ = [
    "QueryEngine",
    "AgenticLoop",
    "BaseProvider",
    "create_provider",
    "ContextBuilder",
    "Tool",
    "ToolRegistry",
    "PermissionManager",
    "Message",
    "ToolResult",
    "ToolDefinition",
    "EngineConfig",
    "PermissionRule",
    "PermissionDecision",
]
