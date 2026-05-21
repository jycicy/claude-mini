"""
Mini Agent Framework — 基于 Claude Code 架构的精简版 AI Agent 框架 (Python 版)

用法:
    from mini_agent import QueryEngine

    engine = QueryEngine(
        api_key="sk-ant-...",
        model="claude-sonnet-4-20250514",
        project_root="/path/to/project",
    )
    result = await engine.chat("帮我列出所有 Python 文件")
    print(result.final_text)
"""

from mini_agent.engine.engine import QueryEngine
from mini_agent.loop.loop import AgenticLoop
from mini_agent.api.client import APIClient
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
    "APIClient",
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
