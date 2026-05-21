"""
FileWrite 工具 — 创建或覆写文件

对应 Claude Code 的 src/tools/FileWriteTool/FileWriteTool.ts

AI 的"写"能力。注意：这是一个非只读工具，
需要通过权限系统检查后才能执行。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mini_agent.tools.base import Tool
from mini_agent.types import ToolResult


class FileWriteTool(Tool):
    @property
    def name(self) -> str:
        return "file_write"

    @property
    def description(self) -> str:
        return (
            "Write content to a file. Creates the file if it doesn't exist, "
            "or overwrites it if it does. Parent directories are created automatically. "
            "Use this for creating new files or completely rewriting existing ones. "
            "For small edits to existing files, prefer file_edit instead."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path to the file to write",
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the file",
                },
            },
            "required": ["file_path", "content"],
        }

    @property
    def is_read_only(self) -> bool:
        return False

    async def call(self, **kwargs: Any) -> ToolResult:
        file_path: str = kwargs["file_path"]
        content: str = kwargs["content"]

        try:
            resolved = Path(file_path).resolve()

            # 确保父目录存在
            resolved.parent.mkdir(parents=True, exist_ok=True)

            # 写入文件
            resolved.write_text(content, encoding="utf-8")

            line_count = content.count("\n") + 1
            return ToolResult(content=f"Successfully wrote {line_count} lines to {file_path}")

        except Exception as e:
            return ToolResult(content=f"Error writing file: {e}", is_error=True)
