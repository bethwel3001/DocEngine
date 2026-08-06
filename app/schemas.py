from pydantic import BaseModel, Field
from typing import List, Optional

class DocumentMetadata(BaseModel):
    doc_id: str
    filename: str
    chunk_count: int
    file_size_bytes: int = 0
    preview_text: str = ""

class DocumentListResponse(BaseModel):
    total_documents: int
    total_chunks: int
    documents: List[DocumentMetadata]

class DeleteDocumentResponse(BaseModel):
    status: str
    message: str
    doc_id: Optional[str] = None

class QueryRequest(BaseModel):
    prompt: str = Field(..., example="Summarize the key takeaways from the policy document.")
    top_k: Optional[int] = Field(default=3, ge=1, le=10)

class CitationSource(BaseModel):
    doc_id: str
    filename: str
    chunk_id: int
    text_snippet: str

class QueryResponse(BaseModel):
    query: str
    answer: str
    citations: List[CitationSource]
    latency_ms: float
    status: str
    model_used: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    api_key_configured: bool
    total_documents: int
    total_chunks: int