import logging
from pathlib import Path

from langchain_core.tools import tool

from config import settings
import workflow_log

logger = logging.getLogger(__name__)

REPORTS_DIR = Path(settings.output_dir)


def _truncate(text: str, max_chars: int, label: str = "content") -> str:
    if len(text) <= max_chars:
        return text
    logger.info("Truncating %s from %d to %d chars", label, len(text), max_chars)
    return text[:max_chars] + f"\n\n... [truncated — showed {max_chars} of {len(text)} chars of {label}]"


@tool
def write_report(filename: str, content: str) -> str:
    """Save a Markdown report to the output directory.

    Args:
        filename: Name of the file (e.g. 'summary.md'). A '.md' extension
                  is appended automatically if missing.
        content:  The Markdown text of the report.

    Returns:
        Confirmation message with the absolute path to the saved file.
    """
    logger.info("write_report called: filename=%s, content_length=%d", filename, len(content))

    if workflow_log.get_lane() == "save_report":
        preview = workflow_log.truncate_one_line(content, 120)
        suf = "…" if len(content) > len(preview) else ""
        workflow_log.log_delegate_tool(
            "write_report",
            f"filename={filename!r}, content={preview!r}{suf}",
        )

    if not filename.endswith(".md"):
        filename += ".md"

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    filepath = REPORTS_DIR / filename
    filepath.write_text(content, encoding="utf-8")

    logger.info("Report saved to %s", filepath.resolve())
    resolved = str(filepath.resolve())
    if workflow_log.get_lane() == "save_report":
        workflow_log.log_delegate_attachment_one_line(f"[saved: {resolved}]")
    return f"Report saved successfully: {resolved}"


@tool
def read_file(filepath: str) -> str:
    """Read and return the contents of a local file.

    Args:
        filepath: Path to the file to read.
    """
    logger.info("read_file called: filepath=%s", filepath)

    if workflow_log.get_lane() == "save_report":
        workflow_log.log_delegate_tool("read_file", repr(filepath))

    path = Path(filepath)
    if not path.exists():
        logger.warning("File not found: %s", filepath)
        if workflow_log.get_lane() == "save_report":
            workflow_log.log_delegate_attachment_one_line("[error: file not found]")
        return f"Error: file '{filepath}' not found."
    if not path.is_file():
        logger.warning("Not a file: %s", filepath)
        return f"Error: '{filepath}' is not a file."

    text = path.read_text(encoding="utf-8")
    logger.info("Read %d chars from %s", len(text), filepath)
    if workflow_log.get_lane() == "save_report":
        workflow_log.log_delegate_attachment_one_line(f"[{len(text)} chars]")
    return text


@tool
def list_files(directory: str = ".") -> str:
    """List files and sub-directories in the given directory.

    Args:
        directory: Path to the directory to list (default: current dir).
    """
    logger.info("list_files called: directory=%s", directory)

    if workflow_log.get_lane() == "save_report":
        workflow_log.log_delegate_tool("list_files", repr(directory))

    path = Path(directory)
    if not path.exists():
        logger.warning("Directory not found: %s", directory)
        return f"Error: directory '{directory}' not found."
    if not path.is_dir():
        logger.warning("Not a directory: %s", directory)
        return f"Error: '{directory}' is not a directory."

    entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name))
    logger.info("Found %d entries in %s", len(entries), directory)
    lines = [f"{'[DIR]  ' if e.is_dir() else '[FILE] '}{e.name}" for e in entries]
    if workflow_log.get_lane() == "save_report":
        workflow_log.log_delegate_attachment_one_line(f"[{len(entries)} entries listed]")
    return "\n".join(lines) if lines else "(empty directory)"


