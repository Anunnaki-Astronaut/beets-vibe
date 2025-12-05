# Rich DJ Metadata

## Problem Statement

**Limited DJ-Specific Metadata:** While Beets excels at general music organization, it lacks built-in support for metadata crucial to DJs, such as BPM (Beats Per Minute) and musical key. DJs often rely on separate tools to analyze and tag their music with this information, creating a fragmented workflow.

**Current Workflow Pain Points:**
-   **Manual Analysis:** Users must run separate tools (e.g., Mixed In Key, KeyFinder) to analyze tracks.
-   **Fragmented Metadata:** BPM and key information often lives in non-standard tags or is not imported into the Beets library.
-   **Lack of Visibility:** Even if tags exist, the current `beets-vibe` UI does not display BPM or Key information in the library browser or item details.
-   **No Manual Correction:** There is no easy way to manually correct BPM or Key values within the `beets-vibe` interface if the automated analysis is incorrect.

## Goals

1.  **Automated Analysis:** Integrate with `autobpm` (or `bpmanalyser`) and `keyfinder` plugins to automatically detect and store BPM and Key during import.
2.  **Standardized Storage:** Store musical key information in standard fields, supporting both Open Key and Camelot notation.
3.  **UI Visibility:** Expose BPM and Key information in the Library Browser and Item Details views.
4.  **Manual Control:** Allow users to manually edit BPM and Key fields through the web interface.

## User Stories

-   **As a DJ**, I want my music to be automatically analyzed for BPM and Key when I import it, so I don't have to run separate tools.
-   **As a DJ**, I want to see the BPM and Key of my tracks in the library browser, so I can quickly find compatible tracks for mixing.
-   **As a user**, I want to be able to manually edit the BPM or Key of a track if the automated analysis is wrong, so my library is accurate.
-   **As a user**, I want to see both the musical key (e.g., "Cm") and the Camelot notation (e.g., "5A"), so I can use the notation system I prefer.

## UX Overview

### Library Browser
-   **New Columns:** Add "BPM" and "Key" columns to the tracks view in the Library Browser.
-   **Filtering/Sorting:** Allow sorting by BPM and Key. (Future: Filtering by BPM range or Key).

### Item Details
-   **Metadata Display:** Display BPM and Key prominently in the track details view.
-   **Edit Mode:** When in edit mode, provide input fields for BPM and Key.
    -   **BPM:** Numeric input.
    -   **Key:** Text input (potentially with a dropdown of standard keys).

### Import Preview
-   **Analysis Status:** Indicate if BPM/Key analysis is pending or completed for tracks in the import preview (if feasible with current import pipeline).

## Backend Changes

### Plugin Integration
-   **Configuration:** Ensure `autobpm` and `keyfinder` plugins are correctly configured and enabled (leveraging the work from the "Metadata Settings UI" feature).
-   **Dependencies:** Verify that the necessary binaries (e.g., `keyfinder-cli`) or Python libraries are available in the Docker container.

### Database/Model Updates
-   **Fields:** Ensure the `Item` model in `beets_flask` correctly maps and exposes the `bpm`, `initial_key` (and potentially `key_strength` or custom fields for Camelot) from the underlying Beets library.
-   **API:** Update the `Item` serialization in API responses to include these new fields.

### API Endpoints
-   **Update Item:** Ensure the existing item update endpoint (`PUT /api/library/items/{id}`) accepts and persists changes to `bpm` and `initial_key`.

## Risks

-   **Analysis Performance:** BPM and Key analysis can be CPU-intensive and slow down imports.
    -   *Mitigation:* Ensure analysis happens asynchronously or provide options to run it as a background task after import.
-   **Accuracy:** Automated analysis is not always 100% accurate.
    -   *Mitigation:* Emphasize the ability to manually edit these fields.
-   **Dependency Management:** `keyfinder` often requires external binaries that might be tricky to install in the Docker image.
    -   *Mitigation:* Investigate pure Python alternatives or ensure the Dockerfile includes the necessary package installations.