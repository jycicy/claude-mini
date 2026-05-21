"""
Grep 工具 — 代码内容搜索

对应 Claude Code 的 src/tools/GrepTool/GrepTool.ts

AI 需要在项目中搜索特定代码模式，
比如找到某个函数的所有调用点、搜索错误信息来源等。
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from mini_agent.tools.base import Tool
from mini_agent.types import ToolResult


class GrepTool(Tool):
    @property
    def name(self) -> str:
        return "grep"

    @property
    def description(self) -> str:
        return (
            "Search for a pattern in file contents using regex. "
            "Returns matching lines with file paths and line numbers. "
            "Use this to find function definitions, usages, error messages, etc."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "The regex pattern to search for",
                },
                "path": {
                    "type": "string",
                    "description": "Directory or file to search in (optional, defaults to project root)",
                },
                "include": {
                    "type": "string",
                    "description": 'File pattern to include (e.g., "*.py")',
                },
            },
            "required": ["pattern"],
        }

    @property
    def is_read_only(self) -> bool:
        return True

    async def call(self, **kwargs: Any) -> ToolResult:
        pattern: str = kwargs["pattern"]
        path: str = kwargs.get("path", ".")
        include: str | None = kwargs.get("include")

        try:
            # 构建 grep 命令
            cmd = "grep -rn --color=never"
            if include:
                cmd += f' --include="{include}"'
            # 排除常见无关目录
            cmd += " --exclude-dir=node_modules --exclude-dir=.git"
            cmd += " --exclude-dir=__pycache__ --exclude-dir=.venv"
            cmd += " --exclude-dir=dist --exclude-dir=build"
            cmd += f' "{pattern}" {path}'
            cmd += " 2>/dev/null | head -100"

            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.getcwd(),
            )

            stdout_bytes, _ = await asyncio.wait_for(
                process.communicate(), timeout=15
            )
            stdout = stdout_bytes.decode("utf-8", errors="replace").strip()

            if not stdout:
                return ToolResult(content=f"No matches found for pattern: {pattern}")

            lines = stdout.split("\n")
            return ToolResult(
                content=f"Found {len(lines)} match(es):\n\n{stdout}"
            )

        except asyncio.TimeoutError:
            return ToolResult(content="Error: Search timed out", is_error=True)
        except Exception:
            # grep 返回 exit code 1 表示没找到，不算错误
            return ToolResult(content=f"No matches found for pattern: {pattern}")
