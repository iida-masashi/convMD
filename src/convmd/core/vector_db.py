"""ChromaDB and Gemini Embedding integration for Semantic Search."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, cast

import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings

from convmd.core.gemini import get_client, is_configured

logger = logging.getLogger(__name__)


class GeminiEmbeddingFunction(EmbeddingFunction):
    """Custom embedding function for ChromaDB using Google GenAI SDK."""

    def __init__(self) -> None:
        pass

    @staticmethod
    def name() -> str:
        return "convmd_gemini"

    def get_config(self) -> dict[str, Any]:
        return {}

    @staticmethod
    def build_from_config(config: dict[str, Any]) -> GeminiEmbeddingFunction:
        return GeminiEmbeddingFunction()

    def __call__(self, input: Documents) -> Embeddings:
        client = get_client()
        if not client:
            logger.error("Cannot generate embeddings: Gemini API key not set.")
            # Return zero vectors as fallback so ChromaDB doesn't crash completely,
            # though search will be useless.
            return cast(Embeddings, [[0.0] * 3072 for _ in input])

        embeddings: list[list[float]] = []
        try:
            for text in input:
                # Use the new gemini-embedding-2 model
                res = client.models.embed_content(
                    model="gemini-embedding-2",
                    contents=text,
                )
                if res and res.embeddings and len(res.embeddings) > 0:
                     embeddings.append(res.embeddings[0].values)
                else:
                     embeddings.append([0.0] * 3072)
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            return cast(Embeddings, [[0.0] * 3072 for _ in input])

        return cast(Embeddings, embeddings)


def _chunk_text(text: str, max_chunk_size: int = 1000) -> list[str]:
    """Very simple chunking by paragraphs, keeping chunks under max_chunk_size."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current_chunk: list[str] = []
    current_length = 0

    for p in paragraphs:
        if current_length + len(p) > max_chunk_size and current_chunk:
            chunks.append("\n\n".join(current_chunk))
            current_chunk = [p]
            current_length = len(p)
        else:
            current_chunk.append(p)
            current_length += len(p)

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks


class ChromaManager:
    """Manages the local ChromaDB instance and collections."""

    def __init__(self, output_dir: Path):
        self.db_path = output_dir / ".chroma_db"

        # Suppress verbose ChromaDB telemetry logs if any
        logging.getLogger("chromadb").setLevel(logging.WARNING)

        self.client = chromadb.PersistentClient(path=str(self.db_path))
        self.embed_fn = GeminiEmbeddingFunction()

        self.collection = self.client.get_or_create_collection(
            name="convmd_documents",
            embedding_function=self.embed_fn,
        )

    def upsert_document(self, file_path: Path, text: str) -> None:
        """Chunk a document and upsert it to the vector database."""
        if not is_configured():
            return

        # Optional: Extract title from frontmatter or use filename
        title = file_path.name
        original_url = ""

        # Try to parse frontmatter for title and source
        if text.startswith("---"):
            end_idx = text.find("\n---", 3)
            if end_idx != -1:
                frontmatter = text[3:end_idx]
                import re
                url_match = re.search(r'source:\s*"([^"]+)"', frontmatter)
                if url_match:
                    original_url = url_match.group(1)
                title_match = re.search(r'title:\s*"([^"]+)"', frontmatter)
                if title_match:
                    title = title_match.group(1)

        chunks = _chunk_text(text)
        if not chunks:
            return

        # Delete old chunks for this file path if they exist
        # ChromaDB allows filtering by metadata
        try:
            self.collection.delete(where={"source": str(file_path.absolute())})
        except Exception as e:
            # If collection is empty, delete might raise an exception depending on version
            logger.debug(f"Could not delete old chunks for {file_path}: {e}")

        ids = [f"{file_path.name}_{i}" for i in range(len(chunks))]
        metadatas: list[dict[str, str | int | float | bool]] = [
            {"source": str(file_path.absolute()), "title": title, "original_url": original_url, "chunk_index": i}
            for i in range(len(chunks))
        ]

        try:
            self.collection.add(
                documents=chunks,
                metadatas=cast(Any, metadatas),
                ids=ids
            )
            logger.debug(f"Upserted {len(chunks)} chunks for {file_path.name} into ChromaDB")
        except Exception as e:
            logger.error(f"Failed to upsert to ChromaDB: {e}")

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search the vector database for the closest matches to the query."""
        if not is_configured():
            logger.error("Gemini API not configured. Cannot perform semantic search.")
            return []

        if self.collection.count() == 0:
            logger.warning("Vector database is empty. No results found.")
            return []

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=limit
            )

            out = []
            docs_list = results.get("documents")
            if not docs_list:
                return []

            docs = docs_list[0]
            meta_list = results.get("metadatas")
            metadatas = meta_list[0] if meta_list else []
            dist_list = results.get("distances")
            distances = dist_list[0] if dist_list else []

            for i in range(len(docs)):
                out.append({
                    "document": docs[i],
                    "metadata": metadatas[i] if i < len(metadatas) else {},
                    "distance": distances[i] if i < len(distances) else 0.0
                })
            return out
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
