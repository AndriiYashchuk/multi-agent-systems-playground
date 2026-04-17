from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from config import settings

logger = logging.getLogger(__name__)

REPORTS_DIR = Path(settings.output_dir)


def _truncate(text: str, max_chars: int, label: str = "content") -> str:
    if len(text) <= max_chars:
        return text
    logger.info("Truncating %s from %d to %d chars", label, len(text), max_chars)
    return text[:max_chars] + (
        f"\n\n... [truncated — showed {max_chars} of {len(text)} chars of {label}]"
    )



def web_search(query: str) -> str:
    """Search the internet using DuckDuckGo."""
    max_results = settings.max_search_results
    logger.info("web_search called: query=%r, max_results=%d", query, max_results)

    from ddgs import DDGS

    results = DDGS().text(query, max_results=max_results)
    logger.info("web_search returned %d results", len(results))
    raw = "\n\n".join(
        f"**{r['title']}**\n{r['href']}\n{r['body']}" for r in results
    )
    return _truncate(raw, settings.max_search_content_length, label="search results")


def read_url(url: str) -> str:
    """Fetch and extract the main text content from a web page."""
    logger.info("read_url called: url=%s", url)

    import trafilatura

    try:
        downloaded = trafilatura.fetch_url(url)
    except Exception as e:
        logger.error("Failed to fetch URL %s: %s", url, e)
        return f"Error fetching URL '{url}': {e}"

    if downloaded is None:
        logger.warning("Could not download page at %s", url)
        return (
            f"Error: could not download page at '{url}' "
            "(site may be unavailable or URL is invalid)."
        )

    text = trafilatura.extract(downloaded)

    if not text:
        logger.warning("No readable text extracted from %s", url)
        return (
            f"Error: page at '{url}' was downloaded "
            "but no readable text could be extracted."
        )

    text = _truncate(text, settings.max_url_content_length, label="page content")
    logger.info("read_url returned %d chars from %s", len(text), url)
    return text


def read_file(filepath: str) -> str:
    """Read and return the contents of a local file."""
    logger.info("read_file called: filepath=%s", filepath)

    path = Path(filepath)
    if not path.exists():
        logger.warning("File not found: %s", filepath)
        return f"Error: file '{filepath}' not found."
    if not path.is_file():
        logger.warning("Not a file: %s", filepath)
        return f"Error: '{filepath}' is not a file."

    text = path.read_text(encoding="utf-8")
    logger.info("Read %d chars from %s", len(text), filepath)
    return text


def list_files(directory: str = ".") -> str:
    """List files and sub-directories in the given directory."""
    logger.info("list_files called: directory=%s", directory)

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
    return "\n".join(lines) if lines else "(empty directory)"


def write_report(filename: str, content: str) -> str:
    """Save a Markdown report to the output directory."""
    logger.info(
        "write_report called: filename=%s, content_length=%d", filename, len(content)
    )

    if not filename.endswith(".md"):
        filename += ".md"

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    filepath = REPORTS_DIR / filename
    filepath.write_text(content, encoding="utf-8")

    logger.info("Report saved to %s", filepath.resolve())
    return f"Report saved successfully: {filepath.resolve()}"



TOOL_MAP: dict[str, Any] = {
    "web_search": web_search,
    "read_file": read_file,
    "list_files": list_files,
    "read_url": read_url,
    "write_report": write_report,
}


TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the internet using DuckDuckGo. Returns a list of results, "
                "each containing a title, URL, and a short snippet. "
                "Useful for finding relevant pages; use read_url for full page content."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query string.",
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_url",
            "description": (
                "Fetch and extract the main text content from a web page. "
                "Uses trafilatura to strip navigation, ads, and boilerplate. "
                "The result is automatically truncated to fit within context limits."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL of the page to read.",
                    },
                },
                "required": ["url"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read and return the contents of a local file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path to the file to read.",
                    },
                },
                "required": ["filepath"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and sub-directories in the given directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": (
                            "Path to the directory to list (default: current dir)."
                        ),
                        "default": ".",
                    },
                },
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_report",
            "description": "Save a Markdown report to the output directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": (
                            "Name of the file (e.g. 'summary.md'). "
                            "A '.md' extension is appended automatically if missing."
                        ),
                    },
                    "content": {
                        "type": "string",
                        "description": "The Markdown text of the report.",
                    },
                },
                "required": ["filename", "content"],
                "additionalProperties": False,
            },
        },
    },
]
