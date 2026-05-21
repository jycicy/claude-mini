"""
FileEdit 工具 — 字符串替换式编辑

对应 Claude Code 的 src/tools/FileEditTool/FileEditTool.ts

设计思想：
- 不是"全文覆写"，而是"精准替换"
- AI 提供 old_string 和 new_string，系统找到并替换
- 比全文覆写更安全、更省 token
- 如果 old_string 找不到或有多处匹配，报错（防止误操作）
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mini_agent.tools.base import Tool
from mini_agent.types import ToolResult


class FileEditTool(Tool):
    @property
    def name(self) -> str:
        return "file_edit"

    @property
    def description(self) -> str:
        return (
            "Make a targeted edit to an existing file by replacing a specific string. "
            "Provide the exact text to find (old_string) and the replacement (new_string). "
            "The old_string must match EXACTLY (including whitespace and indentation). "
            "If old_string appears multiple times, the edit will fail — include more context to make it unique."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path to the file to edit",
                },
                "old_string": {
                    "type": "string",
                    "description": "The exact string to find and replace",
                },
                "new_string": {
                    "type": "string",
                    "description": "The replacement string",
                },
            },
            "required": ["file_path", "old_string", "new_string"],
        }

    @property
    def is_read_only(self) -> bool:
        return False

    async def call(self, **kwargs: Any) -> ToolResult:
        file_path: str = kwargs["file_path"]
        old_string: str = kwargs["old_string"]
        new_string: str = kwargs["new_string"]

        try:
            resolved = Path(file_path).resolve()

            if not resolved.exists():
                return ToolResult(
                    content=f"Error: File not found: {file_path}",
                    is_error=True,
                )

            content = resolved.read_text(encoding="utf-8")

            # 检查 old_string 出现次数
            occurrences = content.count(old_string)

            if occurrences == 0:
                return ToolResult(
                    content="Error: old_string not found in file. Make sure it matches exactly (including whitespace).",
                    is_error=True,
                )

            if occurrences > 1:
                return ToolResult(
                    content=f"Error: old_string appears {occurrences} times in the file. Include more surrounding context to make it unique.",
                    is_error=True,
                )

            # 执行替换
            new_content = content.replace(old_string, new_string, 1)
            resolved.write_text(new_content, encoding="utf-8")

            return ToolResult(content=f"Successfully edited {file_path}")

        except Exception as e:
            return ToolResult(content=f"Error editing file: {e}", is_error=True)
