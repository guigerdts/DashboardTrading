# Frontend MT5 Import Specification

## Purpose

Complete CSV upload → preview → confirm → result UI for MT5 trade imports, consuming existing POST `/api/imports/mt5/preview` and POST `/api/imports/mt5/confirm`. This is a new domain — no existing behavior is modified.

## API Contracts

All shapes verified against `backend/app/modules/imports/schemas.py` and `backend/app/modules/imports/router.py` (PRs #1–4, on main).

### PreviewResponse

| Field | Type | Description |
|-------|------|-------------|
| `total_rows` | `int` | Total rows parsed from CSV |
| `valid_rows` | `int` | Rows passing validation |
| `invalid_rows` | `int` | Rows failing validation |
| `rows` | `RowResultPreview[]` | Per-row validation results |

### RowResultPreview

| Field | Type | Description |
|-------|------|-------------|
| `row_index` | `int` | 1-indexed row number |
| `broker_ticket` | `str` | Ticket from CSV |
| `status` | `"valid"` \| `"invalid"` | Row validity |
| `errors` | `str[]` | Validation errors |
| `warnings` | `str[]` | Warnings |

### ImportResult

| Field | Type | Description |
|-------|------|-------------|
| `total_rows` | `int` | Total rows |
| `imported_rows` | `int` | Successfully imported |
| `skipped_rows` | `int` | Skipped (duplicate ticket) |
| `error_rows` | `int` | Failed rows |
| `rows` | `RowResult[]` | Per-row import outcomes |

### RowResult

| Field | Type | Description |
|-------|------|-------------|
| `row_index` | `int` | 1-indexed row number |
| `broker_ticket` | `str` \| `null` | Ticket or null on parse failure |
| `status` | `"imported"` \| `"skipped"` \| `"error"` | Import outcome |
| `trade_id` | `int` \| `null` | Created trade ID if imported |
| `errors` | `str[]` | Import errors |
| `warnings` | `str[]` | Warnings |

### Endpoints

| Method | Path | Request | 200 | Error |
|--------|------|---------|-----|-------|
| `POST` | `/api/imports/mt5/preview` | `multipart/form-data`, field `file: UploadFile` | `PreviewResponse` | `422` |
| `POST` | `/api/imports/mt5/confirm` | `multipart/form-data`, field `file: UploadFile` | `ImportResult` | `422` |

Both endpoints return FastAPI validation error detail structure on 422.

## Requirements

### REQ-SPEC-01: Empty state handling

The system MUST handle these preview outcomes:

| Condition | Preview Behavior | Confirm |
|-----------|-----------------|---------|
| 0 total rows | total=0, valid=0, invalid=0 | Disabled (no rows) |
| 0 valid rows | valid=0, invalid=N, per-row errors shown | Disabled (no valid rows) |
| All rows valid | valid=N, invalid=0 | Enabled |

#### Scenario: Empty CSV file

- GIVEN a CSV file with header row only (no data rows)
- WHEN preview completes
- THEN total_rows is 0, valid_rows is 0, invalid_rows is 0
- AND confirm button is disabled

#### Scenario: All rows invalid

- GIVEN a CSV with all rows failing validation
- WHEN preview completes
- THEN each row shows its validation errors
- AND confirm button is disabled

### REQ-SPEC-02: Navigation during loading

If the user navigates away during `preview-loading` or `confirm-loading`, the system MUST NOT show a confirmation dialog. React Query mutation cancellation on unmount is sufficient (preview is read-only; confirm is a single POST — no multi-step transaction).

#### Scenario: Navigate during confirm loading

- GIVEN the user is in `confirm-loading` state
- WHEN they navigate away from `/imports/mt5`
- THEN no confirmation prompt is shown
- AND the mutation is cancelled on unmount

### REQ-SPEC-03: Retry and flow control

| Condition | Retry Available | Behavior |
|-----------|----------------|----------|
| Preview error | Yes | Retry preview with same file via `useMutation.mutate()` |
| Confirm error | Yes | Retry confirm with same file and preview |
| File changed | N/A — new preview required | Preview cleared, confirm disabled |
| Successful confirm | No | Flow complete. "Import another" resets to idle. |

#### Scenario: Retry preview after network error

- GIVEN the user is in `preview-error` state
- WHEN they click "Retry Preview"
- THEN the same file is re-submitted to POST `/api/imports/mt5/preview`
- AND state transitions to `preview-loading`

#### Scenario: File change after successful preview

- GIVEN the user is in `preview-success` state
- WHEN they select a different file
- THEN the preview is cleared
- AND confirm is disabled
- AND state resets to `file-selected`

## Acceptance Criteria Scenarios

### SC-01: Valid CSV import

- GIVEN a valid MT5 CSV file
- WHEN the user uploads and previews it
- THEN preview shows `valid_rows > 0`
- WHEN the user confirms
- THEN `imported_rows > 0`
- AND the result screen shows total/imported/skipped/error counts
- AND "Go to Dashboard" and "Import another file" buttons are visible

### SC-02: Invalid CSV data

- GIVEN a CSV with malformed rows (e.g. non-numeric volume, missing ticket)
- WHEN the user previews it
- THEN `invalid_rows > 0`
- AND each invalid row shows its errors in the UI
- AND confirm button is disabled

### SC-03: File exceeds 5MB

- GIVEN a file larger than 5MB
- WHEN the user selects it via DnD or file picker
- THEN client-side validation fails
- AND no API request is sent
- AND an error message ("File must be ≤ 5 MB") is displayed

### SC-04: Wrong file extension

- GIVEN a file with extension `.xlsx` or `.txt`
- WHEN the user selects it
- THEN client-side validation fails
- AND no API request is sent
- AND an error message ("File must be a .csv") is displayed

### SC-05: Backend 422 validation error

- GIVEN a CSV that passes client validation but fails backend parsing
- WHEN the user sends a preview or confirm request
- THEN a 422 response is returned
- AND the backend error message is shown verbatim (no generic replacement)

### SC-06: Backend 500 server error

- GIVEN the backend crashes during preview or confirm
- WHEN the request fails with HTTP 500
- THEN a generic "Server error" message is shown
- AND the user can retry

### SC-07: Reimport idempotency

- GIVEN a CSV that has been fully imported (all rows in DB)
- WHEN the user imports it again via confirm
- THEN all rows are skipped
- AND `skipped_rows` equals `total_rows`

### SC-08: File change invalidates preview

- GIVEN the user has a successful preview
- WHEN they upload a different file
- THEN the preview data is cleared from the UI
- AND confirm button is disabled
- AND the new file must be previewed before confirm is available
