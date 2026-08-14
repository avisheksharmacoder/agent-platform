from fastapi import APIRouter, Request

admin_router = APIRouter(prefix="/admin", tags=["admin"])


@admin_router.get("/")
async def get_admin_details(request: Request):
    # Ensure this is the AsyncDBEngine wrapper, not the raw Rust object!
    db = request.app.state.db

    # AWAIT the disk read so the thread pool handles it
    details = await db.get("admin_metrics_global")

    if details:
        return details

    # Return a safe zero-state if the db is fresh and no tickets exist yet
    return {
        "total_tickets": 0,
        "active_tickets": 0,
        "closed_tickets": 0,
        "total_users": 0,
        "total_tokens_spent": 0,
        "pending_queue_events": 0,
    }
