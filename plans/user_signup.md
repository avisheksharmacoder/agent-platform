# Login and Signup System Implementation Plan

This plan details the implementation of a client-side authentication system that integrates with your existing FastAPI backend, specifically using the updated `User` model.

## Proposed Changes

### Backend API Updates
#### [MODIFY] `backend/src/v1/users_router.py`
- **New Endpoint**: Add `@users_router.post("/login")`.
  - It will accept a Pydantic model for login credentials (`email` and `password`).
  - It will iterate over `db.scan_prefix("user_")` to find a match for the provided email and password.
  - Proper comments will be added to explain that this endpoint prevents the insecure and unscalable practice of downloading the entire user list to the frontend just to verify credentials.
  - Returns the user object if successful, or raises an HTTP 401 Unauthorized if credentials don't match.

### State Management
#### [NEW] `frontend/frontend/src/stores/auth.js`
- Create a Pinia store to handle authentication.
- **`signup(userData)`**: Makes a `POST` request to the backend `/users/` endpoint with the full `UserCreate` payload. On success, it calls `login`.
- **`login(email, password)`**: Makes a `POST` request to the new `/users/login` backend endpoint. On success, stores the returned user details in `localStorage` and sets a session expiry (20 minutes).
- **`checkSession()`**: Runs on app load/route changes. Checks `localStorage` to see if the session has expired (time > 20 mins). If expired, clears the storage and prompts re-login.

### UI Components
#### [MODIFY] `frontend/frontend/src/components/Login.vue`
- Add a Vuetify form with Email and Password inputs.
- Hook into `authStore.login`. Show validation/unauthorized errors if the backend rejects the credentials.
- Add a redirect link to the Signup page.

#### [MODIFY] `frontend/frontend/src/components/Signup.vue`
- Add a Vuetify form with the following inputs:
  - Name
  - Email
  - Password
  - Designation
  - Human Agent (Checkbox/Switch)
- Implement strict client-side password validation (regex checking for lowercase, uppercase, number, special character, min 8 characters).
- Hook into `authStore.signup`, defaulting the `tokens_budget` to `50000000` for all new users.
- Add a redirect link to the Login page.

#### [MODIFY] `frontend/frontend/src/App.vue`
- Conditionally render the `<Navbar />` so it is hidden on the `/login` and `/signup` routes.

### Routing
#### [MODIFY] `frontend/frontend/src/router/index.js`
- Add `/login` mapping to `Login.vue`.
- Add `/signup` mapping to `Signup.vue`.
- Add a `beforeEach` navigation guard to check `authStore.checkSession()` and redirect unauthenticated users to `/login`.

### Additional Fixes and Enhancements (Post-Review)
#### [MODIFY] `backend/src/v1/users_router.py`
- **Email Uniqueness on Creation**: Updated `create_user` to scan the database and ensure the requested `user_email` is not already taken. Raises `HTTP 400 Bad Request` if it is.
- **Email Uniqueness on Update**: Updated `update_user` to verify that if a user changes their email, the new email isn't already assigned to a different user. Raises `HTTP 400 Bad Request` if it is.
- **URL Pathing Bug Fix**: Noted that the FastAPI router is prefixed with `/api/v1` instead of `/v1` in `main.py`, requiring the frontend fetch URLs to be updated to match the correct paths.

#### [MODIFY] `backend/src/v1/models.py`
- **Tokens Budget Validation**: Increased the Pydantic `le` (less than or equal to) constraint for `tokens_budget` in the `User` model from `1,000,000` to `50,000,000` to accommodate the requested default 50 million tokens budget for new users.
