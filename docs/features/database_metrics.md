# LorealDB Analytics Implementation Plan

This plan outlines the integration of real-time database analytics and latency benchmarking into the `Database.vue` component.

## Goal
To provide administrators with a real-time visualization of LorealDB's performance and traffic, directly at the top of the Database tab.

## Proposed Changes

### 1. UI Additions in `Database.vue`
At the top of the component (just below the header), we will introduce a new `v-row` split into a 1x2 grid (`cols="12" md="6"`):

**Left Panel: Real-Time Traffic Spikes**
- A `vue-echarts` Line Chart.
- We will set up a Vue `setInterval` that pushes new random data points every 1-2 seconds to simulate real-time database traffic volume (operations per second).
- The chart will automatically slide, keeping the last 30 data points visible to create a "live monitor" effect.

**Right Panel: Operation Latency Benchmark**
- A `vue-echarts` Line/Bar Chart displaying the latency (in milliseconds) for 5 core database operations: `Insert`, `Scan`, `Get`, `Filter`, and `Delete`.
- A **"Run DB Benchmark"** button located near this chart.

### 2. Benchmark Logic Integration
When the user clicks the "Run DB Benchmark" button, the frontend will sequentially execute the following operations against the FastAPI backend, measuring the round-trip time using `performance.now()`:

1. **Insert**: `POST /api/v1/tickets/` (Creates a dummy testing ticket with title `"BENCHMARK_TEST"`).
2. **Get**: `GET /api/v1/tickets/{dummy_id}` (Fetches the exact ticket).
3. **Scan**: `GET /api/v1/tickets/` (Fetches all tickets).
4. **Metadata Filter**: `GET /api/v1/tickets/?status=open`
5. **Delete**: `DELETE /api/v1/tickets/{dummy_id}` (Cleans up the dummy ticket).

Once all 5 operations complete, the array of latencies will be passed to the ECharts instance, visually updating the chart to reflect the actual LorealDB response times.
