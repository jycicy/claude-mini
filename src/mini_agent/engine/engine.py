"""
编排层 — 会话引擎 (QueryEngine)

对应 Claude Code 的 src/QueryEngine.ts (1300+ 行)

设计思想：
- 这是"会话导演"，管理整个对话的生命周期
- 它不关心 API 调用细节（交给 APIClient）
- 它不关心工具执行细节（交给 Loop）
- 它关心的是：上下文构建、状态管理、token 追踪、自动压缩

职责：
1. 初始化各组件（API 客户端、工具注册表、权限管理器、上下文构建器）
2. 管理对话历史
3. 追踪 token 消耗
4. 触发自动压缩
5. 暴露给外层（CLI/API）一个简单的 chat() 接口
"""

from __future__ import annotations

from dataclasses import dataclass

from mini_agent.api.client import APIClient, APIClientConfig
from mini_agent.context.builder import ContextBuilder
from mini_agent.loop.loop import AgenticLoop
from mini_agent.permissions.manager import PermissionManager
from mini_agent.tools import create_default_tool_registry
from mini_agent.tools.base import Tool, ToolRegistry
from mini_agent.types import (
    EngineConfig,
    LoopResult,
    Message,
    PermissionRule,
    Role,
    SimpleCallbacks,
    TokenUsage,
)


@dataclass
class UsageStats:
    """Token 使用统计"""

    total_input: int = 0
    total_output: int = 0
    turn_count: int = 0


class QueryEngine:
    """
    会话引擎 — 整个框架对外暴露的核心接口

    对应 Claude Code 的 QueryEngine.ts

    用法：
        engine = QueryEngine(EngineConfig(api_key="sk-ant-..."))
        result = await engine.chat("帮我列出所有 Python 文件")
        print(result.final_text)
    """

    def __init__(self, config: EngineConfig | None = None, **kwargs) -> None:
        """
        初始化会话引擎

        可以传入 EngineConfig 对象，也可以用关键字参数：
            engine = QueryEngine(api_key="...", model="...", project_root=".")
        """
        if config is None:
            config = EngineConfig(**kwargs)

        self._config = config

        # 1. 初始化 API 客户端
        self._api_client = APIClient(
            APIClientConfig(
                api_key=config.api_key,
                model=config.model,
                max_tokens=config.max_tokens,
            )
        )

        # 2. 初始化上下文构建器
        self._context_builder = ContextBuilder(
            project_root=config.project_root,
            custom_system_prompt=config.custom_system_prompt,
        )

        # 3. 初始化工具注册表（默认 6 个核心工具）
        self._tool_registry = create_default_tool_registry()

        # 4. 初始化权限管理器
        self._permission_manager = PermissionManager(config.permission_rules)

        # 5. 组装 Agentic Loop
        self._loop = AgenticLoop(
            api_client=self._api_client,
            tool_registry=self._tool_registry,
            permission_manager=self._permission_manager,
        )

        # 对话状态
        self._messages: list[Message] = []
        self._usage = UsageStats()

    async def chat(
        self,
        user_input: str,
        callbacks: SimpleCallbacks | None = None,
    ) -> LoopResult:
        """
        发送一条消息并获取 Agent 回复

        这是整个框架对外暴露的核心接口！

        Args:
            user_input: 用户输入的文本
            callbacks: 事件回调（用于实时展示进度）

        Returns:
            LoopResult: Loop 执行结果
        """
        # 1. 将用户消息加入历史
        self._messages.append(Message(role=Role.USER, content=user_input))

        # 2. 动态构建 System Prompt
        system_prompt = await self._context_builder.build()

        # 3. 检查是否需要自动压缩
        if self._config.auto_compact and self._should_compact():
            self._compact()

        # 4. 运行 Agentic Loop
        result = await self._loop.run(
            system_prompt,
            self._messages,
            max_turns=self._config.max_turns,
            callbacks=callbacks,
        )

        # 5. 更新 token 追踪
        self._usage.total_input += result.total_tokens.input_tokens
        self._usage.total_output += result.total_tokens.output_tokens
        self._usage.turn_count += result.turns_used

        return result

    def _should_compact(self) -> bool:
        """
        自动压缩检测

        对应 Claude Code 的 autoCompact.ts
        当对话历史太长时，需要"总结"之前的内容，
        释放 token 空间，让对话可以持续进行。
        """
        estimated = self._estimate_tokens()
        return estimated > self._config.compact_threshold

    def _compact(self) -> None:
        """
        执行压缩

        简化版：将历史消息总结为一条 system 消息
        生产版应该用 LLM 来生成总结
        """
        if len(self._messages) < 4:
            return

        # 保留最近的 4 条消息，其余压缩
        remaining = self._messages[-4:]
        summary = (
            f"[Previous conversation summary: {len(self._messages) - 4} messages "
            f"were compacted. The conversation covered various topics and tool calls.]"
        )

        self._messages = [
            Message(role=Role.USER, content=summary),
            Message(
                role=Role.ASSISTANT,
                content="I understand the previous context. Let me continue helping you.",
            ),
            *remaining,
        ]

    def _estimate_tokens(self) -> int:
        """粗略估算当前 token 数（4 字符 ≈ 1 token）"""
        char_count = 0
        for msg in self._messages:
            if isinstance(msg.content, str):
                char_count += len(msg.content)
            else:
                import json
                char_count += len(json.dumps([vars(b) for b in msg.content], default=str))
        return char_count // 4

    # ============================================================
    # 公开的查询/控制方法
    # ============================================================

    @property
    def messages(self) -> list[Message]:
        """获取对话历史"""
        return list(self._messages)

    @property
    def usage(self) -> UsageStats:
        """获取 token 消耗统计"""
        return self._usage

    def reset(self) -> None:
        """清空对话历史"""
        self._messages.clear()
        self._usage = UsageStats()

    def register_tool(self, tool: Tool) -> None:
        """注册额外的工具（用于扩展）"""
        self._tool_registry.register(tool)

    def add_permission_rule(self, rule: PermissionRule) -> None:
        """添加权限规则"""
        self._permission_manager.add_rule(rule)
