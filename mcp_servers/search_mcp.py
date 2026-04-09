"""SearchMCP: web_search, read_url, knowledge_search; resource knowledge-base-stats."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from fastmcp import FastMCP

from config import settings
from tools import knowledge_search as knowledge_search_tool
from tools import read_url as read_url_tool
from tools import web_search as web_search_tool

logger = logging.getLogger(__name__)

mcp = FastMCP(name="SearchMCP")

SEARCH_HOST = "127.0.0.1"
SEARCH_PORT = 8901


@mcp.tool(name="web_search")
def web_search(query: str) -> str:
    """Search the internet using DuckDuckGo. Returns a list of results,
    each containing a title, URL, and a short snippet.
    Useful for finding relevant pages; use read_url for full page content.

    Args:
        query: The search query string.
    """
    logger.info("MCP web_search: query=%r", query)
    return web_search_tool.invoke({"query": query})


@mcp.tool(name="read_url")
def read_url(url: str) -> str:
    """Fetch and extract the main text content from a web page.
    Uses trafilatura to strip navigation, ads, and boilerplate.
    The result is automatically truncated to fit within context limits.

    Args:
        url: The URL of the page to read.
    """
    logger.info("MCP read_url: url=%s", url)
    return read_url_tool.invoke({"url": url})


@mcp.tool(name="knowledge_search")
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
    logger.info("MCP knowledge_search: query=%r", query)
    return knowledge_search_tool.invoke({"query": query})


@mcp.resource("resource://knowledge-base-stats")
def knowledge_base_stats() -> dict:
    """Document count and last update time for PDFs in the knowledge data directory."""
    pdf_dir = Path(settings.knowledge_data_dir)
    pdfs = sorted(pdf_dir.glob("*.pdf")) if pdf_dir.is_dir() else []
    last_update: str | None = None
    if pdfs:
        max_mtime = max(p.stat().st_mtime for p in pdfs)
        last_update = datetime.fromtimestamp(max_mtime, tz=timezone.utc).isoformat()
    return {
        "document_count": len(pdfs),
        "knowledge_data_dir": str(pdf_dir.resolve()),
        "last_update_utc": last_update,
    }


def main() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logger.info(
        "Starting SearchMCP (SSE) on http://%s:%s — tools: web_search, read_url, knowledge_search",
        SEARCH_HOST,
        SEARCH_PORT,
    )
    mcp.run(transport="sse", host=SEARCH_HOST, port=SEARCH_PORT)


if __name__ == "__main__":
    main()
