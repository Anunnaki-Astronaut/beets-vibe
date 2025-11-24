# Implementation Plan: Metadata Source & Credentials Settings UI

This document outlines the technical plan for implementing the "Metadata Source & Credentials Settings UI" feature.

## 1. Architecture

The implementation will follow the existing architectural patterns of the beets-vibe project, with a clear separation between the frontend and backend.

- **Backend (Quart)**: New API endpoints will be added to handle reading and writing configuration. A new service layer will be introduced to abstract the logic of handling YAML configuration files, ensuring that file operations are safe and maintain the integrity of the user's configuration.
- **Frontend (React)**: A new route and corresponding components will be created for the settings UI. TanStack Query will be used for managing server state, including fetching and updating configurations.

## 2. Data Flow

1.  **Fetch Settings**:
    - The frontend settings page will trigger a `GET /api/config/metadata_plugins` request on load.
    - The backend will read the `beets/config.yaml` file, parse it, and construct a JSON response containing the status of supported plugins and their configurations. Secrets will be redacted.
2.  **Update Settings**:
    - The user modifies settings in the UI (e.g., toggles a plugin, updates an API key).
    - On save, the frontend sends a `POST /api/config/metadata_plugins` request with a payload containing the updated settings for a specific plugin.
    - The backend receives the request, validates the payload, reads the latest version of the config file, updates it in memory using a YAML library that preserves comments and formatting, and writes the changes back to the file.
    - A success or error response is returned to the frontend.

## 3. API Design

The API will be an extension of the existing config routes located in `backend/beets_flask/server/routes/config.py`.

### `GET /api/config/metadata_plugins`

-   **Method**: `GET`
-   **Description**: Retrieves the configuration for all supported metadata plugins.
-   **Response Body**:
    ```json
    {
      "plugins": [
        {
          "name": "discogs",
          "enabled": true,
          "settings": {
            "token": "********"
          }
        },
        {
          "name": "spotify",
          "enabled": false,
          "settings": {
            "client_id": "********",
            "client_secret": "********"
          }
        }
      ]
    }
    ```

### `POST /api/config/metadata_plugins`

-   **Method**: `POST`
-   **Description**: Updates the configuration for a single plugin.
-   **Request Body**:
    ```json
    {
      "plugin": "discogs",
      "enabled": true,
      "settings": {
        "token": "new_secret_token"
      }
    }
    ```
-   **Success Response**: `200 OK` with a confirmation message.
-   **Error Response**: `400 Bad Request` for invalid input, `500 Internal Server Error` for file I/O problems.

## 4. Frontend Design

-   **Routing**: A new route will be added at `/settings/metadata`.
-   **Component Structure**:
    -   `routes/settings/metadata.tsx`: The main page component.
    -   `components/settings/PluginSettingsCard.tsx`: A reusable component to display and manage settings for a single plugin.
    -   `components/settings/CredentialsField.tsx`: A component for secret inputs that obscures the value.
-   **State Management**:
    -   `useQuery` from TanStack Query will fetch the initial settings.
    -   `useMutation` will be used to handle the update operation, providing loading and error states to the UI.
-   **UI**: Material-UI components will be used to build the form, including toggles for enabling/disabling plugins and text fields for credentials.

## 5. Config Persistence Strategy

-   **Library**: The `ruamel.yaml` library will be used in the backend for its ability to read and write YAML files while preserving comments, formatting, and structure. This is critical to avoid corrupting the user's `config.yaml`.
-   **Safety**:
    1.  When updating, the backend will first read the most current content of the `config.yaml` file.
    2.  It will then update the configuration in memory.
    3.  A backup of the original file will be created (e.g., `config.yaml.bak`) before writing the new content.
    4.  The new configuration is written to the original file.
    5.  If the write is successful, the backup can be removed.
-   **Secrets**:
    -   Secrets will be handled exclusively on the backend. They will never be logged.
    -   The `GET` API will return redacted values for secret fields.
    -   The frontend will use password-type inputs for secret fields.

## 6. Testing Strategy

-   **Backend**:
    -   Unit tests for the new configuration service layer, mocking file I/O to test the YAML parsing and updating logic.
    -   Integration tests for the API endpoints, using a temporary config file to verify that `GET` and `POST` requests work as expected.
-   **Frontend**:
    -   Component tests for the new settings components using Vitest and React Testing Library.
    -   Mock API responses will be used to test the behavior of the UI in different states (loading, success, error).

## 7. Rollout and Migration

-   **No Database Migration**: This feature does not introduce any database schema changes.
-   **Configuration**: Existing user configurations will be read correctly. The feature will only modify sections of the config file that it is responsible for.
-   **Documentation**: The official documentation will be updated to guide users on how to use the new settings UI.
-   **Phased Rollout**: The initial implementation will only support the plugins listed in the spec. The architecture will be designed to make it easy to add support for more plugins in the future.

This plan will be broken down into a series of actionable steps in a TODO list.