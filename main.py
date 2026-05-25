"""RagChat -- FastAPI application entrypoint.

A Retrieval-Augmented Generation (RAG) chat app. Users upload PDFs, which
are chunked and embedded into a ChromaDB vector store. Questions are answered
by retrieving the most relevant chunks and passing them as context to the
Groq LLM -- so answers are always grounded in the actual document.

Routes
------
GET  /              Serve the chat UI
GET  /style.css     Stylesheet
GET  /app.js        Frontend JavaScript
POST /upload        Upload and index a PDF
GET  /documents     List all indexed documents
POST /ask           Ask a question about an indexed document
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

import rag
from config import settings

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

load_dotenv()


# ---------------------------------------------------------------------------
# Application lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Log startup and shutdown. The RAG engine initialises at import time."""
    logger.info("RagChat starting up (model: %s).", settings.groq_model)
    yield
    logger.info("RagChat shutting down.")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="RagChat", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------
class Message(BaseModel):
    """A single chat message."""

    role: str = Field(..., description="Either 'user' or 'assistant'.")
    content: str = Field(..., description="Message text.")


class QuestionRequest(BaseModel):
    """Request body for asking a question about an indexed document."""

    question: str = Field(..., min_length=3, description="The user's question.")
    filename: str = Field(..., description="Filename of the document to query.")
    chat_history: list[Message] = Field(
        default_factory=list,
        description="Previous conversation turns for multi-turn context.",
    )


# ---------------------------------------------------------------------------
# Static file routes
# ---------------------------------------------------------------------------
@app.get("/", response_class=FileResponse)
def root() -> FileResponse:
    """Serve the main chat UI."""
    return FileResponse("index.html")


@app.get("/style.css", response_class=FileResponse)
def styles() -> FileResponse:
    """Serve the stylesheet."""
    return FileResponse("style.css")


@app.get("/app.js", response_class=FileResponse)
def scripts() -> FileResponse:
    """Serve the frontend JavaScript."""
    return FileResponse("app.js")


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------
@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)) -> dict:
    """Upload a PDF, extract its text, and index it in ChromaDB.

    The document is chunked, embedded, and stored so it can be queried
    immediately after upload. Re-uploading the same filename replaces the
    previous version.

    Args:
        file: The PDF file to upload (multipart/form-data).

    Returns:
        JSON with a confirmation message, the filename, and chunk count.

    Raises:
        HTTP 400 if the file is not a PDF, is empty, or has no text.
        HTTP 502 if indexing fails unexpectedly.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only PDF files are supported.")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Uploaded file is empty.")

    logger.info("Indexing document: %r (%d bytes)", file.filename, len(file_bytes))

    try:
        num_chunks = rag.add_document(file_bytes, file.filename)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to index %r", file.filename)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Indexing failed: {exc}") from exc

    return {
        "message": f"{file.filename} uploaded and indexed successfully.",
        "filename": file.filename,
        "chunks": num_chunks,
    }


@app.get("/documents")
def list_documents() -> dict:
    """Return a list of all indexed document filenames.

    Returns:
        JSON with a ``documents`` key containing a sorted list of filenames.
    """
    return {"documents": rag.get_documents()}


@app.post("/ask")
async def ask_question(request: QuestionRequest) -> dict:
    """Answer a question using the indexed document as context.

    Embeds the question, retrieves the most relevant chunks from ChromaDB,
    and passes them to the Groq LLM to generate a grounded answer.

    Args:
        request: The question, target filename, and optional chat history.

    Returns:
        JSON with ``answer`` (string) and ``sources`` (list of chunk excerpts).

    Raises:
        HTTP 400 if the question or filename is missing.
        HTTP 502 if the LLM call fails.
    """
    history = [{"role": m.role, "content": m.content} for m in request.chat_history]

    logger.info(
        "Query: %r against %r (history turns: %d)",
        request.question, request.filename, len(history),
    )

    try:
        result = rag.query_document(request.question, history, request.filename)
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected error during query")
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Query failed: {exc}") from exc

    return {"answer": result["answer"], "sources": result["sources"]}


# ---------------------------------------------------------------------------
# Local dev runner
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
    )
