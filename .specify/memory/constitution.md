<!--
Sync Impact Report:
- Version: 1.0.0
- Added sections: Core Principles, Additional Constraints, Development Workflow, Governance
- Templates requiring updates: None
- Follow-up TODOs: None
-->
# beets-vibe Constitution

## Core Principles

### I. Safe File Operations
All destructive file operations (delete, move, overwrite) MUST be confirmed by the user. The system will never delete user data without explicit consent. Rationale: Protecting the user's music library is the highest priority.

### II. Clear API/UI Separation
The backend (Quart) and frontend (React) MUST remain decoupled. The frontend will only interact with the backend through documented RESTful API and WebSocket endpoints. This ensures modularity and allows for independent development and testing.

### III. Docker First
The primary method for distribution and development is Docker. All features and dependencies MUST be compatible with the existing Docker and Docker Compose setup to ensure a consistent environment for all users, including those on Unraid.

### IV. Comprehensive Logging
All backend modules MUST use the centralized logging system (`beets_flask/logger.py`). Logging should be structured and provide clear, actionable information for debugging. Frontend errors should be caught by error boundaries and reported.

### V. Non-Destructive by Default
The application's default behavior for any operation MUST be non-destructive. Destructive actions are only performed after explicit user confirmation. This includes file operations, metadata changes, and library modifications.

### VI. Extensibility Through Plugins
The architecture MUST remain compatible with the Beets plugin ecosystem. Changes to the core application should not break existing plugin functionality without a clear migration path.

### VII. Test-Driven Development
All new features and bug fixes MUST be accompanied by appropriate tests. This includes unit tests for backend logic, integration tests for API endpoints, and component tests for the frontend.

## Additional Constraints

- **Technology Stack:** The core technologies (Quart, React, SQLAlchemy, Redis) are foundational. Any proposal to change them requires a formal architectural review.
- **Dependencies:** New dependencies should be added judiciously and must be compatible with the existing stack and licenses.

## Development Workflow

- **Code Quality:** All code must adhere to the standards enforced by `ruff` and `mypy` for the backend, and `eslint` and `prettier` for the frontend.
- **Branching:** Feature development should happen in separate branches. The `main` branch should always be stable.
- **Pull Requests:** All changes must be submitted via pull requests and reviewed by at least one other contributor.

## Governance

This constitution is the source of truth for the project's development principles. Any proposed changes to this constitution must be submitted as a pull request and approved by the project maintainers.

**Version**: 1.0.0 | **Ratified**: 2025-11-24 | **Last Amended**: 2025-11-24
