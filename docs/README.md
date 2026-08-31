# Tense — Technical Overview

Tense is a full-stack ticketing and analytics platform with **AI-driven ticket triaging**, asynchronous background processing, system observability, and a **RAG-powered support chatbot** currently under development.

The project is designed around separating user-facing request handling from longer-running AI and analytical workloads, allowing the API layer to remain responsive while background workers process asynchronous tasks.

[Frontend-repo](https://github.com/avisheksharmacoder/agent-platform-frontend)

## Project Status

| Feature                           | Status                   |
| --------------------------------- | ------------------------ |
| Automatic Agentic Ticket Triaging | ✅ Complete               |
| RAG-Powered Support Chatbot       | 🚧 In Development (~80%) |

The ticket-triaging pipeline is fully implemented and operational. The RAG-powered chatbot is actively being developed, with the core retrieval, context construction, agent integration, and conversation infrastructure already implemented.

---

## Core Functionalities

### 1. Automatic Agentic Ticket Triaging

When a user creates a ticket, the ticket is immediately persisted and an asynchronous queue event is generated for processing.

A background AI worker retrieves the event, invokes the triage agent, analyzes the ticket, and updates the ticket with the appropriate support-agent assignment and AI-generated summary.

**Status: Complete**

### 2. RAG-Powered Support Chatbot

Tense includes a Support AI Agent designed to answer user questions using **Retrieval-Augmented Generation (RAG)**.

The chatbot architecture includes:

* Document/data retrieval
* Embedding generation
* Context construction
* Agent integration
* Conversation/session persistence
* Structured AI responses
* Response evaluation and rating

**Status: In Development (~80%)**

---

# Tech Stack

### Frontend

* **Vue.js** — Single Page Application (SPA)
* **Vue Router** — Client-side routing
* **Vuetify** — UI component framework
* **ECharts** — Analytics and data visualization

### Backend

* **FastAPI** — Asynchronous HTTP API
* **Python** — Application and AI orchestration
* **Pydantic** — Runtime data validation and structured schemas
* **Pydantic AI** — Agent framework and structured LLM interaction
* **asyncio** — Asynchronous task execution and background workers

### Database

* **LorealDB** — Custom local database engine
* **AsyncDBEngine** — Asynchronous interface for database operations
* **AsyncQueueDBEngine** — Database-backed queue interface

### AI

* Large Language Models such as **NVIDIA Nemotron** and **Gemini**
* Retrieval-Augmented Generation (RAG)
* Embedding-based retrieval
* Structured model outputs
* AI response evaluation

---

# Architecture Overview

Tense follows an event-driven architecture that separates user-facing request handling from background processing.

At a high level, the system consists of three primary layers:

```text
┌─────────────────────────────┐
│        Client Layer         │
│          Vue.js             │
│                             │
│   Users + Administrators    │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│          API Layer          │
│          FastAPI            │
│                             │
│  Request validation         │
│  Authentication             │
│  Database operations        │
│  Queue event creation       │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│       Database Layer        │
│          LorealDB           │
│                             │
│  Tickets                    │
│  Users                      │
│  Sessions                   │
│  Queue events               │
│  Metrics                    │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│     Background Workers      │
│                             │
│  AI Queue Worker            │
│  Metrics Worker             │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│        AI Processing        │
│                             │
│  LLM → Analysis → Result    │
└─────────────────────────────┘
```

The key architectural principle is that **long-running AI processing does not need to remain inside the user's HTTP request path**.

---

# Ticket Lifecycle

The ticket-triaging pipeline follows this flow:

```text
User
 │
 ▼
Create Ticket
 │
 ▼
FastAPI
 │
 ├──────────────► Persist Ticket
 │
 └──────────────► Create Queue Event
                         │
                         ▼
                   AI Queue Worker
                         │
                         ▼
                    AI Agent
                         │
                         ▼
                  Ticket Analysis
                         │
                         ▼
                  Agent Assignment
                         │
                         ▼
                  Update Ticket
```

### 1. Ticket Creation

A user submits a support ticket through the Vue.js frontend.

The frontend sends the ticket data to the FastAPI backend.

### 2. Immediate Persistence and Queuing

FastAPI validates the incoming request using Pydantic models and immediately persists the ticket in LorealDB.

The ticket initially remains unassigned.

At the same time, an event is inserted into the database-backed queue indicating that the ticket requires AI processing.

The API can therefore return the initial request result without waiting for the AI model to finish processing the ticket.

### 3. AI Queue Worker

A background worker continuously checks the database queue for pending events.

New events are retrieved in batches rather than loading the entire queue into memory.

### 4. AI Agent Analysis

The worker passes the relevant ticket information to the AI agent.

The agent can use an LLM such as NVIDIA Nemotron or Gemini to analyze the ticket and determine information such as:

* Ticket context
* Category
* Urgency
* Sentiment
* Appropriate support-agent assignment
* Summary information

### 5. Agent Assignment

The resulting structured agent output is used by the application to determine the appropriate human support agent.

For example:

```text
Billing issue
     ↓
Finance / Billing Support

Technical issue
     ↓
Technical Support
```

### 6. Ticket Update

After successful processing, the worker updates the ticket with the AI-generated information and support-agent assignment.

The administrative dashboard can then display the processed ticket.

---

# Engineering Highlights

## 1. Event-Driven Background Processing

The application uses a **database-backed queue** to move longer-running work out of the HTTP request path.

A simplified queue lifecycle is:

```text
pending
   │
   ▼
processing
   │
   ├──────► completed
   │
   └──────► failed
```

Queue events are processed by a dedicated background worker.

The worker processes tasks in small batches to control memory usage and marks events as `processing` before executing them to reduce the possibility of duplicate processing.

The current worker batch size is **50 events**.

---

## 2. Asynchronous Request Processing

FastAPI handles HTTP requests asynchronously.

LorealDB exposes an asynchronous interface through `AsyncDBEngine` and `AsyncQueueDBEngine`. Because the underlying database operations may be blocking, the asynchronous layer delegates those operations to background threads using Python's:

```python
asyncio.to_thread()
```

This prevents blocking database operations from directly blocking the FastAPI event loop.

The architecture therefore combines:

```text
Async HTTP handling
        +
Thread-offloaded blocking database operations
        +
Independent background workers
```

This keeps the request path isolated from longer-running database and AI workloads.

---

## 3. Structured AI Outputs

The AI agent uses Pydantic models to define the expected structure of model responses.

For example, the ticket-resolution output is represented by a schema containing fields such as:

```text
TicketResolution
├── summary
└── assignee_id
```

Instead of treating an LLM response as an arbitrary string, the application validates the response against an explicit schema before using it.

This provides a predictable machine-readable interface between the AI layer and the rest of the application.

Structured output validation helps detect malformed responses, but it does not guarantee that the model's semantic decision is correct. Model quality is therefore treated as a separate evaluation problem.

---

# Admin Dashboard & Observability

Tense includes an administrative dashboard for monitoring system activity and AI usage.

## Database Metrics

The dashboard provides database performance information including:

* Operations per second
* Insert latency
* Scan latency
* Get latency
* Filter latency
* Delete latency

These metrics provide visibility into the performance characteristics of the custom database layer.

## User Analytics

The dashboard tracks AI usage at the user level, including:

* LLM token consumption
* Model usage
* Estimated LLM expenditure

This provides visibility into the operational cost of AI-powered features.

## Queue Monitoring

The administration interface also exposes queue activity, allowing administrators to inspect background processing events and their current states.

Queue states include:

* Pending
* Processing
* Completed
* Failed

---

# Background Workers

Tense currently uses multiple background workers for workloads that should not execute inside normal API request paths.

## AI Queue Worker

The AI Queue Worker:

1. Retrieves pending queue events.
2. Processes them in controlled batches.
3. Marks events as processing.
4. Invokes the appropriate AI processing pipeline.
5. Updates the relevant database records.
6. Marks successful events as completed.
7. Records failures when processing cannot be completed.

The worker uses asynchronous execution and is designed to operate independently of incoming HTTP traffic.

## Metrics Worker

The Metrics Worker periodically calculates aggregate system statistics.

It runs approximately once every 60 seconds and calculates metrics such as:

* Total tickets
* Active tickets
* Closed tickets
* Token expenditure
* Other global system statistics

The resulting aggregate data is persisted as a cached global metrics record:

```text
admin_metrics_global
```

This prevents the dashboard from repeatedly executing expensive aggregate queries whenever an administrator opens or refreshes the metrics view.

---

# Technical Design

The backend is organized under:

```text
backend/src/v1/
```

The application uses explicit schemas, asynchronous interfaces, and separate processing components to keep responsibilities isolated.

## Pydantic Data Models

Pydantic models define the application's data contracts.

They are used for entities and operations such as:

* Users
* Tickets
* Queue events
* AI responses
* API request payloads
* API response payloads

Validation includes constraints such as:

* Required fields
* Character limits
* Enumerated values
* Status values
* Ticket priorities
* Structured AI output fields

This provides runtime validation at application boundaries before data is persisted or passed into downstream components.

---

# RAG Architecture

The RAG-powered chatbot is currently under development.

The intended architecture separates retrieval, context construction, and agent execution:

```text
User Message
     │
     ▼
Chat API
     │
     ▼
Context Construction
     │
     ├──────► Query / Retrieval
     │             │
     │             ▼
     │        Relevant Data
     │
     ▼
RAG Context
     │
     ▼
Support AI Agent
     │
     ▼
Structured Response
     │
     ▼
Chat Session
```

The RAG subsystem includes dedicated components for:

* Embedding generation
* Retrieval
* RAG database interaction
* Context construction
* Agent/tool integration
* Chat session persistence
* AI response evaluation

The chatbot remains under active development while these components are integrated and refined.

---

# AI Response Evaluation

Tense includes infrastructure for evaluating AI-generated responses.

Responses can be rated and stored so that the behavior of the system can be compared against future model or prompt changes.

This provides a foundation for:

* Comparing different LLMs
* Evaluating prompt changes
* Measuring response quality
* Detecting regressions
* Benchmarking future versions of the AI pipeline

The evaluation system is intended to make AI improvements measurable rather than relying exclusively on subjective testing.

---

# Project Documentation

The repository contains engineering documentation covering the major architectural and implementation areas of Tense.

```text
docs/
├── ai/
├── architecture/
├── decisions/
├── features/
└── issues/
```

The documentation includes design notes for:

* Agent/RAG integration
* Embedding architecture
* Context engineering
* RAG routing
* Background workers
* Queue processing
* Chat sessions
* Database metrics
* Administrative interfaces
* AI response evaluation
* System investigations and debugging

These documents are maintained alongside the implementation so that architectural decisions and implementation details remain discoverable within the repository.

---

# Current Development Roadmap

## Completed

* [x] User ticket creation
* [x] Ticket persistence
* [x] Database-backed queue
* [x] Background AI processing
* [x] Automatic ticket triaging
* [x] AI-based support-agent assignment
* [x] AI-generated ticket summaries
* [x] Administrative dashboard
* [x] Database performance metrics
* [x] User AI usage analytics
* [x] Background metrics processing

## In Development

* [ ] Complete RAG-powered support chatbot
* [ ] Complete chatbot/agent integration
* [ ] Finalize retrieval and context behavior
* [ ] Expand AI response evaluation
* [ ] Benchmark and refine chatbot performance

---

# Project Philosophy

Tense is being developed around a simple principle:

> **Keep user-facing operations fast and predictable, while moving expensive AI and analytical workloads into independently managed background processing.**

The project also treats AI behavior as an engineering problem rather than simply an API integration. Model outputs are structured and validated, retrieval and context construction are explicit parts of the architecture, and response quality can be evaluated against future changes.

The result is intended to be a practical exploration of building **AI-enabled systems rather than simply applications that call an LLM API**.
