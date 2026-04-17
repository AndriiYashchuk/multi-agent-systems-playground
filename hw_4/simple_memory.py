from typing import Any

class SimpleMemory:
    """
    Very small in-memory conversation store.
    Stores message history per thread_id.
    """

    def __init__(self) -> None:
        self._threads: dict[str, list[Any]] = {}

    def get(self, thread_id: str) -> list[Any]:
        return list(self._threads.get(thread_id, []))

    def save(self, thread_id: str, messages: list[Any]) -> None:
        self._threads[thread_id] = list(messages)

    def clear(self, thread_id: str) -> None:
        self._threads.pop(thread_id, None)