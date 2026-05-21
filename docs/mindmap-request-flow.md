# 思维导图 2：用户提问到 Agent 回复的完整流程

## 完整请求流程图

```mermaid
sequenceDiagram
    participant User as User
    participant CLI as cli/main.py
    participant Engine as engine/engine.py
    participant Context as context/builder.py
    participant AgLoop as loop/loop.py
    participant Provider as api/openai_provider.py
    participant LLM as LLM API
    participant Permission as permissions/manager.py
    participant Tool as tools/file_read.py

    Note over User,Tool: Phase 1 - User Input

    User->>CLI: Input text
    CLI->>CLI: main then async_main then run_chat
    CLI->>Engine: engine.chat user_input and callbacks

    Note over User,Tool: Phase 2 - Context Assembly

    Engine->>Engine: Append user message to messages list
    Engine->>Context: context_builder.build
    Context->>Context: _build_environment_context
    Context->>Context: _load_project_knowledge
    Context->>Context: _get_git_status
    Context->>Context: _get_tool_guidelines
    Context-->>Engine: Return full System Prompt

    Note over User,Tool: Phase 3 - Agentic Loop

    Engine->>Engine: _should_compact check
    Engine->>AgLoop: agantic_loop.run with system_prompt and messages

    AgLoop->>Provider: send_message with system_prompt and messages and tools
    Provider->>Provider: _convert_messages
    Provider->>LLM: HTTP POST streaming request
    LLM-->>Provider: Stream chunks with tool_calls
    Provider-->>CLI: on_text_delta callback
    Provider-->>AgLoop: APIResponse with ToolUseContent

    AgLoop->>AgLoop: stop_reason is tool_use

    Note over User,Tool: Phase 4 - Tool Execution

    AgLoop->>Permission: check tool and tool_input
    Permission->>Permission: is_read_only is True
    Permission-->>AgLoop: ALLOW

    AgLoop->>CLI: callbacks.on_tool_start
    AgLoop->>Tool: FileReadTool.call with file_path
    Tool-->>AgLoop: ToolResult with file content
    AgLoop->>CLI: callbacks.on_tool_end

    AgLoop->>AgLoop: Append tool result to messages

    Note over User,Tool: Phase 5 - Second LLM Call

    AgLoop->>Provider: send_message with tool results
    Provider->>LLM: Second request with file content
    LLM-->>Provider: Final text response
    Provider-->>CLI: on_text_delta callback
    Provider-->>AgLoop: APIResponse stop_reason is end_turn

    AgLoop->>AgLoop: Exit the while cycle

    Note over User,Tool: Phase 6 - Return Result

    AgLoop->>AgLoop: _extract_final_text
    AgLoop-->>Engine: LoopResult
    Engine->>Engine: Update usage stats
    Engine-->>CLI: Return LoopResult
    CLI-->>User: Display response
```

## 流程分层图

```mermaid
graph TD
    A[User Input] --> B[cli/main.py: run_chat]
    B --> C[engine/engine.py: chat]
    C --> D[context/builder.py: build]
    D --> D1[_build_environment_context]
    D --> D2[_load_project_knowledge]
    D --> D3[_get_git_status]
    D --> D4[_get_tool_guidelines]
    D1 --> E[Return System Prompt]
    D2 --> E
    D3 --> E
    D4 --> E
    E --> F[engine: _should_compact]
    F --> G[loop/loop.py: run]

    G --> H{While cycle}
    H --> I[Provider: send_message]
    I --> J[LLM API Call - Streaming]
    J --> K{stop_reason?}

    K -->|end_turn| L[Exit cycle]
    K -->|tool_use| M[_execute_tool]

    M --> N[permissions/manager.py: check]
    N --> N1{Decision?}
    N1 -->|Allow| O[Tool.call]
    N1 -->|Ask| P[Ask User via callback]
    N1 -->|Deny| Q[Return Permission Denied]
    P -->|Yes| O
    P -->|No| Q

    O --> R[Return ToolResult]
    R --> S[Append to messages]
    S --> H

    L --> T[_extract_final_text]
    T --> U[Return LoopResult]
    U --> V[engine: Update usage]
    V --> W[cli: Display to User]
```

## 数据变换流程

```mermaid
graph LR
    A[User text string] -->|Message role=USER| B[messages list]
    B -->|plus System Prompt plus Tool defs| C[Provider._convert_messages]
    C -->|OpenAI API format| D[HTTP Request to LLM]
    D -->|Stream chunks| E[APIResponse]
    E -->|ToolUseContent| F[_execute_tool]
    F -->|Permission check| G[Tool.call]
    G -->|ToolResult| H[ToolResultContent]
    H -->|Message role=USER| B
    E -->|TextContent on end_turn| I[LoopResult.final_text]
    I -->|Display| J[User sees response]
```

---

## 文字版流程总结

```
1. 用户输入文本
   |
2. cli/main.py: run_chat() 创建 callbacks, 调用 engine.chat()
   |
3. engine/engine.py: chat()
   - 将用户消息加入 messages
   - 调用 context_builder.build() 组装 System Prompt
   - 检查 _should_compact() 是否需要压缩
   - 调用 agentic_loop.run() 进入循环
   |
4. loop/loop.py: run() — 核心循环
   +-------------------------------------------------------+
   | while turns < max_turns:                               |
   |   a. provider.send_message() -> 调 LLM API (流式)      |
   |   b. 解析响应 -> 加入 messages                         |
   |   c. 如果 stop_reason == end_turn -> 退出循环          |
   |   d. 如果 stop_reason == tool_use:                    |
   |      - permission_manager.check() -> Allow/Ask/Deny   |
   |      - tool.call() -> 执行工具                         |
   |      - 工具结果加入 messages                           |
   |      - 回到 a                                         |
   +-------------------------------------------------------+
   |
5. _extract_final_text() -> 提取最终文本
   |
6. 返回 LoopResult -> engine 更新统计 -> cli 显示给用户
```
