import os
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
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
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
    context = "\n\n".join(chunks)

    messages = [
        {
            "role": "system",
            "content": f"You are a helpful assistant. Answer questions based ONLY on the provided context. If the answer is not in the context, say 'I couldn't find that in the document.'\n\nContext:\n{context}"
        }
    ]

    for msg in chat_history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": question})

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages
    )

    answer = response.choices[0].message.content
    sources = [chunk[:200] + "..." for chunk in chunks[:2]]
    return {"answer": answer, "sources": sources}