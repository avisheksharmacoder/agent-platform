# Goal: Implement Embedding Router

The goal is to implement two FastAPI route handlers in `C:\Python-projects\Tense\backend\src\v1\embedding_router.py` that interface with a local Ollama server to generate text embeddings using the `all-minilm:l6-v2` model.

## Resolved Design Decisions
1. **Ollama URL**: The Ollama host URL (`http://localhost:11434`) will be hardcoded in the router file for now.
2. **Response Structure**: The `/embeddings/generate` endpoint will return a dictionary structured like `{"embedding": [0.1, 0.2, ...], "model": "all-minilm:l6-v2"}` to allow future integration with Pydantic models.

## Implementation Details

### Backend Route Implementation
#### `embedding_router.py`
- Import `APIRouter` from `fastapi` and initialize the router (`prefix="/embeddings"`, `tags=["embeddings"]`).
- Import the `AsyncClient` from the `ollama` library and initialize it with `host="http://localhost:11434"`.
- Define a Pydantic model `EmbeddingRequest` with a single field `prompt: str` to validate the incoming POST requests.
- **Endpoint 1 (`GET /embeddings/status`)**: 
  - Call `await client.list()` to retrieve locally pulled Ollama models.
  - Check if `all-minilm:l6-v2` is present in the results.
  - Return a success message (`{"status": "available", "message": "all-minilm:l6-v2 is ready for embeddings"}`) or an `HTTPException` if not found or server is unreachable.
- **Endpoint 2 (`POST /embeddings/generate`)**:
  - Accept `EmbeddingRequest`.
  - Call `await client.embeddings(model="all-minilm:l6-v2", prompt=request.prompt)`.
  - Return the resulting embedding vector as a dictionary `{"embedding": [...], "model": "all-minilm:l6-v2"}`.

## RAG Embedding Strategy Update
- When storing tickets into the RAG database (e.g., in `rag_router.py` via `POST /rag/add_ticket`), we follow the optimal "Problem-to-Problem" RAG pattern.
- **Vector Embedding**: The semantic vector must be generated from a combination of the ticket's **Title** and **Description** ONLY. This ensures accurate similarity matching against new user problems. The prompt passed to the embedding model should be formatted as: `Title: {title}\nDescription: {description}`.
- **Stored Document Content**: While the **Resolution** field is explicitly excluded from the embedding text, it MUST be included in the final `doc_content` payload saved to the database. This guarantees the LLM (Nemotron) receives the prior solution when a similar problem is retrieved. The stored content should be formatted as: `Title: {title}\nDescription: {description}\nResolution: {resolution}`.
