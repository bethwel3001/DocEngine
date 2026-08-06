import os
from fastapi import FastAPI, HTTPException, UploadFile, File, Path
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.schemas import (
    QueryRequest,
    QueryResponse,
    DocumentListResponse,
    DeleteDocumentResponse,
    HealthResponse
)
from app.rag_engine import RAGEngine

load_dotenv()

app = FastAPI(
    title="DocEngine AI Core API",
    description="Enterprise NotebookLM-style RAG Engine & REST API",
    version="2.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static directory path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Instantiate RAG Engine with error capture
rag_engine_instance = None
rag_init_error = None

try:
    rag_engine_instance = RAGEngine()
    
    # Auto-ingest default sample doc if present
    sample_path = os.path.join(os.path.dirname(BASE_DIR), "sample_docs", "manual.txt")
    if os.path.exists(sample_path):
        with open(sample_path, "rb") as f:
            rag_engine_instance.ingest_document(f.read(), filename="system_manual.txt")
except Exception as e:
    rag_init_error = str(e)


def get_rag():
    if not rag_engine_instance:
        raise HTTPException(
            status_code=500,
            detail=f"DocEngine initialization error: {rag_init_error or 'GEMINI_API_KEY is missing or invalid in .env'}"
        )
    return rag_engine_instance


@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check():
    """Engine health status and active vector memory metrics."""
    api_configured = bool(os.getenv("GEMINI_API_KEY"))
    if rag_engine_instance:
        docs = rag_engine_instance.list_documents()
        total_chunks = rag_engine_instance.vector_store.count()
        total_docs = len(docs)
    else:
        total_chunks = 0
        total_docs = 0

    return HealthResponse(
        status="healthy" if rag_engine_instance else "error",
        api_key_configured=api_configured,
        total_documents=total_docs,
        total_chunks=total_chunks
    )


@app.post("/api/v1/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """Uploads, chunks, and indexes custom PDF or TXT domain documents into vector memory."""
    rag = get_rag()
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided in upload request.")

    try:
        contents = await file.read()
        if len(contents) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty (0 bytes).")
            
        metadata = rag.ingest_document(file_bytes=contents, filename=file.filename)
        return {"status": "success", "document": metadata}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")


@app.get("/api/v1/documents", response_model=DocumentListResponse)
async def list_documents():
    """Lists all active source documents currently powering vector memory."""
    rag = get_rag()
    docs = rag.list_documents()
    total_chunks = rag.vector_store.count()
    return DocumentListResponse(
        total_documents=len(docs),
        total_chunks=total_chunks,
        documents=docs
    )


@app.delete("/api/v1/documents/{doc_id}", response_model=DeleteDocumentResponse)
async def delete_document(doc_id: str = Path(..., description="The unique document ID")):
    """Deletes a specific document from vector memory and doc registry."""
    rag = get_rag()
    success = rag.delete_document(doc_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Document ID '{doc_id}' not found.")
    
    return DeleteDocumentResponse(
        status="success",
        message="Document deleted successfully.",
        doc_id=doc_id
    )


@app.delete("/api/v1/documents", response_model=DeleteDocumentResponse)
async def clear_all_documents():
    """Clears all ingested documents from vector store and memory."""
    rag = get_rag()
    count = rag.clear_all_documents()
    return DeleteDocumentResponse(
        status="success",
        message=f"Cleared {count} documents from knowledge store."
    )


@app.post("/api/v1/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """Executes grounded synthesis query against uploaded domain documents."""
    rag = get_rag()
    
    if not request.prompt or not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Query prompt cannot be empty.")

    try:
        result = rag.query(user_query=request.prompt.strip(), top_k=request.top_k or 3)
        return QueryResponse(
            query=request.prompt,
            answer=result["answer"],
            citations=result["citations"],
            latency_ms=result["latency_ms"],
            status="success",
            model_used=result["model_used"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def serve_workspace():
    """Serves the centered, modern web workspace UI."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse({"status": "active", "message": "DocEngine AI Core API running. Static UI template missing."})