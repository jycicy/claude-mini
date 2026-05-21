"""
CLI 入口 — REPL 交互循环

支持通过环境变量配置任意 Provider 和模型：
  PROVIDER=openai MODEL=deepseek-v4-pro BASE_URL=https://api.deepseek.com/v1 API_KEY=sk-... mini-agent
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any

from mini_agent.engine.engine import QueryEngine
from mini_agent.types import EngineConfig, SimpleCallbacks, ToolResult


# ============================================================
# 颜色辅助
# ============================================================

class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    RED = "\033[31m"
    CYAN = "\033[36m"
    MAGENTA = "\033[35m"


def colorize(color: str, text: str) -> str:
    return f"{color}{text}{Colors.RESET}"


# ============================================================
# 配置加载（支持多 Provider）
# ============================================================

# Provider 默认模型映射
DEFAULT_MODELS: dict[str, str] = {
    "anthropic": "claude-sonnet-4-20250514",
    "openai": "gpt-4o",
}


def load_config() -> EngineConfig:
    """
    从环境变量加载配置

    环境变量优先级：
    - API_KEY 或 ANTHROPIC_API_KEY 或 OPENAI_API_KEY
    - PROVIDER: anthropic (默认) / openai
    - MODEL: 模型名
    - BASE_URL: 自定义 API 地址
    - MAX_TURNS: 最大循环次数
    - MAX_TOKENS: 最大输出 token

    快捷用法（预设 Provider）：
    - PROVIDER=deepseek → 自动设 base_url 和默认 model
    - PROVIDER=mimo → 自动设 base_url 和默认 model
    - PROVIDER=qwen → 自动设 base_url 和默认 model
    - PROVIDER=ollama → 自动设 base_url 和默认 model
    """
    # 检测 provider
    provider_raw = os.environ.get("PROVIDER", "anthropic").lower()

    # 预设 Provider 快捷方式
    from mini_agent.api.openai_provider import PROVIDER_PRESETS

    if provider_raw in PROVIDER_PRESETS:
        preset = PROVIDER_PRESETS[provider_raw]
        provider = "openai"  # 预设都走 openai 兼容格式
        default_base_url = preset["base_url"]
        default_model = preset["default_model"]
    elif provider_raw in ("anthropic", "openai"):
        provider = provider_raw
        default_base_url = None
        default_model = DEFAULT_MODELS.get(provider, "gpt-4o")
    else:
        # 未知 provider，尝试当作 openai 兼容
        provider = "openai"
        default_base_url = None
        default_model = "gpt-4o"

    # API Key（支持多种环境变量名）
    api_key = (
        os.environ.get("API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or os.environ.get("DEEPSEEK_API_KEY")
    )

    if not api_key:
        print(colorize(Colors.RED, "错误: 请设置 API_KEY 环境变量"))
        print("")
        print("  支持的环境变量名：API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY, DEEPSEEK_API_KEY")
        print("")
        print("  示例：")
        print("    # Claude")
        print("    export API_KEY=sk-ant-... && mini-agent")
        print("")
        print("    # DeepSeek")
        print("    export PROVIDER=deepseek API_KEY=sk-... && mini-agent")
        print("")
        print("    # GPT")
        print("    export PROVIDER=openai API_KEY=sk-... MODEL=gpt-4o && mini-agent")
        sys.exit(1)

    model = os.environ.get("MODEL", default_model)
    base_url = os.environ.get("BASE_URL", default_base_url)

    return EngineConfig(
        provider=provider,
        api_key=api_key,
        model=model,
        base_url=base_url if base_url else None,
        max_turns=int(os.environ.get("MAX_TURNS", "25")),
        max_tokens=int(os.environ.get("MAX_TOKENS", "4096")),
        project_root=os.getcwd(),
        auto_compact=True,
        compact_threshold=80000,
    )


# ============================================================
# 权限询问
# ============================================================

async def ask_permission(tool_name: str, tool_input: dict[str, Any]) -> bool:
    """交互式权限确认"""
    input_str = json.dumps(tool_input, ensure_ascii=False)[:200]
    print(colorize(Colors.MAGENTA, f"\n  🔒 权限确认: {tool_name}"))
    print(colorize(Colors.DIM, f"     {input_str}"))
    try:
        answer = input(colorize(Colors.MAGENTA, "     允许? (y/n): "))
        return answer.strip().lower().startswith("y")
    except (EOFError, KeyboardInterrupt):
        return False


# ============================================================
# REPL 主循环
# ============================================================

async def run_chat(engine: QueryEngine, user_input: str) -> None:
    """执行一次对话"""
    is_first_text = True

    def on_text_delta(text: str) -> None:
        nonlocal is_first_text
        if is_first_text:
            sys.stdout.write("\n")
            is_first_text = False
        sys.stdout.write(text)
        sys.stdout.flush()

    def on_tool_start(name: str, tool_input: dict[str, Any]) -> None:
        input_str = json.dumps(tool_input, ensure_ascii=False)[:100]
        print(colorize(Colors.YELLOW, f"\n  ⚙ {name}") + colorize(Colors.DIM, f" {input_str}"))

    def on_tool_end(name: str, result: ToolResult) -> None:
        status = colorize(Colors.RED, "✗") if result.is_error else colorize(Colors.GREEN, "✓")
        preview = result.content[:80].replace("\n", " ")
        print(colorize(Colors.DIM, f"  {status} {preview}..."))

    callbacks = SimpleCallbacks(
        on_text_delta=on_text_delta,
        on_tool_start=on_tool_start,
        on_tool_end=on_tool_end,
        on_permission_ask=ask_permission,
    )

    result = await engine.chat(user_input, callbacks=callbacks)

    # 展示统计
    print("\n")
    tokens = result.total_tokens
    print(colorize(
        Colors.DIM,
        f"  [tokens: in={tokens.input_tokens} out={tokens.output_tokens} | turns: {result.turns_used}]",
    ))


async def async_main() -> None:
    """异步主函数"""
    config = load_config()
    engine = QueryEngine(config)

    # 打印欢迎信息
    print("")
    print(colorize(Colors.BOLD, "  Mini Agent Framework v0.2.0 (Python)"))
    print(colorize(Colors.DIM, "  基于 Claude Code 架构的精简版 Agent — 多模型支持"))
    print(colorize(Colors.DIM, f"  Provider: {engine.provider_info}"))
    if config.base_url:
        print(colorize(Colors.DIM, f"  Endpoint: {config.base_url}"))
    print(colorize(Colors.DIM, f"  项目: {config.project_root}"))
    print("")
    print(colorize(Colors.DIM, "  输入你的需求，Agent 会自动思考并执行。"))
    print(colorize(Colors.DIM, "  输入 /quit 退出，/clear 清空对话，/usage 查看消耗"))
    print("")

    while True:
        try:
            user_input = input(colorize(Colors.GREEN, "> "))
        except (EOFError, KeyboardInterrupt):
            print(colorize(Colors.DIM, "\nBye!"))
            break

        trimmed = user_input.strip()
        if not trimmed:
            continue

        # 斜杠命令
        if trimmed in ("/quit", "/exit"):
            print(colorize(Colors.DIM, "\nBye!"))
            break

        if trimmed == "/clear":
            engine.reset()
            print(colorize(Colors.DIM, "对话已清空。\n"))
            continue

        if trimmed == "/usage":
            usage = engine.usage
            print(colorize(
                Colors.CYAN,
                f"\nToken 消耗: input={usage.total_input}, output={usage.total_output}, turns={usage.turn_count}\n",
            ))
            continue

        if trimmed == "/model":
            print(colorize(Colors.CYAN, f"\n  当前: {engine.provider_info}\n"))
            continue

        # 正常对话
        try:
            await run_chat(engine, trimmed)
        except Exception as e:
            print(colorize(Colors.RED, f"\n错误: {e}\n"))


def main() -> None:
    """入口函数"""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
