"""
Glob 工具 — 文件模式搜索

对应 Claude Code 的 src/tools/GlobTool/GlobTool.ts

AI 需要"发现"项目中有哪些文件，Glob 就是它的"目录浏览器"。
比如搜索所有 .py 文件、找到某个模块的所有测试文件等。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mini_agent.tools.base import Tool
from mini_agent.types import ToolResult

# 排除的目录
EXCLUDED_DIRS = {
    "node_modules",
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    ".tox",
    "dist",
    "build",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "egg-info",
}


class GlobTool(Tool):
    @property
    def name(self) -> str:
        return "glob"

    @property
    def description(self) -> str:
        return (
            "Find files matching a glob pattern in the project. "
            "Use this to discover project structure, find specific file types, or locate files by name. "
            'Examples: "**/*.py", "src/**/test_*.py", "pyproject.toml"'
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "The glob pattern to match files against",
                },
                "cwd": {
                    "type": "string",
                    "description": "Directory to search in (optional, defaults to project root)",
                },
            },
            "required": ["pattern"],
        }

    @property
    def is_read_only(self) -> bool:
        return True

    async def call(self, **kwargs: Any) -> ToolResult:
        pattern: str = kwargs["pattern"]
        cwd: str | None = kwargs.get("cwd")

        try:
            search_dir = Path(cwd) if cwd else Path.cwd()

            # 使用 pathlib glob，过滤排除目录
            matches: list[str] = []
            for path in sorted(search_dir.glob(pattern)):
                # 排除指定目录
                parts = path.parts
                if any(part in EXCLUDED_DIRS for part in parts):
                    continue
                # 返回相对路径
                try:
                    rel = path.relative_to(search_dir)
                    matches.append(str(rel))
                except ValueError:
                    matches.append(str(path))

                # 限制结果数量
                if len(matches) >= 200:
                    break

            if not matches:
                return ToolResult(content=f"No files matched pattern: {pattern}")

            return ToolResult(
                content=f"Found {len(matches)} file(s):\n" + "\n".join(matches)
            )

        except Exception as e:
            return ToolResult(content=f"Error searching files: {e}", is_error=True)
