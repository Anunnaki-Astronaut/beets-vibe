# Task Breakdown: Metadata Source & Credentials Settings UI

This document breaks down the implementation of the "Metadata Source & Credentials Settings UI" feature into smaller, actionable tasks.

## Phase 1: Backend

### Task 1.1: Refine Configuration Service
- **File**: `backend/beets_flask/config_service.py`
- **Description**: Refine the `ConfigService` to ensure it robustly handles YAML parsing, updating, and writing. The current implementation is a good start, but needs to be hardened.
- **Acceptance Criteria**:
    - The service correctly reads the `beets/config.yaml` file.
    - The `get_metadata_plugins_config` method returns the correct enabled status and redacted settings for all supported plugins.
    - The `update_metadata_plugin_config` method correctly modifies the `plugins` list and plugin-specific settings.
    - A backup of the config file is created before writing.
    - **[SECRET]**: This task handles reading and writing files that may contain secrets.

### Task 1.2: Refine API Endpoints
- **File**: `backend/beets_flask/server/routes/config.py`
- **Description**: Ensure the `GET` and `POST` endpoints in the `config_bp` blueprint correctly use the `ConfigService` and handle all success and error cases.
- **Acceptance Criteria**:
    - `GET /api/config/metadata_plugins` returns a 200 status with the correct JSON payload.
    - `POST /api/config/metadata_plugins` returns a 200 status on success and updates the config.
    - The `POST` endpoint returns a 400 error for invalid requests (e.g., missing plugin name).
    - The `POST` endpoint returns a 500 error if the `ConfigService` throws an exception.

### Task 1.3: Add Backend Tests [X]
- **File**: `backend/tests/integration/test_routes/test_config.py` (and new unit test files)
- **Description**: Write unit tests for the `ConfigService` and integration tests for the new API endpoints.
- **Acceptance Criteria**:
    - Unit tests for `ConfigService` cover successful updates, backup creation, and edge cases.
    - Integration tests for the `GET` endpoint verify the response structure and redaction of secrets.
    - Integration tests for the `POST` endpoint verify that the config file is correctly modified.

## Phase 2: Frontend

### Task 2.1: Create Settings Page Route
- **File**: `frontend/src/routeTree.gen.ts`, `frontend/src/routes/settings.tsx`
- **Description**: Add a new top-level navigation item for "Settings" and create the route for the "Metadata Sources" page.
- **Acceptance Criteria**:
    - A "Settings" link appears in the main navigation.
    - Navigating to `/settings/metadata` renders a placeholder page.

### Task 2.2: Build the Plugin Settings UI
- **Files**: `frontend/src/routes/settings.tsx`, `frontend/src/components/settings/PluginSettingsCard.tsx`
- **Description**: Create the main UI for the settings page, which will display a list of `PluginSettingsCard` components.
- **Acceptance Criteria**:
    - The page fetches data from the `GET /api/config/metadata_plugins` endpoint using TanStack Query.
    - A `PluginSettingsCard` is rendered for each plugin returned by the API.
    - Each card displays the plugin name, an enable/disable toggle, and input fields for its settings.
    - **[SECRET]**: A `CredentialsField` component should be used for any field containing a secret, which will render a password input.

### Task 2.3: Implement Update Logic
- **File**: `frontend/src/components/settings/PluginSettingsCard.tsx`
- **Description**: Implement the logic to save changes for a single plugin.
- **Acceptance Criteria**:
    - Clicking "Save" on a card triggers a `useMutation` hook from TanStack Query.
    - The mutation sends a `POST` request to `/api/config/metadata_plugins` with the updated data for that plugin.
    - The UI displays loading indicators while the mutation is in progress.
    - Success and error messages are displayed to the user.

### Task 2.4: Add Frontend Tests
- **File**: New test files in the `frontend` directory.
- **Description**: Write component tests for the new settings page and its components.
- **Acceptance Criteria**:
    - Tests for `PluginSettingsCard` verify that it correctly displays data and that user interactions (toggling, typing) update its state.
    - Tests for the main settings page verify that it correctly renders a list of cards based on mock API data.

## Phase 3: Documentation and Finalization

### Task 3.1: Update User Documentation
- **File**: `beets_flask_project_summary.md` and/or `docs/configuration.md`
- **Description**: Update the project documentation to explain how to use the new UI for managing metadata plugins and credentials.
- **Acceptance Criteria**:
    - The documentation includes screenshots of the new settings page.
    - It clearly explains which plugins are supported and how to enter credentials.
    - It mentions that for more advanced configuration, manual editing of `config.yaml` is still required.

### Task 3.2: Manual End-to-End Testing
- **Description**: Perform a full manual test of the feature in a local development environment.
- **Acceptance Criteria**:
    - Enable and disable a plugin, and verify the change in `config.yaml`.
    - Add, update, and clear credentials for Discogs and Spotify, and verify the changes.
    - Ensure that comments and other parts of the `config.yaml` file are not disturbed.
    - Verify that redacted secrets are not visible in the browser's network inspector.