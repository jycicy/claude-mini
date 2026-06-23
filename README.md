# Mini Agent Framework

> 基于 Claude Code 架构精简的 AI Agent 开发框架 — 支持 Claude / GPT / DeepSeek / MiMo / Qwen / Gemini / 本地模型

## 特性

- **多模型支持** — 一套代码，接入任意大模型（只要兼容 OpenAI 或 Anthropic 格式）
- **Agentic Loop** — ReAct 模式的核心循环：思考 → 行动 → 观察 → 循环
- **6 个内置工具** — 文件读写编辑 + Shell 命令 + 代码搜索，开箱即用
- **权限控制** — Allow / Ask / Deny 三级权限，防止 AI 执行危险操作
- **动态上下文** — System Prompt 根据环境、项目知识、Git 状态实时组装
- **自动压缩** — 长对话不爆 token，自动总结历史
- **极简依赖** — 仅依赖 `anthropic` + `openai` 两个 SDK
- **Python 3.10+** — 全异步设计，类型完备


---

## 📌 必看：架构图解（传送门）

在阅读代码之前，强烈建议先看这两张图，帮你建立全局认知：

| 文档 | 内容 | 链接 |
|------|------|------|
| 🗂️ **项目结构思维导图** | 所有文件、类、方法一览无余。快速了解"这个框架有什么" | [👉 查看](./docs/mindmap-project-structure.md) |
| 🔄 **请求流程图** | 用户输入一句话后，代码如何在文件和函数之间流动，最终返回结果 | [👉 查看](./docs/mindmap-request-flow.md) |

> **项目结构图** = 让你知道每个文件是干什么的、里面有哪些方法  
> **请求流程图** = 让你知道一次对话从头到尾经过了哪些步骤（含时序图 + 分层流程图 + 数据流图）


---

## 架构概览

```
┌──────────────────────────────────────────────────┐
│              CLI Layer (cli/)                     │
│         REPL 交互 / 流式输出 / 斜杠命令            │
├──────────────────────────────────────────────────┤
│            Engine Layer (engine/)                 │
│       会话管理 / token 追踪 / 自动压缩             │
├──────────────────────────────────────────────────┤
│             Loop Layer (loop/)                    │
│    Agentic Loop: 请求 → 响应 → 工具执行 → 请求    │
├──────────────────────────────────────────────────┤
│            Tool Layer (tools/)                    │
│   file_read / file_write / file_edit / bash       │
│   glob / grep — 可插拔扩展                        │
├──────────────────────────────────────────────────┤
│         Permission Layer (permissions/)           │
│           Allow / Ask / Deny 三级权限             │
├──────────────────────────────────────────────────┤
│           Context Layer (context/)                │
│    System Prompt 动态组装 (环境 + 项目 + Git)      │
├──────────────────────────────────────────────────┤
│             API Layer (api/)                      │
│  ┌───────────────────────────────────────────┐   │
│  │           BaseProvider (统一接口)           │   │
│  ├───────────────────┬───────────────────────┤   │
│  │ AnthropicProvider │   OpenAIProvider      │   │
│  │    (Claude)       │ (GPT/DeepSeek/MiMo/  │   │
│  │                   │  Qwen/GLM/Gemini/    │   │
│  │                   │  Ollama/OpenRouter)   │   │
│  └───────────────────┴───────────────────────┘   │
└──────────────────────────────────────────────────┘
```

---

## 快速开始

### 安装

```bash
git clone https://github.com/jycicy/claude-mini.git
cd claude-mini
pip install -e .
```

### 配置

在项目目录或用户主目录创建 `.mini` 配置文件：

```toml
# .mini — DeepSeek 配置示例（推荐国内用户）
[provider]
type = "deepseek"
api_key = "$DEEPSEEK_API_KEY"    # 引用环境变量，也可直接写 key
model = "deepseek-v4-pro"

[agent]
max_turns = 25
max_tokens = 4096
```

<details>
<summary>更多配置示例（点击展开）</summary>

```toml
# Claude
[provider]
type = "anthropic"
api_key = "$ANTHROPIC_API_KEY"

# GPT-4o
[provider]
type = "openai"
api_key = "$OPENAI_API_KEY"
model = "gpt-4o"

# MiMo（小米）
[provider]
type = "mimo"
api_key = "$MIMO_API_KEY"

# 本地 Ollama（免费）
[provider]
type = "ollama"
api_key = "ollama"
model = "llama3"

# OpenRouter（一个 key 调所有模型）
[provider]
type = "openrouter"
api_key = "$OPENROUTER_API_KEY"
model = "deepseek/deepseek-v4-pro"

# 自定义 OpenAI 兼容接口
[provider]
type = "openai"
api_key = "$MY_API_KEY"
model = "my-model"
base_url = "https://my-api.com/v1"
```

