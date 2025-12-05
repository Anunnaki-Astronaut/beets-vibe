# Implementation Plan - Rich DJ Metadata

## 1. Architecture & Data Flow

### Backend
*   **New Job:** `run_analyze_attributes` in `backend/beets_flask/invoker/enqueue.py`.
    *   **Input:** List of Item IDs.
    *   **Logic:**
        1.  Open Beets Library.
        2.  Fetch items by ID.
        3.  Load `autobpm` and `keyfinder` plugins (if enabled).
        4.  Run analysis on each item.
        5.  Store results (`bpm`, `initial_key`) in Beets DB.
        6.  **Write tags to file** (standard Beets behavior).
        7.  Emit WebSocket update for item changes.
*   **New Endpoint:** `POST /api/library/analyze`
    *   **Body:** `{ "item_ids": [1, 2, 3] }`
    *   **Action:** Enqueues `run_analyze_attributes` job.
*   **Database:** No schema changes needed. `bpm` and `initial_key` are standard Beets Item fields.

### Frontend
*   **Library Browser:**
    *   Update `ItemListRow` to display BPM and Key.
    *   (Optional) Add sort options for BPM and Key if not already present.
*   **Item Details:**
    *   Add BPM and Key to the details grid.
    *   Add "Analyze" button to trigger the new endpoint.
    *   Reuse existing "Edit" modal to allow manual updates to BPM/Key via `PATCH /api/library/item/{id}`.

### Data Flow
1.  **User** clicks "Analyze" on Item Details page.
2.  **Frontend** calls `POST /api/library/analyze` with item ID.
3.  **Backend** enqueues `run_analyze_attributes` job to Redis `import_queue`.
4.  **Worker** picks up job, runs Beets plugins (`autobpm`, `keyfinder`).
5.  **Plugins** update `Item` fields in SQLite/MySQL.
6.  **Worker** emits `item_updated` event (or generic library update).
7.  **Frontend** receives update via WebSocket (or invalidates query) and refreshes view.

## 2. Implementation Steps

### Backend
1.  [ ] **Define Job:** Add `ANALYZE_ATTRIBUTES` to `EnqueueKind` in `backend/beets_flask/invoker/enqueue.py`.
2.  [ ] **Implement Job Logic:** Create `run_analyze_attributes` function in `backend/beets_flask/invoker/enqueue.py`.
    *   Needs to handle plugin loading/execution.
3.  [ ] **Create Endpoint:** Add `POST /api/library/analyze` in `backend/beets_flask/server/routes/library/metadata.py` (create file if needed, or use `items.py`).
4.  [ ] **Update API Types:** Ensure `ItemResponse` includes `bpm` and `initial_key` (already verified, but double check).

### Frontend
1.  [ ] **Update Types:** Ensure `ItemResponse` in `frontend/src/pythonTypes.ts` matches backend.
2.  [ ] **Library Browser:** Modify `ItemListRow` in `frontend/src/components/common/browser/items.tsx` to show BPM/Key columns.
3.  [ ] **Item Details:**
    *   Update `frontend/src/routes/library/(resources)/item.$itemId.index.tsx` to show BPM/Key.
    *   Add "Analyze" button.
    *   Update existing "Edit" dialog to include BPM/Key fields for manual corrections.
4.  [ ] **API Client:** Add `analyzeItems` function to `frontend/src/api/library.ts`.

## 3. Testing Strategy

*   **Unit Tests:**
    *   Test `run_analyze_attributes` with mocked Beets library and plugins.
    *   Test `POST /api/library/analyze` endpoint.
*   **Integration Tests:**
    *   Test the full flow: API call -> Job Enqueue -> Job Execution -> DB Update.
    *   Mock the actual binary execution of `keyfinder`/`autobpm` to avoid dependency issues in test environment.

## 4. Risks & Mitigations

*   **Plugin Availability:** `keyfinder` requires external binaries.
    *   *Mitigation:* Check if binary exists before running. If not, log warning/error and skip.
*   **Performance:** Analysis is slow.
    *   *Mitigation:* Run in background worker (already planned).