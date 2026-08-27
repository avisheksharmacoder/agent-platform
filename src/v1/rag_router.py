from fastapi import APIRouter, Request, Query, HTTPException
from src.v1.models import RAGDocumentCreate, RAGDocumentEmbeddingIn, RAGDocumentSource, RAGDocumentSourceOut
import ollama

rag_router = APIRouter(prefix="/rag", tags=["rag"])

OLLAMA_HOST = "http://localhost:11434"
client = ollama.AsyncClient(host=OLLAMA_HOST)

@rag_router.get("/documents", response_model=RAGDocumentSourceOut)
async def get_all_rag_documents(request: Request, limit: int = Query(100, ge=1, le=1000)):
    """
    Fetches all RAG documents from the vector database (e.g. for the admin panel).
    """
    vector_db = request.app.state.vector_db
    results = vector_db.get_all_documents(limit=limit)
    
    documents = [
        RAGDocumentSource(
            doc_id=res.get("doc_id", ""),
            doc_title=res.get("doc_title", ""),
            doc_content=res.get("doc_content", ""),
            doc_embedding=res.get("doc_embedding")
        )
        for res in results
    ]
    
    return RAGDocumentSourceOut(documents=documents)

@rag_router.post("/documents")
async def create_rag_document(doc: RAGDocumentCreate, request: Request):
    """
    Stores a RAG document with its embedding in the vector database.
    """
    vector_db = request.app.state.vector_db
    vector_db.store_document(doc)
    return {"message": "Document stored successfully", "doc_id": doc.doc_id}

@rag_router.delete("/documents/{doc_id}")
async def delete_rag_document(doc_id: str, request: Request):
    """
    Deletes a RAG document from the vector database.
    """
    vector_db = request.app.state.vector_db
    try:
        vector_db.delete_document(doc_id)
        return {"message": "Document deleted successfully", "doc_id": doc_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@rag_router.post("/search", response_model=RAGDocumentSourceOut)
async def search_rag_documents(
    payload: RAGDocumentEmbeddingIn, 
    request: Request,
    limit: int = Query(5, ge=1, le=100)
):
    """
    Searches for similar documents in the vector database using the provided embedding.
    """
    vector_db = request.app.state.vector_db
    results = vector_db.search_similar_documents(
        query_embedding=payload.content_embedding, 
        limit=limit
    )
    
    # Map the dictionary results to the Pydantic models
    documents = [
        RAGDocumentSource(
            doc_id=res.get("doc_id", ""),
            doc_title=res.get("doc_title", ""),
            doc_content=res.get("doc_content", ""),
            doc_embedding=res.get("doc_embedding")
        )
        for res in results
    ]
    
    return RAGDocumentSourceOut(documents=documents)

@rag_router.post("/add_ticket")
async def add_ticket_to_rag(payload: dict, request: Request):
    """
    Endpoint to generate an embedding for a ticket's title and description
    and store them in the RAG DB along with the resolution.
    """
    ticket_id = payload.get("id", "unknown_id")
    title = payload.get("title", "")
    description = payload.get("description", "")
    resolution = payload.get("resolution", "")
    
    # 1. Text used ONLY for generating the vector embedding (Problem only)
    embedding_text = f"Title: {title}\nDescription: {description}"
    
    # 2. Text stored in the database to be retrieved by the LLM (Problem + Solution)
    content = f"Title: {title}\nDescription: {description}\nResolution: {resolution}"
    
    try:
        # Generate embedding using ONLY the problem text
        response = await client.embeddings(model="all-minilm:l6-v2", prompt=embedding_text)
        embedding_vector = response.get("embedding", [])
        
        if not embedding_vector:
            raise HTTPException(status_code=500, detail="Failed to generate embedding vector from Ollama.")
            
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Failed to connect to Ollama server: {str(e)}")
        
    doc = RAGDocumentCreate(
        doc_id=ticket_id,
        doc_title=title,
        doc_content=content,
        doc_embedding=embedding_vector
    )
    
    vector_db = request.app.state.vector_db
    vector_db.store_document(doc)
    
    return {"message": "Ticket successfully added to RAG database."}
