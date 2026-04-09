import json
import logging
import re
import uuid

from langgraph.types import Command

from config import settings
import workflow_log

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

PREVIEW_CHARS = 2000


def _suggested_filename(report: str) -> str:
    for line in report.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            title = stripped.lstrip("#").strip()
            slug = re.sub(r"[^\w\s-]", "", title.lower())
            slug = re.sub(r"[-\s]+", "_", slug).strip("_")
            if slug:
                return f"{slug[:80]}.md"
    return "report.md"


def _print_message_token(msg) -> None:
    content = getattr(msg, "content", None)
    if not content:
        return
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        content = "".join(parts)
    if content:
        print(content, end="", flush=True)


def _one_hitl_decision_from_user() -> dict:
    """Single decision dict for one pending tool call (see HumanInTheLoopMiddleware)."""

    choice = input(
        "\n👉 approve / edit / reject — type [a] approve, [e] edit (feedback), [r] reject: "
    ).strip().lower()

    if choice in ("a", "approve", ""):
        return {"type": "approve"}

    if choice in ("e", "edit", "revise"):
        feedback = input("✏️  Your feedback (report will be revised, then you can approve again):\n").strip()
        msg = (
            "The human reviewer asked for changes before saving. "
            "Revise the final markdown report accordingly, then call save_report again.\n\n"
            f"Feedback:\n{feedback}"
        )
        return {"type": "reject", "message": msg}

    if choice in ("r", "reject", "cancel"):
        reason = input("Reason for reject / cancel (optional):\n").strip() or "User cancelled the save."
        msg = (
            "The human reviewer chose not to save this report. Acknowledge briefly. "
            "Do not call save_report again for this turn.\n\n"
            f"Reason: {reason}"
        )
        return {"type": "reject", "message": msg}

    print("Unrecognized choice; defaulting to approve.")
    return {"type": "approve"}


def _display_pending_save_reports(action_requests: list[dict]) -> None:
    shown = False
    for i, req in enumerate(action_requests, start=1):
        if req.get("name") != "save_report":
            continue
        shown = True
        args = req.get("args") or {}
        report = args.get("report") or ""
        fname = _suggested_filename(report)
        preview = report if len(report) <= PREVIEW_CHARS else report[:PREVIEW_CHARS] + "\n... [truncated]"
        desc = req.get("description")

        display_args = dict(args)
        if "report" in display_args and isinstance(display_args["report"], str):
            r = display_args["report"]
            display_args["report"] = (
                r if len(r) <= PREVIEW_CHARS else r[:PREVIEW_CHARS] + "… [truncated]"
            )
        workflow_log.log_approval_required(req.get("name") or "save_report", display_args)

        print(f"\n--- Human review: save_report ({i}/{len(action_requests)}) ---")
        if desc:
            print(desc)
        print(f"\nSuggested filename (for display; saver may adjust): {fname}")
        print(f"\nPreview (up to {PREVIEW_CHARS} chars):\n")
        print(preview)
        print("\n--- End preview ---")
        print("\nFull args (JSON, report may be truncated above):")
        try:
            print(json.dumps(display_args, ensure_ascii=False, indent=2))
        except (TypeError, ValueError):
            print(display_args)

    if not shown:
        print("\n--- Human review pending (non-save_report action) ---")
        print(action_requests)


def _run_supervisor_repl(supervisor_graph, recursion_limit: int) -> None:
    print("Supervisor agent (type 'exit' to quit)")
    print("-" * 40)

    thread_id = str(uuid.uuid4())
    config: dict = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": recursion_limit,
    }

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

        pending: Command | dict = {"messages": [{"role": "user", "content": user_input}]}
        reset_workflow_log_for_turn = True

        while True:
            if reset_workflow_log_for_turn:
                workflow_log.reset_session()
                reset_workflow_log_for_turn = False

            interrupts: list = []
            print("\nAgent: ", end="", flush=True)

            for chunk in supervisor_graph.stream(
                pending,
                config=config,
                stream_mode=["values", "messages"],
                version="v2",
            ):
                if chunk["type"] == "messages":
                    _print_message_token(chunk["data"][0])
                elif chunk["type"] == "values":
                    interrupts = list(chunk.get("interrupts") or ())

            print()

            if not interrupts:
                break

            for intr in interrupts:
                payload = getattr(intr, "value", intr)
                if not isinstance(payload, dict):
                    print(f"(Unexpected interrupt payload: {payload!r})")
                    continue
                action_requests = payload.get("action_requests") or []
                _display_pending_save_reports(action_requests)
                n = len(action_requests)
                if n == 0:
                    decisions = []
                elif n == 1:
                    decisions = [_one_hitl_decision_from_user()]
                else:
                    print(
                        f"\n{n} tool calls await review; one choice applies to all pending actions."
                    )
                    one = _one_hitl_decision_from_user()
                    decisions = [one] * n
                pending = Command(resume={"decisions": decisions})


def main():
    from supervisor import SUPERVISOR_RECURSION_LIMIT, supervisor

    _run_supervisor_repl(supervisor, SUPERVISOR_RECURSION_LIMIT)


if __name__ == "__main__":
    main()
