import os
import re
import chromadb
import fitz
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from groq import Groq

load_dotenv()

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
embedder = SentenceTransformer("all-MiniLM-L6-v2")

chroma_client = chromadb.Client()
collection = chroma_client.get_or_create_collection(name="documents")


def extract_text_from_pdf(file_bytes: bytes) -> str:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text()
        if text.strip():
            pages.append(f"[Page {i + 1}]\n{text.strip()}")
    return "\n\n".join(pages)


def chunk_text(text: str, chunk_size: int = 600, overlap: int = 80) -> list[str]:
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) <= chunk_size:
            current += (" " if current else "") + sentence
        else:
            if current:
                chunks.append(current.strip())
            if chunks:
                current = chunks[-1][-overlap:] + " " + sentence
            else:
                current = sentence

    if current.strip():
        chunks.append(current.strip())

    return chunks


def get_embedding(text: str) -> list[float]:
    return embedder.encode(text).tolist()


def add_document(file_bytes: bytes, filename: str):
    collection.delete(where={"filename": filename})
    text = extract_text_from_pdf(file_bytes)
    chunks = chunk_text(text)
    embeddings = [get_embedding(chunk) for chunk in chunks]
    collection.add(
        documents=chunks,
        embeddings=embeddings,
        ids=[f"{filename}_{i}" for i in range(len(chunks))],
        metadatas=[{"filename": filename} for _ in chunks]
    )
    return len(chunks)


def get_documents() -> list[str]:
    results = collection.get()
    if not results["metadatas"]:
        return []
    filenames = list(set(m["filename"] for m in results["metadatas"]))
    return sorted(filenames)


def query_document(question: str, chat_history: list, filename: str, n_results: int = 5):
    question_embedding = get_embedding(question)
    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=n_results,
        where={"filename": filename}
    )

    chunks = results["documents"][0]
    context = "\n\n---\n\n".join(chunks)

    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful document assistant. Your job is to answer questions "
                "based on the document context provided below.\n\n"
                "Rules:\n"
                "- Answer only from the context. If the answer isn't there, say so clearly.\n"
                "- Keep answers concise and easy to read.\n"
                "- If the context includes page numbers, mention them.\n"
                "- Never make things up.\n\n"
                f"Document context:\n{context}"
            )
        }
    ]

    for msg in chat_history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": question})

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.3,
        max_tokens=1024,
    )

    answer = response.choices[0].message.content
    sources = [chunk[:250] + "..." if len(chunk) > 250 else chunk for chunk in chunks[:2]]
    return {"answer": answer, "sources": sources}