# AI Chat Session Persistence Implementation

We need to persist AI chat sessions to the NoSQL database using the provided Pydantic models (`UserChatMessage`, `AIChatMessage`, `UserAIChatSession`). We will implement full CRUD capabilities for chat sessions mapped by their `session_id`.

## Proposed Changes

### [MODIFY] `backend/src/v1/chats_router.py`
Use the existing FastAPI router file for managing AI chat sessions.

- **`POST /chats/`**: 
  - Accepts a `UserAIChatSession` model payload (omitting the `session_id` from the payload, or generating it if missing).
  - Generates the `session_id` dynamically using `uuid4` in Python.
  - Generates a default `name` (e.g., "New Chat") if one is not provided.
  - Saves the payload to the database using the key `chat_{session_id}`.
  - Returns the saved session.
- **`GET /chats/{session_id}`**: 
  - Retrieves a specific chat session by its ID (`chat_{session_id}`).
  - Returns a 404 if not found.
- **`GET /chats/user/{user_id}`**: 
  - Scans the database using the `chat_` prefix.
  - Filters and returns all chat sessions where `user_id` matches the requested ID without pagination.
- **`PUT /chats/{session_id}`**: 
  - Accepts a `UserAIChatSessionUpdate` model.
  - Fetches the existing session, updates the modified fields (like appending messages, updating token counts, and modifying timestamps), and saves it back to the database.
- **`DELETE /chats/{session_id}`**: 
  - Deletes the specific chat session from the database.

### [MODIFY] `backend/main.py`
- Import `chats_router` from `src.v1.chats_router`.
- Register the router to the main app instance: `app.include_router(chats_router, prefix="/api/v1")`.
