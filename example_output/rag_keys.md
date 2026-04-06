# Key Strategies of RAG

## Summary
Retrieval-Augmented Generation (RAG) works best when you optimize both **retrieval** and **generation grounding**. The core strategies are improving the query, improving retrieval quality, refining retrieved context, and making the overall pipeline efficient and reliable.

## Key Strategies

### 1. Query improvement
- **Query expansion**: rewrite or expand the user query to include related terms.
- **Query decomposition**: break complex questions into smaller sub-questions.
- **Multi-query retrieval**: generate several search variants and merge the results.

### 2. Better retrieval methods
- **Dense retrieval**: use embeddings for semantic similarity.
- **Sparse retrieval**: use keyword-based methods for exact term matching.
- **Hybrid retrieval**: combine dense and sparse retrieval to get both semantic and lexical relevance.

### 3. Efficient indexing and search
- Use **vector indexes** for fast semantic search.
- Use **Approximate Nearest Neighbor (ANN)** methods for scalable retrieval.
- Optimize chunking and metadata so the retriever searches the right units of information.

### 4. Reranking and context selection
- **Reranking**: score retrieved passages again with a stronger model.
- **Context filtering**: keep only the most relevant chunks.
- **Late interaction methods** can improve ranking precision after initial retrieval.

### 5. Retriever optimization
- Train or fine-tune the retriever on domain data.
- Use supervision signals to better align retrieval with answer quality.
- Improve retriever behavior with iterative evaluation.

### 6. Grounded generation
- Ensure the model answers based on retrieved evidence.
- Pass clean, relevant, and well-ordered context to the generator.
- Reduce hallucinations by limiting irrelevant or conflicting passages.

### 7. Feedback and iteration
- Monitor failures such as missed retrievals or noisy context.
- Add memory, caching, or self-improvement loops where useful.
- Continuously evaluate with recall, precision, answer quality, and faithfulness metrics.

## Practical takeaway
The most important RAG strategies are:
1. **Improve the query**
2. **Use strong retrieval (often hybrid)**
3. **Rerank and filter context**
4. **Ground generation in retrieved evidence**
5. **Continuously evaluate and refine the system**

## Sources
- Internal knowledge base search on RAG strategies
- Web search: DuckDuckGo results for "key strategies of RAG retrieval augmented generation"
