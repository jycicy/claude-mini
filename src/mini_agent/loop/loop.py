"""
核心循环层 — Agentic Loop

对应 Claude Code 的 src/query.ts (1700+ 行)

这是整个 Agent 的"心跳"！

设计思想 (ReAct 模式)：
1. 思考 (Reason) — AI 分析上下文，决定下一步
2. 行动 (Act)    — AI 调用工具
3. 观察 (Observe) — 获取工具执行结果
4. 循环或结束     — 根据观察决定是否继续

为什么不是"一次规划批量执行"？
- 每步有真实反馈（文件内容只有读了才知道）
- 动态调整（发现意外情况可以立刻改策略）
- 错误恢复（某步失败了可以当场修复）
- 用户可控（可随时中断）
"""

from __future__ import annotations

from typing import Any

from mini_agent.api.base import BaseProvider
from mini_agent.permissions.manager import PermissionManager
from mini_agent.tools.base import ToolRegistry
from mini_agent.types import (
    ContentBlock,
    LoopResult,
    Message,
    Role,
    SimpleCallbacks,
    TextContent,
    TokenUsage,
    ToolResultContent,
    ToolUseContent,
)


class AgenticLoop:
    """
    Agentic Loop 核心实现

    这是框架最重要的类！整个 Agent 的行为都由这个循环驱动。
    """

    def __init__(
        self,
        api_client: BaseProvider,
        tool_registry: ToolRegistry,
        permission_manager: PermissionManager,
    ) -> None:
        self._api_client = api_client
        self._tool_registry = tool_registry
        self._permission_manager = permission_manager

    async def run(
        self,
        system_prompt: str,
        messages: list[Message],
        *,
        max_turns: int = 25,
        callbacks: SimpleCallbacks | None = None,
    ) -> LoopResult:
        """
        运行 Agentic Loop

        这是框架的核心方法！整个 Agent 的行为都由这个循环驱动。

        Args:
            system_prompt: 动态组装好的系统提示
            messages: 当前对话历史（会被原地修改）
            max_turns: 最大循环次数（防止无限循环）
            callbacks: 事件回调（用于 UI 展示）

        Returns:
            LoopResult: 循环执行结果
        """
        turns_used = 0
        total_input = 0
        total_output = 0
        reached_max_turns = False

        # ==================== 核心循环开始 ====================
        while turns_used < max_turns:
            turns_used += 1

            # ---- Step 1: 发送请求给 LLM ----
            response = await self._api_client.send_message(
                system_prompt=system_prompt,
                messages=messages,
                tools=self._tool_registry.to_definitions(),
                on_text_delta=callbacks.on_text_delta if callbacks else None,
            )

            # 累计 token
            total_input += response.usage.input_tokens
            total_output += response.usage.output_tokens

            # ---- Step 2: 解析响应 ----
            # 将 AI 的回复添加到消息历史
            assistant_message = Message(
                role=Role.ASSISTANT,
                content=response.content,
            )
            messages.append(assistant_message)

            # ---- Step 3: 检查是否需要调用工具 ----
            if response.stop_reason != "tool_use":
                # AI 没有调用工具 = 任务完成，退出循环
                break

            # ---- Step 4: 提取并执行工具调用 ----
            tool_use_blocks = [
                b for b in response.content if isinstance(b, ToolUseContent)
            ]

            # 逐个执行工具
            tool_results: list[ToolResultContent] = []
            for tool_use in tool_use_blocks:
                result = await self._execute_tool(tool_use, callbacks)
                tool_results.append(result)

            # ---- Step 5: 将工具结果加入消息历史 ----
            user_message = Message(role=Role.USER, content=tool_results)
            messages.append(user_message)

            # 循环回到 Step 1，让 AI 看到工具结果并继续思考
        # ==================== 核心循环结束 ====================

        if turns_used >= max_turns:
            reached_max_turns = True

        # 提取最终文本回复
        final_text = self._extract_final_text(messages)
        if callbacks and callbacks.on_complete:
            callbacks.on_complete(final_text)

        return LoopResult(
            final_text=final_text,
            turns_used=turns_used,
            total_tokens=TokenUsage(input_tokens=total_input, output_tokens=total_output),
            reached_max_turns=reached_max_turns,
        )

    async def _execute_tool(
        self,
        tool_use: ToolUseContent,
        callbacks: SimpleCallbacks | None,
    ) -> ToolResultContent:
        """
        执行单个工具调用

        包含权限检查流程：
        1. 找到工具
        2. 权限裁决
        3. 执行（或拒绝）
        """
        tool = self._tool_registry.get(tool_use.name)

        # 工具不存在
        if tool is None:
            return ToolResultContent(
                tool_use_id=tool_use.id,
                content=f'Error: Unknown tool "{tool_use.name}"',
                is_error=True,
            )

        # 权限检查
        decision = self._permission_manager.check(tool, tool_use.input)

        if decision.value == "deny":
            return ToolResultContent(
                tool_use_id=tool_use.id,
                content=f'Permission denied: Tool "{tool_use.name}" is not allowed with these parameters.',
                is_error=True,
            )

        if decision.value == "ask":
            # 询问用户
            allowed = False
            if callbacks and callbacks.on_permission_ask:
                allowed = await callbacks.on_permission_ask(tool_use.name, tool_use.input)
            if not allowed:
                return ToolResultContent(
                    tool_use_id=tool_use.id,
                    content="Permission denied by user.",
                    is_error=True,
                )

        # 执行工具
        if callbacks and callbacks.on_tool_start:
            callbacks.on_tool_start(tool_use.name, tool_use.input)

        try:
            result = await tool.call(**tool_use.input)
            if callbacks and callbacks.on_tool_end:
                callbacks.on_tool_end(tool_use.name, result)

            return ToolResultContent(
                tool_use_id=tool_use.id,
                content=result.content,
                is_error=result.is_error,
            )
        except Exception as e:
            from mini_agent.types import ToolResult as TR

            error_result = TR(content=f"Tool execution error: {e}", is_error=True)
            if callbacks and callbacks.on_tool_end:
                callbacks.on_tool_end(tool_use.name, error_result)

            return ToolResultContent(
                tool_use_id=tool_use.id,
                content=error_result.content,
                is_error=True,
            )

    def _extract_final_text(self, messages: list[Message]) -> str:
        """从消息历史中提取最终文本回复"""
        for msg in reversed(messages):
            if msg.role == Role.ASSISTANT:
                if isinstance(msg.content, str):
                    return msg.content
                text_parts = [
                    b.text for b in msg.content if isinstance(b, TextContent)
                ]
                return "\n".join(text_parts)
        return ""
