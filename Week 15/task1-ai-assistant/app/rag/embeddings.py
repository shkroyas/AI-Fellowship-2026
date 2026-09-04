"""
Embedding Manager Module.

Handles vectorization of text chunks using sentence-transformers
and stores them in a ChromaDB vector database.
"""

import logging
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from .chunking import TextChunk

logger = logging.getLogger(__name__)


class EmbeddingManager:
    """
    Manages text embeddings and vector storage.

    Uses sentence-transformers for embedding generation and
    ChromaDB for persistent vector storage and retrieval.
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        persist_dir: str = "./data/chroma_db",
        collection_name: str = "documents",
    ):
        self.model_name = model_name
        self.persist_dir = persist_dir
        self.collection_name = collection_name

        # Initialize embedding model
        logger.info(f"Loading embedding model: {model_name}")
        self.embedding_model = SentenceTransformer(model_name)

        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        # Get or create collection
        self.collection = self.chroma_client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        logger.info(
            f"ChromaDB collection '{collection_name}' initialized "
            f"with {self.collection.count()} existing documents"
        )

    def embed_text(self, text: str) -> list[float]:
        """Generate embedding vector for a single text."""
        return self.embedding_model.encode(text).tolist()

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for multiple texts (batch)."""
        return self.embedding_model.encode(texts).tolist()

    def add_chunks(self, chunks: list[TextChunk]) -> int:
        """Add text chunks to the vector database."""
        if not chunks:
            return 0

        ids = [chunk.chunk_id for chunk in chunks]
        documents = [chunk.content for chunk in chunks]
        metadatas = [
            {
                "doc_id": chunk.doc_id,
                "chunk_index": chunk.chunk_index,
                **{k: str(v) for k, v in chunk.metadata.items()},
            }
            for chunk in chunks
        ]

        # Generate embeddings
        embeddings = self.embed_texts(documents)

        # Upsert to ChromaDB
        self.collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        logger.info(f"Added {len(chunks)} chunks to vector database")
        return len(chunks)

    def query(
        self,
        query_text: str,
        top_k: int = 5,
        where: Optional[dict] = None,
    ) -> list[dict]:
        """
        Query the vector database for similar documents.

        Returns a list of dicts with 'content', 'metadata', and 'distance'.
        """
        query_embedding = self.embed_text(query_text)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        output = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                output.append({
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0.0,
                })

        return output

    def delete_collection(self):
        """Delete the entire collection."""
        self.chroma_client.delete_collection(self.collection_name)
        logger.info(f"Deleted collection: {self.collection_name}")

    def get_stats(self) -> dict:
        """Get statistics about the vector database."""
        return {
            "collection_name": self.collection_name,
            "document_count": self.collection.count(),
            "embedding_model": self.model_name,
            "persist_dir": self.persist_dir,
        }
