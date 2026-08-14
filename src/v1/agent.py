import os
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

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

# 2. Pass the custom client to OpenAIModel
nemotron_model = OpenAIChatModel(
    "nvidia/nvidia-nemotron-nano-9b-v2",
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
