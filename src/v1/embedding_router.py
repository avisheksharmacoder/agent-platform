from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import ollama

embedding_router = APIRouter(prefix="/embeddings", tags=["embeddings"])

# Hardcoded Ollama URL as requested
OLLAMA_HOST = "http://localhost:11434"
client = ollama.AsyncClient(host=OLLAMA_HOST)

class EmbeddingRequest(BaseModel):
    prompt: str

@embedding_router.get("/status")
async def check_embedding_status():
    """
    Checks if the local Ollama instance is running and has the 'all-minilm:l6-v2' model available.
    """
    try:
        response = await client.list()
        # Extract model names. Ollama usually puts this in 'model' or 'name' fields.
        models = [model.get("model", model.get("name", "")) for model in response.get("models", [])]
        
        if any("all-minilm:l6-v2" in model_name for model_name in models):
            return {"status": "available", "message": "all-minilm:l6-v2 is ready for embeddings"}
        else:
            raise HTTPException(
                status_code=404, 
                detail="Embedding model 'all-minilm:l6-v2' is not found in local Ollama. Please run 'ollama pull all-minilm:l6-v2'."
            )
            
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=503, detail=f"Failed to connect to Ollama server: {str(e)}")

@embedding_router.post("/generate")
async def generate_embedding(request: EmbeddingRequest):
    """
    Generates an embedding vector for the provided prompt string.
    """
    try:
        response = await client.embeddings(model="all-minilm:l6-v2", prompt=request.prompt)
        
        embedding_vector = response.get("embedding", [])
        
        if not embedding_vector:
            raise HTTPException(status_code=500, detail="Ollama returned an empty embedding vector.")
            
        return {
            "embedding": embedding_vector,
            "model": "all-minilm:l6-v2"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate embedding: {str(e)}")
