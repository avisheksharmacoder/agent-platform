from fastapi import APIRouter, Request, HTTPException, Query
from uuid import uuid4
from datetime import datetime
from .models import (
    Ticket,
    TicketCreate,
    TicketUpdate,
    TicketOut,
    Status,
    QueueItem,
    OperationType,
)

tickets_router = APIRouter(prefix="/tickets", tags=["tickets"])


# O(1) Metrics Helper
# ==========================================
async def _update_metrics(db, total_delta=0, active_delta=0, closed_delta=0):
    """Fetches the global metrics record, applies the deltas, and saves it."""
    metrics = await db.get("admin_metrics_global")
    if not metrics:
        return  # Failsafe in case the lifespan event hasn't run yet

    metrics["total_tickets"] = metrics.get("total_tickets", 0) + total_delta
    metrics["active_tickets"] = metrics.get("active_tickets", 0) + active_delta
    metrics["closed_tickets"] = metrics.get("closed_tickets", 0) + closed_delta

    await db.upsert("admin_metrics_global", metrics)


@tickets_router.post("/", response_model=TicketOut)
async def create_ticket(ticket: TicketCreate, request: Request):
    db = request.app.state.db
    queue = request.app.state.queue

    id = f"ticket_{uuid4().hex}"

    # Build the full ticket with required status
    ticket_data = ticket.model_dump()
    ticket_data["status"] = Status.OPEN

    # Use the Ticket base model to apply async defaults and validate
    full_ticket = Ticket(**ticket_data)
    payload = full_ticket.model_dump(mode="json")

    await db.insert(id, payload)

    # Update metrics: +1 Total, +1 Active
    await _update_metrics(db, total_delta=1, active_delta=1)

    # Push lightweight event to queue (DO NOT embed all support agents here)
    queue_item = QueueItem(
        ticket_id=id,
        ticket_title=full_ticket.title,
        ticket_description=full_ticket.description,
        support_agents=[],  # The consumer worker should fetch this independently!
        operation_type=OperationType.CREATE,
    )
    await queue.insert(f"event_{uuid4().hex}", queue_item.model_dump(mode="json"))

    return TicketOut(id=id, **payload)


@tickets_router.get("/", response_model=list[TicketOut])
async def get_tickets(
    request: Request, limit: int = Query(100, le=1000), offset: int = Query(0)
):
    db = request.app.state.db
    records = await db.scan_prefix("ticket_")

    # Paginate BEFORE Pydantic validation
    paginated_records = records[offset : offset + limit]

    tickets = [TicketOut(id=tid, **payload) for tid, payload in paginated_records]
    return tickets


@tickets_router.get("/{id}", response_model=TicketOut)
async def get_ticket(id: str, request: Request):
    db = request.app.state.db
    payload = await db.get(id)
    if not payload:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return TicketOut(id=id, **payload)


@tickets_router.put("/{id}", response_model=TicketOut)
async def update_ticket(id: str, ticket_update: TicketUpdate, request: Request):
    db = request.app.state.db
    queue = request.app.state.queue

    existing = await db.get(id)
    if not existing:
        raise HTTPException(status_code=404, detail="Ticket not found")

    update_data = ticket_update.model_dump(exclude_unset=True, mode="json")

    is_closing = False
    is_reopening = False

    # Check if closing a previously open ticket
    if (
        "status" in update_data
        and update_data["status"] == Status.CLOSED.value
        and existing.get("status") != Status.CLOSED.value
    ):
        is_closing = True
        update_data["closed_at"] = datetime.now().isoformat()

    # Check if reopening a previously closed ticket (edge case safety)
    elif (
        "status" in update_data
        and update_data["status"] != Status.CLOSED.value
        and existing.get("status") == Status.CLOSED.value
    ):
        is_reopening = True

    update_data["modified_at"] = datetime.now().isoformat()
    existing.update(update_data)

    updated_ticket = Ticket(**existing)
    payload = updated_ticket.model_dump(mode="json")

    await db.upsert(id, payload)

    # Update metrics based on status shifts
    if is_closing:
        await _update_metrics(db, active_delta=-1, closed_delta=1)
    elif is_reopening:
        await _update_metrics(db, active_delta=1, closed_delta=-1)

    return TicketOut(id=id, **payload)


@tickets_router.delete("/{id}")
async def delete_ticket(id: str, request: Request):
    db = request.app.state.db

    existing = await db.get(id)

    # Fire and forget deletion
    await db.delete(id)

    # Determine which metrics to decrement
    if existing.get("status") == Status.CLOSED.value:
        await _update_metrics(db, total_delta=-1, closed_delta=-1)
    else:
        await _update_metrics(db, total_delta=-1, active_delta=-1)

    return {"message": "Ticket deleted successfully", "id": id}
