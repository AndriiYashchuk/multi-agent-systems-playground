import logging
import sys
import uuid

from config import settings

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)


def _run_agent_loop(agent, agent_name: str, recursion_limit: int = 15):
    print(f"{agent_name} (type 'exit' to quit)")
    print("-" * 40)

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": recursion_limit}

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        for chunk in agent.stream(
            {"messages": [{"role": "user", "content": user_input}]},
            config=config,
        ):
            if "agent" in chunk and "messages" in chunk["agent"]:
                for msg in chunk["agent"]["messages"]:
                    if hasattr(msg, "content") and msg.content:
                        print(f"\nAgent: {msg.content}")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "research"

    if mode == "search":
        from rag_agent import search_agent, RECURSION_LIMIT
        _run_agent_loop(search_agent, "Search Agent", recursion_limit=RECURSION_LIMIT)
    else:
        from agent import agent
        _run_agent_loop(agent, "Research Agent", recursion_limit=15)


if __name__ == "__main__":
    main()
