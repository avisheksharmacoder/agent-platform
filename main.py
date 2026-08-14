from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from lorealdb import DBEngine
from src.v1.database import AsyncDBEngine, AsyncQueueDBEngine
from contextlib import asynccontextmanager
from src.v1.tickets_router import tickets_router
from src.v1.users_router import users_router
from src.v1.nemotron_router import nemotron_router
from src.v1.queue_router import queue_router
from src.v1.agent_state_router import agent_state_router
from src.v1.admin_router import admin_router
import asyncio
import time
from fastapi import Request
from src.v1.dependencies import ai_queue_worker
from datetime import datetime


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Booting up backend and mounting databases...")

    # create the ticket queue instance.
    app.state.queue = AsyncQueueDBEngine("database/queue.redb")

    # create the database for storing records.
    app.state.db = AsyncDBEngine("database/database.redb")

    # Start the background workers
    app.state.ai_worker_task = asyncio.create_task(
        ai_queue_worker(app.state.queue, app.state.db)
    )

    # generate the admin metrics.
    print("📊 Running startup metrics sync (O(N) scan)...")
    try:
        tickets = await app.state.db.scan_prefix("ticket_")
        users = await app.state.db.scan_prefix("user_")

        active_tickets = 0
        closed_tickets = 0
        total_tokens = 0

        for _, ticket_data in tickets:
            if ticket_data.get("status") == "closed":
                closed_tickets += 1
            else:
                active_tickets += 1
            total_tokens += ticket_data.get("total_tokens", 0)

        # We can use our efficient metadata filter here!
        pending_events = await app.state.queue.filter_by_metadata("status", "pending")

        metrics_payload = {
            "total_tickets": len(tickets),
            "active_tickets": active_tickets,
            "closed_tickets": closed_tickets,
            "total_users": len(users),
            "total_tokens_spent": total_tokens,
            "pending_queue_events": len(pending_events) if pending_events else 0,
            "last_updated": datetime.now().isoformat(),
        }

        # Seed/Overwrite the global record
        await app.state.db.upsert("admin_metrics_global", metrics_payload)
        print("✅ Startup metrics synced perfectly.")
    except Exception as e:
        print(f"⚠️ Warning: Could not sync metrics on startup: {e}")

    # We pass the db and queue to the worker and keep a reference to the task
    ai_worker_task = asyncio.create_task(ai_queue_worker(app.state.queue, app.state.db))

    # yield control back to app.
    yield

    print("Shutting down database and background workers...")
    # Clean up the model and release the resources
    # Cancel the background tasks so they stop gracefully
    app.state.ai_worker_task.cancel()

    app.state.queue.close_engine()
    app.state.db.close_engine()
    print("app closed!")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global request tracker for Ops/Sec
app.state.request_timestamps = []


@app.middleware("http")
async def track_requests(request: Request, call_next):
    now = time.time()
    app.state.request_timestamps.append(now)
    # Prune older than 10 seconds
    app.state.request_timestamps = [
        t for t in app.state.request_timestamps if now - t <= 10
    ]
    return await call_next(request)


@app.get("/api/v1/metrics/traffic")
def get_traffic():
    now = time.time()
    app.state.request_timestamps = [
        t for t in app.state.request_timestamps if now - t <= 10
    ]
    ops_per_sec = len(app.state.request_timestamps) / 10.0
    return {"ops_per_sec": round(ops_per_sec, 2)}


# Register routers
app.include_router(tickets_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(nemotron_router, prefix="/api/v1")
app.include_router(queue_router, prefix="/api/v1")
app.include_router(agent_state_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
