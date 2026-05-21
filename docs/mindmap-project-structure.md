# 思维导图 1：项目文件结构 + 方法清单

## 项目总览

```mermaid
graph TD
    ROOT[mini-agent] --> TYPES[types.py]
    ROOT --> API[api/]
    ROOT --> TOOLS[tools/]
    ROOT --> LOOP[loop/]
    ROOT --> CTX[context/]
    ROOT --> ENGINE[engine/]
    ROOT --> PERM[permissions/]
    ROOT --> CLI[cli/]
```

## 各模块详细结构

### types.py — 核心类型

```mermaid
graph LR
    TYPES[types.py] --> MSG[Message 消息]
    TYPES --> TOOL_T[Tool 工具类型]
    TYPES --> PERM_T[Permission 权限]
    TYPES --> CFG[Config 配置]
    TYPES --> RESULT[Result 结果]
    TYPES --> CB[Callbacks 回调]

    MSG --> Role[Role: USER/ASSISTANT/SYSTEM]
    MSG --> TextContent[TextContent: type, text]
    MSG --> ToolUseContent[ToolUseContent: id, name, input]
    MSG --> ToolResultContent[ToolResultContent: tool_use_id, content, is_error]

    TOOL_T --> ToolDefinition[ToolDefinition: name, description, input_schema]
    TOOL_T --> ToolResult[ToolResult: content, is_error]

    PERM_T --> PermissionDecision[PermissionDecision: ALLOW/ASK/DENY]
    PERM_T --> PermissionRule[PermissionRule: tool, decision, pattern]

    CFG --> EngineConfig[EngineConfig: provider, api_key, model, base_url, max_turns, max_tokens, project_root]

    RESULT --> TokenUsage[TokenUsage: input_tokens, output_tokens]
    RESULT --> LoopResult[LoopResult: final_text, turns_used, total_tokens]

    CB --> SimpleCallbacks[SimpleCallbacks: on_text_delta, on_tool_start, on_tool_end, on_permission_ask]
```

### api/ — 通信层

```mermaid
graph TD
    API[api/] --> BASE[base.py]
    API --> ANTH[anthropic_provider.py]
    API --> OAI[openai_provider.py]

    BASE --> APIResponse[APIResponse: content, stop_reason, usage]
    BASE --> BaseProvider[BaseProvider - 抽象基类]
    BASE --> create_provider[create_provider - 工厂函数]

    BaseProvider --> bp_send[send_message]
    BaseProvider --> bp_model[model property]
    BaseProvider --> bp_name[provider_name property]

    ANTH --> AnthropicProvider[AnthropicProvider]
    AnthropicProvider --> ap_init[__init__ - api_key, model, base_url]
    AnthropicProvider --> ap_send[send_message]
    AnthropicProvider --> ap_convert[_convert_messages]

    OAI --> PRESETS[PROVIDER_PRESETS: deepseek, mimo, qwen, glm, openrouter, siliconflow, ollama]
    OAI --> OpenAIProvider[OpenAIProvider]
    OpenAIProvider --> op_init[__init__ - api_key, model, base_url]
    OpenAIProvider --> op_send[send_message]
    OpenAIProvider --> op_convert[_convert_messages]
```

### tools/ — 工具层

```mermaid
graph TD
    TOOLS[tools/] --> TB[base.py]
    TOOLS --> TI[__init__.py]
    TOOLS --> FR[file_read.py]
    TOOLS --> FW[file_write.py]
    TOOLS --> FE[file_edit.py]
    TOOLS --> BA[bash.py]
    TOOLS --> GL[glob.py]
    TOOLS --> GR[grep.py]

    TB --> Tool[Tool 抽象基类]
    Tool --> t_name[name property]
    Tool --> t_desc[description property]
    Tool --> t_schema[input_schema property]
    Tool --> t_readonly[is_read_only property]
    Tool --> t_call[call - 执行工具]
    Tool --> t_def[to_definition]

    TB --> ToolRegistry[ToolRegistry]
    ToolRegistry --> tr_register[register]
    ToolRegistry --> tr_all[register_all]
    ToolRegistry --> tr_get[get]
    ToolRegistry --> tr_getall[get_all]
    ToolRegistry --> tr_defs[to_definitions]
    ToolRegistry --> tr_has[has]

    TI --> create_default[create_default_tool_registry]

    FR --> FileReadTool[FileReadTool - call: file_path, offset, limit]
    FW --> FileWriteTool[FileWriteTool - call: file_path, content]
    FE --> FileEditTool[FileEditTool - call: file_path, old_string, new_string]
    BA --> BashTool[BashTool - call: command, cwd, timeout]
    GL --> GlobTool[GlobTool - call: pattern, cwd]
    GR --> GrepTool[GrepTool - call: pattern, path, include]
```

### loop/ — 核心循环层

```mermaid
graph TD
    LOOP[loop/loop.py] --> AgenticLoop[AgenticLoop]
    AgenticLoop --> al_init[__init__ - api_client, tool_registry, permission_manager]
    AgenticLoop --> al_run[run - system_prompt, messages, max_turns, callbacks]
    AgenticLoop --> al_exec[_execute_tool - tool_use, callbacks]
    AgenticLoop --> al_text[_extract_final_text - messages]
```

