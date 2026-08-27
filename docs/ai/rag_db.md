# Goal: Implement Weaviate RAG Database Operations

The goal is to design a Weaviate-based database class for storing and retrieving RAG documents via vector search, and then integrate this class into the FastAPI application's lifecycle in `main.py`.

## Resolved Design Decisions
1. **Weaviate Port**: We will use the default Weaviate port (`8080`) assuming it is running locally on the standard setup.
2. **Vector Distance Metric**: We will rely on Weaviate's default `cosine` distance, which is suitable for `all-minilm:l6-v2`.

## Implementation Details

### 1. `src/v1/rag_database.py`
We will implement a `WeaviateRAGDatabase` class with the following methods:
- **`__init__`**: Connects to the local Weaviate instance using `weaviate.connect_to_local()`.
- **`create_schema`**: Checks if the `RAGDocument` collection exists. If not, creates it. The collection will have the following properties: `doc_id`, `doc_title`, and `doc_content`. The collection is configured to NOT use an internal vectorizer since embeddings are provided manually.
- **`store_document`**: Accepts a `RAGDocumentCreate` object. Inserts the properties and the custom vector into the `RAGDocument` collection.
- **`search_similar_documents`**: Accepts a `query_embedding` (list of floats) and a `limit` integer. Performs a `near_vector` search on the `RAGDocument` collection and returns the matching documents along with their similarity distances.
- **`close`**: Closes the Weaviate connection gracefully.

### 2. `main.py` (FastAPI Lifespan Integration)
- **Import**: `from src.v1.rag_database import WeaviateRAGDatabase`
- **Startup**: Inside the `lifespan` context manager, instantiate the database: `app.state.weaviate_db = WeaviateRAGDatabase()`.
- **Initialization**: Call `app.state.weaviate_db.create_schema()` to ensure the collections are ready.
- **Shutdown**: At the end of the `lifespan` function (after `yield`), call `app.state.weaviate_db.close()` to clean up the connection.