@tool
def web_search(query: str) -> str:
    """Search the internet using DuckDuckGo. Returns a list of results,
    each containing a title, URL, and a short snippet.
    Useful for finding relevant pages; use read_url for full page content.

    Args:
        query: The search query string.
    """
    max_results = settings.max_search_results
    logger.info("web_search called: query=%r, max_results=%d", query, max_results)

    lane = workflow_log.get_lane()
    if lane:
        note = None
        q = query.lower()
        if lane == "Critic" and any(x in q for x in ("2025", "2026", "fresh", "current", "recent")):
            note = "checking freshness / recency"
        elif lane == "Critic" and any(x in q for x in ("benchmark", "verify", "accuracy")):
            note = "verifying data"
        workflow_log.log_delegate_tool("web_search", repr(query), note=note)

    from ddgs import DDGS

    results = DDGS().text(query, max_results=max_results)
    logger.info("web_search returned %d results", len(results))
    if lane:
        workflow_log.log_delegate_attachment_one_line(f"[{len(results)} results found]")
    raw = "\n\n".join(
        f"**{r['title']}**\n{r['href']}\n{r['body']}" for r in results
    )
    return _truncate(raw, settings.max_search_content_length, label="search results")


@tool
def read_url(url: str) -> str:
    """Fetch and extract the main text content from a web page.
    Uses trafilatura to strip navigation, ads, and boilerplate.
    The result is automatically truncated to fit within context limits.

    Args:
        url: The URL of the page to read.
    """
    logger.info("read_url called: url=%s", url)

    if workflow_log.get_lane():
        workflow_log.log_delegate_tool("read_url", repr(url))

    import trafilatura

    try:
        downloaded = trafilatura.fetch_url(url)
    except Exception as e:
        logger.error("Failed to fetch URL %s: %s", url, e)
        return f"Error fetching URL '{url}': {e}"

    if downloaded is None:
        logger.warning("Could not download page at %s", url)
        return f"Error: could not download page at '{url}' (site may be unavailable or URL is invalid)."

    text = trafilatura.extract(downloaded)

    if not text:
        logger.warning("No readable text extracted from %s", url)
        return f"Error: page at '{url}' was downloaded but no readable text could be extracted."

    text = _truncate(text, settings.max_url_content_length, label="page content")

    logger.info("read_url returned %d chars from %s", len(text), url)
    if workflow_log.get_lane():
        workflow_log.log_delegate_attachment_one_line(f"[{len(text)} chars]")
    return text


_search_agent = None


def _get_search_agent():
    global _search_agent
    if _search_agent is None:
        from rag_agent import search_agent, RECURSION_LIMIT
        _search_agent = (search_agent, RECURSION_LIMIT)
    return _search_agent


_planner_agent = None


def _get_planner_agent():
    global _planner_agent
    if _planner_agent is None:
        from planer_agent.agent import planner_agent as _planner

        _planner_agent = _planner
    return _planner_agent


_research_agent = None


def _get_research_agent():
    global _research_agent
    if _research_agent is None:
        from research_agent.agent import RECURSION_LIMIT, research_agent as _research

        _research_agent = (_research, RECURSION_LIMIT)
    return _research_agent


_save_report_agent = None


def _get_save_report_agent():
    global _save_report_agent
    if _save_report_agent is None:
        from save_report.agent import RECURSION_LIMIT, save_report_agent as _saver

        _save_report_agent = (_saver, RECURSION_LIMIT)
    return _save_report_agent


_critic_agent = None


def _get_critic_agent():
    global _critic_agent
    if _critic_agent is None:
        from critic_agent.agent import critic_agent as _critic

        _critic_agent = _critic
    return _critic_agent


