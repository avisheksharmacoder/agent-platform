# Tense - Technical Overview

Welcome to the **Tense** project! This document provides a high-level overview of the application's architecture and design, written simply for recruiters and team members.

## What is Tense?
Tense is a modern, full-stack ticketing and analytics platform. It features a seamless user interface for creating and managing tickets, paired with a powerful administrative dashboard for real-time monitoring and AI-driven data processing.

## Tech Stack Overview
- **Frontend**: Built with **Vue.js** as a Single Page Application (SPA). It uses **Vue Router** for seamless page transitions without reloading, and **Vuetify** for a beautiful, responsive, and material-design-inspired user interface.
- **Backend**: Powered by **FastAPI** (Python), ensuring blazing fast performance and asynchronous request handling.
- **Database**: Custom **LorealDB** for fast, local data storage and retrieval.
- **Charts & Visualizations**: Uses **ECharts** to display real-time analytics and metrics in the dashboard.

## Architecture Overview: How It Works

The Tense platform follows a modern, event-driven architecture that separates user interactions from heavy processing. At its core, the application is broken down into three main layers:
1. **The Client Layer (Vue.js)**: Where users and admins interact with the system.
2. **The API Layer (FastAPI)**: The bridge that handles instant requests and writes initial data to the database.
3. **The Background Layer (AI Workers)**: A silent engine running parallel to the web server that handles complex, time-consuming tasks like AI analysis without keeping the user waiting.

### The Ticket Lifecycle: From Creation to Assignment

Here is the step-by-step journey of how a ticket is raised and intelligently assigned to a human agent using Artificial Intelligence:

1. **Ticket Creation**: A user fills out a support form on the Vue.js frontend and hits submit. The frontend instantly sends this data to the FastAPI backend.
2. **Instant Saving & Queuing**: The backend immediately saves the new ticket into the database (LorealDB) as an "Unassigned" ticket. Simultaneously, it places an "event" into a background Database Queue to notify the system that a new ticket needs processing. The user gets an immediate success response—no loading screens or waiting for AI!
3. **The AI Worker Steps In**: Running continuously in the background, an asynchronous Python worker constantly polls the Database Queue for new tasks. It spots the newly raised ticket.
4. **AI Agent Analysis**: The worker hands the ticket's details (title, description, urgency) to the Autonomous AI Agent. Powered by Large Language Models (LLMs like Nemotron Ultra or Gemini), the AI Agent reads the ticket and determines its context, sentiment, and category.
5. **Smart Assignment**: Based on its analysis, the AI Agent decides which human support agent is best suited to resolve the issue (e.g., routing a billing issue to the finance team, or a technical bug to an engineer).
6. **Ticket Update**: Finally, the AI Worker updates the ticket in the database with the assigned human agent's name and any helpful summary notes. The next time the admin dashboard refreshes, the ticket is fully categorized and assigned!

## Key Features

### 1. Admin Dashboard & Real-Time Analytics
The application includes a dedicated Admin Panel that allows administrators to monitor the health and usage of the system. 
- **Database Metrics**: The dashboard visualizes real-time database traffic (operations per second) and benchmarks database latency (Insert, Scan, Get, Filter, Delete) in milliseconds.
- **User Analytics**: It tracks and visualizes individual user spending on Large Language Models (LLMs) and token consumption across different AI models.

### 2. AI-Driven Background Workers
The backend doesn't just respond to web requests; it also runs asynchronous background processes (workers) seamlessly alongside the main web server:
- **AI Task Queue Worker**: Continuously polls a database queue for pending tasks and hands them off to the autonomous AI agent.
- **Admin Metrics Worker**: A cron-like worker that wakes up every minute to calculate global system statistics (total tickets, active vs. closed tickets, token expenditures) and saves them for the dashboard to display.

### 3. Asynchronous by Design
From the Vue frontend fetching data without page reloads to the FastAPI backend running background tasks alongside web traffic, the entire system is built completely asynchronously. This ensures the app never "freezes" and can handle a high volume of traffic efficiently.

## Technical Design Deep-Dive

Under the hood, the backend (found in `src/v1/`) is structured to be highly scalable, strictly typed, and non-blocking:

### Strict Data Validation (`models.py`)
Tense relies heavily on **Pydantic** to define strict schemas for all data entering and leaving the system. Everything from `User` profiles to `Ticket` payloads and `QueueItem` events are strictly typed with validation rules (e.g., character limits, required fields, and precise Enums for status/priority). This ensures that bad data never reaches the database or the AI models.

### Asynchronous Database Engine (`database.py`)
To prevent the web server from freezing during heavy database reads or writes, the custom LorealDB engine is wrapped in an Asynchronous interface (`AsyncDBEngine` & `AsyncQueueDBEngine`). It uses Python's `asyncio.to_thread` to push all database interactions to background threads. This allows FastAPI to continue serving other users while the database does its heavy lifting.

### The Pydantic AI Agent (`agent.py`)
The system integrates with NVIDIA's Nemotron LLM via the **Pydantic-AI** framework. Instead of hoping the AI returns a usable string, we define a strict Pydantic model (`TicketResolution` requiring a `summary` and an `assignee_id`). The routing agent uses this schema to guarantee that the LLM responds with a perfectly formatted, machine-readable JSON object that the backend can safely parse and use to update the ticket without fear of hallucinations.

### Background Concurrency (`dependencies.py`)
The workers are built using native `asyncio` loops that run concurrently with the web server. 
- The **AI Queue Worker** is optimized to fetch tasks in small batches (limit=50) to avoid memory spikes, safely updating the task status (`pending` -> `processing` -> `completed`) to prevent duplicate processing. 
- The **Admin Metrics Worker** performs low-priority table scans every 60 seconds to pre-calculate expensive metrics (like total token spend), saving the result as a single cached record (`admin_metrics_global`). This ensures the admin dashboard loads instantly.
