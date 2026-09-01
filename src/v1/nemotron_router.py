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
    AIChatFinalResponse
)
from src.v1.agent import classifier_agent, chat_worker, ticket_worker, ActionType

class QueryRequest(BaseModel):
    messages: list[UserChatMessage | AIChatMessage]


@nemotron_router.post("/generate", response_model=AIChatMessage)
async def generate_nemotron_response(prompt: QueryRequest, request: Request):
    try:
        # We pass the conversation as a formatted string to the agent
        history_str = "CHAT HISTORY:\n"
        for msg in prompt.messages[:-1]:
            role_name = "User" if msg.role == Role.USER else "ai"
            history_str += f"{role_name}: {msg.content}\n"
            
        history_str += "\nCURRENT USER MESSAGE:\n"
        if prompt.messages:
            history_str += prompt.messages[-1].content
            
        # Run the agent
        print("1. Request received", flush=True)
        
        # Step 1: Classify
        classification = await classifier_agent.run(history_str)
        action = classification.output
        print(f"2. Classification completed: {action}", flush=True)
        
        from src.v1.models import AITicketDraft, AIChatMessage
        
        # Step 2: Route to specific worker
        if action == ActionType.CHAT:
            result = await chat_worker.run(history_str, model_settings={"max_tokens": 4096})
            output_data = result.output  # This is just a string!
            print(f"3. Chat worker completed", flush=True)
            
            # Since it is native text, there is no JSON formatting bug
            safe_content = output_data.replace("{", "&#123;").replace("}", "&#125;")
            final_response = AIChatMessage(
                role=Role.AI,
                content=safe_content,
                tokens=result.usage.total_tokens if result.usage else 0
            )
            
        elif action == ActionType.TICKET:
            result = await ticket_worker.run(history_str, model_settings={"max_tokens": 4096})
            output_data = result.output  # This is an AITicketDraft
            print(f"3. Ticket worker completed", flush=True)
            
            safe_description = output_data.description.replace("{", "&#123;").replace("}", "&#125;")
            output_data.description = safe_description
            final_response = AIChatMessage(
                role=Role.AI,
                content=output_data.model_dump_json(),
                tokens=result.usage.total_tokens if result.usage else 0
            )
        else:
            raise ValueError(f"Unknown action type: {action}")
            
        return final_response
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
