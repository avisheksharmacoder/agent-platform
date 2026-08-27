# Frontend RAG Bubble UX Implementation Plan

## Overview
This document outlines the implementation strategy to expose internal RAG data (documents retrieved by the AI agent) all the way to the frontend Vue component, ensuring total transparency of the AI's thought process.

## 1. Backend Payload Extraction

### `models.py`
We are adding the `sources` field to `AIUserChatTicketEscalation` (it already exists in `AIChatMessage` for standard responses). This ensures that even if the AI decides to escalate to a ticket, we can still transmit the knowledge base documents it reviewed.

### `nemotron_router.py`
After the `chat_agent` finishes its execution, Pydantic-AI returns a `RunResult` containing the entire conversation history, including tool executions. We will iterate through `result.new_messages()` to find the `ToolReturnPart` where `tool_name == "search_knowledge_base"`. We will extract this data and attach it to the final Pydantic response models before serializing to JSON.

## 2. Frontend UX Implementation

### `AIChat.vue`
We will update the chat parsing logic to ingest the `sources` data. When a message contains `sources`, we will render a special "Knowledge Retrieval" RAG bubble directly above the AI's response text.

This RAG bubble will use a sleek Vuetify `v-expansion-panels` component to remain compact, but when clicked, it will expand to display the title and resolution of the exact tickets the AI analyzed.