@tool
def knowledge_search(query: str) -> str:
    """Search the internal knowledge base (PDF documents) using an
    autonomous search agent that performs hybrid retrieval with iterative
    refinement (searching, expanding context of promising chunks, and
    re-querying as needed).

    Use this tool when the question is about RAG (Retrieval-Augmented Generation)
    concepts, techniques, or architectures. The knowledge base contains detailed
    information about RAG, so prefer this tool over web search for RAG-related queries.

    Args:
        query: Natural-language search query.
    """
    import uuid

    logger.info("knowledge_search called — delegating to search agent: query=%r", query)

    if workflow_log.get_lane():
        workflow_log.log_delegate_tool("knowledge_search", repr(query))

    agent, recursion_limit = _get_search_agent()
    config = {
        "configurable": {"thread_id": uuid.uuid4().hex},
        "recursion_limit": recursion_limit,
    }

    with workflow_log.knowledge_inner():
        result = agent.invoke(
            {"messages": [{"role": "user", "content": query}]},
            config=config,
        )

    ai_messages = [
        m for m in result["messages"]
        if hasattr(m, "content") and m.content and m.type == "ai" and not m.tool_calls
    ]

    if ai_messages:
        answer = ai_messages[-1].content
    else:
        answer = "The search agent could not produce an answer."

    logger.info("knowledge_search: search agent returned %d chars", len(answer))
    if workflow_log.get_lane():
        chunks_guess = answer.count("chunk_id=") + answer.count("chunk id")
        if chunks_guess > 0:
            workflow_log.log_delegate_attachment_one_line(f"[{chunks_guess} chunk references in answer]")
        else:
            workflow_log.log_delegate_attachment_one_line(f"[knowledge search answer; {len(answer)} chars]")
    return _truncate(answer, settings.max_search_content_length, label="knowledge results")

@tool
def plan(request: str) -> str:
    """Turn a research question into a structured plan (goal, search queries, sources, output format).

    Delegates to the planner agent — the first step of the research pipeline. Use this
    before deep searching when you need a clear decomposition and query strategy.

    Args:
        request: The user's research question or topic to plan for.
    """
    import uuid

    logger.info("plan called: request_length=%d", len(request))

    with workflow_log.lane("Planner"):
        workflow_log.log_handoff_planner()
        workflow_log.log_supervisor_tool("plan", repr(workflow_log.truncate_one_line(request, 220)))

        agent = _get_planner_agent()
        config = {"configurable": {"thread_id": uuid.uuid4().hex}}

        result = agent.invoke(
            {"messages": [{"role": "user", "content": request}]},
            config=config,
        )

        from planer_agent.agent import ResearchPlan

        structured = result.get("structured_response")
        if structured is None:
            raise RuntimeError(
                "Planner agent returned no structured_response; expected a validated ResearchPlan."
            )
        if not isinstance(structured, ResearchPlan):
            raise TypeError(
                f"Planner structured_response has wrong type {type(structured).__name__!r}; "
                "expected ResearchPlan."
            )

        try:
            out = structured.model_dump_json(indent=2)
        except Exception as e:
            raise RuntimeError(f"Failed to serialize ResearchPlan to JSON: {e}") from e

        logger.info("plan: returning structured plan (%d chars)", len(out))
        workflow_log.log_research_plan_block(
            structured.goal,
            structured.search_queries,
            structured.sources_to_check,
            structured.output_format,
        )
        return out


@tool
def research(plan: str) -> str:
    """Run multi-step research following a given plan (web search, page fetch, knowledge base).

    Delegates to the research sub-agent. Use after `plan` or whenever you have an
    explicit breakdown of what to search for and how to present results.

    Args:
        plan: How to conduct the research: goals, queries, sources, and output shape
              (e.g. JSON from the planner).
    """
    import uuid

    logger.info("research called: plan_length=%d", len(plan))

    rnd = workflow_log.next_research_round()
    user_message = (
        "Follow this research plan and produce a complete answer for the orchestrating agent.\n\n"
        "## Plan\n\n"
        f"{plan}"
    )

    with workflow_log.lane("Researcher"):
        workflow_log.log_handoff_researcher(rnd)
        workflow_log.log_supervisor_tool("research", repr(workflow_log.truncate_one_line(user_message, 240)))

        agent, recursion_limit = _get_research_agent()
        config = {
            "configurable": {"thread_id": uuid.uuid4().hex},
            "recursion_limit": recursion_limit,
        }

        result = agent.invoke(
            {"messages": [{"role": "user", "content": user_message}]},
            config=config,
        )

        ai_messages = [
            m
            for m in result["messages"]
            if hasattr(m, "content") and m.content and m.type == "ai" and not m.tool_calls
        ]

        if ai_messages:
            answer = ai_messages[-1].content
        else:
            answer = "The research agent could not produce an answer."

        logger.info("research: returning %d chars", len(answer))
        workflow_log.log_delegate_attachment_one_line(f"[research answer; {len(answer)} chars]")
        return _truncate(answer, settings.max_search_content_length, label="research results")


