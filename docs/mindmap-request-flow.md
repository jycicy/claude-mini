# 思维导图 2：用户提问 → Agent 回复的完整流程

> 当你输入一个问题，代码是怎么在文件和函数之间流动的？

## 流程图

```mermaid
sequenceDiagram
    participant User as 👤 用户
    participant CLI as cli/main.py
    participant Engine as engine/engine.py
    participant Context as context/builder.py
    participant Loop as loop/loop.py
    participant Provider as api/openai_provider.py
    participant LLM as 🤖 MiMo / DeepSeek / GPT
    participant Permission as permissions/manager.py
    participant Tool as tools/bash.py (等)

    Note over User,Tool: ===== 第一阶段：用户输入 =====

    User->>CLI: 输入 "帮我看看 main.py"
    CLI->>CLI: main() → async_main() → run_chat()
    CLI->>Engine: engine.chat("帮我看看 main.py", callbacks)

    Note over User,Tool: ===== 第二阶段：上下文构建 =====

    Engine->>Engine: 将用户消息加入 messages 列表
    Engine->>Context: context_builder.build()
    Context->>Context: _build_environment_context() → OS/日期/CWD
    Context->>Context: _load_project_knowledge() → 读 AGENT.md
    Context->>Context: _get_git_status() → git branch/status/log
    Context->>Context: _get_tool_guidelines() → 工具使用指南
    Context-->>Engine: 返回完整 System Prompt

    Note over User,Tool: ===== 第三阶段：Agentic Loop =====

    Engine->>Engine: _should_compact() → 检查是否需要压缩
    Engine->>Loop: loop.run(system_prompt, messages, max_turns, callbacks)

    rect rgb(255, 245, 230)
        Note over Loop,Tool: while turns < max_turns:
        
        Loop->>Provider: send_message(system_prompt, messages, tools)
        Provider->>Provider: _convert_messages() → 转换为 API 格式
        Provider->>LLM: HTTP POST /v1/chat/completions (流式)
        LLM-->>Provider: stream chunks (文本 + tool_calls)
        Provider-->>CLI: on_text_delta("我来帮你读...") → 实时显示
        Provider-->>Loop: APIResponse(content=[ToolUseContent(name="file_read")])
        
        Loop->>Loop: 检查 stop_reason == "tool_use" → 需要执行工具

        Note over Loop,Tool: ===== 第四阶段：工具执行 =====

        Loop->>Permission: check(FileReadTool, {"file_path": "main.py"})
        Permission->>Permission: is_read_only == True → Allow
        Permission-->>Loop: PermissionDecision.ALLOW

        Loop->>CLI: callbacks.on_tool_start("file_read", {...})
        Loop->>Tool: FileReadTool.call(file_path="main.py")
        Tool-->>Loop: ToolResult(content="文件内容...")
        Loop->>CLI: callbacks.on_tool_end("file_read", result)

        Loop->>Loop: 将工具结果加入 messages
        
        Note over Loop,Tool: 回到循环顶部 ↑↑↑

        Loop->>Provider: send_message(含工具结果的 messages)
        Provider->>LLM: 第二次请求（带文件内容）
        LLM-->>Provider: "这是 main.py 的内容分析..."
        Provider-->>CLI: on_text_delta(分析文本) → 实时显示
        Provider-->>Loop: APIResponse(stop_reason="end_turn")
        
        Loop->>Loop: stop_reason != "tool_use" → 退出循环
    end

    Note over User,Tool: ===== 第五阶段：返回结果 =====

    Loop->>Loop: _extract_final_text(messages)
    Loop-->>Engine: LoopResult(final_text, turns_used, total_tokens)
    Engine->>Engine: 更新 usage 统计
    Engine-->>CLI: 返回 LoopResult
    CLI->>CLI: 打印 token 消耗统计
    CLI-->>User: 显示完整回复
```

---

## 思维导图版

```mermaid
mindmap
  root((用户提问))
    1. CLI 入口
      main()
      async_main()
      run_chat(engine, input)
        创建 callbacks
        调用 engine.chat()
    2. Engine 编排
      chat(user_input, callbacks)
        添加消息到 messages
        调用 context_builder.build()
        检查 _should_compact()
        调用 loop.run()
        更新 usage 统计
    3. Context 构建
      build()
        基础人设 BASE_SYSTEM_PROMPT
        环境信息 _build_environment_context()
        项目知识 _load_project_knowledge()
        Git 状态 _get_git_status()
        工具指南 _get_tool_guidelines()
        用户自定义 custom_prompt
    4. Agentic Loop 核心循环
      run(system_prompt, messages)
        while turns < max_turns
          Step1: provider.send_message()
          Step2: 解析响应 → assistant message
          Step3: 检查 stop_reason
            end_turn → 退出循环
            tool_use → 继续执行工具
          Step4: _execute_tool()
            权限检查 permission.check()
              Allow → 执行
              Ask → 询问用户
              Deny → 拒绝
            tool.call() 执行工具
            收集 ToolResult
          Step5: 工具结果加入 messages
          回到 Step1
    5. Provider 通信
      send_message()
        _convert_messages() 格式转换
        HTTP 流式请求到 LLM
        解析流式 chunks
        组装 APIResponse
    6. 工具执行
      ToolRegistry.get(name)
      Tool.call(**kwargs)
        FileReadTool → 读文件
        BashTool → 执行命令
        GrepTool → 搜索代码
    7. 返回结果
      _extract_final_text()
      LoopResult → Engine → CLI → 用户
```

---

## 简化版：一句话总结

```
用户输入 → CLI.run_chat() → Engine.chat()
  → ContextBuilder.build() 组装 System Prompt
  → AgenticLoop.run() 进入循环
    → Provider.send_message() 调用 LLM
    → LLM 返回工具调用 → Permission.check() 权限检查
    → Tool.call() 执行工具 → 结果回传 LLM
    → LLM 生成最终回复
  → 返回 LoopResult → CLI 展示给用户
```

## 关键数据流

```
EngineConfig → QueryEngine.__init__()
  → create_provider() → BaseProvider 实例
  → create_default_tool_registry() → ToolRegistry (6个工具)
  → PermissionManager (权限规则)
  → ContextBuilder (项目根目录)
  → AgenticLoop (组合以上所有)

用户文本 → Message(role=USER)
  → [System Prompt + Messages + Tools] → LLM API
  → APIResponse → [TextContent | ToolUseContent]
  → ToolUseContent → Permission → Tool.call()
  → ToolResult → ToolResultContent → Message(role=USER)
  → 再次发给 LLM → 最终 TextContent
  → LoopResult.final_text → 显示给用户
```
