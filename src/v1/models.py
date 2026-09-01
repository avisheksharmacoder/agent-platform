from urllib3.exceptions import TimeoutStateError
from pydantic import BaseModel, Field, computed_field
from enum import Enum
from datetime import datetime
from uuid import uuid4, UUID
from typing import Literal, Annotated, Union


# Enums.
class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Status(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    IN_PROGRESS = "in_progress"


class OperationType(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    CLOSE = "close"


class QueueStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Role(str, Enum):
    ADMIN = "admin"
    USER = "user"


# ------------------------------- USER MODELS ---------------------------
# Base user model.
class User(BaseModel):
    name: str = Field(max_length=100, description="Name of the user.")
    user_email: str = Field(max_length=100, description="Email of the user.")
    user_password: str = Field(max_length=100, description="Password of the user.")
    designation: str = Field(max_length=50, description="Designation of the user.")
    human_agent: bool = Field(
        description="Whether the user is a human support agent or not"
    )
    tokens_budget: int = Field(
        ge=0, le=50000000, description="Tokens budget for the user."
    )
    role: Role = Field(default=Role.USER, description="Role of the user.")


# User model for creation.
class UserCreate(User):
    pass


# User model for login.
class UserLogin(BaseModel):
    user_email: str = Field(max_length=100, description="Email of the user.")
    user_password: str = Field(max_length=100, description="Password of the user.")


# User model for updating.
class UserUpdate(BaseModel):
    name: str | None = Field(
        default=None, max_length=100, description="Name of the user."
    )
    user_email: str | None = Field(max_length=100, description="Email of the user.")
    user_password: str | None = Field(max_length=100, description="Password of the user.")
    designation: str | None = Field(
        default=None, max_length=50, description="Designation of the user."
    )
    human_agent: bool | None = Field(
        description="Whether the user is a human support agent or not"
    )
    tokens_budget: int | None = Field(
        default=None, ge=0, le=1000000, description="Tokens budget for the user."
    )
    role: Role | None = Field(default=None, description="Role of the user.")


# User model for frontend output.
class UserOut(User):
    id: str = Field(description="Unique identifier of the user.")


# ------------------------------- USER MODELS ---------------------------


class Comment(BaseModel):
    user_id: str = Field(description="User ID of the comment.")
    ticket_id: str = Field(description="Ticket ID of the comment.")
    comment: str = Field(max_length=2000, description="Comment of the ticket.")


# ------------------------------- TICKET MODELS ---------------------------
# Base Ticket model.
# AI Training fields are included.
class Ticket(BaseModel):
    title: str = Field(max_length=200, description="Title of the ticket.")
    description: str = Field(max_length=2000, description="Description of the ticket.")
    priority: Priority
    status: Status
    # Field for AI summary.
    summary: str | None = Field(
        default=None, max_length=2000, description="Summary of the ticket."
    )
    # Field for AI resolution once the problem is solved.
    resolution: str | None = Field(
        default=None, max_length=2000, description="Resolution of the ticket."
    )
    tags: list[str] | None = Field(default=None, description="Tags of the ticket.")
    total_tokens: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.now)
    modified_at: datetime = Field(default_factory=datetime.now)
    created_by: str
    assignee_id: str | None = Field(
        default=None, description="User ID of the assigned agent."
    )
    modified_by: str | None = Field(default=None)
    comments: list[Comment] | None = Field(default=None)

    closed_at: datetime | None = Field(default=None)
    # Field for AI training dataset.
    archived: bool = Field(default=False)


# Ticket model for creation.
class TicketCreate(BaseModel):
    title: str = Field(max_length=200, description="Title of the ticket.")
    description: str = Field(max_length=2000, description="Description of the ticket.")
    priority: Priority
    tags: list[str] | None = Field(default=None, description="Tags of the ticket.")
    created_by: str


# Ticket model for updating.
class TicketUpdate(BaseModel):
    title: str | None = Field(
        default=None, max_length=200, description="Title of the ticket."
    )
    description: str | None = Field(
        default=None, max_length=2000, description="Description of the ticket."
    )
    priority: Priority | None = Field(default=None)
    status: Status | None = Field(default=None)
    summary: str | None = Field(
        default=None, max_length=2000, description="Summary of the ticket."
    )
    resolution: str | None = Field(
        default=None, max_length=2000, description="Resolution of the ticket."
    )
    tags: list[str] | None = Field(default=None, description="Tags of the ticket.")
    total_tokens: int | None = Field(default=None)
    modified_by: str | None = Field(default=None)
    comments: list[Comment] | None = Field(default=None)
    closed_at: datetime | None = Field(default=None)
    archived: bool | None = Field(default=None)


# Ticket model for frontend output.
class TicketOut(Ticket):
    id: str = Field(description="Unique identifier of the ticket.")


# ------------------------------- TICKET MODELS ---------------------------


# Queue event model.
class QueueItem(BaseModel):
    ticket_id: str = Field(description="Ticket ID of the queue item.")
    ticket_title: str
    ticket_description: str
    support_agents: list[UserOut]
    operation_type: OperationType = Field(
        description="Operation type of the queue item."
    )
    status: QueueStatus = Field(
        default=QueueStatus.PENDING, description="Status of the queue event."
    )


# ------------------------------- RAG and AI CHAT MODELS ---------------------------
# role of the attendant. 
# we use a Role Enum so that in future, we can assign more roles to either 
# AI or users, based on their positions. 
class Role(str, Enum):
    USER = "user"
    AI = "ai"

# quality of the response 
class Quality(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXCELLENT = "excellent"


# RAG document source and content models.
# This model is sent to the embedding router to create the embeddings. 
# Here the content is only the problem description (title + description)
# The resolution is not included in the embedding text because vector similarity searches are triggered 
# by user-provided details (which only consist of title and description) when trying to resolve future tickets.
# The resolution field is explicitly excluded from the embedding text because vector similarity searches are triggered by user-provided details (which only consist of title and description) when trying to resolve future tickets.
# Thus, the string passed to the embedding model for indexing should be formatted as: `Title: {title}\nDescription: {description}`.
class RAGDocumentEmbeddingIn(BaseModel):
    content: str = Field(description="the string for finding vector searches")
    content_embedding: list[float] = Field(description="Embedding of the string content from embedding model")


# create a rag document record in the vector db. 
class RAGDocumentCreate(BaseModel):
    doc_id: str = Field(description="ID of the document")
    doc_title: str = Field(description="Title of the document")
    doc_content: str = Field(description="Content of the document")
    doc_embedding: list[float] = Field(description="Embedding of the document")


# retrieve records from the vector db to send to the model API. 
class RAGDocumentSource(BaseModel):
    doc_id: str = Field(description="ID of the document")
    doc_title: str = Field(description="Title of the document")
    doc_content: str = Field(description="Content of the document")
    doc_embedding: list[float] | None = Field(default=None, description="Embedding vector of the document")


# wrap the rag documents in a list of top-k relevant documents.
class RAGDocumentSourceOut(BaseModel):
    documents: list[RAGDocumentSource] = Field(description="list of documents")
    

# User chat message model. 
class UserChatMessage(BaseModel):
    role: Role = Field(default=Role.USER ,description="role of the party who sent the message")
    content: str = Field(description="content of the message")
    timestamp: datetime = Field(default_factory=datetime.now)
    tokens: int = Field(default=0, description="tokens in the message")


class AIResponseDraft(BaseModel):
    role: Role = Field(default=Role.AI, description="role of the party who sent the message")
    content: str = Field(description="content of the message")

class AITicketDraft(BaseModel):
    title: str = Field(default="", description="Title of the ticket")
    description: str = Field(default="", description="Description of the ticket")
    priority: Priority = Field(default=Priority.MEDIUM, description="Priority of the ticket")
    tags: list[str] = Field(default_factory=list, description="List of tags for the ticket for keyword search")


AIChatFinalResponse = Union[AIResponseDraft, AITicketDraft]



class AIChatMessage(BaseModel):
    role: Role = Field(default=Role.AI, description="role of the party who sent the message")
    content: str = Field(description="content of the message")
    timestamp: datetime = Field(default_factory=datetime.now)
    tokens: int = Field(default=0, description="tokens in the message")
    quality: Quality | None = Field(default=None, description="quality of the response")
    response_summary: str | None = Field(default="", description="summary of the response for context window slimming")





# user chat session model. 
class UserAIChatSession(BaseModel):
    session_id: str = Field(description="unique id of the chat session")
    user_id: str = Field(description="id of the user who is chatting with AI")
    name: str = Field(description="Name of the chat session")
    model_name: str = Field(description="")
    created_at: datetime = Field(default_factory=datetime.now)
    modified_at: datetime = Field(default_factory=datetime.now)
    messages: list[UserChatMessage | AIChatMessage] = Field(default_factory=list,description="User and AI chat messages")
    total_tokens: int = Field(default=0, description="tokens in the chat session")
    ai_response_quality: Quality | None = Field(default=None, description="overall quality of the AI responses")
    ai_response_summary: str | None = Field(default=None, description="overall summary of the AI responses")    


# user chat session update model. 
class UserAIChatSessionUpdate(BaseModel):   
    name: str | None = Field(default=None, description="Name of the chat session")
    messages: list[UserChatMessage | AIChatMessage] | None = Field(default=None, description="User and AI chat messages")
    total_tokens: int | None = Field(default=None, description="tokens in the chat session")
    ai_response_quality: Quality | None = Field(default=None, description="overall quality of the AI responses")
    ai_response_summary: str | None = Field(default=None, description="overall summary of the AI responses")
    modified_at: datetime | None = Field(default=None)


