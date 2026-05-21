# Mini Agent Framework (Python)

> 基于 Claude Code 架构精简的 AI Agent 开发框架 — Python 版

## 架构概览

```
┌─────────────────────────────────────────┐
│         CLI Layer (cli/)                │
│      REPL 交互 / 流式输出 / 命令解析      │
├─────────────────────────────────────────┤
│       Engine Layer (engine/)             │
│    会话管理 / token 追踪 / 自动压缩       │
├─────────────────────────────────────────┤
│        Loop Layer (loop/)                │
│   Agentic Loop: 请求→响应→工具→请求      │
├─────────────────────────────────────────┤
│       Tool Layer (tools/)                │
│  file_read/write/edit + bash + grep/glob │
├─────────────────────────────────────────┤
│    Permission Layer (permissions/)        │
│      Allow / Ask / Deny 三级权限         │
├─────────────────────────────────────────┤
│     Context Layer (context/)             │
│   System Prompt 动态组装 (环境+项目+Git)   │
├─────────────────────────────────────────┤
│         API Layer (api/)                 │
│       Anthropic SDK 流式通信             │
└─────────────────────────────────────────┘
```

## 快速开始

```bash
# 1. 安装
pip install -e .

# 2. 设置 API Key
export ANTHROPIC_API_KEY=sk-ant-api03-...

# 3. 运行
mini-agent
```

## 配置环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ANTHROPIC_API_KEY` | (必填) | Anthropic API Key |
| `MODEL` | `claude-sonnet-4-20250514` | 使用的模型 |
| `MAX_TURNS` | `25` | 最大循环次数 |
| `MAX_TOKENS` | `4096` | 单次请求最大输出 token |

## 作为库使用

```python
import asyncio
from mini_agent import QueryEngine
from mini_agent.types import EngineConfig

async def main():
    engine = QueryEngine(EngineConfig(
        api_key="sk-ant-...",
        model="claude-sonnet-4-20250514",
        project_root="/path/to/project",
    ))

    result = await engine.chat("帮我列出所有 Python 文件")
    print(result.final_text)

asyncio.run(main())
```

## 目录说明

```
claude-mini/
├── src/mini_agent/
│   ├── __init__.py           # 库入口（export 所有公开接口）
│   ├── types.py              # 核心类型定义（所有模块共享）
│   ├── api/
│   │   └── client.py         # LLM 通信（封装 Anthropic SDK）
│   ├── tools/
│   │   ├── __init__.py       # 工具注册入口
│   │   ├── base.py           # Tool 抽象基类 + ToolRegistry
│   │   ├── file_read.py      # 文件读取
│   │   ├── file_write.py     # 文件写入
│   │   ├── file_edit.py      # 文件编辑（精准替换）
│   │   ├── bash.py           # Shell 命令执行
│   │   ├── glob.py           # 文件搜索
│   │   └── grep.py           # 内容搜索
│   ├── loop/
│   │   └── loop.py           # Agentic Loop（核心循环）
│   ├── context/
│   │   └── builder.py        # System Prompt 动态组装
│   ├── engine/
│   │   └── engine.py         # 会话引擎（QueryEngine）
│   ├── permissions/
│   │   └── manager.py        # 权限管理
│   └── cli/
│       └── main.py           # REPL 命令行界面
├── AGENT.md                  # 项目知识文件（会注入 System Prompt）
├── pyproject.toml            # 项目配置
└── README.md
```



## 核心概念对照表

| Claude Code (原版) | Mini Agent (本框架) | 说明 |
|-------------------|--------------------|----- |
| `src/services/api/claude.ts` | `api/client.py` | API 通信 |
| `src/Tool.ts` + `src/tools.ts` | `tools/base.py` + `__init__.py` | 工具系统 |
| `src/query.ts` (1700行) | `loop/loop.py` | Agentic Loop |
| `src/context.ts` | `context/builder.py` | 上下文组装 |
| `src/QueryEngine.ts` (1300行) | `engine/engine.py` | 会话引擎 |
| `src/utils/permissions/` (6300行) | `permissions/manager.py` | 权限控制 |
| `src/entrypoints/cli.tsx` (React/Ink) | `cli/main.py` (asyncio) | CLI 入口 |

## 学习顺序建议

| 顺序 | 文件 | 学什么 |
|------|------|--------|
| 1 | `types.py` | 理解所有核心类型（Message、Tool、Permission） |
| 2 | `loop/loop.py` | **Agentic Loop** — Agent 的灵魂 (while 循环) |
| 3 | `tools/base.py` + 任意一个工具 | Tool 统一接口怎么设计 |
| 4 | `context/builder.py` | System Prompt 怎么动态组装 |
| 5 | `permissions/manager.py` | 权限系统 Allow/Ask/Deny |
| 6 | `engine/engine.py` | 引擎如何编排一切 |
| 7 | `cli/main.py` | 入口如何连接到引擎 |

## 后续扩展方向

学会这个框架后，你可以逐步添加：

1. **自定义工具** — 比如数据库查询工具、HTTP 请求工具
2. **子代理系统** — 让 Agent 派生子 Agent 处理子任务
3. **MCP 协议支持** — 动态连接外部工具服务器
4. **会话持久化** — 保存/恢复对话
5. **Web API** — 用 FastAPI 包一层 HTTP 接口
6. **多 Provider** — 支持 OpenAI / Bedrock / Vertex
7. **Hook 系统** — 工具执行前后插入自定义逻辑
8. **YOLO 分类器** — 自动识别安全命令并放行
9. **流式工具执行** — 边接收响应边执行工具（并行）
10. **记忆系统** — 让 Agent 记住跨会话的信息

## License

MIT — 仅供学习研究。Claude Code 架构设计归 Anthropic 所有。
