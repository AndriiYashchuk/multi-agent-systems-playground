"""ReportMCP: save_report; resource output-dir."""

from __future__ import annotations

import logging
from pathlib import Path

from fastmcp import FastMCP

from config import settings
from tools import save_report as save_report_tool

logger = logging.getLogger(__name__)

mcp = FastMCP(name="ReportMCP")

REPORT_HOST = "127.0.0.1"
REPORT_PORT = 8902


@mcp.tool(name="save_report")
def save_report(report: str) -> str:
    """Persist the final Markdown report produced by the supervisor to disk.

    Delegates to the save-report sub-agent, which chooses a filename and calls write_report.

    Args:
        report: The complete final Markdown report text to save.
    """
    logger.info("MCP save_report: report_length=%d", len(report))
    return save_report_tool.invoke({"report": report})


@mcp.resource("resource://output-dir")
def output_dir() -> dict:
    """Absolute output directory path and list of saved Markdown reports."""
    out = Path(settings.output_dir).resolve()
    reports: list[str] = []
    if out.is_dir():
        reports = sorted(p.name for p in out.glob("*.md"))
    return {
        "output_dir": str(out),
        "saved_reports": reports,
    }


def main() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logger.info(
        "Starting ReportMCP (SSE) on http://%s:%s — tool: save_report",
        REPORT_HOST,
        REPORT_PORT,
    )
    mcp.run(transport="sse", host=REPORT_HOST, port=REPORT_PORT)


if __name__ == "__main__":
    main()
