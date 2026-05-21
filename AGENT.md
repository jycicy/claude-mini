# Mini Agent Framework (Python)

这是一个基于 Claude Code 架构的精简版 Agent 框架。

## 技术栈
- Python 3.10+
- Anthropic SDK
- asyncio (异步)

## 项目结构
- `src/mini_agent/api/` — 通信层（LLM API 客户端）
- `src/mini_agent/tools/` — 工具层（AI 的能力）
- `src/mini_agent/loop/` — 核心循环层（Agentic Loop）
- `src/mini_agent/context/` — 上下文层（System Prompt 组装）
- `src/mini_agent/engine/` — 编排层（会话引擎）
- `src/mini_agent/permissions/` — 权限层（安全控制）
- `src/mini_agent/cli/` — 入口层（REPL 交互）

## 开发约定
- 每个模块一个目录，入口文件为对应功能名
- 类型统一定义在 types.py
- 工具描述要写得好——AI 根据描述决定用哪个工具
- 使用 async/await 异步编程

## 如何运行
```bash
export ANTHROPIC_API_KEY=sk-ant-...
pip install -e .
mini-agent
```
