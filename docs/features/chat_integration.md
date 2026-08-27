# Chat Sessions Frontend Integration Plan

We need to fully connect the Vue frontend (`AIChat.vue` and `AIChatLeftPanel.vue`) to the backend `chats_router.py` and refactor `nemotron_router.py` to use the new structured Pydantic message models.

## Technical Deep Dive: Orchestrator Architecture

The **Vue Frontend** will act as the "orchestrator" for this process to keep our backend routers cleanly separated. Here is the exact step-by-step loop for a single message flow:

1. **User Types a Message**: The frontend creates a `UserChatMessage`.
2. **Save User Message**: The frontend immediately sends a `PUT` request to `chats_router` to save the user's message to the database.
3. **Ask the AI**: The frontend sends a `POST` request to `nemotron_router`. Instead of just sending a string, it sends the **entire chat history** (a list of `UserChatMessage` and `AIChatMessage` models) so the AI remembers the context of the conversation.
4. **AI Processing**: `nemotron_router` maps these Pydantic models down to the simple `{"role": "user", "content": "..."}` format expected by the LLM API. It then talks to the API, concatenates the reasoning and response together into an expandable markdown block, and returns a strictly formatted `AIChatMessage` back to the frontend.
5. **Save AI Message**: The frontend receives that `AIChatMessage` and sends another `PUT` request to `chats_router` to save the AI's response to the database.

This architecture is best practice because `nemotron_router` stays completely focused on AI generation, and `chats_router` stays completely focused on database storage.

## Proposed Changes

### [MODIFY] `backend/src/v1/nemotron_router.py`
- Refactor the input payload (`QueryRequest`) to accept a list of historical messages: `messages: list[UserChatMessage | AIChatMessage]`. This allows the Nemotron AI to have full conversational context.
- Update the generation logic to map the Pydantic messages to the OpenAI dictionary format (`[{"role": m.role.value, "content": m.content}]`).
- **Reasoning Concatenation**: If the Nemotron API returns reasoning tokens, concatenate them directly with the response content formatted as a markdown `<details><summary>Thought Process</summary>...` block.
- Return the generated response as a strictly formatted `AIChatMessage` model.

### [MODIFY] `frontend/frontend/src/components/AIChatLeftPanel.vue`
- On mount, fetch the user's chat sessions via `GET /api/v1/chats/user/{user_id}` (using the user ID from the `authStore`).
- Remove hardcoded UI sessions and render the fetched sessions dynamically.
- Update the **Rename** dialog to trigger `PUT /api/v1/chats/{session_id}`.
- Update the **Delete** dialog to trigger `DELETE /api/v1/chats/{session_id}`.
- Update the component to emit the selected session back to `AIChat.vue` when a user clicks on an older session.

### [MODIFY] `frontend/frontend/src/components/AIChat.vue`
- Track the `currentSessionId`.
- Implement the orchestrator workflow described above.
- Remove the dedicated `:reasoning` prop logic since the reasoning will now naturally flow through the main Markdown renderer as an expandable HTML block.
