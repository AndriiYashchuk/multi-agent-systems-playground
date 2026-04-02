import logging
from typing import Optional

from langchain_core.tools import tool

from config import settings

logger = logging.getLogger(__name__)

_retrieval_service: Optional["RetrievalService"] = None


def _get_retrieval_service():
    global _retrieval_service
    if _retrieval_service is None:
        from agentic_rag import RetrievalService
        logger.info("Initializing RetrievalService with dir=%s", settings.knowledge_data_dir)
        _retrieval_service = RetrievalService(pdf_dir=settings.knowledge_data_dir)
    return _retrieval_service


def _truncate(text: str, max_chars: int, label: str = "content") -> str:
    if len(text) <= max_chars:
        return text
    logger.info("Truncating %s from %d to %d chars", label, len(text), max_chars)
    return text[:max_chars] + f"\n\n... [truncated — showed {max_chars} of {len(text)} chars of {label}]"


@tool
def search(query: str) -> str:
    """Search the internal knowledge base using hybrid retrieval
    (BM25 + vector similarity + cross-encoder reranking).

    Returns the top matching chunks with their IDs, page numbers, and content.
    Use the returned chunk_id values with expand_chunk_context to get
    surrounding text when a chunk seems cut off or you need more detail.

    Args:
        query: Natural-language search query.
    """
    logger.info("search called: query=%r", query)

    service = _get_retrieval_service()
    results = service.rag_search(query)

    if not results:
        return "No relevant chunks found in the knowledge base."

    logger.info("search returned %d results for query=%r", len(results), query)

    parts: list[str] = []
    for r in results:
        header = f"[chunk_id={r.chunk_id} | page={r.page} | score={r.score}]"
        parts.append(f"{header}\n{r.content}")

    output = "\n\n---\n\n".join(parts)
    return _truncate(output, settings.max_search_content_length, label="search results")


@tool
def expand_chunk_context(chunk_id: str, before: int = 1, after: int = 1) -> str:
    """Retrieve a chunk together with its neighboring chunks from the same
    document to get broader context.

    Use this after a search call when a returned chunk seems incomplete or
    you need more surrounding text to fully understand the content.

    Args:
        chunk_id: The chunk identifier returned by the search tool
                  (e.g. 'rent_ag::chunk_12').
        before:   Number of preceding chunks to include (default 1).
        after:    Number of following chunks to include (default 1).
    """
    logger.info("expand_chunk_context called: chunk_id=%r, before=%d, after=%d",
                chunk_id, before, after)

    service = _get_retrieval_service()
    try:
        result = service.expand_chunk_context(chunk_id, before=before, after=after)
    except ValueError as exc:
        return f"Error: {exc}"

    sections: list[str] = []

    for chunk in result.before:
        sections.append(f"[BEFORE | chunk_id={chunk.chunk_id} | page={chunk.page}]\n{chunk.content}")

    sections.append(f"[TARGET | chunk_id={result.target.chunk_id} | page={result.target.page}]\n{result.target.content}")

    for chunk in result.after:
        sections.append(f"[AFTER | chunk_id={chunk.chunk_id} | page={chunk.page}]\n{chunk.content}")

    output = "\n\n---\n\n".join(sections)
    return _truncate(output, settings.max_search_content_length, label="expanded context")
