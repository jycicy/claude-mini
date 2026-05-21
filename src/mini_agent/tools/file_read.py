"""
FileRead 工具 — 读取文件内容

对应 Claude Code 的 src/tools/FileReadTool/FileReadTool.ts

这是最基础的工具之一。AI 需要"看"代码才能理解项目，
FileRead 就是 AI 的"眼睛"。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from mini_agent.tools.base import Tool
from mini_agent.types import ToolResult


class FileReadTool(Tool):
    @property
    def name(self) -> str:
        return "file_read"

    @property
    def description(self) -> str:
        return (
            "Read the contents of a file from the local filesystem. "
            "Use this when you need to examine code, configuration files, or any text file. "
            "The file_path must be an absolute path or relative to the project root. "
            "For large files, use offset and limit to read specific sections."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path to the file to read",
                },
                "offset": {
                    "type": "integer",
                    "description": "Line number to start reading from (0-indexed, optional)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of lines to read (optional, default: 2000)",
                },
            },
            "required": ["file_path"],
        }

    @property
    def is_read_only(self) -> bool:
        return True

    async def call(self, **kwargs: Any) -> ToolResult:
        file_path: str = kwargs["file_path"]
        offset: int = kwargs.get("offset", 0)
        limit: int = kwargs.get("limit", 2000)

        try:
            resolved = Path(file_path).resolve()

            if not resolved.exists():
                return ToolResult(
                    content=f"Error: File not found: {file_path}",
                    is_error=True,
                )

            if not resolved.is_file():
                return ToolResult(
                    content=f"Error: Not a file: {file_path}",
                    is_error=True,
                )

            text = resolved.read_text(encoding="utf-8")
            lines = text.split("\n")
            total_lines = len(lines)

            # 应用 offset 和 limit
            sliced = lines[offset : offset + limit]
            result = "\n".join(sliced)

            # 构建输出（带行号信息）
            output = ""
            if offset > 0 or limit < total_lines:
                end = min(offset + limit, total_lines)
                output += f"[Showing lines {offset + 1}-{end} of {total_lines}]\n\n"
            output += result

            return ToolResult(content=output)

        except UnicodeDecodeError:
            return ToolResult(
                content=f"Error: File is not valid UTF-8 text: {file_path}",
                is_error=True,
            )
        except Exception as e:
            return ToolResult(content=f"Error reading file: {e}", is_error=True)
