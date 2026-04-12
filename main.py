from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
from rag import add_document, query_document, get_documents

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    role: str
    content: str

class QuestionRequest(BaseModel):
    question: str
    filename: str
    chat_history: Optional[List[Message]] = []

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    file_bytes = await file.read()
    num_chunks = add_document(file_bytes, file.filename)
    return {"message": f"✅ {file.filename} uploaded!", "filename": file.filename}

@app.get("/documents")
def list_documents():
    return {"documents": get_documents()}

@app.post("/ask")
async def ask_question(request: QuestionRequest):
    history = [{"role": m.role, "content": m.content} for m in request.chat_history]
    result = query_document(request.question, history, request.filename)
    return {"answer": result["answer"], "sources": result["sources"]}

@app.get("/")
def root():
    return FileResponse("index.html")

@app.get("/style.css")
def styles():
    return FileResponse("style.css")

@app.get("/app.js")
def scripts():
    return FileResponse("app.js")