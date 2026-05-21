"""
工具层 — 基础工具定义

对应 Claude Code 的 src/Tool.ts

设计思想：
- 每个工具是一个独立的"能力单元"
- 统一接口：name + description + input_schema + call()
- AI 根据 description 决定用哪个工具（所以描述质量很重要！）
- is_read_only 标记影响权限检查逻辑
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from mini_agent.types import ToolDefinition, ToolResult


class Tool(ABC):
    """
    工具基类 — 所有工具必须继承此类

    对应 Claude Code 中每个工具的标准接口。
    AI 根据 description 决定使用哪个工具，
    所以描述质量直接影响 AI 的决策准确性。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称（唯一标识）"""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """给 AI 看的描述（AI 据此决定是否使用该工具）"""
        ...

    @property
    @abstractmethod
    def input_schema(self) -> dict[str, Any]:
        """参数的 JSON Schema"""
        ...

    @property
    def is_read_only(self) -> bool:
        """是否只读（只读工具可跳过权限检查）"""
        return False

    @abstractmethod
    async def call(self, **kwargs: Any) -> ToolResult:
        """执行工具"""
        ...

    def to_definition(self) -> ToolDefinition:
        """导出为 API 所需的 ToolDefinition 格式"""
        return ToolDefinition(
            name=self.name,
            description=self.description,
            input_schema=self.input_schema,
        )


class ToolRegistry:
    """
    工具注册表 — 管理所有可用工具

    对应 Claude Code 的 src/tools.ts (getTools 函数)
    """

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """注册一个工具"""
        if tool.name in self._tools:
            raise ValueError(f'Tool "{tool.name}" already registered')
        self._tools[tool.name] = tool

    def register_all(self, tools: list[Tool]) -> None:
        """注册多个工具"""
        for tool in tools:
            self.register(tool)

    def get(self, name: str) -> Tool | None:
        """通过名称获取工具"""
        return self._tools.get(name)

    def get_all(self) -> list[Tool]:
        """获取所有已注册工具"""
        return list(self._tools.values())

    def to_definitions(self) -> list[ToolDefinition]:
        """导出为 API 所需的 ToolDefinition 格式列表"""
        return [tool.to_definition() for tool in self._tools.values()]

    def has(self, name: str) -> bool:
        """检查工具是否存在"""
        return name in self._tools
