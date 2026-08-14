from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
from uuid import uuid4, UUID


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
    designation: str = Field(max_length=50, description="Designation of the user.")
    human_agent: bool = Field(
        description="Whether the user is a human support agent or not"
    )
    tokens_budget: int = Field(
        ge=0, le=1000000, description="Tokens budget for the user."
    )
    role: Role = Field(default=Role.USER, description="Role of the user.")


# User model for creation.
class UserCreate(User):
    pass


# User model for updating.
class UserUpdate(BaseModel):
    name: str | None = Field(
        default=None, max_length=100, description="Name of the user."
    )
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
