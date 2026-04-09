import os
import glob
import logging
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import ContextualCompressionRetriever
from langchain_classic.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder

load_dotenv()

logger = logging.getLogger(__name__)


# ── Result schemas ──────────────────────────────────────────────────────


class ChunkResult(BaseModel):
    """Structured representation of a single retrieved chunk."""

    chunk_id: str
    doc_id: str
    chunk_index: int
    content: str
    page: Optional[int] = None
    score: Optional[float] = None
    source: Optional[str] = None


class ExpandedContextResult(BaseModel):
    """A target chunk together with its surrounding neighbors."""

    target: ChunkResult
    before: list[ChunkResult]
    after: list[ChunkResult]


# ── Retrieval Service ───────────────────────────────────────────────────


class RetrievalService:
    """
    Hybrid RAG retrieval backend backed by FAISS + BM25 + cross-encoder
    reranking.  Accepts a directory path and loads **all** PDF files found
    inside it.  Exposes two methods designed to be wrapped as LangGraph
    tools for a search-agent:

        rag_search(query)                – hybrid retrieval
        expand_chunk_context(chunk_id)   – neighbor lookup
    """

    def __init__(
        self,
        pdf_dir: str,
        index_path: str = "./faiss_index",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        embedding_model: str = "text-embedding-3-large",
        reranker_model_name: str = "BAAI/bge-reranker-base",
        bm25_k: int = 5,
        vector_k: int = 10,
        reranker_top_n: int = 3,
        bm25_weight: float = 0.4,
        vector_weight: float = 0.6,
    ):
        self.pdf_dir = pdf_dir
        self.index_path = index_path
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.embedding_model = embedding_model
        self.reranker_model_name = reranker_model_name
        self.bm25_k = bm25_k
        self.vector_k = vector_k
        self.reranker_top_n = reranker_top_n
        self.bm25_weight = bm25_weight
        self.vector_weight = vector_weight

        self._chunks: list = []
        self._chunk_registry: dict[str, ChunkResult] = {}
        self._chunks_by_doc: dict[str, list[ChunkResult]] = {}
        self._reranking_retriever: Optional[ContextualCompressionRetriever] = None

        self._initialize()

    # ── Initialization ───────────────────────────────────────────────

    def _discover_pdfs(self) -> list[str]:
        """Return sorted list of PDF file paths found in ``self.pdf_dir``."""
        pattern = os.path.join(self.pdf_dir, "*.pdf")
        pdf_files = sorted(glob.glob(pattern))
        if not pdf_files:
            raise FileNotFoundError(
                f"No PDF files found in '{self.pdf_dir}'"
            )
        logger.info("Discovered %d PDF(s) in %s", len(pdf_files), self.pdf_dir)
        return pdf_files

    def _initialize(self) -> None:
        pdf_files = self._discover_pdfs()

        for pdf_path in pdf_files:
            self._chunks.extend(self._load_and_chunk(pdf_path))

        self._build_chunk_registry()
        self._build_retrievers()

    def _load_and_chunk(self, pdf_path: str) -> list:
        """Load a single PDF via PyPDFLoader and split with metadata preserved.

        ``split_documents`` keeps the per-page metadata that PyPDFLoader
        attaches, so every chunk knows its source page.
        """
        doc_id = os.path.splitext(os.path.basename(pdf_path))[0]

        logger.info("Loading PDF: %s", pdf_path)
        pages = PyPDFLoader(pdf_path).load()
        logger.info("Loaded %d pages from %s", len(pages), pdf_path)

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

        raw_chunks = splitter.split_documents(pages)
        total = len(raw_chunks)
        logger.info("Created %d chunks from %s (size=%d, overlap=%d)",
                     total, pdf_path, self.chunk_size, self.chunk_overlap)

        for idx, chunk in enumerate(raw_chunks):
            chunk.metadata["doc_id"] = doc_id
            chunk.metadata["chunk_index"] = idx
            chunk.metadata["chunk_id"] = f"{doc_id}::chunk_{idx}"
            chunk.metadata["total_chunks"] = total
            chunk.metadata.setdefault("source", pdf_path)

        return raw_chunks

    def _build_chunk_registry(self) -> None:
        """Index every chunk for O(1) lookup and ordered neighbor access."""
        self._chunk_registry.clear()
        self._chunks_by_doc.clear()

        for chunk in self._chunks:
            meta = chunk.metadata
            entry = ChunkResult(
                chunk_id=meta["chunk_id"],
                doc_id=meta["doc_id"],
                chunk_index=meta["chunk_index"],
                content=chunk.page_content,
                page=meta.get("page"),
                source=meta.get("source"),
            )
            self._chunk_registry[entry.chunk_id] = entry
            self._chunks_by_doc.setdefault(entry.doc_id, []).append(entry)

        for doc_id in self._chunks_by_doc:
            self._chunks_by_doc[doc_id].sort(key=lambda c: c.chunk_index)

        logger.info("Chunk registry: %d chunks, %d documents",
                     len(self._chunk_registry), len(self._chunks_by_doc))

    def _build_retrievers(self) -> None:
        """Wire up FAISS, BM25, ensemble, and cross-encoder reranker."""
        embeddings = OpenAIEmbeddings(
            model=self.embedding_model,
            check_embedding_ctx_length=False,
        )
        vectorstore = self._load_or_create_vectorstore(embeddings)

        bm25_retriever = BM25Retriever.from_documents(self._chunks)
        bm25_retriever.k = self.bm25_k

        vector_retriever = vectorstore.as_retriever(
            search_kwargs={"k": self.vector_k},
        )

        ensemble_retriever = EnsembleRetriever(
            retrievers=[bm25_retriever, vector_retriever],
            weights=[self.bm25_weight, self.vector_weight],
        )

        logger.info("Loading reranker model: %s", self.reranker_model_name)
        reranker_model = HuggingFaceCrossEncoder(
            model_name=self.reranker_model_name,
        )
        compressor = CrossEncoderReranker(
            model=reranker_model,
            top_n=self.reranker_top_n,
        )

        self._reranking_retriever = ContextualCompressionRetriever(
            base_compressor=compressor,
            base_retriever=ensemble_retriever,
        )

    def _load_or_create_vectorstore(self, embeddings) -> FAISS:
        faiss_file = os.path.join(self.index_path, "index.faiss")
        pkl_file = os.path.join(self.index_path, "index.pkl")

        if os.path.isfile(faiss_file) and os.path.isfile(pkl_file):
            logger.info("Loading existing FAISS index from %s", self.index_path)
            return FAISS.load_local(
                self.index_path,
                embeddings,
                allow_dangerous_deserialization=True,
            )

        logger.info("Building new FAISS index (%s not found) …", self.index_path)
        vectorstore = FAISS.from_documents(self._chunks, embeddings)
        vectorstore.save_local(self.index_path)
        logger.info("FAISS index saved to %s", self.index_path)
        return vectorstore

    # ── Public API ───────────────────────────────────────────────────

    def rag_search(self, query: str) -> list[ChunkResult]:
        """Run the full hybrid retrieval pipeline and return structured
        results suitable for consumption by a search-agent.

        The pipeline: BM25 ∪ FAISS → ensemble → cross-encoder reranker.
        """
        docs = self._reranking_retriever.invoke(query)

        results: list[ChunkResult] = []
        for doc in docs:
            chunk_id = doc.metadata.get("chunk_id")

            if chunk_id and chunk_id in self._chunk_registry:
                entry = self._chunk_registry[chunk_id].model_copy()
                entry.score = doc.metadata.get("relevance_score")
                results.append(entry)
            else:
                results.append(ChunkResult(
                    chunk_id=doc.metadata.get("chunk_id", "unknown"),
                    doc_id=doc.metadata.get("doc_id", "unknown"),
                    chunk_index=doc.metadata.get("chunk_index", -1),
                    content=doc.page_content,
                    page=doc.metadata.get("page"),
                    score=doc.metadata.get("relevance_score"),
                    source=doc.metadata.get("source"),
                ))

        return results

    def expand_chunk_context(
        self,
        chunk_id: str,
        before: int = 1,
        after: int = 1,
    ) -> ExpandedContextResult:
        """Return the target chunk together with *before* preceding and
        *after* following chunks from the same document.

        Preserves document order so the search-agent can read surrounding
        context when a retrieved chunk is cut off mid-sentence.
        """
        if chunk_id not in self._chunk_registry:
            raise ValueError(f"Unknown chunk_id: {chunk_id!r}")

        target = self._chunk_registry[chunk_id]
        doc_chunks = self._chunks_by_doc[target.doc_id]
        idx = target.chunk_index

        before_chunks = [
            c for c in doc_chunks
            if idx - before <= c.chunk_index < idx
        ]
        after_chunks = [
            c for c in doc_chunks
            if idx < c.chunk_index <= idx + after
        ]

        return ExpandedContextResult(
            target=target,
            before=before_chunks,
            after=after_chunks,
        )
