# User Data Analysis Implementation Plan

This plan outlines the creation and integration of a new modular component, `UserDataAnalysis.vue`, which will provide deep insights into individual users' LLM spending and token usage.

## Proposed Changes

### `src/components/admin_components/UserDataAnalysis.vue`
This will be a brand new Vue component tailored for analyzing individual user token consumption.

**Data & State:**
- We will accept `users` as a prop from the parent (`AdminPanel.vue`) to populate the user selection dropdown.
- We will maintain a `selectedUserId` ref to track which user is currently being analyzed.
- We will generate **fake analytical data** (computed properties) that randomly shifts based on the selected user so that the charts are interactive and look real.

**UI Layout:**
1. **Header Row**: A title and a `<v-select>` dropdown to choose a user.
2. **Metrics Row (Row 1)**: Four compact summary cards showing:
   - **Total LLM Spend** (e.g., "$45.20")
   - **Tokens Per Model** (e.g., "Nemotron Ultra: 12k, Gemini 3.6: 8k")
   - **Avg. Tokens / Session** (e.g., "1,250")
   - **Total Tokens Left** (e.g., "30,000")
3. **Visualization Row (Row 2)**: 
   - A large container using `vue-echarts` to display a dynamic Pie/Donut Chart.
   - The chart will visualize the ratio of:
     - Tokens Left (e.g. 50%)
     - Usage for Nemotron Ultra (e.g. 30%)
     - Usage for Gemini 3.6 (e.g. 20%)

### `src/components/AdminPanel.vue`
- Import `UserDataAnalysis.vue`.
- Replace the current static placeholder for the `users` tab (around line 56) with the newly imported `<UserDataAnalysis>` component.
- Pass the `databaseUsers` down as a prop so the dropdown can populate real user names from the database.
