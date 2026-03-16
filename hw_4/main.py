import logging
import uuid

from config import settings

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

from hw_4.agent import agent


def main() -> None:
    print("Custom ReAct Agent (type 'exit' to quit)")
    print("-" * 45)

    thread_id = str(uuid.uuid4())

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

        result = agent.invoke(user_input, thread_id=thread_id)

        print(f"\nAgent: {result['output']}")
        print(
            f"\n  [{result['iterations']} iteration(s), "
            f"stop_reason={result['stop_reason']}]"
        )


if __name__ == "__main__":
    main()
