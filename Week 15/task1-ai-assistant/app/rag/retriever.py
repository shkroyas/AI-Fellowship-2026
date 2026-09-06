"""
RAG Retriever Module.

Orchestrates the full Retrieval-Augmented Generation pipeline:
document ingestion → chunking → embedding → retrieval → context building.
"""

import logging
from typing import Optional

from ..config import settings
from .chunking import TextChunker
from .embeddings import EmbeddingManager
from .ingestion import Document, DocumentIngester

logger = logging.getLogger(__name__)


class RAGRetriever:
    """
    Complete RAG pipeline orchestrator.

    Manages the end-to-end process of:
    1. Ingesting documents from files or text
    2. Chunking documents into smaller pieces
    3. Embedding and storing chunks in a vector database
    4. Retrieving relevant context for user queries
    """

    def __init__(
        self,
        source_dir: str = "./data/sample_docs",
        persist_dir: Optional[str] = None,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        embedding_model: Optional[str] = None,
        top_k: Optional[int] = None,
    ):
        self.source_dir = source_dir
        self.top_k = top_k or settings.retrieval_top_k

        # Initialize components
        self.ingester = DocumentIngester(source_dir=source_dir)
        self.chunker = TextChunker(
            chunk_size=chunk_size or settings.chunk_size,
            chunk_overlap=chunk_overlap or settings.chunk_overlap,
            strategy="recursive",
        )
        self.embeddings = EmbeddingManager(
            model_name=embedding_model or settings.embedding_model,
            persist_dir=persist_dir or settings.chroma_persist_dir,
        )

        logger.info("RAG Retriever initialized")

    def ingest_documents(self, directory: Optional[str] = None) -> int:
        """Ingest all documents from a directory into the vector database."""
        docs = self.ingester.ingest_directory(directory or self.source_dir)
        total_chunks = 0

        for doc in docs:
            chunks = self.chunker.chunk_text(doc.content, doc.doc_id)
            # Add source metadata to each chunk
            for chunk in chunks:
                chunk.metadata["source"] = doc.source
                chunk.metadata["filename"] = doc.metadata.get("filename", "unknown")
            added = self.embeddings.add_chunks(chunks)
            total_chunks += added

        logger.info(f"Ingested {len(docs)} documents, {total_chunks} total chunks")
        return total_chunks

    def ingest_text(self, text: str, source: str = "direct_input") -> int:
        """Ingest raw text directly into the vector database."""
        doc = self.ingester.ingest_text(text, source)
        chunks = self.chunker.chunk_text(doc.content, doc.doc_id)
        for chunk in chunks:
            chunk.metadata["source"] = source
        return self.embeddings.add_chunks(chunks)

    def retrieve(self, query: str, top_k: Optional[int] = None) -> list[dict]:
        """Retrieve relevant document chunks for a query."""
        k = top_k or self.top_k
        results = self.embeddings.query(query, top_k=k)
        logger.info(f"Retrieved {len(results)} chunks for query: '{query[:50]}...'")
        return results

    def build_context(self, query: str, top_k: Optional[int] = None) -> str:
        """
        Build a context string from retrieved documents for RAG.

        Returns formatted context with source attribution suitable
        for injection into an LLM prompt.
        """
        results = self.retrieve(query, top_k)

        if not results:
            return "No relevant documents found in the knowledge base."

        context_parts = []
        for i, result in enumerate(results, 1):
            source = result["metadata"].get("filename", result["metadata"].get("source", "unknown"))
            score = 1 - result["distance"]  # Convert cosine distance to similarity
            context_parts.append(
                f"[Source {i}: {source} (relevance: {score:.2f})]\n{result['content']}"
            )

        context = "\n\n---\n\n".join(context_parts)
        return context

    def get_stats(self) -> dict:
        """Get pipeline statistics."""
        return {
            "vector_db": self.embeddings.get_stats(),
            "chunk_size": self.chunker.chunk_size,
            "chunk_overlap": self.chunker.chunk_overlap,
            "top_k": self.top_k,
        }
