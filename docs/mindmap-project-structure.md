# 思维导图 1：项目文件结构 + 方法清单

> GitHub 会自动渲染 Mermaid 图表，直接在浏览器中查看即可。

## 完整项目结构与方法

```mermaid
mindmap
  root((mini-agent))
    **types.py**
      类 Role
        USER / ASSISTANT / SYSTEM
      类 TextContent
        type, text
      类 ToolUseContent
        type, id, name, input
      类 ToolResultContent
        type, tool_use_id, content, is_error
      类 Message
        role, content
      类 ToolDefinition
        name, description, input_schema
      类 ToolResult
        content, is_error
      类 PermissionDecision
        ALLOW / ASK / DENY
      类 PermissionRule
        tool, decision, pattern
      类 EngineConfig
        provider, api_key, model, base_url
        max_turns, max_tokens, project_root
      类 TokenUsage
        input_tokens, output_tokens
      类 LoopResult
        final_text, turns_used, total_tokens
      类 SimpleCallbacks
        on_text_delta, on_tool_start
        on_tool_end, on_permission_ask
    **api/**
      base.py
        类 APIResponse
          content, stop_reason, usage
        类 BaseProvider «抽象»
          send_message()
          model (property)
          provider_name (property)
        函数 create_provider()
      anthropic_provider.py
        类 AnthropicProvider
          __init__(api_key, model, base_url)
          send_message()
          _convert_messages()
      openai_provider.py
        常量 PROVIDER_PRESETS
          deepseek / mimo / qwen / glm
          openrouter / siliconflow / ollama
        类 OpenAIProvider
          __init__(api_key, model, base_url)
          send_message()
          _convert_messages()
    **tools/**
      base.py
        类 Tool «抽象»
          name (property)
          description (property)
          input_schema (property)
          is_read_only (property)
          call()
          to_definition()
        类 ToolRegistry
          register()
          register_all()
          get()
          get_all()
          to_definitions()
          has()
      __init__.py
        函数 create_default_tool_registry()
      file_read.py — FileReadTool
        call(file_path, offset, limit)
      file_write.py — FileWriteTool
        call(file_path, content)
      file_edit.py — FileEditTool
        call(file_path, old_string, new_string)
      bash.py — BashTool
        call(command, cwd, timeout)
      glob.py — GlobTool
        call(pattern, cwd)
      grep.py — GrepTool
        call(pattern, path, include)
    **loop/**
      loop.py
        类 AgenticLoop
          __init__(api_client, tool_registry, permission_manager)
          run(system_prompt, messages, max_turns, callbacks)
          _execute_tool(tool_use, callbacks)
          _extract_final_text(messages)
    **context/**
      builder.py
        常量 BASE_SYSTEM_PROMPT
        类 ContextBuilder
          __init__(project_root, custom_system_prompt)
          build()
          _build_environment_context()
          _load_project_knowledge()
          _get_git_status()
          _get_tool_guidelines()
    **engine/**
      engine.py
        类 UsageStats
          total_input, total_output, turn_count
        类 QueryEngine
          __init__(config)
          chat(user_input, callbacks)
          _should_compact()
          _compact()
          _estimate_tokens()
          reset()
          register_tool()
          add_permission_rule()
          provider_info (property)
    **permissions/**
      manager.py
        常量 DANGEROUS_PATTERNS
        常量 SAFE_PATTERNS
        类 PermissionManager
          __init__(rules)
          check(tool, tool_input)
          _check_bash_command(command)
          _match_custom_rules(tool, tool_input)
          _match_pattern(text, pattern)
          add_rule(rule)
    **cli/**
      main.py
        常量 DEFAULT_MODELS
        函数 load_config()
        函数 ask_permission()
        函数 run_chat(engine, user_input)
        函数 async_main()
        函数 main()
```

---

## 文字版（Markdown 表格）

| 文件 | 类/函数 | 方法 |
|------|---------|------|
| `types.py` | `EngineConfig` | 数据类：provider, api_key, model, base_url, max_turns, max_tokens... |
| `types.py` | `SimpleCallbacks` | on_text_delta, on_tool_start, on_tool_end, on_permission_ask... |
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
