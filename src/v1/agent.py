import os
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from src.v1.models import AIChatFinalResponse, RAGDocumentSourceOut, RAGDocumentSource
from typing import Annotated, Literal, Union, Any
from dataclasses import dataclass
from pydantic_ai import RunContext
from src.v1.embedding_router import generate_embedding, EmbeddingRequest

load_dotenv()

@dataclass
class ChatDependencies:
    vector_db: Any
    rag_docs: Any = None


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
                
    return response

nvidia_client.chat.completions.create = patched_create
# ------------------------------------------------

# 2. Pass the custom client to OpenAIModel
nemotron_model = OpenAIChatModel(
    "nvidia/nemotron-3.5-lightning-30b-a3b",
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



# Flat models to avoid Nvidia grammar $defs bug
class AgentRespond(BaseModel):
    action: Literal["respond"] = "respond"
    content: str = Field(description="The final message content to show to the user")

class AgentEscalate(BaseModel):
    action: Literal["escalate"] = "escalate"
    title: str = Field(max_length=100, description="Title of the ticket")
    description: str = Field(max_length=1000, description="Description of the ticket")
    priority: Literal["low", "medium", "high", "critical"] = Field(description="Priority of the ticket")
    tags: list[str] | None = Field(default=None, description="Tags of the ticket")

AgentOutput = Annotated[Union[AgentRespond, AgentEscalate], Field(discriminator="action")]

chat_agent = Agent(
    nemotron_model,
    deps_type=ChatDependencies,
    output_type=AgentOutput,
    system_prompt=(
        """
        You are an IT support assistant.

        Determine the appropriate action:

        1. General queries:
        Use `respond` directly. Do not search the knowledge base.

        2. IT/support problems:
        Use `search_knowledge_base` to look for relevant previous resolutions.

        3. If the knowledge base contains a relevant resolution:
        Use `respond` and provide the complete useful resolution to the user.

        4. If the knowledge base does not contain a relevant resolution:
        Use `respond` with the best answer you can provide.

        5. If the user explicitly asks to create/escalate a support ticket:
        Use `escalate`.

        For `respond`, put the complete user-facing answer in `content`.
        For `escalate`, provide the required ticket fields.

        Never expose internal reasoning or tool-selection logic to the user.
        """
    ),
)

@chat_agent.tool
async def search_knowledge_base(ctx: RunContext[ChatDependencies], problem_description: str) -> str:
    """
    Search the knowledge base for existing tickets and resolutions that match the problem description.
    Use this to find a solution before escalating to a new ticket.
    """
    # 1. Generate the embedding natively using the existing router's logic
    request = EmbeddingRequest(prompt=problem_description)
    embedding_response = await generate_embedding(request)
    embedding_vector = embedding_response["embedding"]
    
    # 2. Search the vector database
    results = ctx.deps.vector_db.search_similar_documents(
        query_embedding=embedding_vector, 
        limit=3
    )
    
    # 3. Map the raw dictionary results to the expected Pydantic models
    documents = [
        RAGDocumentSource(
            doc_id=res.get("doc_id", ""),
            doc_title=res.get("doc_title", ""),
            doc_content=res.get("doc_content", ""),
            doc_embedding=res.get("doc_embedding")
        )
        for res in results
    ]
    
    # Save structured data to dependencies for the frontend
    ctx.deps.rag_docs = RAGDocumentSourceOut(documents=documents)
    
    # Return formatted plain text to avoid LLM JSON grammar confusion
    if not documents:
        return "No relevant documents found."
    
    text_results = []
    for doc in documents:
        text_results.append(f"Title: {doc.doc_title}\nContent: {doc.doc_content}")
    
    return "\n\n---\n\n".join(text_results)
