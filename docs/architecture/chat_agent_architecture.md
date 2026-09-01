## Tense Assistant - 3-Agent AI Architecture

The backend uses a sophisticated **3-Agent Classification Pattern** to handle user interactions dynamically. This design ensures that general IT questions are answered quickly with raw text, while ticketing requests are strictly formatted into structured data, bypassing token truncation bugs often found in LLM structured output parsing.

### How It Works

The routing logic is located in `backend/src/v1/nemotron_router.py` and powered by `backend/src/v1/agent.py`. The architecture consists of three specialized agents working together:

#### 1. The Classifier Agent (`classifier_agent`)
When a user sends a message, it is first routed to the **Classifier Agent**.
* **Goal**: Analyze the user's intent.
* **Output**: A strict Enum (`ActionType.CHAT` or `ActionType.TICKET`).
* **Behavior**: If the user explicitly asks to create a ticket or escalate an issue, it returns `TICKET`. Otherwise, it defaults to `CHAT`.

#### 2. The Chat Worker (`chat_worker`)
If the classifier determines the user just needs an answer or code snippet, the request is passed to the **Chat Worker**.
* **Goal**: Answer IT and support questions.
* **Output**: Native raw markdown string (No structured output / tool calling).
* **Behavior**: Because it outputs raw text natively, it bypasses bugs related to LLM JSON parsing (like truncating long markdown code blocks). The backend takes this string and wraps it into an `AIChatMessage` for the frontend.

#### 3. The Ticket Worker (`ticket_worker`)
If the classifier determines the user wants to create a ticket, the request is passed to the **Ticket Worker**.
* **Goal**: Extract the necessary fields to draft a support ticket.
* **Output**: A structured Pydantic model (`AITicketDraft`).
* **Behavior**: The agent strictly extracts the `title`, `description`, `priority`, and `tags`. The backend serializes this model into JSON, places it inside the `content` field of an `AIChatMessage`, and sends it to the frontend for user confirmation.

### Flow Summary
1. User -> API `/generate`
2. API -> **Classifier Agent** -> (`CHAT` | `TICKET`)
3. If `CHAT` -> **Chat Worker** -> Raw Markdown -> `AIChatMessage`
4. If `TICKET` -> **Ticket Worker** -> `AITicketDraft` -> JSON String -> `AIChatMessage`
5. API -> Frontend