</details>

### 运行

```bash
mini-agent
```

配置文件查找顺序：`./.mini`（项目级）→ `~/.mini`（用户全局）。

---

## 支持的模型

| Provider 名 | 模型示例 | base_url（自动配置） |
|-------------|---------|---------------------|
| `anthropic` | claude-sonnet-4-20250514 | https://api.anthropic.com |
| `openai` | gpt-4o, gpt-4-turbo | https://api.openai.com/v1 |
| `deepseek` | deepseek-v4-pro, deepseek-v4-flash | https://api.deepseek.com/v1 |
| `mimo` | mimo-v2.5-pro, mimo-v2-flash | https://api.mimo.xiaomi.com/v1 |
| `qwen` | qwen-max, qwen-plus | https://dashscope.aliyuncs.com/compatible-mode/v1 |
| `glm` | glm-4 | https://open.bigmodel.cn/api/paas/v4 |
| `openrouter` | 任意模型（400+可选） | https://openrouter.ai/api/v1 |
| `siliconflow` | deepseek-ai/DeepSeek-V3 | https://api.siliconflow.cn/v1 |
| `ollama` | llama3, qwen2, mistral | http://localhost:11434/v1 |

> 任何兼容 OpenAI `/v1/chat/completions` 格式的模型都可以接入！只需在 `.mini` 中设置 `type = "openai"` + `base_url` + `model`。

---

## .mini 配置文件

配置文件使用 TOML 格式，支持以下字段：

```toml
[provider]
type = "deepseek"                          # 必填：provider 类型
api_key = "$DEEPSEEK_API_KEY"              # 必填：API 密钥（支持 $ENV_VAR 引用）
model = "deepseek-v4-pro"                  # 可选：模型名（有默认值）
base_url = "https://api.deepseek.com/v1"   # 可选：自定义 API 地址（预设自动填）

[agent]
max_turns = 25                             # 可选：最大循环次数（默认 25）
max_tokens = 4096                          # 可选：最大输出 token（默认 4096）
project_root = "."                         # 可选：项目根目录（默认当前目录）

[permissions]
allow = ["bash:git *", "file_read"]        # 可选：自动放行的工具/命令
deny = ["bash:rm -rf *"]                   # 可选：自动拒绝的工具/命令
```

**API Key 安全提示**：建议使用 `$ENV_VAR` 引用环境变量，避免将密钥明文写入配置文件。`.mini` 应加入 `.gitignore`。

---

## 作为库使用

```python
import asyncio
from mini_agent import QueryEngine
from mini_agent.types import EngineConfig

async def main():
    # DeepSeek V4 Pro
    engine = QueryEngine(EngineConfig(
        provider="openai",
        api_key="sk-your-key",
        model="deepseek-v4-pro",
        base_url="https://api.deepseek.com/v1",
        project_root="/path/to/project",
    ))

    result = await engine.chat("帮我找到项目中所有未使用的导入并删除")
    print(result.final_text)
    print(f"消耗: {result.total_tokens.input_tokens} in / {result.total_tokens.output_tokens} out")

asyncio.run(main())
```

### 自定义工具

```python
from mini_agent.tools.base import Tool
from mini_agent.types import ToolResult

class MyDatabaseTool(Tool):
    @property
    def name(self) -> str:
        return "query_db"

    @property
    def description(self) -> str:
        return "Execute a SQL query against the project database"

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {"sql": {"type": "string", "description": "SQL query to execute"}},
            "required": ["sql"],
        }

    @property
    def is_read_only(self) -> bool:
        return True

    async def call(self, **kwargs) -> ToolResult:
        sql = kwargs["sql"]
        # ... 执行查询 ...
        return ToolResult(content="查询结果: ...")

# 注册到引擎
engine.register_tool(MyDatabaseTool())
```

---

## 项目结构