@tool
def critique(original_request: str, research_findings: str) -> str:
    """Independently review research quality: verify claims with web/knowledge tools; return APPROVE or REVISE.

    Delegates to the critic sub-agent. Use after research output exists. The critic checks \
    freshness (vs. current date), completeness (vs. the original request), and structure \
    (report-readiness), and returns structured JSON.

    Args:
        original_request: The user's original question or task (for completeness checking).
        research_findings: The research output to evaluate (e.g. from the research agent).
    """
    import uuid
    from datetime import date

    logger.info(
        "critique called: original_request_length=%d, findings_length=%d",
        len(original_request),
        len(research_findings),
    )

    from critic_agent.agent import CriticVerdict, RECURSION_LIMIT

    today = date.today().isoformat()
    user_message = (
        f"Today's date: {today}\n\n"
        "## Original user request\n\n"
        f"{original_request}\n\n"
        "## Research findings to review\n\n"
        f"{research_findings}"
    )

    with workflow_log.lane("Critic"):
        workflow_log.log_handoff_critic()
        workflow_log.log_supervisor_tool(
            "critique",
            f"original_request={repr(workflow_log.truncate_one_line(original_request, 140))}, "
            f"research_findings={repr(workflow_log.truncate_one_line(research_findings, 200))}",
        )

        agent = _get_critic_agent()
        config = {
            "configurable": {"thread_id": uuid.uuid4().hex},
            "recursion_limit": RECURSION_LIMIT,
        }

        result = agent.invoke(
            {"messages": [{"role": "user", "content": user_message}]},
            config=config,
        )

        structured = result.get("structured_response")
        if structured is None:
            raise RuntimeError(
                "Critic agent returned no structured_response; expected a validated CriticVerdict."
            )
        if not isinstance(structured, CriticVerdict):
            raise TypeError(
                f"Critic structured_response has wrong type {type(structured).__name__!r}; "
                "expected CriticVerdict."
            )

        try:
            out = structured.model_dump_json(indent=2)
        except Exception as e:
            raise RuntimeError(f"Failed to serialize CriticVerdict to JSON: {e}") from e

        logger.info("critique_research: returning structured verdict (%d chars)", len(out))
        workflow_log.log_critic_verdict_block(
            verdict=structured.decision,
            is_fresh=structured.freshness.sufficient,
            is_complete=structured.completeness.sufficient,
            is_well_structured=structured.structure.sufficient,
            strengths=structured.strengths,
            gaps=structured.gaps,
            revision_requests=structured.revision_requests,
        )
        return out


@tool
def save_report(report: str) -> str:
    """Persist the final Markdown report produced by the supervisor to disk.

    Delegates to the save-report sub-agent, which chooses a filename and calls write_report.

    Args:
        report: The complete final Markdown report text to save.
    """
    import uuid

    logger.info("save_report called: report_length=%d", len(report))

    user_message = (
        "Save the following report using your tools. Preserve the content exactly.\n\n"
        "## Report\n\n"
        f"{report}"
    )

    with workflow_log.lane("save_report"):
        workflow_log.log_handoff_save_report()
        preview = workflow_log.truncate_one_line(report, 160)
        suf = "…" if len(report) > len(preview) else ""
        workflow_log.log_supervisor_tool("save_report", f"report={preview!r}{suf}")

        agent, recursion_limit = _get_save_report_agent()
        config = {
            "configurable": {"thread_id": uuid.uuid4().hex},
            "recursion_limit": recursion_limit,
        }

        result = agent.invoke(
            {"messages": [{"role": "user", "content": user_message}]},
            config=config,
        )

        ai_messages = [
            m
            for m in result["messages"]
            if hasattr(m, "content") and m.content and m.type == "ai" and not m.tool_calls
        ]

        if ai_messages:
            answer = ai_messages[-1].content
        else:
            answer = "The save-report agent did not return a final confirmation."

        logger.info("save_report: returning %d chars", len(answer))
        workflow_log.log_delegate_attachment_one_line(f"[save-report agent: {len(answer)} chars]")
        return answer
