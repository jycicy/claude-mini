"""
CLI 入口 — REPL 交互循环

对应 Claude Code 的 src/entrypoints/cli.tsx + src/main.tsx

设计思想：
- 最简单的入口：读取用户输入 → 调用 Engine → 展示结果
- 支持流式输出（逐字打印 AI 回复）
- 工具调用时展示进度
- 权限询问时等待用户确认
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
# 配置加载
# ============================================================

def load_config() -> EngineConfig:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(colorize(Colors.RED, "错误: 请设置 ANTHROPIC_API_KEY 环境变量"))
        print("  export ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)

    return EngineConfig(
        api_key=api_key,
        model=os.environ.get("MODEL", "claude-sonnet-4-20250514"),
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
    print(f"\n")
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
    print(colorize(Colors.BOLD, "  Mini Agent Framework v0.1.0 (Python)"))
    print(colorize(Colors.DIM, "  基于 Claude Code 架构的精简版 Agent"))
    print(colorize(Colors.DIM, f"  模型: {config.model}"))
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
