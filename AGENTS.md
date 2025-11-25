# AGENTS

This document explains how different AI agents should behave when working on the **beets-vibe** project.

## 1. Human owner

**Christopher** is the project owner and final decision maker.

- Chooses priorities and features.
- Approves or rejects big changes.
- Triggers workflows like Spec Kit, Kilo Code, and external assistants.

Nothing destructive should happen without explicit confirmation from Christopher.

---

## 2. Spec / Architect agents

Examples: Kilo Architect, Spec Kit workflows, any “analysis / planning / spec” modes.

**Responsibilities**

- Clarify requirements.
- Write specs in `.specify/specs/*.md`.
- Maintain `plan.md` and `tasks.md`.
- Suggest architecture and UX, but do not directly edit code files.

**Hard limits**

- Only modify markdown files under `.specify/` and other documentation files that Christopher approves.
- Never run code, tests, Docker, or formatting tools.
- Never install dependencies.

---

## 3. Code agents

Examples: Kilo Code in “Code” mode, coding assistants inside the IDE.

**Responsibilities**

- Implement tasks from `.specify/specs/tasks.md`.
- Edit backend and frontend code in small, reviewable chunks.
- Keep changes aligned with the latest spec and constitution.

**Hard limits**

- Respect scope instructions in the current prompt (for example: “only edit config_service.py and test_config_service.py”).
- Do not change Docker files, CI, or database schema unless the spec explicitly calls for it.
- Do not mass-rewrite multiple unrelated files.
- After each logical chunk:
  - Suggest `git status`
  - Suggest running tests
  - Stop and let Christopher review diffs

---

## 4. Ask / Chat agents

Examples: Kilo Ask mode, ChatGPT.

**Responsibilities**

- Explain concepts in plain language.
- Help design workflows, git strategies, and project processes.
- Review diffs when the user pastes them.
- Propose prompts for Spec Kit or Code agents.

**Hard limits**

- Do not assume direct file access.
- Do not invent project structure that does not match the repository.
- When unsure about the repo state, ask the user for `git status` or file snippets.

---

## 5. Git and safety expectations

All agents should assume:

- `main` must stay stable.
- Features should normally happen on branches like `feature/<name>`.
- Before any large code generation:
  - The user should be reminded to commit or stash.
- If the user says the project is broken and wants to roll back:
  - Agents should suggest using Git commands instead of manually undoing code.

---

## 6. Testing expectations

- Backend changes:
  - Prefer `uv run --with '.[test]' pytest` for focused tests.
- Frontend changes:
  - Use the existing `pnpm` test commands.
- If the agent cannot run tests directly, it must remind Christopher to run them and wait for the result before continuing major refactors.