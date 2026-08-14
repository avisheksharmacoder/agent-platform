from fastapi import APIRouter, Request, HTTPException, Query
from pydantic import BaseModel
from typing import Any

queue_router = APIRouter(prefix="/queue", tags=["queue"])


# Always validate queue states to prevent worker crashes!
class QueueEventUpdate(BaseModel):
    status: str | None = None

    # Add any other fields the frontend is allowed to modify
    class Config:
        extra = "allow"


@queue_router.get("/")
async def get_queue(
    request: Request, limit: int = Query(100, le=1000), offset: int = Query(0)
):
    queue = request.app.state.queue

    # Use the limit/offset here depending on if you implemented the Rust-level
    # pagination or the Python array slicing approach we discussed.
    records = await queue.scan_prefix("event_", limit=limit, offset=offset)

    events = [{"id": qid, **payload} for qid, payload in records]
    return events


@queue_router.put("/{id}")
async def update_queue_event(id: str, event_update: QueueEventUpdate, request: Request):
    queue = request.app.state.queue

    # We keep the get() here because it's a PUT/PATCH and we need to merge data
    existing = await queue.get(id)
    if not existing:
        raise HTTPException(status_code=404, detail="Event not found")

    update_data = event_update.model_dump(exclude_unset=True)
    update_data.pop("id", None)

    existing.update(update_data)

    await queue.upsert(id, existing)
    return {"message": "Event updated successfully", "id": id, **existing}


@queue_router.delete("/{id}")
async def delete_queue_event(id: str, request: Request):
    queue = request.app.state.queue

    # Fire and forget deletion to bypass disk I/O overhead
    await queue.delete(id)

    return {"message": "Event deleted successfully", "id": id}
