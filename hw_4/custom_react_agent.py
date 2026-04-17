from __future__ import annotations

import json
import logging
from typing import Any, Callable

from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from hw_4.simple_memory import SimpleMemory

logger = logging.getLogger(__name__)


class CustomReActAgent:
    def __init__(
        self,
        model: ChatOpenAI,
        tool_schemas: list[dict[str, Any]],
        tool_map: dict[str, Callable[..., Any]],
        system_prompt: str,
        memory: SimpleMemory | None = None,
        max_iterations: int = 10,
        max_tool_output_chars: int = 20_000,
    ) -> None:
        self.model = model.bind_tools(tool_schemas)
        self.system_prompt = system_prompt
        self.memory = memory or SimpleMemory()
        self.max_iterations = max_iterations
        self.max_tool_output_chars = max_tool_output_chars
        self.tool_map = tool_map

    def invoke(
        self,
        user_input: str,
        thread_id: str = "default",
    ) -> dict[str, Any]:
        """
        Runs a full agent loop until:
        - model returns final answer without tool calls
        - or max_iterations is reached
        """
        messages = self.memory.get(thread_id)

        if not messages:
            messages.append(SystemMessage(content=self.system_prompt))

        messages.append(HumanMessage(content=user_input))

        for step in range(1, self.max_iterations + 1):
            ai_msg = self.model.invoke(messages)
            messages.append(ai_msg)

            tool_calls = getattr(ai_msg, "tool_calls", None) or []

            # Stop if model produced final answer
            if not tool_calls:
                self.memory.save(thread_id, messages)
                return {
                    "output": ai_msg.content,
                    "messages": messages,
                    "iterations": step,
                    "stop_reason": "final_answer",
                }

            # Execute requested tools
            for tool_call in tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call.get("args", {})
                tool_call_id = tool_call["id"]

                if tool_name not in self.tool_map:
                    tool_result = {
                        "error": f"Unknown tool: {tool_name}"
                    }
                else:
                    tool_fn = self.tool_map[tool_name]
                    try:
                        raw_result = tool_fn(**tool_args)
                        tool_result = self._normalize_tool_result(raw_result)
                    except Exception as e:
                        tool_result = {
                            "error": f"{type(e).__name__}: {str(e)}"
                        }

                messages.append(
                    ToolMessage(
                        content=self._serialize_tool_result(tool_result),
                        tool_call_id=tool_call_id,
                    )
                )

        # Fallback if loop limit is reached
        final_answer = self._force_final_answer(messages)
        self.memory.save(thread_id, messages + [final_answer])

        return {
            "output": final_answer.content,
            "messages": messages + [final_answer],
            "iterations": self.max_iterations,
            "stop_reason": "max_iterations",
        }

    def _force_final_answer(self, messages: list[Any]) -> AIMessage:
        """
        Ask the model to stop using tools and summarize what it already knows.
        """
        forced_messages = messages + [
            HumanMessage(
                content=(
                    "Stop using tools. "
                    "Based only on the information already gathered, "
                    "provide the best possible final answer."
                )
            )
        ]
        return self.model.invoke(forced_messages)

    def _normalize_tool_result(self, result: Any) -> Any:
        """
        Make tool outputs safe and consistent for LLM consumption.
        """
        if isinstance(result, (str, int, float, bool)) or result is None:
            return result

        try:
            json.dumps(result)
            return result
        except TypeError:
            return str(result)

    def _serialize_tool_result(self, result: Any) -> str:
        if isinstance(result, str):
            text = result
        else:
            text = json.dumps(result, ensure_ascii=False, indent=2)

        if len(text) > self.max_tool_output_chars:
            text = text[: self.max_tool_output_chars] + "\n\n[TRUNCATED]"
        return text