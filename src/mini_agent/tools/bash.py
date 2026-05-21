"""
Bash 工具 — 执行 Shell 命令

对应 Claude Code 的 src/tools/BashTool/BashTool.ts

这是最强大也最危险的工具。AI 可以执行任意命令，
因此权限系统对它的管控最严格。

设计思想：
- 给 AI 完整的 shell 能力（安装依赖、运行测试、git 操作等）
- 超时机制防止命令卡死
- 输出长度限制防止 token 爆炸
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from mini_agent.tools.base import Tool
from mini_agent.types import ToolResult

# 输出最大长度（字符数），防止 token 爆炸
MAX_OUTPUT_LENGTH = 30000
# 默认超时（秒）
DEFAULT_TIMEOUT = 120


class BashTool(Tool):
    @property
    def name(self) -> str:
        return "bash"

    @property
    def description(self) -> str:
        return (
            "Execute a bash command in the shell. "
            "Use this for running programs, installing packages, git operations, searching files, etc. "
            "Commands run in the project root directory by default. "
            "Long-running commands (like dev servers) should NOT be run with this tool. "
            "Output is truncated if it exceeds 30000 characters."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The bash command to execute",
                },
                "cwd": {
                    "type": "string",
                    "description": "Working directory (optional, defaults to project root)",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (optional, default: 120)",
                },
            },
            "required": ["command"],
        }

    @property
    def is_read_only(self) -> bool:
        return False

    async def call(self, **kwargs: Any) -> ToolResult:
        command: str = kwargs["command"]
        cwd: str = kwargs.get("cwd", os.getcwd())
        timeout: int = kwargs.get("timeout", DEFAULT_TIMEOUT)

        try:
            env = {**os.environ, "TERM": "dumb"}

            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return ToolResult(
                    content=f"Error: Command timed out after {timeout} seconds",
                    is_error=True,
                )

            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")

            # 合并 stdout 和 stderr
            output = ""
            if stdout:
                output += stdout
            if stderr:
                output += ("\n" if output else "") + f"[stderr]\n{stderr}"

            # 截断过长输出
            if len(output) > MAX_OUTPUT_LENGTH:
                output = (
                    output[:MAX_OUTPUT_LENGTH]
                    + "\n\n[Output truncated — exceeded 30000 characters]"
                )

            # 检查退出码
            if process.returncode != 0:
                return ToolResult(
                    content=f"Command failed (exit code {process.returncode}):\n{output}" if output else f"Command failed with exit code {process.returncode}",
                    is_error=True,
                )

            return ToolResult(content=output or "(no output)")

        except Exception as e:
            return ToolResult(content=f"Error executing command: {e}", is_error=True)
