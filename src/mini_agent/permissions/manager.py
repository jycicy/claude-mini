"""
权限层 — 简化版权限控制

对应 Claude Code 的 src/utils/permissions/ (6300+ 行！)

设计思想：
- AI 操作真实环境是强大但危险的
- 每个工具调用都经过权限裁决
- 三种决策：Allow（自动放行）、Ask（询问用户）、Deny（拒绝）
- 只读工具默认 Allow
- 写操作默认 Ask
- 危险命令可以 Deny

简化版本只实现基础规则匹配，不含 Claude Code 的：
- YOLO 分类器
- 路径边界验证
- 规则持久化
- Denial Tracking

这些你以后可以逐步加上。
"""

from __future__ import annotations

import re
from typing import Any

from mini_agent.tools.base import Tool
from mini_agent.types import PermissionDecision, PermissionRule


# 默认危险命令模式（一律拒绝）
DANGEROUS_PATTERNS = [
    "rm -rf /",
    "rm -rf ~",
    "sudo rm",
    ":(){:|:&};:",  # fork bomb
    "mkfs",
    "dd if=",
    "> /dev/sd",
]

# 默认安全命令模式（自动放行）
SAFE_PATTERNS = [
    "git status",
    "git log",
    "git branch",
    "git diff",
    "ls",
    "cat",
    "head",
    "tail",
    "wc",
    "echo",
    "pwd",
    "which",
    "python --version",
    "pip --version",
    "pip list",
]


class PermissionManager:
    """
    权限管理器

    裁决逻辑（优先级从高到低）：
    1. 检查用户自定义规则
    2. 只读工具 → Allow
    3. 危险命令 → Deny
    4. 安全命令 → Allow
    5. 其他 → Ask（询问用户）
    """

    def __init__(self, rules: list[PermissionRule] | None = None) -> None:
        self._rules: list[PermissionRule] = rules or []

    def check(self, tool: Tool, tool_input: dict[str, Any]) -> PermissionDecision:
        """
        裁决一个工具调用是否被允许

        Args:
            tool: 要调用的工具
            tool_input: 工具参数

        Returns:
            PermissionDecision: allow / ask / deny
        """
        # 1. 用户自定义规则
        custom = self._match_custom_rules(tool, tool_input)
        if custom is not None:
            return custom

        # 2. 只读工具直接放行
        if tool.is_read_only:
            return PermissionDecision.ALLOW

        # 3. Bash 工具需要额外检查命令内容
        if tool.name == "bash":
            command = tool_input.get("command", "")
            return self._check_bash_command(command)

        # 4. 其他写操作 → Ask
        return PermissionDecision.ASK

    def _check_bash_command(self, command: str) -> PermissionDecision:
        """检查 bash 命令是否安全"""
        normalized = command.strip().lower()

        # 危险命令 → Deny
        for pattern in DANGEROUS_PATTERNS:
            if pattern.lower() in normalized:
                return PermissionDecision.DENY

        # 安全命令 → Allow
        for pattern in SAFE_PATTERNS:
            if normalized.startswith(pattern.lower()):
                return PermissionDecision.ALLOW

        # 其他 → Ask
        return PermissionDecision.ASK

    def _match_custom_rules(
        self, tool: Tool, tool_input: dict[str, Any]
    ) -> PermissionDecision | None:
        """匹配用户自定义规则"""
        for rule in self._rules:
            # 匹配工具名
            if rule.tool != "*" and rule.tool != tool.name:
                continue

            # 如果规则有 pattern，匹配命令内容
            if rule.pattern:
                command = tool_input.get("command", "")
                if not self._match_pattern(command, rule.pattern):
                    continue

            return rule.decision

        return None

    def _match_pattern(self, text: str, pattern: str) -> bool:
        """简单的模式匹配（支持 * 通配符）"""
        regex_pattern = "^" + re.escape(pattern).replace(r"\*", ".*") + "$"
        return bool(re.match(regex_pattern, text, re.IGNORECASE))

    def add_rule(self, rule: PermissionRule) -> None:
        """动态添加规则（用户在会话中授权时调用）"""
        self._rules.insert(0, rule)  # 新规则优先级最高
