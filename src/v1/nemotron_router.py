import os
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

nemotron_router = APIRouter(prefix="/nemotron", tags=["nemotron"])


from src.v1.models import (
    UserChatMessage, 
    AIChatMessage, 
    Role, 
    AIChatFinalResponse, 
    AIUserChatResponse, 
    AIUserChatTicketEscalation
)
from src.v1.agent import chat_agent, ChatDependencies

class QueryRequest(BaseModel):
    messages: list[UserChatMessage | AIChatMessage]


@nemotron_router.post("/generate", response_model=AIChatFinalResponse)
async def generate_nemotron_response(prompt: QueryRequest, request: Request):
    try:
        # Extract the vector database from app state
        vector_db = request.app.state.vector_db

        # We pass the conversation as a formatted string to the agent
        history_str = "CHAT HISTORY:\n"
        for msg in prompt.messages[:-1]:
            role_name = "User" if msg.role == Role.USER else "ai"
            history_str += f"{role_name}: {msg.content}\n"
            
        history_str += "\nCURRENT USER MESSAGE:\n"
        if prompt.messages:
            history_str += prompt.messages[-1].content
            
        # Run the agent
        deps = ChatDependencies(vector_db=vector_db)
        print("1. Request received", flush=True)
        result = await chat_agent.run(
            history_str, 
            deps=deps,
            model_settings={'max_tokens': 4096}
        )
        print("2. Agent completed", flush=True)
        print(type(result.output))
        print(result.output)
        print(result.output.content)
        
        # We get the usage from pydantic-ai's result
        usage = result.usage
        total_tokens = (usage.total_tokens if usage.total_tokens is not None else 0) if usage else 0
        print(f"3. Usage obtained: {total_tokens} tokens", flush=True)
        
        # Extract RAG documents from dependencies
        rag_docs = deps.rag_docs
                    
        # Map flat AgentOutput to the actual AIChatFinalResponse models
        output_data = result.output
        print(f"4. Output action: {output_data.action}", flush=True)
        
        if output_data.action == "respond":
            # Sanitize curly braces to prevent frontend template engine crashes
            safe_content = output_data.content.replace("{", "&#123;").replace("}", "&#125;")
            final_response = AIUserChatResponse(
                reasoning_trace="",
                message=AIChatMessage(
                    role=Role.AI,
                    content=safe_content,
                    tokens=total_tokens,
                    sources=rag_docs
                )
            )
        else:
            safe_description = output_data.description.replace("{", "&#123;").replace("}", "&#125;")
            final_response = AIUserChatTicketEscalation(
                reasoning_trace="",
                title=output_data.title,
                description=safe_description,
                priority=output_data.priority,
                tags=output_data.tags,
                sources=rag_docs
            )
            
        return final_response
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
