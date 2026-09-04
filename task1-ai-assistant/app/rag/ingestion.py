"""
Document Ingestion Module.

Handles loading documents from various sources (text files, PDFs, markdown)
into a standardized format for processing by the RAG pipeline.
"""

import hashlib
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Document:
    """Represents a loaded document with metadata."""
    content: str
    source: str
    doc_id: str = ""
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.doc_id:
            self.doc_id = hashlib.md5(
                (self.source + self.content[:100]).encode()
            ).hexdigest()


class DocumentIngester:
    """
    Loads and processes documents from various file formats.

    Supported formats:
    - Plain text (.txt)
    - Markdown (.md)
    - PDF (.pdf) - requires PyPDF2
    - JSON (.json)
    """

    SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".json", ".csv"}

    def __init__(self, source_dir: str = "./data/sample_docs"):
        self.source_dir = Path(source_dir)

    def ingest_file(self, file_path: str) -> Optional[Document]:
        """Load a single file and return a Document object."""
        path = Path(file_path)

        if not path.exists():
            logger.error(f"File not found: {file_path}")
            return None

        if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            logger.warning(f"Unsupported file format: {path.suffix}")
            return None

        try:
            content = self._read_file(path)
            if content:
                doc = Document(
                    content=content,
                    source=str(path),
                    metadata={
                        "filename": path.name,
                        "extension": path.suffix,
                        "size_bytes": path.stat().st_size,
                    },
                )
                logger.info(f"Ingested: {path.name} ({len(content)} chars)")
                return doc
        except Exception as e:
            logger.error(f"Error ingesting {file_path}: {e}")
            return None

    def ingest_directory(self, directory: Optional[str] = None) -> list[Document]:
        """Load all supported files from a directory."""
        dir_path = Path(directory) if directory else self.source_dir
        documents = []

        if not dir_path.exists():
            logger.warning(f"Directory not found: {dir_path}")
            return documents

        for file_path in sorted(dir_path.rglob("*")):
            if file_path.is_file() and file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                doc = self.ingest_file(str(file_path))
                if doc:
                    documents.append(doc)

        logger.info(f"Ingested {len(documents)} documents from {dir_path}")
        return documents

    def ingest_text(self, text: str, source: str = "direct_input") -> Document:
        """Create a Document from raw text input."""
        return Document(content=text, source=source)

    def _read_file(self, path: Path) -> Optional[str]:
        """Read content from a file based on its extension."""
        ext = path.suffix.lower()

        if ext in {".txt", ".md"}:
            return path.read_text(encoding="utf-8", errors="replace")

        elif ext == ".pdf":
            return self._read_pdf(path)

        elif ext == ".json":
            import json
            data = json.loads(path.read_text(encoding="utf-8"))
            return json.dumps(data, indent=2)

        elif ext == ".csv":
            return path.read_text(encoding="utf-8", errors="replace")

        return None

    def _read_pdf(self, path: Path) -> Optional[str]:
        """Extract text from a PDF file."""
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(str(path))
            text_parts = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            return "\n\n".join(text_parts)
        except ImportError:
            logger.warning("PyPDF2 not installed. Install with: pip install PyPDF2")
            # Fallback: try reading as text
            try:
                return path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                return None
        except Exception as e:
            logger.error(f"Error reading PDF {path}: {e}")
            return None
