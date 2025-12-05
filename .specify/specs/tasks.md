# Task Breakdown - Rich DJ Metadata

## Phase 1: Backend Core

### Task 1.0: Update Docker Environment
**Description:**
Update the Dockerfile to include necessary system dependencies for analysis tools.
**Steps:**
1.  Modify `docker/Dockerfile`.
2.  Install `keyfinder-cli` (or `libkeyfinder`) and dependencies for `autobpm` (e.g., `libessentia` or `bpm-tools`).
**Acceptance Criteria:**
*   Container builds successfully.
*   `keyfinder-cli` and BPM tools are available in the container path.

### Task 1.1: Define Job for Attribute Analysis
**Description:**
Implement the background job that will run the analysis plugins (`autobpm`, `keyfinder`) on selected items.
**Steps:**
1.  Modify `backend/beets_flask/invoker/enqueue.py` to add `ANALYZE_ATTRIBUTES` to `EnqueueKind`.
2.  Implement `run_analyze_attributes` in `backend/beets_flask/invoker/job.py` (or `enqueue.py` if that's where jobs are defined - check existing patterns).
    *   Input: List of Item IDs.
    *   Logic:
        *   Retrieve items from Beets library.
        *   Check if `autobpm` and `keyfinder` plugins are enabled/configured.
        *   Execute analysis commands/plugins on the item's file path.
        *   Update `bpm` and `initial_key` fields in the Beets `Item`.
        *   Store changes in the database (`item.store()`).
        *   Emit a WebSocket event to notify frontend of updates.
**Acceptance Criteria:**
*   Job can be enqueued and executed via RQ.
*   Job successfully updates `bpm` and `initial_key` fields for a given item ID.
*   Job handles missing plugins gracefully (logs warning, skips analysis).

### Task 1.2: Implement Analysis API Endpoint
**Description:**
Create a new API endpoint to trigger the analysis job.
**Steps:**
1.  Create or update `backend/beets_flask/server/routes/library/metadata.py` (or similar).
2.  Add `POST /api/library/analyze` endpoint.
    *   Request Body: `{ "item_ids": [int] }`
    *   Response: `{ "job_id": str, "status": "queued" }`
3.  Endpoint should validate input and enqueue the `ANALYZE_ATTRIBUTES` job.
**Acceptance Criteria:**
*   Endpoint accepts a list of item IDs.
*   Endpoint returns 202 Accepted with job ID.
*   Invalid input returns 400 Bad Request.

### Task 1.3: Backend Tests
**Description:**
Add unit and integration tests for the new job and API endpoint.
**Steps:**
1.  Create `backend/tests/unit/test_invoker/test_analyze.py` (or similar).
    *   Test `run_analyze_attributes` logic with mocked plugins.
2.  Create `backend/tests/integration/test_routes/test_analyze.py`.
    *   Test `POST /api/library/analyze` endpoint.
**Acceptance Criteria:**
*   Tests pass with high coverage.
*   Mocking is used to avoid running actual heavy analysis tools during tests.

## Phase 2: Frontend Integration

### Task 2.1: Update API Client
**Description:**
Update the frontend API client to support the new endpoint.
**Steps:**
1.  Modify `frontend/src/api/library.ts`.
2.  Add `analyzeItems(itemIds: number[])` function calling `POST /api/library/analyze`.
**Acceptance Criteria:**
*   Function is typed correctly.
*   Function successfully calls the backend.

### Task 2.2: Update Library Browser
**Description:**
Display BPM and Key information in the main library list.
**Steps:**
1.  Modify `frontend/src/components/library/ItemListRow.tsx` (or equivalent).
2.  Add columns for "BPM" and "Key".
3.  Ensure these fields are included in the data fetched from the API (update `pythonTypes.ts` if necessary, though Beets `Item` should already have them).
**Acceptance Criteria:**
*   BPM and Key columns are visible in the library browser.
*   Data is displayed correctly for items that have it.
*   Columns handle missing data gracefully (empty or "-").

### Task 2.3: Update Item Details Page
**Description:**
Show and allow editing of BPM/Key on the item details page.
**Steps:**
1.  Modify `frontend/src/routes/library/item/$itemId.tsx` (or equivalent).
2.  Add BPM and Key to the metadata display grid.
3.  Add an "Analyze" button that calls `analyzeItems` for the current item.
    *   **Important:** The UI must warn the user that this action will modify the files on disk (write tags).
4.  Ensure the existing "Edit" functionality includes these fields.
**Acceptance Criteria:**
*   BPM and Key are displayed on the details page.
*   "Analyze" button triggers the backend job and shows a loading state/notification.
*   UI warns about file modification before analysis.
*   Users can manually edit BPM and Key values using the existing edit modal.

## Phase 3: Testing & Polish

### Task 3.1: End-to-End Testing
**Description:**
Verify the entire flow from UI to backend and back.
**Steps:**
1.  Manually test the "Analyze" button on an item.
2.  Verify the job runs (check logs/Redis).
3.  Verify the UI updates with the new values (via WebSocket or refresh).
4.  Verify manual editing works.
**Acceptance Criteria:**
*   Full feature works as expected in a dev environment.

### Task 3.2: Documentation
**Description:**
Update documentation to reflect the new feature.
**Steps:**
1.  Update `docs/` to mention the new "Rich DJ Metadata" capabilities.
2.  Add instructions on how to enable/configure `autobpm` and `keyfinder` plugins.
**Acceptance Criteria:**
*   Documentation is accurate and helpful.