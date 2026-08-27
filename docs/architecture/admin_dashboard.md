# Admin Dashboard Technical Implementation Plan

## Goal
To implement an Admin Dashboard UI (`AdminPanel.vue`) and introduce Vue Router to seamlessly switch between the Main Ticket UI and the Admin Dashboard, whilst preserving the top Navigation Bar across both views.

## Technical Details

### 1. Architectural Shift (Vue Router Setup)
Currently, `App.vue` statically renders the `<MainUI />` component, which in turn includes `<Navbar />`.
Because we are adding a second distinct view (`AdminPanel.vue`), we need to transition the application to a Single Page Application (SPA) routing model using `vue-router`.

- **`router/index.js`**: We will define two core routes:
  - `path: '/'` rendering `MainUI.vue`
  - `path: '/admin'` rendering `AdminPanel.vue`

### 2. Global Navbar (App.vue changes)
You requested that the top `Navbar.vue` remains visible at all times. 
To achieve this efficiently without duplicating code:
- We will lift the `<Navbar />` component out of `MainUI.vue` and place it directly into `App.vue`.
- `App.vue` will now act as the global layout shell:
  ```vue
  <v-app>
    <Navbar />
    <router-view /> <!-- This will dynamically inject MainUI or AdminPanel based on the URL -->
  </v-app>
  ```
- Because `Navbar.vue` utilizes Vuetify's `<v-app-bar>`, the `<v-main>` containers within `MainUI` and `AdminPanel` will automatically calculate and apply the correct top-padding so content doesn't get hidden under the header.

### 3. Navbar Routing Logic
The "Admin" icon button in `Navbar.vue` currently just prints to the console.
- We will import `useRouter` and `useRoute` from `vue-router`.
- The button's logic will dynamically switch: if you are on the main UI (`/`), clicking it will push to `/admin`. If you are already on `/admin`, it will act as a back button and push to `/` (home).
- We'll dynamically change the label/icon to "Home" if the user is currently viewing the Admin Panel.

### 4. AdminPanel.vue Implementation
The `AdminPanel.vue` will act as a dashboard layout container.
- **Vuetify Layout**: It will utilize `<v-navigation-drawer>` for the left-side pane and `<v-main>` for the content area.
- **Navigation Options**: The drawer will render a `v-list` containing 4 fixed options:
  1. Agent Data Analysis
  2. Tickets Analysis
  3. Tokens Analysis
  4. User Data Analysis
- **Dynamic Content**: A reactive state variable `activeTab` will track the currently selected option. The main content area will conditionally render placeholder metrics depending on the value of `activeTab`.

### 5. MainUI.vue Adjustments
Since `<Navbar />` is moving to `App.vue`:
- We will remove the `<Navbar />` import and tag from `MainUI.vue`.
- We will ensure `MainUI.vue` functions perfectly as a child route without doubling up on navigation bars.
