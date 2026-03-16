# Task: Research Agent with a Custom ReAct Loop

Extend your Research Agent from homework-lesson-3 by **replacing `create_react_agent` with your own ReAct loop implementation** and **improving the system prompt** using prompting techniques from the lecture.

**Goal:** understand how the ReAct loop works internally — without the “magic” of frameworks — and learn how to write effective prompts that significantly influence agent behavior.

---

### What changes compared to homework-lesson-3

| homework-lesson-3                       | homework-lesson-4                                       |
| --------------------------------------- | ------------------------------------------------------- |
| `create_react_agent` from LangChain     | Custom ReAct loop implementation                        |
| LangChain manages the tool-calling loop | You manage the loop yourself                            |
| The framework parses LLM responses      | You process `tool_calls` from the API response yourself |
| `MemorySaver` for memory                | You manage the `messages` list yourself                 |
| LangChain `@tool` decorator             | Tools are described as JSON Schema for the API          |
| Basic system prompt                     | Improved prompt using prompting techniques              |

---

### What needs to be implemented

1. **Custom ReAct Loop** — replace `create_react_agent` with your own loop that sends messages to the LLM API with tool definitions, processes the response, executes tool calls, and repeats until a final answer is produced.
2. **Tools as JSON Schema** — describe the tools (`web_search`, `read_url`, `write_report`) in the tool-calling API format of your provider instead of using the LangChain `@tool` decorator.
3. **Dialogue memory** — implement context persistence between requests without `MemorySaver`.
4. **System Prompt** — write a meaningful system prompt that controls the agent’s behavior. Experiment with wording — this is prompt engineering in practice.
5. **Step logging** — print to the console which tool is being called, with which arguments, and what result it returns.
6. **Error handling** — tool errors must not crash the agent; add an iteration limit so the agent does not get stuck in a loop.
7. **Improved System Prompt** — rewrite the system prompt from homework-lesson-3 using prompt-engineering practices from the lecture (clear role, structured instructions, examples, behavioral constraints, etc.).

---

### Expected result

1. **Working agent** — runs via `python main.py` and works in interactive mode.
2. **Custom ReAct loop** — without `create_react_agent`, `AgentExecutor`, or other framework agent abstractions.
3. **Tool calling through API** — tools are described as JSON Schema, and the LLM decides when to call them.
4. **Logging** — the console shows every step: which tool was called, with which parameters, and what result it returned.
5. **Multi-step reasoning** — the agent makes 3–5+ tool calls for a single request.
6. **Dialogue memory** — the agent remembers previous messages within the session.
7. **Report** — the agent generates and saves a Markdown report via `write_report`.

Example console log:

```text
You: Compare naive RAG and sentence-window retrieval

🔧 Tool call: web_search(query="naive RAG approach explained")
📎 Result: Found 5 results...

🔧 Tool call: web_search(query="sentence window retrieval RAG")
📎 Result: Found 5 results...

🔧 Tool call: read_url(url="https://example.com/rag-comparison")
📎 Result: [5000 chars] Article about RAG approaches...

🔧 Tool call: write_report(filename="rag_comparison.md", content="# RAG Comparison...")
📎 Result: Report saved to output/rag_comparison.md

Agent: The report has been saved to output/rag_comparison.md. Here are the key differences: ...
```
