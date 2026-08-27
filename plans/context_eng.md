# Implement Context Window Token Tracking in AI Chat

This plan outlines the steps to display a real-time token counter in the chat interface's header, showing the accumulated tokens against the model's maximum context window.

## Proposed Changes

### Frontend Component

#### [MODIFY] `AIChat.vue` (file:///C:/Python-projects/Tense/frontend/frontend/src/components/AIChat.vue)
- **Script Updates:**
  - Define a reactive constant `maxContextLength` set to `12800` (for testing purposes).
  - Create a Vue `computed` property called `totalSessionTokens`. This property will iterate over the `messages` array and sum up the `realTokenCount` of all messages.
  - Create a Vue `computed` property called `tokenColorClass`. It will return:
    - `'text-blue'` if `totalSessionTokens` < 50% of `maxContextLength`
    - `'text-orange'` if `totalSessionTokens` >= 50% and < 80%
    - `'text-red'` if `totalSessionTokens` >= 80%
- **Template Updates:**
  - In the `<v-app-bar>` header section, after the `<v-spacer></v-spacer>`, add the token usage UI.
  - The label will use the computed `tokenColorClass` to dynamically change color based on usage, displaying `{{ totalSessionTokens }} / {{ maxContextLength }}`.

## Verification Plan

### Manual Verification
- Start the frontend development server.
- Open the AI Chat interface.
- Observe the token counter turning orange when passing 6,400 tokens and red when passing 10,240 tokens.
