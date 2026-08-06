# DocEngine AI Core

DocEngine AI Core is a high-performance Retrieval-Augmented Generation (RAG) backend engine designed for custom domain knowledge processing and grounded query answering.

It uses FastAPI for REST API serving, ChromaDB for vector similarity search, and Google Gemini models (`gemini-3.5-flash` with automatic fallback to `gemini-3.6-flash` and `gemini-flash-latest`) for response generation.

---

## Key Features

- **Document Processing**: Automatic parsing, text extraction, and chunking for PDF, TXT, MD, JSON, and CSV files.
- **Vector Search**: Contextual text retrieval powered by ChromaDB and Google Gemini embeddings (`gemini-embedding-001`).
- **Grounded AI Generation**: Enforces source document grounding to prevent model hallucination.
- **Robust Exception Handling**: Full error and success feedback across backend endpoints and frontend UI.
- **Minimalist Web UI**: White/light mode user interface with centered layout, document management, and error presentation.

---

## Tech Stack

- **Backend Framework**: FastAPI (Python 3.11+)
- **Generative LLM**: Google Gemini API (`gemini-3.5-flash`, `gemini-3.6-flash`, `gemini-flash-latest`)
- **Vector Store**: ChromaDB
- **Embedding Model**: Google Gemini Embeddings (`gemini-embedding-001`)
- **Data Validation**: Pydantic v2 Schemas

---

## Project Structure

```
docengine-ai-core/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application routes and server setup
│   ├── rag_engine.py    # ChromaDB vector store and Gemini API integration
│   ├── schemas.py       # Pydantic request and response schemas
│   └── static/
│       ├── index.html   # Web UI template
│       ├── style.css    # Clean light mode stylesheet
│       └── app.js       # Client side API handler
├── sample_docs/
│   └── manual.txt       # Sample document for initial engine testing
├── .env.example         # Environment variable template
├── requirements.txt     # Python dependencies
├── setup.sh             # Repository initialization script
└── README.md            # System documentation
```

---

## Installation & Setup

### 1. Prerequisites

Ensure Python 3.11 or higher is installed on your system.

### 2. Set Up Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the root directory and add your Google Gemini API key:

```bash
cp .env.example .env
```

Edit `.env` and insert your key:

```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

---

## Running the Application

Start the FastAPI application using Uvicorn:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Once running, access the application in your browser:

- **Web Interface**: `http://127.0.0.1:8000/`
- **Interactive OpenAPI Documentation**: `http://127.0.0.1:8000/docs`

---

## REST API Specification

### 1. Health Check

- **Endpoint**: `GET /api/v1/health`
- **Description**: Returns system health status and active vector store metrics.
- **Response**:
  ```json
  {
    "status": "healthy",
    "api_key_configured": true,
    "total_documents": 1,
    "total_chunks": 2
  }
  ```

### 2. Upload Document

- **Endpoint**: `POST /api/v1/documents/upload`
- **Description**: Uploads and indexes a PDF or text document into vector memory.
- **Request Body**: `multipart/form-data` with `file` payload.
- **Response**:
  ```json
  {
    "status": "success",
    "document": {
      "doc_id": "doc_a1b2c3d4",
      "filename": "policy.pdf",
      "chunk_count": 5,
      "file_size_bytes": 124000,
      "preview_text": "Sample document content..."
    }
  }
  ```

### 3. List Ingested Documents

- **Endpoint**: `GET /api/v1/documents`
- **Description**: Returns metadata for all currently indexed domain documents.
- **Response**:
  ```json
  {
    "total_documents": 1,
    "total_chunks": 5,
    "documents": [
      {
        "doc_id": "doc_a1b2c3d4",
        "filename": "policy.pdf",
        "chunk_count": 5,
        "file_size_bytes": 124000,
        "preview_text": "Sample document content..."
      }
    ]
  }
  ```

### 4. Delete Specific Document

- **Endpoint**: `DELETE /api/v1/documents/{doc_id}`
- **Description**: Deletes a specific document and its vector chunks.
- **Response**:
  ```json
  {
    "status": "success",
    "message": "Document deleted successfully.",
    "doc_id": "doc_a1b2c3d4"
  }
  ```

### 5. Clear Knowledge Base

- **Endpoint**: `DELETE /api/v1/documents`
- **Description**: Removes all documents from memory and resets the vector store.
- **Response**:
  ```json
  {
    "status": "success",
    "message": "Cleared 1 documents from knowledge store."
  }
  ```

### 6. Execute Grounded Query

- **Endpoint**: `POST /api/v1/query`
- **Description**: Performs vector search and returns a Gemini-generated grounded response with source citations.
- **Request Body**:
  ```json
  {
    "prompt": "What are the core operating metrics?",
    "top_k": 3
  }
  ```
- **Response**:
  ```json
  {
    "query": "What are the core operating metrics?",
    "answer": "Based on the uploaded manual, the target latency is under 600ms.",
    "citations": [
      {
        "doc_id": "doc_a1b2c3d4",
        "filename": "manual.txt",
        "chunk_id": 1,
        "text_snippet": "Target Total Latency: < 600ms"
      }
    ],
    "latency_ms": 320.45,
    "status": "success",
    "model_used": "gemini-3.5-flash"
  }
  ```

---

## License

This project is open-source software built for **IEEE Tech Ignite Summer School**.
