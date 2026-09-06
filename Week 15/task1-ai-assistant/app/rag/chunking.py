"""
Text Chunking Module.

Implements multiple chunking strategies for splitting documents
into smaller, semantically meaningful chunks for vectorization.
"""

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """Represents a chunk of text with its metadata."""
    content: str
    chunk_id: str
    doc_id: str
    chunk_index: int
    metadata: dict = field(default_factory=dict)


class TextChunker:
    """
    Splits documents into chunks using configurable strategies.

    Strategies:
    - fixed: Split by fixed character count with overlap
    - sentence: Split by sentences, respecting boundaries
    - recursive: Recursively split using multiple separators
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        strategy: str = "recursive",
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.strategy = strategy

        # Recursive separators in order of priority
        self._separators = ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " "]

    def chunk_text(self, text: str, doc_id: str = "") -> list[TextChunk]:
        """Split text into chunks using the configured strategy."""
        if not text.strip():
            return []

        if self.strategy == "fixed":
            raw_chunks = self._fixed_chunk(text)
        elif self.strategy == "sentence":
            raw_chunks = self._sentence_chunk(text)
        elif self.strategy == "recursive":
            raw_chunks = self._recursive_chunk(text)
        else:
            logger.warning(f"Unknown strategy '{self.strategy}', using recursive")
            raw_chunks = self._recursive_chunk(text)

        chunks = []
        for i, content in enumerate(raw_chunks):
            chunk = TextChunk(
                content=content.strip(),
                chunk_id=f"{doc_id}_chunk_{i}",
                doc_id=doc_id,
                chunk_index=i,
                metadata={
                    "char_count": len(content),
                    "word_count": len(content.split()),
                    "strategy": self.strategy,
                },
            )
            chunks.append(chunk)

        logger.info(f"Created {len(chunks)} chunks from document {doc_id}")
        return chunks

    def _fixed_chunk(self, text: str) -> list[str]:
        """Split text into fixed-size chunks with overlap."""
        chunks = []
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk)
            start = end - self.chunk_overlap
        return chunks

    def _sentence_chunk(self, text: str) -> list[str]:
        """Split text by sentences, grouping into chunks."""
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)

        chunks = []
        current_chunk = []
        current_length = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            if current_length + len(sentence) > self.chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                # Keep overlap by retaining some sentences
                overlap_text = " ".join(current_chunk)
                if len(overlap_text) > self.chunk_overlap:
                    # Keep the last part for overlap
                    overlap_sentences = []
                    ol = 0
                    for s in reversed(current_chunk):
                        if ol + len(s) < self.chunk_overlap:
                            overlap_sentences.insert(0, s)
                            ol += len(s)
                        else:
                            break
                    current_chunk = overlap_sentences
                    current_length = sum(len(s) for s in current_chunk)
                else:
                    current_chunk = []
                    current_length = 0

            current_chunk.append(sentence)
            current_length += len(sentence)

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    def _recursive_chunk(self, text: str) -> list[str]:
        """Recursively split text using multiple separators."""
        return self._recursive_split(text, self._separators)

    def _recursive_split(self, text: str, separators: list[str]) -> list[str]:
        """Internal recursive splitting implementation."""
        if len(text) <= self.chunk_size:
            return [text] if text.strip() else []

        # Try each separator in order
        for sep in separators:
            if sep in text:
                splits = text.split(sep)
                chunks = []
                current_chunk = ""

                for split in splits:
                    test_chunk = current_chunk + sep + split if current_chunk else split

                    if len(test_chunk) <= self.chunk_size:
                        current_chunk = test_chunk
                    else:
                        if current_chunk.strip():
                            chunks.append(current_chunk)
                        current_chunk = split

                if current_chunk.strip():
                    chunks.append(current_chunk)

                # Recursively split any chunks that are still too large
                result = []
                remaining_seps = separators[separators.index(sep) + 1:]
                for chunk in chunks:
                    if len(chunk) > self.chunk_size and remaining_seps:
                        result.extend(self._recursive_split(chunk, remaining_seps))
                    else:
                        result.append(chunk)

                return result

        # If no separator works, fall back to fixed chunking
        return self._fixed_chunk(text)
