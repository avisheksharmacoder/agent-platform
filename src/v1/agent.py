import os
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from src.v1.models import AIResponseDraft, AITicketDraft
from typing import Annotated, Literal, Union, Any

load_dotenv()


class TicketResolution(BaseModel):
    summary: str = Field(description="A 2-3 sentence technical summary of the ticket.")
    assignee_id: str = Field(
        description="The exact database ID of the chosen support agent."
    )


api_key = os.environ.get("NVIDIA_API_KEY")

# 1. Initialize an AsyncOpenAI client pointing to NVIDIA's API
nvidia_client = AsyncOpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY"),
)

MODEL1 = "nvidia/nemotron-3.5-lightning-30b-a3b"
MODEL2 = "nvidia/nemotron-3-ultra-550b-a55b"

# --- PATCH FOR NEMOTRON 120B TOOL CALLING BUG ---
import json
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall, Function

original_create = nvidia_client.chat.completions.create

async def patched_create(*args, **kwargs):
    # Enable Nvidia's native thinking mode for better logical reasoning
    if "extra_body" not in kwargs:
        kwargs["extra_body"] = {"chat_template_kwargs": {"enable_thinking": True}, "reasoning_budget": 16384}
    elif isinstance(kwargs["extra_body"], dict):
        kwargs["extra_body"].update({"chat_template_kwargs": {"enable_thinking": True}, "reasoning_budget": 16384})
    
    # Reasoning requires a larger token pool
    kwargs["max_tokens"] = 16384
    
    print("\n" + "="*50)
    print("🤖 [AGENT API REQUEST]")
    messages = kwargs.get('messages', [])
    if messages:
        print(f"Last user message: {messages[-1]}")
    
    response = await original_create(*args, **kwargs)
    
    if hasattr(response, 'choices') and response.choices:
        msg = response.choices[0].message
        
        print("\n🧠 [AGENT REASONING TRACE]")
        reasoning = getattr(msg, "reasoning_content", None)
        if reasoning:
            print(reasoning)
        else:
            print("(No reasoning trace provided by model)")
            
        print("\n📝 [AGENT MESSAGE CONTENT]")
        print(msg.content)

        if getattr(msg, "tool_calls", None):
            print("\n🛠️ [AGENT STRUCTURED OUTPUT]")
            for tc in msg.tool_calls:
                print(f"Tool: {tc.function.name}")
                print(f"Args: {tc.function.arguments}")
        
        if getattr(msg, "tool_calls", None):
            print("\n🛠️ [AGENT TOOL CALLS]")
            for tc in msg.tool_calls:
                print(f"Tool: {tc.function.name} | Args: {tc.function.arguments}")
        print("="*50 + "\n")
        msg = response.choices[0].message
        
        # If the model hallucinates the tool call as raw text in msg.content
        if msg.content and '"name":' in msg.content and '"parameters":' in msg.content:
            content = msg.content.strip()
            
            # Fix the EOF JSON bracket bug (model outputs [[ { ... } ] instead of [{...}] )
            if content.startswith("[[") and content.endswith("]") and not content.endswith("]]"):
                content += "]"
                
            try:
                parsed = json.loads(content)
                # Unpack nested arrays if present
                while isinstance(parsed, list) and len(parsed) > 0:
                    parsed = parsed[0]
                    
                if isinstance(parsed, dict) and "name" in parsed and "parameters" in parsed:
                    tc = ChatCompletionMessageToolCall(
                        id="call_patched_120b",
                        type="function",
                        function=Function(
                            name=parsed["name"],
                            arguments=json.dumps(parsed["parameters"])
                        )
                    )
                    # Shift from content to native tool_calls
                    msg.tool_calls = [tc]
                    msg.content = None
            except Exception as e:
                print(f"Nemotron patch failed to parse JSON: {e}")
                
        # Merge fragmented tool calls from Nemotron
        if getattr(msg, "tool_calls", None) and len(msg.tool_calls) > 1:
            first_name = msg.tool_calls[0].function.name
            if all(tc.function.name == first_name for tc in msg.tool_calls):
                merged_args = {}
                for tc in msg.tool_calls:
                    try:
                        args = json.loads(tc.function.arguments)
                        for k, v in args.items():
                            if k in merged_args and isinstance(merged_args[k], str) and isinstance(v, str):
                                merged_args[k] += "\n" + v
                            else:
                                merged_args[k] = v
                    except Exception:
                        pass
                msg.tool_calls = [
                    ChatCompletionMessageToolCall(
                        id=msg.tool_calls[0].id,
                        type="function",
                        function=Function(
                            name=first_name,
                            arguments=json.dumps(merged_args)
                        )
                    )
                ]
                
    return response

nvidia_client.chat.completions.create = patched_create
# ------------------------------------------------

# 2. Pass the custom client to OpenAIModel
nemotron_model = OpenAIChatModel(
    MODEL1,
    provider=OpenAIProvider(openai_client=nvidia_client),
)

# 3. Initialize the agent
routing_agent = Agent(
    nemotron_model,
    output_type=TicketResolution,
    system_prompt=(
        """
        You are an autonomous IT routing engine. Your job is to analyze a support ticket, 
        summarize the core issue, and assign it to the most qualified human support agent 
        based strictly on their designation. Do not invent IDs. 
        """
    ),
)



from enum import Enum

class ActionType(str, Enum):
    CHAT = "chat"
    TICKET = "ticket"

classifier_agent = Agent(
    nemotron_model,
    output_type=ActionType,
    system_prompt=(
        "Analyze the user request.\n"
        "If they explicitly want to create or escalate a support ticket, return \"ticket\".\n"
        "For all other IT queries, explanations, or code requests, return \"chat\"."
    )
)

chat_worker = Agent(
    nemotron_model,
    system_prompt=(
        "You are an IT support assistant.\n"
        "Respond to the user with the solution they are asking for so they can get back to work.\n"
        "Provide code snippets natively in markdown if needed. Do not mention tickets."
    )
)

ticket_worker = Agent(
    nemotron_model,
    output_type=AITicketDraft,
    system_prompt=(
        "You are an IT ticket extraction agent.\n"
        "Extract the required ticket fields (title, description, priority, tags) from the user request."
    )
)
