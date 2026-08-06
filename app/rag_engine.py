import os
import uuid
import io
import time
import pypdf
import chromadb
from chromadb import EmbeddingFunction, Documents, Embeddings
from google import genai
from google.genai import types
from langchain_text_splitters import RecursiveCharacterTextSplitter


class GeminiEmbeddingFunction(EmbeddingFunction):
    """Custom ChromaDB Embedding Function using Google Gemini embedding-001."""
    def __init__(self, client: genai.Client):
        self.client = client

    def __call__(self, input: Documents) -> Embeddings:
        if not input:
            return []
        try:
            # Generate embeddings via Google GenAI SDK
            embeddings_list = []
            # Process in small batches if necessary
            for text in input:
                response = self.client.models.embed_content(
                    model="gemini-embedding-001",
                    contents=text
                )
                embeddings_list.append(response.embeddings[0].values)
            return embeddings_list
        except Exception as e:
            # Fallback warning if embedding call fails
            raise RuntimeError(f"Gemini Embedding Service error: {str(e)}")


class RAGEngine:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required.")

        self.client = genai.Client(api_key=self.api_key)
        self.chroma_client = chromadb.Client()
        self.collection_name = "docengine_domain_store"

        # Persistent document registry tracking active domain sources
        self.doc_registry = {}

        # Reset or initialize collection cleanly with custom embedding function
        existing_collections = [c.name for c in self.chroma_client.list_collections()]
        if self.collection_name in existing_collections:
            self.chroma_client.delete_collection(self.collection_name)

        try:
            self.embedding_fn = GeminiEmbeddingFunction(self.client)
            self.vector_store = self.chroma_client.create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_fn
            )
        except Exception:
            # Fallback to default ChromaDB collection if custom embedding setup runs into environment issue
            self.vector_store = self.chroma_client.create_collection(
                name=self.collection_name
            )

    def extract_text_from_file(self, file_bytes: bytes, filename: str) -> str:
        """Parses PDF, Markdown, JSON, CSV, or raw text files into clean string content."""
        ext = filename.lower().split('.')[-1] if '.' in filename else ""

        if ext == "pdf":
            try:
                pdf_reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                text_parts = []
                for idx, page in enumerate(pdf_reader.pages):
                    extracted = page.extract_text()
                    if extracted:
                        text_parts.append(extracted)
                return "\n\n".join(text_parts)
            except Exception as e:
                raise ValueError(f"Failed to parse PDF document '{filename}': {str(e)}")
        else:
            try:
                return file_bytes.decode("utf-8", errors="ignore")
            except Exception as e:
                raise ValueError(f"Failed to read text file '{filename}': {str(e)}")

    def ingest_document(self, file_bytes: bytes, filename: str) -> dict:
        """Ingests, chunks, and indexes custom domain files into vector memory."""
        extracted_text = self.extract_text_from_file(file_bytes, filename)
        cleaned_text = extracted_text.strip()
        
        if not cleaned_text:
            raise ValueError(f"Document '{filename}' appears empty or contains no extractable text.")

        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        chunks = splitter.split_text(cleaned_text)

        if not chunks:
            raise ValueError(f"Document '{filename}' produced 0 text chunks during processing.")

        doc_id = f"doc_{str(uuid.uuid4())[:8]}"
        ids = [f"{doc_id}_chunk_{i+1}" for i in range(len(chunks))]
        metadatas = [
            {
                "doc_id": doc_id,
                "filename": filename,
                "chunk_id": i + 1,
                "total_chunks": len(chunks)
            }
            for i in range(len(chunks))
        ]

        self.vector_store.add(
            documents=chunks,
            ids=ids,
            metadatas=metadatas
        )

        preview = cleaned_text[:120].replace('\n', ' ') + ("..." if len(cleaned_text) > 120 else "")
        doc_entry = {
            "doc_id": doc_id,
            "filename": filename,
            "chunk_count": len(chunks),
            "file_size_bytes": len(file_bytes),
            "preview_text": preview,
            "chunk_ids": ids
        }

        self.doc_registry[doc_id] = doc_entry
        return doc_entry

    def list_documents(self) -> list[dict]:
        """Returns all currently ingested domain documents."""
        return list(self.doc_registry.values())

    def delete_document(self, doc_id: str) -> bool:
        """Deletes a specific document and its chunks from ChromaDB and registry."""
        if doc_id not in self.doc_registry:
            return False

        doc_info = self.doc_registry[doc_id]
        chunk_ids = doc_info.get("chunk_ids", [])
        
        if chunk_ids:
            try:
                self.vector_store.delete(ids=chunk_ids)
            except Exception:
                pass

        del self.doc_registry[doc_id]
        return True

    def clear_all_documents(self) -> int:
        """Clears all ingested documents from memory and vector store."""
        count = len(self.doc_registry)
        self.doc_registry.clear()
        
        # Re-create vector store collection
        try:
            self.chroma_client.delete_collection(self.collection_name)
        except Exception:
            pass

        try:
            self.vector_store = self.chroma_client.create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_fn
            )
        except Exception:
            self.vector_store = self.chroma_client.create_collection(
                name=self.collection_name
            )
        return count

    def query(self, user_query: str, top_k: int = 3) -> dict:
        """Executes source-grounded vector search and Gemini generation with model fallbacks."""
        start_time = time.time()
        
        total_chunks = self.vector_store.count()
        if total_chunks == 0:
            latency_ms = round((time.time() - start_time) * 1000, 2)
            return {
                "answer": "No domain documents uploaded yet. Please upload a source document (PDF or TXT) first to populate the knowledge base.",
                "citations": [],
                "latency_ms": latency_ms,
                "model_used": "none"
            }

        # Safe n_results capping to avoid ChromaDB index out-of-bounds error
        actual_k = min(top_k, total_chunks)

        results = self.vector_store.query(query_texts=[user_query], n_results=actual_k)

        retrieved_docs = results["documents"][0] if (results and results.get("documents")) else []
        retrieved_metas = results["metadatas"][0] if (results and results.get("metadatas")) else []

        if not retrieved_docs:
            latency_ms = round((time.time() - start_time) * 1000, 2)
            return {
                "answer": "No relevant domain knowledge matches your query.",
                "citations": [],
                "latency_ms": latency_ms,
                "model_used": "none"
            }

        # Assemble grounded context with source markers
        context_blocks = []
        for doc, meta in zip(retrieved_docs, retrieved_metas):
            context_blocks.append(f"[Source Document: {meta['filename']} | Chunk {meta['chunk_id']}]\n{doc}")

        context_str = "\n\n".join(context_blocks)

        system_prompt = f"""You are DocEngine AI, an enterprise grounded knowledge engine.
Answer the user query relying STRICTLY on the provided source document excerpts.
Rules:
1. For every key point, cite the source document name.
2. If the context does not contain the answer, reply cleanly: "Requested information is not present in the uploaded source documents."
3. Keep the answer structured, well-explained, complete, and fully written without cutting off mid-sentence.

--- INGESTED DOMAIN KNOWLEDGE ---
{context_str}
--- END DOMAIN KNOWLEDGE ---

User Query: {user_query}
Grounded Answer:"""

        candidate_models = ["gemini-3.5-flash", "gemini-3.6-flash", "gemini-flash-latest", "gemini-2.0-flash"]
        last_error = None
        response_text = None
        model_used = None

        for model_name in candidate_models:
            try:
                res = self.client.models.generate_content(
                    model=model_name,
                    contents=system_prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.2,
                        max_output_tokens=2500
                    )
                )
                response_text = res.text.strip()
                model_used = model_name
                break
            except Exception as e:
                last_error = e
                continue

        if not response_text:
            raise RuntimeError(f"Gemini API model generation failed across candidates: {str(last_error)}")

        citations = [
            {
                "doc_id": meta.get("doc_id", "unknown"),
                "filename": meta.get("filename", "unknown"),
                "chunk_id": meta.get("chunk_id", 0),
                "text_snippet": doc
            }
            for meta, doc in zip(retrieved_metas, retrieved_docs)
        ]

        latency_ms = round((time.time() - start_time) * 1000, 2)

        return {
            "answer": response_text,
            "citations": citations,
            "latency_ms": latency_ms,
            "model_used": model_used
        }