```
claude-mini/
├── src/mini_agent/
│   ├── __init__.py               # 库入口
│   ├── types.py                  # 核心类型定义
│   ├── api/
│   │   ├── base.py               # Provider 基类 + 工厂函数
│   │   ├── anthropic_provider.py # Claude 适配器
│   │   └── openai_provider.py    # OpenAI 格式万能适配器
│   ├── tools/
│   │   ├── base.py               # Tool 抽象基类 + Registry
│   │   ├── file_read.py          # 文件读取
│   │   ├── file_write.py         # 文件写入
│   │   ├── file_edit.py          # 精准编辑（字符串替换）
│   │   ├── bash.py               # Shell 命令执行
│   │   ├── glob.py               # 文件模式搜索
│   │   └── grep.py               # 内容正则搜索
│   ├── loop/
│   │   └── loop.py               # Agentic Loop（核心循环）
│   ├── context/
│   │   └── builder.py            # System Prompt 动态组装
│   ├── engine/
│   │   └── engine.py             # 会话引擎 (QueryEngine)
│   ├── permissions/
│   │   └── manager.py            # 权限管理
│   └── cli/
│       └── main.py               # REPL 命令行入口
├── AGENT.md                      # 项目知识（自动注入 Prompt）
├── pyproject.toml
└── README.md
```

---

## 核心概念

### Agentic Loop（核心循环）

```
while 未完成 and 未超限:
    1. 发送消息给 LLM（带工具定义）
    2. LLM 回复（可能包含工具调用请求）
    3. 如果有工具调用 → 权限检查 → 执行 → 结果回传
    4. 如果无工具调用 → 任务完成，退出
```

### Tool（工具）

AI 不能直接操作文件系统，工具是 AI 的"双手"。每个工具有统一接口：
- `name` — 唯一标识
- `description` — AI 根据这个决定用哪个工具
- `input_schema` — 参数定义
- `call()` — 实际执行逻辑

### Permission（权限）

每次工具调用都经过裁决：
- **Allow** — 自动放行（只读工具、安全命令）
- **Ask** — 询问用户确认（写操作、未知命令）
- **Deny** — 直接拒绝（危险命令如 `rm -rf /`）

### Context（上下文）

System Prompt 不是静态文本，而是动态组装：
```
基础人设 + 环境信息 + 项目知识(AGENT.md) + Git状态 + 工具指南
```

---

## 与 Claude Code 的对照

| Claude Code (原版 5000+ 模块) | Mini Agent (本框架) | 说明 |
|------------------------------|--------------------|----- |
| `src/services/api/` (3400行) | `api/base.py` + providers | 多 Provider API 通信 |
| `src/Tool.ts` + `src/tools.ts` | `tools/base.py` + 6 个工具 | 工具系统 |
| `src/query.ts` (1700行) | `loop/loop.py` (~200行) | Agentic Loop |
| `src/context.ts` | `context/builder.py` | 上下文组装 |
| `src/QueryEngine.ts` (1300行) | `engine/engine.py` (~180行) | 会话引擎 |
| `src/utils/permissions/` (6300行) | `permissions/manager.py` (~120行) | 权限控制 |
| `src/entrypoints/cli.tsx` (React/Ink) | `cli/main.py` (asyncio readline) | CLI 入口 |

---

## 学习路线

| 顺序 | 文件 | 学什么 |
|:----:|------|--------|
| 1 | `types.py` | 理解核心类型：Message、Tool、Permission |
| 2 | `loop/loop.py` | **Agentic Loop** — Agent 的灵魂 |
| 3 | `tools/base.py` + `bash.py` | Tool 统一接口设计 |
| 4 | `api/base.py` + `openai_provider.py` | 多 Provider 适配模式 |
| 5 | `context/builder.py` | System Prompt 动态组装 |
| 6 | `permissions/manager.py` | 权限系统 Allow/Ask/Deny |
| 7 | `engine/engine.py` | 引擎如何编排一切 |
| 8 | `cli/main.py` | 入口如何连接到引擎 |

---

## 后续扩展方向

- [ ] **子代理系统** — Agent 派生子 Agent 处理子任务
- [ ] **MCP 协议** — 动态连接外部工具服务器
- [ ] **会话持久化** — 保存/恢复对话
- [ ] **Web API** — FastAPI 包装 HTTP 接口
- [ ] **Hook 系统** — 工具执行前后插入自定义逻辑
- [ ] **YOLO 分类器** — 智能识别安全命令自动放行
- [ ] **并行工具执行** — 边接收流式响应边执行工具
- [ ] **记忆系统** — 跨会话记忆
- [ ] **流式 UI** — Rich / Textual 终端界面

---

## License

MIT — 仅供学习研究。Claude Code 架构设计归 [Anthropic](https://www.anthropic.com/) 所有。
