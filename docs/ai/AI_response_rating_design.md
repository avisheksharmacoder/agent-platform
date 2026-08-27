# AI Message Rating System Implementation Plan

This plan outlines the steps to implement a per-message quality rating system for AI responses, utilizing the `Quality` enum defined in the backend models.

## Open Questions
- Does the Quality=HIGH chip need to be clickable again if the user wants to change their rating later, or should it be locked in once selected? 
  **Resolution**: Yes, let the user change the rating as they like. Use Vuetify colors: RED for Low, orange for MED, Blue for High and GREEN for Excellent.

## Proposed Changes

### Frontend Components

#### [MODIFY] `ChatBubble.vue`
- **Props & Emits**:
  - Add a `quality` prop (String, default: `null`).
  - Define an `emit` for `rate-quality`.
- **UI Additions**:
  - Add a new block at the bottom of the AI message template (`v-if="isAi"`).
  - Use a `v-menu` for both unrated and rated states.
  - **Unrated State**: Display a small icon button (e.g., a thumbs-up or star icon).
  - **Rated State**: Display a clickable chip formatted as `Quality=SELECTION` using Vuetify colors (`error` for low, `warning` for medium, `info` for high, `success` for excellent).
  - Emitting the selection: When an option in the menu is clicked, emit the lowercase string (e.g., `'high'`) to the parent.

#### [MODIFY] `AIChat.vue`
- **State Mapping**:
  - In `handleSelectSession()`: Update the `messages.value` mapping to extract and store `quality: m.quality || null` from the backend payload.
  - In `sendMessage()`: Ensure the newly generated AI message pushes `quality: aiMsgData.quality || null` initially to the local `messages.value` array.
  - In `getRawMessages()`: Include `quality: m.isAi ? (m.quality || null) : undefined` in the generated JSON payload so it can be serialized back to the database.
- **Event Handling & Database Sync**:
  - Bind `@rate-quality="(q) => handleRateQuality(msg.id, q)"` to the `<ChatBubble>` component in the `v-for` loop.
  - Create the `handleRateQuality` function:
    1. Find the target message by ID in `messages.value` and update its `quality` property.
    2. Generate the updated `rawHistory` using `getRawMessages()`.
    3. Make an asynchronous `PUT` request to `/api/v1/chats/${currentSessionId.value}` with the updated history to persist the rating to the backend database instantly.
