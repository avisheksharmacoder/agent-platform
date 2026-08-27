# Goal: Implement RAG Router

The goal is to design the implementation of the `rag_router.py` endpoint using the defined Pydantic models. The `rag_database.py` class will retain its dependency on the `RAGDocumentCreate` Pydantic model for simplicity and strong typing.

## Implementation Details

### 1. `rag_database.py`
- We will retain the `store_document(self, doc: RAGDocumentCreate)` signature, passing the perfectly validated Pydantic model from the router directly to the database.

### 2. Implement `rag_router.py`
- Initialize an `APIRouter` with `prefix="/rag"` and `tags=["rag"]`.
- Create a `POST /rag/documents` endpoint:
  - **Input Model**: `RAGDocumentCreate`
  - **Logic**: Passes the `doc` payload directly to `request.app.state.weaviate_db.store_document(doc)`.
  - **Output**: Returns a success message `{"message": "Document stored successfully", "doc_id": payload.doc_id}`.
- Create a `POST /rag/search` endpoint:
  - **Input Model**: `RAGDocumentEmbeddingIn` (contains the prompt and its embedding)
  - **Query Parameter**: Add `limit: int = Query(5)` to allow for dynamic limits.
  - **Logic**: Calls `request.app.state.weaviate_db.search_similar_documents(query_embedding=payload.content_embedding, limit=limit)`.
  - **Output**: Maps the returned list of dictionaries to `RAGDocumentSource` models, and encapsulates them inside the `RAGDocumentSourceOut(documents=[...])` response model.
