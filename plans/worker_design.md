# Background Workers Design

This document outlines the design and implementation of two background workers using `asyncio` and integrating them into the FastAPI application lifespan.

## AI Queue Worker
**Goal**: Poll the queue database for pending tasks and pass them to the AI agent.

- Currently implemented as a **placeholder stub** that simply prints an initialization message and stays active.
- Real logic to fetch `status="pending"` items will be added later.

## Admin Metrics Worker
**Goal**: Calculate global system metrics every minute and save them to the primary database.

- Runs an infinite loop waking up every 60 seconds.
- Uses `db.scan_prefix("ticket_")` and `db.scan_prefix("user_")` to calculate:
    - Total tickets, users
    - Active vs. Closed tickets
    - Total token expenditure
- Queries `queue.filter_by_metadata("status", "pending")` for pending event count.
- Upserts the combined metrics into `db` under the key `admin_metrics_global`.
- Prints terminal log output every minute to confirm activity.

## Application Lifecycle (`main.py`)
Both workers are spawned as concurrent asyncio tasks (`asyncio.create_task()`) inside the FastAPI `lifespan` context manager. When FastAPI shuts down, `.cancel()` is called on both tasks for a graceful exit before closing the database engines.
