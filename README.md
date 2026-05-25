# RagChat

> **Upload any PDF. Ask anything. Get answers grounded in the document.**

RagChat is a full Retrieval-Augmented Generation (RAG) app. It chunks your PDF into semantically meaningful pieces, embeds them with a local SentenceTransformers model, stores them in ChromaDB, and uses the Groq LLM to answer questions — citing only what's actually in the document.

![status](https://img.shields.io/badge/status-complete-brightgreen)
![stack](https://img.shields.io/badge/stack-FastAPI%20%C2%B7%20Groq%20%C2%B7%20ChromaDB%20%C2%B7%20SentenceTransformers-blueviolet)

## How it works

```
PDF upload
   │
   ▼
Extract text (PyMuPDF)
   │
   ▼
Split into overlapping chunks (~600 chars)
   │
   ▼
Embed each chunk (all-MiniLM-L6-v2, runs locally)
   │
   ▼
Store in ChromaDB (in-memory vector store)
   │
   ▼
User asks a question
   │
   ▼
Embed question → retrieve top-5 matching chunks
   │
   ▼
Groq LLM answers using retrieved chunks as context
```

## Stack

- **FastAPI** + Uvicorn — Python web framework
- **Groq** (`llama-3.3-70b-versatile`) — LLM for answer generation
- **ChromaDB** — in-memory vector store for chunk retrieval
- **SentenceTransformers** (`all-MiniLM-L6-v2`) — local text embeddings (no API cost)
- **PyMuPDF** — PDF text extraction
- **pydantic-settings** — typed configuration from environment variables
- **Vanilla JS** — frontend, no build step

## Project layout

```
RagChat/
├── main.py           FastAPI app -- routes, error handling
├── rag.py            RAG engine -- chunking, embedding, retrieval, LLM query
├── config.py         Typed settings (pydantic-settings)
├── index.html        Chat UI
├── style.css         Styles
├── app.js            Frontend JavaScript
├── requirements.txt
├── Procfile
├── .env.example
├── .gitignore
└── README.md
```

## Quick start

### 1. Get a Groq API key
Sign up for free at [console.groq.com](https://console.groq.com/keys).

### 2. Install

```bash
cd RagChat
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env    # Windows
# cp .env.example .env    # macOS / Linux
```

Open `.env` and paste your Groq API key.

> **Note:** On first run, SentenceTransformers will download the `all-MiniLM-L6-v2` model (~80 MB). This only happens once.

### 3. Run

```bash
uvicorn main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000), upload a PDF, and start chatting.

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Chat UI |
| `POST` | `/upload` | Upload and index a PDF |
| `GET` | `/documents` | List all indexed documents |
| `POST` | `/ask` | Ask a question about a document |

### `POST /ask`

```json
{
  "question": "What are the main conclusions?",
  "filename": "report.pdf",
  "chat_history": [
    {"role": "user", "content": "Who wrote this?"},
    {"role": "assistant", "content": "The document was written by..."}
  ]
}
```

## Configuration

All settings can be overridden via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | — | **Required.** Groq API key |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | LLM model |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | SentenceTransformers model |
| `RETRIEVAL_TOP_K` | `5` | Chunks retrieved per query |
| `CHUNK_SIZE` | `600` | Max chars per chunk |
| `CHUNK_OVERLAP` | `80` | Overlap chars between chunks |

## Deployment

The `Procfile` works on Render, Railway, and Fly.io.
Set `GROQ_API_KEY` in your host's environment dashboard.

> **Note:** ChromaDB runs in-memory by default, so indexed documents are lost on restart. For persistent storage, swap `chromadb.Client()` for `chromadb.PersistentClient(path="./chroma_db")` in `rag.py`.

## License

MIT — built by Martin Genov.
