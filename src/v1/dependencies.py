import asyncio
from datetime import datetime
import os
from dotenv import load_dotenv
from .agent import routing_agent


import asyncio


async def ai_queue_worker(queue, db):
    """
    Background worker that continuously drains the queue of pending tasks.
    """
    print("🤖 AI Queue Worker initialized and running...")

    while True:
        try:
            load_dotenv(override=True)
            if os.getenv("AGENT_ACTIVE", "False") != "True":
                await asyncio.sleep(60)
                continue

            # 1. LET RUST DO THE FILTERING.
            # Fetch only up to 50 pending tasks at a time. No full table scans!
            pending_tasks = await queue.filter_by_metadata(
                "status", "pending", limit=50, offset=0
            )

            if not pending_tasks:
                # If the queue is empty, sleep for 5 seconds (not 60!) and check again
                await asyncio.sleep(5)
                continue

            # 2. Drain the fetched batch
            for task_id, task_data in pending_tasks:
                # Claim the task
                task_data["status"] = "processing"
                await queue.upsert(task_id, task_data)

                try:
                    await process_ticket(task_data, db)
                    task_data["status"] = "completed"
                except Exception as ex:
                    print(f"Error processing task {task_id}: {ex}")
                    task_data["status"] = "failed"

                # Save final status
                await queue.upsert(task_id, task_data)

            # Note: We do NOT sleep here! We loop back immediately to fetch the next
            # batch of 50 until the queue is completely empty.

        except asyncio.CancelledError:
            print("🤖 AI Queue Worker shutting down gracefully...")
            break
        except Exception as e:
            print(f"❌ AI Worker error: {e}")
            await asyncio.sleep(5)


async def admin_metrics_worker(queue, db):
    """
    Background worker that calculates system metrics every 1 minute
    and saves them to a global admin record.
    """
    print("📊 Admin Metrics Worker initialized and running...")
    while True:
        try:
            print(
                f"[{datetime.now().strftime('%H:%M:%S')}] 📊 Calculating admin metrics..."
            )

            # Scan all tickets and users in the database
            tickets = await db.scan_prefix("ticket_")
            users = await db.scan_prefix("user_")

            # Tally metrics
            total_tickets = len(tickets)
            total_users = len(users)
            active_tickets = 0
            closed_tickets = 0
            total_tokens = 0

            for _, ticket_data in tickets:
                if ticket_data.get("status") == "closed":
                    closed_tickets += 1
                else:
                    active_tickets += 1

                total_tokens += ticket_data.get("total_tokens", 0)

            # Find how many items are waiting in the queue
            pending_events = len(await queue.filter_by_metadata("status", "pending"))

            # Build the metrics payload
            metrics_payload = {
                "total_tickets": total_tickets,
                "active_tickets": active_tickets,
                "closed_tickets": closed_tickets,
                "total_users": total_users,
                "total_tokens_spent": total_tokens,
                "pending_queue_events": pending_events,
                "last_updated": datetime.now().isoformat(),
            }

            # Save to database
            await db.upsert("admin_metrics_global", metrics_payload)
            print("✅ Admin metrics updated successfully.")

            # Wait for 1 minute before running again
            await asyncio.sleep(60)

        except asyncio.CancelledError:
            print("📊 Admin Metrics Worker shutting down...")
            break
        except Exception as e:
            print(f"❌ Metrics Worker error: {e}")
            await asyncio.sleep(60)


# Assign Task to human agent via AI Agent.
async def process_ticket(task: dict, db):
    ticket_id = task.get("ticket_id")
    if not ticket_id:
        return

    try:
        # 1. Fetch details directly from the queue payload
        ticket_title = task.get("ticket_title", "No Title")
        ticket_description = task.get("ticket_description", "No Description")

        # 2. FETCH AGENTS DYNAMICALLY (The right way)
        # We use the new human_agent field from the Pydantic schema!
        # Passing the boolean as a string to satisfy PyO3 strict typing.
        agent_records = await db.filter_by_metadata("human_agent", "true")
        
        # Fallback if the Rust backend stringified it using Python's str() instead of JSON
        if not agent_records:
            agent_records = await db.filter_by_metadata("human_agent", "True")

        # Format the roster
        roster_text = "\n".join(
            [
                f"- Name: {payload.get('name')} | ID: {uid} | Expertise: {payload.get('designation', 'Support Staff')}"
                for uid, payload in agent_records
            ]
        )

        # 3. Assemble the prompt
        user_prompt = f"""
        TICKET DETAILS:
        Title: {ticket_title}
        Description: {ticket_description}

        AVAILABLE SUPPORT AGENTS:
        {roster_text}
        """

        # 4. Execute the Agent (Inference)
        print(f"Routing ticket {ticket_id}...")
        result = await routing_agent.run(user_prompt)
        resolution = getattr(result, "output", getattr(result, "data", None))

        # 5. Update the ticket
        ticket = await db.get(ticket_id)
        if ticket:
            ticket["assignee_id"] = resolution.assignee_id
            if hasattr(resolution, "summary"):
                ticket["summary"] = resolution.summary
            await db.upsert(ticket_id, ticket)
            print(f"Successfully routed {ticket_id} to {resolution.assignee_id}")
        else:
            print(f"Warning: Ticket {ticket_id} missing during routing.")

    except Exception as e:
        print(f"Failed to process {ticket_id}: {e}")
