"""
核心类型定义
整个框架的类型基础，所有模块共享

对应 TypeScript 版的 src/types.ts
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Protocol


# ============================================================
# Message 类型 — 对话历史的基本单元
# ============================================================


class Role(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class TextContent:
    """纯文本内容块"""

    type: str = "text"
    text: str = ""


@dataclass
class ToolUseContent:
    """AI 请求调用工具的内容块"""

    type: str = "tool_use"
    id: str = ""
    name: str = ""
    input: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResultContent:
    """工具执行结果的内容块"""

    type: str = "tool_result"
    tool_use_id: str = ""
    content: str = ""
    is_error: bool = False


# 内容块的联合类型
ContentBlock = TextContent | ToolUseContent | ToolResultContent


@dataclass
class Message:
    """对话消息"""

    role: Role
    content: str | list[ContentBlock] = ""


# ============================================================
# Tool 类型 — 工具的统一抽象
# ============================================================


@dataclass
class ToolDefinition:
    """工具定义（发送给 API 的格式）"""

    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass
class ToolResult:
    """工具执行结果"""

    content: str
    is_error: bool = False


# ============================================================
# Permission 类型 — 权限裁决
# ============================================================


class PermissionDecision(str, Enum):
    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"


@dataclass
class PermissionRule:
    """权限规则"""

    tool: str  # 工具名，"*" 表示匹配所有
    decision: PermissionDecision
    pattern: str | None = None  # glob 模式匹配（如 "git *"）


# ============================================================
# Provider 配置类型
# ============================================================


class ProviderType(str, Enum):
    """支持的 Provider 类型"""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"


@dataclass
class EngineConfig:
    """
    会话引擎配置

    支持多种使用方式：

    1. Claude（默认）:
        EngineConfig(api_key="sk-ant-...")

    2. DeepSeek:
        EngineConfig(
            provider="openai",
            api_key="sk-...",
            model="deepseek-v4-pro",
            base_url="https://api.deepseek.com/v1",
        )

    3. MiMo:
        EngineConfig(
            provider="openai",
            api_key="sk-...",
            model="mimo-v2.5-pro",
            base_url="https://api.mimo.xiaomi.com/v1",
        )

    4. GPT:
        EngineConfig(
            provider="openai",
            api_key="sk-...",
            model="gpt-4o",
        )

    5. OpenRouter（一个 key 调所有模型）:
        EngineConfig(
            provider="openai",
            api_key="sk-or-...",
            model="deepseek/deepseek-v4-pro",
            base_url="https://openrouter.ai/api/v1",
        )

    6. 本地 Ollama:
        EngineConfig(
            provider="openai",
            api_key="ollama",
            model="llama3",
            base_url="http://localhost:11434/v1",
        )
    """

    # --- 必填 ---
    api_key: str

    # --- Provider 配置 ---
    provider: str = "anthropic"  # "anthropic" 或 "openai"
    model: str = "claude-sonnet-4-20250514"
    base_url: str | None = None  # 自定义 API 地址

    # --- Agent 行为 ---
    max_turns: int = 25
    max_tokens: int = 4096
    project_root: str = "."
    custom_system_prompt: str | None = None

    # --- 权限 ---
    permission_rules: list[PermissionRule] = field(default_factory=list)

    # --- 自动压缩 ---
    auto_compact: bool = True
    compact_threshold: int = 80000


# ============================================================
# Loop 结果类型
# ============================================================


@dataclass
class TokenUsage:
    """Token 消耗统计"""

    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class LoopResult:
    """Agentic Loop 执行结果"""

    final_text: str = ""
    turns_used: int = 0
    total_tokens: TokenUsage = field(default_factory=TokenUsage)
    reached_max_turns: bool = False


# ============================================================
# 回调类型 — 事件监听
# ============================================================


class AgentCallbacks(Protocol):
    """Agent 事件回调协议（可选实现）"""

    def on_text_delta(self, text: str) -> None:
        """AI 输出文本片段时"""
        ...

    def on_tool_start(self, tool_name: str, tool_input: dict[str, Any]) -> None:
        """工具被调用时"""
        ...

    def on_tool_end(self, tool_name: str, result: ToolResult) -> None:
        """工具执行完成时"""
        ...

    async def on_permission_ask(
        self, tool_name: str, tool_input: dict[str, Any]
    ) -> bool:
        """需要用户确认权限时，返回 True 允许，False 拒绝"""
        ...

    def on_complete(self, final_message: str) -> None:
        """循环结束时"""
        ...

    def on_error(self, error: Exception) -> None:
        """发生错误时"""
        ...


@dataclass
class SimpleCallbacks:
    """简单回调实现（使用可选函数）"""

    on_text_delta: Callable[[str], None] | None = None
    on_tool_start: Callable[[str, dict[str, Any]], None] | None = None
    on_tool_end: Callable[[str, ToolResult], None] | None = None
    on_permission_ask: Callable[[str, dict[str, Any]], Awaitable[bool]] | None = None
    on_complete: Callable[[str], None] | None = None
    on_error: Callable[[Exception], None] | None = None
