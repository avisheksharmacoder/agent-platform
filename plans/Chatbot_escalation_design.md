# Chatbot Escalation Design Document

## 1. Overview
This document outlines the architectural changes and implementation details required to integrate a Pydantic AI agent into the `Tense` support chatbot workflow. 

The goal is to enable the chatbot to autonomously detect when a user's query requires human intervention, and transparently escalate the interaction into a formal IT Support Ticket. The user will be presented with the proposed ticket details and must confirm its creation.

## 2. Pydantic Models (`backend/src/v1/models.py`)

To ensure strictly structured outputs and preserve the internal reasoning trace (for debugging and evidence), the `AIChatFinalResponse` will be a discriminated union composed of two possible schemas:

### `AIUserChatResponse`
Used for standard conversational interactions.
- `action`: `Literal["respond"]`
- `reasoning_trace`: Detailed step-by-step reasoning on why the AI chose to respond normally.
- `message`: `AIChatMessage`

### `AIUserChatTicketEscalation`
Used when the user explicitly requests a ticket or their issue dictates human intervention.
- `action`: `Literal["escalate"]`
- `reasoning_trace`: Step-by-step reasoning on why escalation is necessary.
- `title`: `str` (max 100 chars)
- `description`: `str` (max 1000 chars)
- `priority`: `Priority` (low, medium, high, critical)
- `tags`: `list[str] | None`

These schemas replace the previous raw text completion models, and syntax errors (such as missing type hints on Literals, improper Annotated usage) will be fixed.

## 3. Pydantic AI Agent (`backend/src/v1/agent.py`)

A new `chat_agent` will be defined using the `pydantic-ai` library.
- **Model**: `nvidia/nvidia-nemotron-nano-9b-v2`
- **Output Type**: `AgentOutput` (a union of `AgentRespond` and `AgentEscalate`)

### The NVIDIA Grammar Bug & Flat Models Workaround
The Nvidia API's JSON grammar parser struggles with nested Pydantic schemas. If we used our official `AIUserChatResponse` schema directly, `pydantic-ai` would generate a JSON schema containing nested `$defs` (for the inner `AIChatMessage` model), causing the API to throw a `Grammar error: Pointer '/$defs/AIChatMessage' does not exist` (400 Bad Request). 

To solve this, we introduce **flat intermediate models** in `agent.py`:
- **`AgentRespond`**: Contains `action`, `reasoning_trace`, and a simple `content` string (no nested `AIChatMessage`).
- **`AgentEscalate`**: Identical to `AIUserChatTicketEscalation`.

The agent exclusively outputs these flat models, completely avoiding the JSON grammar bug.

- **System Prompt**: 
  "You are a helpful IT support assistant. Evaluate the user's issue. If the user asks a general question, provide a helpful answer using the `respond` action. If the user explicitly asks to create a ticket, or describes a problem that requires human intervention, use the `escalate` action to generate a proposed ticket. You must write your reasoning into the `reasoning_trace` field before outputting the final action."

## 4. API Refactoring (`backend/src/v1/nemotron_router.py`)

The `/generate` endpoint will be modified to use `chat_agent.run()`.
- It will parse the incoming chat history and format it into a string prompt compatible with Pydantic AI.
- The endpoint will execute the agent and retrieve the flat `result.data`.
- **Model Transformation**: The router immediately maps the flat `AgentOutput` back into the official `AIChatFinalResponse` models from `models.py` (e.g. manually constructing the `AIChatMessage` object and injecting the exact token counts).
- The API returns the official `AIUserChatTicketEscalation` or `AIUserChatResponse` payload to the frontend.

## 5. Frontend UI Modifications (`frontend/src/components/AIChat.vue`)

The `sendMessage` function and UI renderer will be updated to handle the new structured payload.

### Handling the Escalation Payload
- When the API returns an `escalate` action, the chat interface will display a **4x2 Grid Card**.
- **Grid Layout**:
  - Row 1: Title (Label & Value)
  - Row 2: Description (Label & Value)
  - Row 3: Priority (Label & Value)
  - Row 4: Tags (Label & Value)
- Below the grid, two action buttons will be provided: **Yes (Create Ticket)** and **No (Cancel)**.

### Interactivity
- **Yes**: Triggers an HTTP POST request to the `/api/v1/tickets/` endpoint, creating the actual ticket in the database. An alert is shown to confirm success, and the chat UI updates to reflect the created ticket.
- **No**: Cancels the creation. A system message is injected into the chat stating "Ticket creation cancelled by user."

### Handling the Reasoning Trace
- Regardless of the action, the `reasoning_trace` returned by the model will be formatted into a Markdown `<details>` block (labeled "Thought Process") and prepended to the AI's message. This ensures exact parity with the prior Nemotron reasoning visualization.

## 6. Critical Context Engineering Metric: The Reasoning Trace Output Constraint

> [!CAUTION]
> **CRITICAL ARCHITECTURAL LEARNING:** Our initial implementations failed and hung the API indefinitely. **Do NOT force the model to generate a long "chain-of-thought" (reasoning trace) inside a structured JSON schema.** 

### The Problem (In Layman's Terms)
When we use `pydantic-ai` to enforce a strict output structure (like forcing the model to output a ticket escalation), the NVIDIA API uses a strict "grammar engine" to make sure the LLM's response is perfectly valid JSON. 

Initially, we asked the model to write a long, unpredictable paragraph explaining its thoughts *inside* a strict JSON field (e.g., `"reasoning_trace": "Well, the user said their computer crashed, so I should..."`). 

Forcing a Large Language Model to write a long, free-flowing essay while simultaneously obeying the strict, rigid rules of a JSON schema (especially inside a complex Discriminated Union) causes the grammar engine to choke. The API simply hangs in an infinite loop trying to reconcile the unpredictable long-form text with the strict JSON formatting. 

### The Confusion: Input Context vs. Output Generation
It is a common misconception that this fails because the reasoning traces are being sent back into the chat history, thus "cluttering the context window" and confusing the model on subsequent turns. **This is false.** Our frontend already extracts *only* the message content, so reasoning traces never re-enter the input context. 

The failure happens purely at the **Output Generation** phase. The model gets stuck trying to format its long thoughts into the rigid JSON box.

### The Solution
We completely removed the `reasoning_trace` from the `AgentRespond` and `AgentEscalate` Pydantic models and updated the system prompt to stop asking for it. By doing this, the model only has to output short, highly predictable fields (like `action` and `content`). Without the burden of generating a massive paragraph inside a JSON string, the model resolves and returns the escalation payload almost instantly without hanging!
