"""RagChat -- Retrieval-Augmented Generation (RAG) engine.

Pipeline
--------
1. Upload  : PDF -> extract text -> chunk -> embed -> store in ChromaDB
2. Query   : question -> embed -> retrieve top-k chunks -> LLM answers with context

The three module-level objects (Groq client, embedder, ChromaDB collection)
are initialised once at import time. They are relatively expensive to create
(the embedder downloads a ~80 MB model on first run), so loading them once
and reusing them across requests is the right approach here.
"""
from __future__ import annotations

import logging
import re

import chromadb
import fitz
from groq import Groq
from sentence_transformers import SentenceTransformer

from config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level singletons
# These are initialised once when the module is first imported.
# ---------------------------------------------------------------------------
logger.info("Loading embedding model: %s", settings.embedding_model)
_embedder = SentenceTransformer(settings.embedding_model)

logger.info("Initialising ChromaDB collection: %s", settings.chroma_collection)
_chroma = chromadb.Client()
_collection = _chroma.get_or_create_collection(name=settings.chroma_collection)

logger.info("Initialising Groq client (model: %s)", settings.groq_model)
_groq = Groq(api_key=settings.groq_api_key)


# ---------------------------------------------------------------------------
# PDF text extraction
# ---------------------------------------------------------------------------
def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract plain text from a PDF, prefixing each page with its number.

    Args:
        file_bytes: Raw PDF bytes (e.g. from an uploaded file).

    Returns:
        A single string with all pages joined by blank lines.
        Pages with no extractable text are skipped.

    Raises:
        ValueError: If the PDF contains no extractable text at all.
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages: list[str] = []
    for i, page in enumerate(doc):
        text = page.get_text().strip()
        if text:
            pages.append(f"[Page {i + 1}]\n{text}")
    doc.close()

    if not pages:
        raise ValueError("No extractable text found. This may be an image-only PDF.")

    return "\n\n".join(pages)


# ---------------------------------------------------------------------------
# Text chunking
# ---------------------------------------------------------------------------
def chunk_text(text: str) -> list[str]:
    """Split text into overlapping chunks suitable for embedding.

    Splits on sentence boundaries to avoid cutting sentences mid-way.
    Each chunk is at most ``settings.chunk_size`` characters. The last
    ``settings.chunk_overlap`` characters of each chunk are repeated at
    the start of the next to preserve context across boundaries.

    Args:
        text: The full document text.

    Returns:
        A list of non-empty text chunks.
    """
    chunk_size = settings.chunk_size
    overlap = settings.chunk_overlap

    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) <= chunk_size:
            current += (" " if current else "") + sentence
        else:
            if current:
                chunks.append(current.strip())
            # Carry forward a tail of the previous chunk for overlap.
            tail = chunks[-1][-overlap:] if chunks else ""
            current = (tail + " " + sentence).strip() if tail else sentence

    if current.strip():
        chunks.append(current.strip())

    return chunks


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------
def get_embedding(text: str) -> list[float]:
    """Return the vector embedding for a single piece of text.

    Args:
        text: Any string to embed.

    Returns:
        A list of floats representing the text in embedding space.
    """
    return _embedder.encode(text).tolist()


# ---------------------------------------------------------------------------
# Document management
# ---------------------------------------------------------------------------
def add_document(file_bytes: bytes, filename: str) -> int:
    """Parse a PDF, chunk it, embed the chunks, and store them in ChromaDB.

    If the document was previously uploaded, its old chunks are deleted first
    so the collection stays in sync with the latest version of the file.

    Args:
        file_bytes: Raw PDF bytes.
        filename:   Original filename, used as a metadata key for filtering.

    Returns:
        The number of chunks stored.

    Raises:
        ValueError: If the PDF contains no extractable text.
    """
    # Remove any existing chunks for this file before re-indexing.
    _collection.delete(where={"filename": filename})

    text = extract_text_from_pdf(file_bytes)
    chunks = chunk_text(text)

    if not chunks:
        raise ValueError("Document produced no usable chunks after splitting.")

    embeddings = [get_embedding(chunk) for chunk in chunks]

    _collection.add(
        documents=chunks,
        embeddings=embeddings,
        ids=[f"{filename}_{i}" for i in range(len(chunks))],
        metadatas=[{"filename": filename} for _ in chunks],
    )

    logger.info("Indexed %d chunks from %r", len(chunks), filename)
    return len(chunks)


def get_documents() -> list[str]:
    """Return a sorted list of all unique filenames in the collection.

    Returns:
        A sorted list of filename strings, or an empty list if the
        collection is empty.
    """
    results = _collection.get()
    if not results["metadatas"]:
        return []
    return sorted({m["filename"] for m in results["metadatas"]})


# ---------------------------------------------------------------------------
# RAG query
# ---------------------------------------------------------------------------
def query_document(question: str, chat_history: list[dict], filename: str) -> dict:
    """Answer a question using retrieved document chunks as context.

    Retrieves the top-k most relevant chunks for the question, builds a
    conversation with the document context in the system prompt, and
    returns the LLM answer together with the source chunks used.

    Args:
        question:     The user's question.
        chat_history: Previous messages as a list of {role, content} dicts.
        filename:     Which uploaded document to query against.

    Returns:
        A dict with keys:
        - ``answer``  : The LLM's response as a string.
        - ``sources`` : Up to 2 source chunk excerpts (truncated to 250 chars).

    Raises:
        RuntimeError: If the LLM call fails.
    """
    question_embedding = get_embedding(question)

    results = _collection.query(
        query_embeddings=[question_embedding],
        n_results=settings.retrieval_top_k,
        where={"filename": filename},
    )

    chunks: list[str] = results["documents"][0]
    context = "\n\n---\n\n".join(chunks)

    messages: list[dict] = [
        {
            "role": "system",
            "content": (
                "You are a helpful document assistant. Answer questions based ONLY "
                "on the document context provided below.\n\n"
                "Rules:\n"
                "- If the answer is not in the context, say so clearly.\n"
                "- Keep answers concise and easy to read.\n"
                "- If the context includes page numbers, mention them.\n"
                "- Never make things up.\n\n"
                f"Document context:\n{context}"
            ),
        }
    ]

    # Append the prior conversation turns.
    for msg in chat_history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": question})

    try:
        response = _groq.chat.completions.create(
            model=settings.groq_model,
            messages=messages,
            temperature=0.3,
            max_tokens=1024,
        )
    except Exception as exc:
        logger.exception("LLM request failed during query")
        raise RuntimeError(f"LLM request failed: {exc}") from exc

    answer = response.choices[0].message.content
    # Return a short excerpt of the top 2 source chunks for transparency.
    sources = [
        (chunk[:250] + "...") if len(chunk) > 250 else chunk
        for chunk in chunks[:2]
    ]

    logger.info("Query answered for %r (chunks used: %d)", filename, len(chunks))
    return {"answer": answer, "sources": sources}