### context/ — 上下文层

```mermaid
graph TD
    CTX[context/builder.py] --> CONST[BASE_SYSTEM_PROMPT 常量]
    CTX --> ContextBuilder[ContextBuilder]
    ContextBuilder --> cb_init[__init__ - project_root, custom_system_prompt]
    ContextBuilder --> cb_build[build - 组装完整 System Prompt]
    ContextBuilder --> cb_env[_build_environment_context - OS, 日期, CWD]
    ContextBuilder --> cb_proj[_load_project_knowledge - 读 AGENT.md]
    ContextBuilder --> cb_git[_get_git_status - branch, status, log]
    ContextBuilder --> cb_tool[_get_tool_guidelines - 工具使用指南]
```

### engine/ — 编排层

```mermaid
graph TD
    ENG[engine/engine.py] --> UsageStats[UsageStats: total_input, total_output, turn_count]
    ENG --> QueryEngine[QueryEngine]
    QueryEngine --> qe_init[__init__ - config]
    QueryEngine --> qe_chat[chat - user_input, callbacks]
    QueryEngine --> qe_compact_check[_should_compact]
    QueryEngine --> qe_compact[_compact]
    QueryEngine --> qe_estimate[_estimate_tokens]
    QueryEngine --> qe_reset[reset]
    QueryEngine --> qe_reg_tool[register_tool]
    QueryEngine --> qe_add_rule[add_permission_rule]
    QueryEngine --> qe_info[provider_info property]
```

### permissions/ — 权限层

```mermaid
graph TD
    PERM[permissions/manager.py] --> DANGER[DANGEROUS_PATTERNS 常量]
    PERM --> SAFE[SAFE_PATTERNS 常量]
    PERM --> PermissionManager[PermissionManager]
    PermissionManager --> pm_init[__init__ - rules]
    PermissionManager --> pm_check[check - tool, tool_input]
    PermissionManager --> pm_bash[_check_bash_command - command]
    PermissionManager --> pm_custom[_match_custom_rules - tool, tool_input]
    PermissionManager --> pm_pattern[_match_pattern - text, pattern]
    PermissionManager --> pm_add[add_rule - rule]
```

### cli/ — 入口层

```mermaid
graph TD
    CLI_M[cli/main.py] --> DEFAULT_MODELS[DEFAULT_MODELS 常量]
    CLI_M --> load_config[load_config - 从环境变量加载配置]
    CLI_M --> ask_permission[ask_permission - 交互式权限确认]
    CLI_M --> run_chat[run_chat - engine, user_input]
    CLI_M --> async_main[async_main - REPL 主循环]
    CLI_M --> main_fn[main - 入口函数]
```

---

## 文字版总结表格

| 文件 | 类/函数 | 方法 |
|------|---------|------|
| `types.py` | `EngineConfig` | provider, api_key, model, base_url, max_turns, max_tokens |
| `types.py` | `SimpleCallbacks` | on_text_delta, on_tool_start, on_tool_end, on_permission_ask |
| `api/base.py` | `BaseProvider` | `send_message()`, `model`, `provider_name` |
| `api/base.py` | `create_provider()` | 工厂函数，根据 provider 名创建实例 |
| `api/anthropic_provider.py` | `AnthropicProvider` | `send_message()`, `_convert_messages()` |
| `api/openai_provider.py` | `OpenAIProvider` | `send_message()`, `_convert_messages()` |
| `tools/base.py` | `Tool` (ABC) | `name`, `description`, `input_schema`, `is_read_only`, `call()`, `to_definition()` |
| `tools/base.py` | `ToolRegistry` | `register()`, `register_all()`, `get()`, `get_all()`, `to_definitions()`, `has()` |
| `tools/__init__.py` | `create_default_tool_registry()` | 创建并注册 6 个默认工具 |
| `tools/file_read.py` | `FileReadTool` | `call(file_path, offset, limit)` |
| `tools/file_write.py` | `FileWriteTool` | `call(file_path, content)` |
| `tools/file_edit.py` | `FileEditTool` | `call(file_path, old_string, new_string)` |
| `tools/bash.py` | `BashTool` | `call(command, cwd, timeout)` |
| `tools/glob.py` | `GlobTool` | `call(pattern, cwd)` |
| `tools/grep.py` | `GrepTool` | `call(pattern, path, include)` |
| `loop/loop.py` | `AgenticLoop` | `run()`, `_execute_tool()`, `_extract_final_text()` |
| `context/builder.py` | `ContextBuilder` | `build()`, `_build_environment_context()`, `_load_project_knowledge()`, `_get_git_status()`, `_get_tool_guidelines()` |
| `engine/engine.py` | `QueryEngine` | `chat()`, `_should_compact()`, `_compact()`, `_estimate_tokens()`, `reset()`, `register_tool()`, `add_permission_rule()` |
| `permissions/manager.py` | `PermissionManager` | `check()`, `_check_bash_command()`, `_match_custom_rules()`, `_match_pattern()`, `add_rule()` |
| `cli/main.py` | 顶层函数 | `load_config()`, `ask_permission()`, `run_chat()`, `async_main()`, `main()` |
