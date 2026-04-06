"""Structured workflow logging: [Supervisor → …], tool calls, and attachments."""

from __future__ import annotations

import contextvars
import json
import logging
from contextlib import contextmanager
from typing import Any, Iterator

_logger = logging.getLogger("workflow")

_lane: contextvars.ContextVar[str | None] = contextvars.ContextVar("workflow_lane", default=None)
_knowledge_inner: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "workflow_knowledge_inner", default=False
)

_research_invocation = 0


def configure_workflow_logging() -> None:
    _logger.setLevel(logging.INFO)
    if not _logger.handlers:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter("%(message)s"))
        _logger.addHandler(h)
    _logger.propagate = False


def reset_session() -> None:
    global _research_invocation
    _research_invocation = 0


def next_research_round() -> int:
    global _research_invocation
    _research_invocation += 1
    return _research_invocation


def get_lane() -> str | None:
    return _lane.get()


def is_knowledge_inner() -> bool:
    return _knowledge_inner.get()


@contextmanager
def lane(name: str) -> Iterator[None]:
    tok = _lane.set(name)
    try:
        yield
    finally:
        _lane.reset(tok)


@contextmanager
def knowledge_inner() -> Iterator[None]:
    tok = _knowledge_inner.set(True)
    try:
        yield
    finally:
        _knowledge_inner.reset(tok)


def _emit(msg: str) -> None:
    _logger.info(msg)


def truncate_one_line(s: str, max_len: int = 200) -> str:
    s = " ".join(s.split())
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


def _nested_pad() -> str:
    return "    " if _knowledge_inner.get() else "  "


def log_handoff_planner() -> None:
    _emit("[Supervisor → Planner]")


def log_handoff_researcher(round_n: int) -> None:
    _emit(f"[Supervisor → Researcher]  (round {round_n})")


def log_handoff_critic() -> None:
    _emit("[Supervisor → Critic]")


def log_handoff_save_report() -> None:
    _emit("[Supervisor → save_report]")


def log_supervisor_tool(name: str, args_repr: str) -> None:
    _emit(f"🔧 {name}({args_repr})")


def log_delegate_tool(name: str, args_repr: str, note: str | None = None) -> None:
    pad = _nested_pad()
    line = f"{pad}🔧 {name}({args_repr})"
    if note:
        line += f"  ← {note}"
    _emit(line)


def log_delegate_attachment_one_line(text: str) -> None:
    pad = _nested_pad()
    _emit(f"{pad}📎 {text}")


def log_research_plan_block(goal: str, search_queries: list[str], sources: list[str], out_fmt: str) -> None:
    _emit("  📎 ResearchPlan(")
    _emit(f"       goal={truncate_one_line(goal, 120)!r},")
    sq = search_queries if len(str(search_queries)) < 200 else search_queries[:5] + ["…"]
    _emit(f"       search_queries={sq!r},")
    _emit(f"       sources_to_check={sources!r},")
    _emit(f"       output_format={truncate_one_line(out_fmt, 120)!r}")
    _emit("     )")


def log_critic_verdict_block(
    verdict: str,
    is_fresh: bool,
    is_complete: bool,
    is_well_structured: bool,
    strengths: list[str],
    gaps: list[str],
    revision_requests: list[str],
) -> None:
    _emit("  📎 CritiqueResult(")
    _emit(f'       verdict="{verdict}",')
    _emit(f"       is_fresh={is_fresh},")
    _emit(f"       is_complete={is_complete},")
    _emit(f"       is_well_structured={is_well_structured},")
    _emit(f"       strengths={strengths!r},")
    _emit(f"       gaps={gaps!r},")
    _emit(f"       revision_requests={revision_requests!r}")
    _emit("     )")


def format_args_preview(args: dict[str, Any], content_keys: frozenset[str], max_len: int = 240) -> str:
    """JSON-ish preview; long string values (e.g. report) are truncated."""
    preview: dict[str, Any] = {}
    for k, v in args.items():
        if isinstance(v, str) and k in content_keys:
            t = truncate_one_line(v, max_len)
            preview[k] = t + ("…" if len(v) > len(t) else "")
        else:
            preview[k] = v
    return json.dumps(preview, ensure_ascii=False)


def log_approval_required(tool_name: str, args: dict[str, Any]) -> None:
    body = format_args_preview(
        args,
        content_keys=frozenset({"report", "content"}),
        max_len=200,
    )
    _emit("")
    _emit("  " + "=" * 60)
    _emit("  ⏸️  ACTION REQUIRES APPROVAL")
    _emit("  " + "=" * 60)
    _emit(f"    Tool:  {tool_name}")
    _emit(f"    Args:  {body}")
    _emit("")

