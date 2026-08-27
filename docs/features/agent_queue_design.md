# Add Queue Table and Statistics to Database View

This plan outlines the steps to add a table displaying current agent queue tasks and a visual pie chart summarizing queue status in the Database view of the Admin Dashboard.

## Proposed Changes

### Backend API

#### [NEW] `queue_router.py` (file:///C:/Python-projects/Tense/backend/src/v1/queue_router.py)
- Create a new router file `queue_router.py` using `fastapi.APIRouter` with prefix `/queue` and tags `["queue"]`.
- Implement a GET endpoint `/` that fetches all events from `request.app.state.queue.scan_prefix("event_")` and returns them as a list of dictionaries.

#### [MODIFY] `main.py` (file:///C:/Python-projects/Tense/backend/main.py)
- Import `queue_router` from `src.v1.queue_router`.
- Register the router: `app.include_router(queue_router, prefix="/api/v1")`.

### Frontend Dashboard

#### [MODIFY] `Database.vue` (file:///C:/Python-projects/Tense/frontend/frontend/src/components/admin_components/Database.vue)
- Add a new `v-data-table` to display the queue elements. Place it above the Tickets and Users tables.
- Define table headers for the Queue (e.g., Event ID, Ticket ID, Operation Type, Status).
- Implement a pie chart using `vue-echarts` to visually represent the status of queue events.
  - Metrics: Completed (Green), Failed (Red), Processing (Orange), Pending/Queued (Blue).
  - The chart will update dynamically based on the queue data fetched.
- Create state variables (`queueEvents`, `loadingQueue`) to store the queue data and manage loading states.
- Implement a `fetchQueue` method to call the new `/api/v1/queue/` endpoint.
- Process the fetched data to calculate the counts for the pie chart.
- Trigger `fetchQueue` on component mount and within the existing global `refresh` function.

## Verification Plan

### Automated Tests
- Restart the backend server.
- Invoke the new `/api/v1/queue/` API endpoint and verify it returns all queue events correctly.

### Manual Verification
- Open the Admin Dashboard -> Database view.
- Verify the new pie chart accurately reflects the proportions of completed, pending, processing and failed queue tasks.
- Verify the Queue table is visible and displays correct event details.
- Create or update a ticket and verify the queue table and chart update correctly upon refreshing the page.
