# Feature Specification: Metadata Source & Credentials Settings UI

**Feature Branch**: `feature/metadata-settings-ui`
**Created**: 2025-11-24
**Status**: Draft
**Input**: User description: "Create a specification for a new "Metadata Source & Credentials Settings UI" feature for the beets-vibe project (my fork of beets-flask)."

## 1. Problem

Currently, configuring metadata sources (like MusicBrainz, Discogs, Spotify) and their corresponding API credentials in `beets-vibe` requires manual editing of YAML configuration files (`config.yaml`). This process is error-prone, cumbersome for non-technical users, and lacks a user-friendly interface. There is no central place in the UI to manage which plugins are active or to securely store and update API keys.

## 2. Goals

- Provide a web UI for users to view, enable/disable, and configure metadata sources and plugins.
- Allow users to securely enter, update, and clear credentials (API keys, tokens) for these sources.
- Persist these settings safely into the existing `beets` and `beets-vibe` configuration files.
- Ensure the feature is compliant with the `beets-vibe` constitution, especially regarding safe file operations and clear API/UI separation.

## 3. Non-Goals

- This feature will not manage the installation or removal of beets plugins themselves.
- It will not provide a full-fledged configuration editor for all of `beets` or `beets-vibe`. The scope is limited to metadata plugins and their credentials.
- It will not support every possible beets plugin in the first iteration.

## 4. User Stories

### User Story 1 - View and Manage Metadata Plugins (Priority: P1)
As a user, I want to see a list of available metadata plugins so that I can enable or disable them through the web UI.

**Why this priority**: This is the foundational feature that allows users to control their metadata sources without touching config files.
**Independent Test**: The UI correctly displays the status (enabled/disabled) of the in-scope plugins, and toggling a plugin correctly updates the `beets/config.yaml` file.
**Acceptance Scenarios**:
1.  **Given** the `discogs` plugin is enabled in `config.yaml`, **When** I navigate to the settings page, **Then** the Discogs plugin toggle should be "on".
2.  **Given** the `lyrics` plugin is disabled, **When** I enable it via the UI and save, **Then** the `plugins` list in `beets/config.yaml` should be updated to include `lyrics`.

### User Story 2 - Manage Discogs Credentials (Priority: P1)
As a user, I want to enter, update, and clear my Discogs API token so that the Discogs plugin can authenticate and fetch metadata.

**Why this priority**: Discogs is a primary metadata source for many users and often requires authentication for full access.
**Independent Test**: Entering a token in the UI and saving results in the `discogs` section of `beets/config.yaml` being correctly updated with the new token.
**Acceptance Scenarios**:
1.  **Given** I have no Discogs token set, **When** I enter a valid token and save, **Then** the `discogs.token` key in `config.yaml` is populated.
2.  **Given** an existing token, **When** I clear the token field and save, **Then** the `discogs.token` key is removed from `config.yaml`.

### User Story 3 - Manage Spotify Credentials (Priority: P2)
As a user, I want to enter and update my Spotify API credentials (client ID and client secret) so that beets plugins that use Spotify can function correctly.

**Why this priority**: Spotify is another key source for metadata and playlist integration.
**Independent Test**: The UI allows for entering both a client ID and a client secret for Spotify, and saving them updates the `spotify` section in `config.yaml`.
**Acceptance Scenarios**:
1.  **Given** no Spotify credentials are set, **When** I enter a client ID and secret and save, **Then** `spotify.client_id` and `spotify.client_secret` are correctly written to `config.yaml`.

## 5. UX Overview

- A new "Settings" page will be added to the main navigation.
- Inside "Settings", there will be a "Metadata Sources" tab.
- This tab will display a list of supported plugins (e.g., Discogs, Spotify, MusicBrainz).
- Each plugin will have:
    - An enable/disable toggle switch.
    - A section for credential management (e.g., text fields for API keys/tokens).
    - Input fields for secrets will use a password-type input to obscure the value.
    - A "Save" button will persist the changes for that section.
- The UI will show a confirmation message on successful save and display validation errors (e.g., "Invalid token format") if the backend reports an issue.

## 6. Backend Changes

### API Endpoints
New endpoints will be created under `/api/config/`. The existing config routes in `backend/beets_flask/server/routes/config.py` will be expanded.

- `GET /api/config/metadata_plugins`:
  - **Action**: Reads the current `beets/config.yaml` to determine which plugins are enabled and retrieves their settings.
  - **Response**: A JSON object detailing the status and configuration of each supported plugin. Secrets will be redacted (e.g., `"token": "********"`).
- `POST /api/config/metadata_plugins`:
  - **Action**: Receives a JSON payload with updated settings for one or more plugins. It will validate the input and then safely update the `beets/config.yaml` and/or `beets-flask/config.yaml` files.
  - **Request Body**: `{ "plugin": "discogs", "enabled": true, "settings": { "token": "new_token_value" } }`
  - **Security**: The backend will handle writing to the YAML files. It will use a library that preserves comments and structure to avoid breaking the file. Secrets will never be logged. This adheres to the **Safe File Operations** and **Non-Destructive by Default** principles.
  - **Logging**: A log entry will be created upon successful configuration change, e.g., `INFO: User updated 'discogs' plugin settings.`. This aligns with the **Comprehensive Logging** principle.

### In-Scope Plugins (First Iteration)
- **MusicBrainz**: (Enabled by default, no credentials needed)
- **Discogs**: Enable/disable, `token` credential.
- **Beatport**: Enable/disable.
- **Spotify**: Enable/disable, `client_id` and `client_secret` credentials.
- **Lyrics**: Enable/disable.
- **BPM (autobpm)**: Enable/disable.
- **Key (keyfinder)**: Enable/disable.
- **ReplayGain**: Enable/disable.

### Out-of-Scope Plugins
- Any plugin not listed above. The framework should be extensible to add more later.

## 7. Risks and Open Questions

- **Risk**: Concurrently editing the config file from the UI and manually could lead to conflicts.
  - **Mitigation**: The backend will read the config file just before writing to minimize the race condition window. A file-locking mechanism could be considered if this proves to be a significant issue.
- **Risk**: Storing secrets in plain text in YAML is standard for Beets but may be a security concern for some users.
  - **Mitigation**: The documentation will clearly state how secrets are stored. The UI will obscure secret inputs. For Unraid/Docker users, environment variables will continue to take precedence, which is a more secure practice. This aligns with the **Docker First** principle.
- **Open Question**: How should the UI handle plugins that have many configuration options beyond just credentials?
  - **Answer for v1**: We will only expose the most common and essential settings (enable/disable, credentials). Advanced configuration will still require manual file editing.