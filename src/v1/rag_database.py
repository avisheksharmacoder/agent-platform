from qdrant_client import QdrantClient
from qdrant_client.http import models
from src.v1.models import RAGDocumentCreate
import uuid

class QdrantRAGDatabase:
    def __init__(self):
        # Store Qdrant database files locally in the "database" folder
        self.client = QdrantClient(path="database/qdrant_db")
        self.collection_name = "RAGDocument"
        
    def create_schema(self):
        """
        Creates the RAGDocument collection if it doesn't exist.
        all-minilm:l6-v2 embedding vectors have 384 dimensions.
        """
        if not self.client.collection_exists(self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=384, 
                    distance=models.Distance.COSINE
                )
            )
            print("✅ Created RAGDocument schema in Qdrant.")
        else:
            print("✅ RAGDocument schema already exists in Qdrant.")
            
    def store_document(self, doc: RAGDocumentCreate):
        """
        Stores a document with its pre-computed vector embedding.
        """
        # Qdrant requires IDs to be UUIDs or unsigned integers. 
        # We generate a UUID and store the actual doc_id in the payload.
        point_id = str(uuid.uuid4())
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                models.PointStruct(
                    id=point_id,
                    vector=doc.doc_embedding,
                    payload={
                        "doc_id": doc.doc_id,
                        "doc_title": doc.doc_title,
                        "doc_content": doc.doc_content,
                    }
                )
            ]
        )
        
    def search_similar_documents(self, query_embedding: list[float], limit: int = 5):
        """
        Performs a vector similarity search and returns the closest documents.
        """
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_embedding,
            limit=limit,
        )
        
        results = []
        for point in response.points:
            results.append({
                "doc_id": point.payload.get("doc_id"),
                "doc_title": point.payload.get("doc_title"),
                "doc_content": point.payload.get("doc_content"),
                "distance": point.score
            })
        return results

    def get_all_documents(self, limit: int = 100):
        """
        Fetches all documents from the vector database.
        """
        records, _ = self.client.scroll(
            collection_name=self.collection_name,
            limit=limit,
            with_payload=True,
            with_vectors=True
        )
        
        results = []
        for record in records:
            results.append({
                "doc_id": record.payload.get("doc_id"),
                "doc_title": record.payload.get("doc_title"),
                "doc_content": record.payload.get("doc_content"),
                "doc_embedding": record.vector
            })
        return results

    def delete_document(self, doc_id: str):
        """
        Deletes a document from the vector database by its payload doc_id.
        """
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="doc_id",
                            match=models.MatchValue(value=doc_id),
                        ),
                    ],
                )
            ),
        )

    def close(self):
        """
        Closes the Qdrant client connection gracefully.
        """
        self.client.close()
        print("🛑 Qdrant connection closed.")
