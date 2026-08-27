# Admin Chat Sessions Table Implementation Plan

This plan outlines how we will display the saved chat sessions for the selected user in the `UserDataAnalysis.vue` admin panel.

## Open Questions
- Do you want a "View Details" button in the table that opens a dialog showing the actual messages of that specific chat session, or is a high-level summary table (Name, Date, Tokens) sufficient for now?
  **Resolution**: Yes, create a dialog when the user selects a row in the table and clicks view to view the record single.

## Proposed Changes

### [MODIFY] `UserDataAnalysis.vue`

**1. Data Fetching & State:**
- Introduce new reactive variables: `userChatSessions` (array), `loadingChats` (boolean), `viewDialog` (boolean), and `selectedSession` (object).
- Add a `watch` effect on `selectedUserId`. Whenever the admin selects a different user from the dropdown, it triggers `fetchUserChats(newId)`.
- The `fetchUserChats` function will make a `GET` request to `http://127.0.0.1:8000/api/v1/chats/user/${userId}` to retrieve the list of `UserAIChatSession` objects for that user.

**2. UI Additions (Template):**
- Add a new `<v-row>` at the very bottom of the template.
- Inside it, place a `<v-card>` with a `<v-data-table>` component.
- Configure the table headers to display:
  - **Session Name** (fallback to "Untitled Chat" if empty)
  - **Created At** (formatted nicely, e.g., `Oct 24, 14:30`)
  - **Total Tokens** (colored based on usage)
  - **Actions** (View button)

**3. Dialog Implementation:**
- Create a `<v-dialog v-model="viewDialog" max-width="800" scrollable>` component.
- When the View button is clicked, set `selectedSession` and open the dialog.
- The dialog will render the session metadata (ID, Tokens, Date) as chips at the top.
- The dialog will iterate through `selectedSession.messages` and display them in a conversational format (differentiating AI and User messages using colors and alignment). It will also show the `quality` rating for AI messages if available.
