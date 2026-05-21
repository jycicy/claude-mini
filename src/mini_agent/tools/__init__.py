"""
工具层入口 — 注册所有内置工具

对应 Claude Code 的 src/tools.ts (getTools 函数)
"""

from mini_agent.tools.base import Tool, ToolRegistry
from mini_agent.tools.file_read import FileReadTool
from mini_agent.tools.file_write import FileWriteTool
from mini_agent.tools.file_edit import FileEditTool
from mini_agent.tools.bash import BashTool
from mini_agent.tools.glob import GlobTool
from mini_agent.tools.grep import GrepTool


def create_default_tool_registry() -> ToolRegistry:
    """创建并返回一个注册了所有默认工具的注册表"""
    registry = ToolRegistry()
    registry.register_all([
        FileReadTool(),
        FileWriteTool(),
        FileEditTool(),
        BashTool(),
        GlobTool(),
        GrepTool(),
    ])
    return registry


__all__ = [
    "Tool",
    "ToolRegistry",
    "FileReadTool",
    "FileWriteTool",
    "FileEditTool",
    "BashTool",
    "GlobTool",
    "GrepTool",
    "create_default_tool_registry",
]
