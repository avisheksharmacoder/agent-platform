import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

nemotron_router = APIRouter(prefix="/nemotron", tags=["nemotron"])


class QueryRequest(BaseModel):
    query: str


# Global variable to lazy-load the client
_client = None

def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        api_key = os.environ.get("NVIDIA_API_KEY")
        if not api_key:
            raise ValueError("NVIDIA_API_KEY environment variable not set in .env")
        
        _client = AsyncOpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key,
        )
    return _client


@nemotron_router.post("/generate")
async def generate_nemotron_response(prompt: QueryRequest):
    try:
        client = get_client()
    except ValueError as ve:
        raise HTTPException(status_code=500, detail=str(ve))

    try:
        completion = await client.chat.completions.create(
            model="nvidia/nvidia-nemotron-nano-9b-v2",
            messages=[{"role": "user", "content": prompt.query}],
            temperature=0.6,
            top_p=0.95,
            max_tokens=2048,
            frequency_penalty=0,
            presence_penalty=0,
            stream=False,
            extra_body={"min_thinking_tokens": 1024, "max_thinking_tokens": 2048},
        )

        message = completion.choices[0].message
        reasoning = getattr(message, "reasoning_content", None)

        return {"response": message.content, "reasoning": reasoning}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
