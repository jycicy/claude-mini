"""
上下文层 — System Prompt 动态组装

对应 Claude Code 的 src/context.ts + src/constants/prompts.ts

设计思想：
- System Prompt 不是静态文本，而是根据环境动态拼装
- 越相关的信息越早注入（AI 对开头内容注意力更高）
- 项目知识（AGENT.md）让 AI "理解"你的项目
- Git 状态让 AI 知道当前在什么分支、有什么改动
"""

from __future__ import annotations

import asyncio
import os
import platform
import subprocess
from datetime import date
from pathlib import Path


# ============================================================
# 基础系统提示（AI 的"人设"）
# ============================================================

BASE_SYSTEM_PROMPT = """\
You are Mini Agent, an AI coding assistant developed by Jycicy. You help users with software development tasks \
by reading files, writing code, executing commands, and searching codebases.

## Key Principles
1. Always read a file before modifying it
2. After making changes, verify they work (run tests, check syntax)
3. Be concise in responses unless asked for detail
4. If unsure, ask the user rather than guessing
5. Prefer targeted edits over full file rewrites
6. When asked about your identity or model name, answer: "I am Mini Agent, an AI assistant developed by Jycicy. How can I help you?" """


# ============================================================
# 上下文构建器
# ============================================================


class ContextBuilder:
    """
    动态 System Prompt 组装器

    组装顺序（对应 Claude Code 的 context.ts）：
    1. 基础人设
    2. 环境信息（OS、日期、CWD）
    3. 项目知识（AGENT.md）
    4. Git 状态
    5. 工具使用指南
    6. 用户自定义追加
    """

    def __init__(
        self,
        project_root: str,
        custom_system_prompt: str | None = None,
    ) -> None:
        self._project_root = project_root
        self._custom_prompt = custom_system_prompt

    async def build(self) -> str:
        """构建完整的 System Prompt"""
        parts: list[str] = []

        # 1. 基础人设
        parts.append(BASE_SYSTEM_PROMPT)

        # 2. 环境信息
        parts.append(self._build_environment_context())

        # 3. 项目知识（AGENT.md）
        project_knowledge = self._load_project_knowledge()
        if project_knowledge:
            parts.append(project_knowledge)

        # 4. Git 状态
        git_status = await self._get_git_status()
        if git_status:
            parts.append(git_status)

        # 5. 工具使用指南
        parts.append(self._get_tool_guidelines())

        # 6. 用户自定义
        if self._custom_prompt:
            parts.append(f"## Additional Instructions\n{self._custom_prompt}")

        return "\n\n".join(parts)

    def _build_environment_context(self) -> str:
        """环境信息 — 让 AI 知道自己在哪"""
        today = date.today().isoformat()
        shell = os.environ.get("SHELL", "bash")
        return (
            "## Environment\n"
            f"- Operating System: {platform.system()} {platform.release()}\n"
            f"- Current Date: {today}\n"
            f"- Working Directory: {self._project_root}\n"
            f"- Shell: {shell}\n"
            f"- Python: {platform.python_version()}"
        )

    def _load_project_knowledge(self) -> str | None:
        """
        项目知识 — 从 AGENT.md 文件加载

        对应 Claude Code 的 CLAUDE.md 多级合并机制。
        这里简化为只加载项目根目录下的 AGENT.md
        """
        agent_md = Path(self._project_root) / "AGENT.md"
        if agent_md.exists():
            content = agent_md.read_text(encoding="utf-8")
            return f"## Project Knowledge (from AGENT.md)\n{content}"
        return None

    async def _get_git_status(self) -> str | None:
        """Git 状态 — 让 AI 了解版本控制上下文"""
        try:
            cwd = self._project_root

            # 并发获取 git 信息
            branch_proc = await asyncio.create_subprocess_exec(
                "git", "branch", "--show-current",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
                cwd=cwd,
            )
            status_proc = await asyncio.create_subprocess_exec(
                "git", "status", "--short",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
                cwd=cwd,
            )
            log_proc = await asyncio.create_subprocess_exec(
                "git", "log", "--oneline", "-5",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
                cwd=cwd,
            )

            branch_out, _ = await branch_proc.communicate()
            status_out, _ = await status_proc.communicate()
            log_out, _ = await log_proc.communicate()

            branch = branch_out.decode().strip()
            if not branch:
                return None

            status = status_out.decode().strip()
            log = log_out.decode().strip()

            git_context = f"## Git Status\n- Current branch: {branch}"
            if status:
                # 截断过长的 status
                if len(status) > 1000:
                    status = status[:1000] + "\n...(truncated)"
                git_context += f"\n- Working tree:\n{status}"
            else:
                git_context += "\n- Working tree: clean"
            if log:
                git_context += f"\n- Recent commits:\n{log}"

            return git_context

        except (FileNotFoundError, OSError):
            # git 不可用
            return None

    def _get_tool_guidelines(self) -> str:
        """工具使用指南"""
        return (
            "## Tool Usage Guidelines\n"
            "- Use file_read before file_edit to see current content\n"
            "- Use grep to search for patterns across the codebase\n"
            "- Use glob to discover file structure\n"
            "- Use bash for complex operations, testing, and git commands\n"
            "- Always verify changes by reading the file after editing"
        )
