# 📄 RAG Chat App — Ask Questions About Any PDF

RAG Chat App lets you upload any PDF and have a conversation with it. Ask questions, get accurate answers, and see exactly which parts of the document the answer came from — all powered by a full RAG (Retrieval-Augmented Generation) pipeline built from scratch.

---

## ✨ Features

- 📤 **Upload any PDF** — drag and drop or click to upload
- 💬 **Chat with your document** — ask questions in natural language
- 🔍 **Semantic search** — finds the most relevant chunks using vector embeddings, not just keyword matching
- 📌 **Source references** — every answer shows the exact passages it was based on
- 🧠 **Multi-turn conversation** — remembers the chat history for follow-up questions
- 📚 **Multiple documents** — upload and switch between several PDFs in one session
- ⚡ **Fast answers** — powered by Llama 3.3 70B via Groq

---

## 🖥️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI |
| PDF Parsing | PyMuPDF (fitz) |
| Embeddings | Sentence Transformers (all-MiniLM-L6-v2) |
| Vector Database | ChromaDB |
| AI Model | Llama 3.3 70B (via Groq API) |
| Frontend | HTML, CSS, JavaScript |
| Server | Uvicorn |

---

## 🧠 How the RAG Pipeline Works

```
PDF Upload
    ↓
Extract text (PyMuPDF) — page by page
    ↓
Split into overlapping chunks (600 chars, 80 char overlap)
    ↓
Embed each chunk (Sentence Transformers all-MiniLM-L6-v2)
    ↓
Store embeddings in ChromaDB
    ↓
User asks a question
    ↓
Embed the question → find top-5 most similar chunks
    ↓
Send chunks + chat history as context to Llama 3.3 70B
    ↓
Return answer + source passages
```

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/Martin-gif-maker/rag-chat-app
cd rag-chat-app
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> ⚠️ First run will download the Sentence Transformers model (~90MB). This only happens once.

### 4. Set up your API key

Create a `.env` file in the root folder:

```
GROQ_API_KEY=your_groq_api_key_here
```

Get a free API key at [console.groq.com](https://console.groq.com)

### 5. Run the app

```bash
uvicorn main:app --reload
```

Then open your browser and go to: **http://localhost:8000**

---

## 📖 How to Use

1. **Upload a PDF** — drag and drop into the sidebar or click "Browse"
2. **Select the document** from the list on the left
3. **Type your question** in the chat input and press Enter or click Send
4. **Read the answer** — the app also shows the source passages it used
5. **Ask follow-up questions** — the app remembers the conversation

---

## 📁 Project Structure

```
rag-chat-app/
├── main.py              # FastAPI routes
├── rag.py               # Full RAG pipeline (parsing, chunking, embedding, querying)
├── index.html           # Frontend UI
├── style.css            # Dark theme styles
├── app.js               # Frontend logic
├── requirements.txt     # Python dependencies
└── Procfile             # Deployment config
```

---

## 🔑 Environment Variables

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | Your Groq API key (required) |

---

## 📄 License

MIT License — free to use and modify.

---

Made by [Martin Genov](https://github.com/Martin-gif-maker)
