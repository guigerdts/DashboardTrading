# Proposal: MT5 Import Frontend Integration

## Intent

MT5 Import backend is complete (PRs #1–4 merged to main) but has no UI. Traders cannot import their MT5 trade history. This change builds a complete frontend integration: upload CSV → preview → confirm → see results — without any backend modifications.

## Scope

### In Scope

- New `modules/imports/mt5/` module with components, hooks, and page
- 3-step transactional flow: Upload → Preview → Confirm → Result
- Native HTML5 Drag & Drop + file select (no dropzone library)
- FormData support in `api/client.js` (backward-compatible, no JSON breakage)
- Client-side validation: file required, `.csv` only, ≤5MB, UTF-8/UTF-8-BOM
- Result screen: summary (total/imported/skipped/errors) with "Go to Dashboard" and "Import another file" — no auto-navigation
- Route: `/imports/mt5` as independent page (not modal, not inside Dashboard)

### Out of Scope

- NO backend changes (endpoints, models, migrations)
- NO new npm packages
- NO toast/notification system
- NO multi-file or partial retry
- NO background jobs or websockets
- NO trade editing after import
- NO Excel/ZIP support
- NO authentication (backend has none)

## Explicit Requirements

### REQ-01 — Client-side file validation
Before any API call, validate on the client:
- File extension must be `.csv` (case-insensitive)
- File size must be ≤ 5 MB
- Exactly one file must be selected (no multi-file)
- If validation fails, do NOT send the request — show the error message in the UI immediately

### REQ-02 — Preview invalidation on file change
If the user changes the file (selects a new one):
- Clear any existing preview results
- Clear any previous import result
- Disable the Confirm button until a new preview is generated
- The UI resets to the `file-selected` state

### REQ-03 — Explicit state machine
The import flow follows a strict state machine with these states and transitions:

```
idle → file-selected → preview-loading → preview-success
  → confirm-loading → confirm-success
```

Error branches:
- `preview-loading` → `preview-error` (retry allowed)
- `confirm-loading` → `confirm-error` (retry allowed)

Invalid transitions are forbidden:
- Cannot go to `confirm-loading` from `idle` or `file-selected`
- Cannot go to `preview-success` from `confirm-loading`
- File change from any state after `file-selected` resets to `file-selected` (with cleared preview/result)

### REQ-04 — Protected Confirm button
The Confirm button must only be enabled when ALL of these are true:
- A valid preview exists (`preview-success` state)
- No API request is currently in flight
- A file is currently selected

### REQ-05 — Navigation
- The "Go to Dashboard" button only appears after `confirm-success`
- The "Import another file" button resets the flow to `idle`
- No auto-navigation ever

### REQ-06 — Accessibility
- Full keyboard support: Tab to navigate, Enter/Space to activate file select and buttons
- All inputs must have associated `<label>` elements
- Visible focus indicators on all interactive elements (matching Tailwind's `focus:ring` pattern)
- The Drag & Drop zone must be accessible: announce drop zone role, handle keyboard activation

### REQ-07 — React Query
- Use `useMutation` for both preview and confirm endpoints
- Do NOT cache preview or confirm results (they are transactional, not query data)
- No `queryKey` needed — mutations don't cache

### REQ-08 — Error handling
- Display the error message returned by the backend (422/400 responses)
- Use the existing error parsing from `api/client.js` (`error.data` on non-ok responses)
- Do NOT replace backend messages with generic frontend messages
- Network errors (no response) show a generic "Connection error" message

## Capabilities

### New

- `frontend-mt5-import`: CSV upload → preview → confirm → result UI for MT5 trades, consuming existing POST `/api/imports/mt5/preview` and POST `/api/imports/mt5/confirm` endpoints

### Modified

- None (existing specs unchanged — this is additive frontend work only)

## Approach

Structure mirrors `modules/analytics/` but under `modules/imports/mt5/` so future importers (cTrader, NinjaTrader) slot in as `modules/imports/<name>/`.

Explicit state machine via `useImportFlow` hook following **REQ-03**:

```
idle → file-selected → preview-loading → preview-success
  → confirm-loading → confirm-success
```

Error branches: `preview-loading → preview-error`, `confirm-loading → confirm-error`. File change from any non-idle state resets to `file-selected` and clears preview/result. Invalid transitions are forbidden (e.g., cannot jump from `file-selected` to `confirm-loading`).

`usePreview`/`useConfirm` React Query mutations POST FormData. `api/client.js` detects `body instanceof FormData` → skips JSON Content-Type header — fully backward-compatible.

`FileUploader` component renders both native HTML5 DnD zone and `<input type=file>` in the same surface. Client validation runs before any API call (backend validation is authoritative — no business rule duplication).

`PreviewTable` is a read-only Card with row status badges. `ImportResultScreen` shows final summary in Cards with action buttons. Lazy-loaded route in `App.jsx`.

## Feature Breakdown

- **api/client.js**: FormData guard (`body instanceof FormData`) — no Content-Type override (REQ-08: preserves existing error parsing)
- **FileUploader**: DnD zone + file select, client-side validation (REQ-01: .csv, ≤5MB, single file), file state management, accessible (REQ-06: keyboard, labels, focus, DnD role)
- **useImportFlow**: explicit state machine hook (REQ-03) — idle → file-selected → preview-loading → preview-success → confirm-loading → confirm-success, with error branches; preview invalidation on file change (REQ-02); protected confirm gating (REQ-04)
- **usePreview**: React Query `useMutation` (REQ-07: no cache) → POST `/api/imports/mt5/preview`; reads error from `api/client.js` `error.data` (REQ-08)
- **useConfirm**: React Query `useMutation` (REQ-07: no cache) → POST `/api/imports/mt5/confirm`; reads error from `api/client.js` `error.data` (REQ-08)
- **PreviewTable + PreviewSummary**: read-only valid/invalid row display, shown only in `preview-success`
- **ImportResultScreen**: per-row results summary + "Go to Dashboard" (only after `confirm-success`, REQ-05) + "Import another file" (resets to `idle`, REQ-05)
- **App.jsx**: lazy import + route for `/imports/mt5`

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `frontend/src/api/client.js` | Modified | FormData detection (instanceof guard) |
| `frontend/src/App.jsx` | Modified | Add `/imports/mt5` lazy route |
| `frontend/src/modules/imports/mt5/` | New | 8 files (pages/, hooks/, components/) |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| FormData detection breaks JSON calls | Low | `body instanceof FormData` — only skips Content-Type for FormData, all other calls keep JSON |
| Native DnD cross-browser quirks | Med | Test dragenter/dragleave/drop, preventDefaults, stopPropagation; fallback file select always visible |
| Large CSV (5000 rows) slow preview/confirm | Med | Skeleton loading states during preview; all buttons disabled + spinner during confirm |
| User navigates away during confirm | Low | Dedicated result screen (not a toast); no auto-nav; block UI but cannot prevent tab close |

## Delivery Strategy

**Single PR** (~350–400 lines). The module is self-contained, tightly coupled (flow depends on all pieces working together), and small enough for a focused review. No external dependencies or backend coordination needed. If the 400-line budget becomes tight, split into 2 stacked PRs: (1) API client + FileUploader + route scaffolding, (2) Preview/Confirm integration + Result screen.

## Rollback Plan

`git revert <sha>` of the single PR commit — removes all new files and reverts the two modifications (`api/client.js`, `App.jsx`). No data migration needed (preview is read-only, no DB impact).

## Dependencies

- MT5 Import backend endpoints (PRs #1–4, on main)
- React Query, Card, Skeleton, ErrorBoundary (existing frontend)
- Zero new npm packages

## Success Criteria

- [ ] Client-side validation: `.csv` extension, ≤5MB, single file — fails before API call (REQ-01)
- [ ] File change clears preview + result + disables Confirm (REQ-02)
- [ ] State machine transitions are strict: no invalid jumps (REQ-03)
- [ ] Confirm only enabled when preview-success + no in-flight request + file selected (REQ-04)
- [ ] "Go to Dashboard" only after confirm-success; "Import another file" resets to idle (REQ-05)
- [ ] Keyboard navigation, labels, focus indicators, accessible DnD zone (REQ-06)
- [ ] `useMutation` for preview/confirm — no caching (REQ-07)
- [ ] Backend error messages shown verbatim — no generic replacements (REQ-08)
- [ ] CSV upload via DnD and file select both work with client validation
- [ ] Preview shows valid/invalid split with per-row status (read-only)
- [ ] Confirm imports trades, shows result screen with summary
- [ ] Confirm in progress: all buttons disabled, spinner shown, no double-submit
- [ ] Existing JSON API calls (analytics, etc.) continue working unchanged
