# Design: MT5 Import Frontend Integration

## Technical Approach

New `modules/imports/mt5/` module following the existing `modules/analytics/` structure (hooks/components/pages/api). A strict state machine hook (`useImportFlow`) drives the entire 3-step flow — upload, preview, confirm, result. Two React Query `useMutation` wrappers handle the two POST endpoints. `api/client.js` gets one backward-compatible FormData guard. The route is lazy-loaded in `App.jsx`.

No new packages. No backend changes. ~350–400 total lines.

## Hard Constraints (non-negotiable — enforce in code review)

### C-01: Single source of truth for state
The state machine (`useImportFlow`) MUST be the **only** source of truth for UI state. Prohibited:
- ❌ Multiple `useState` booleans (`isPreviewing`, `isConfirming`, `showResult`, etc.)
- ❌ Independent loading/error flags outside the machine
- Use a single `reducer` or state enum. All derived booleans come from the current state value.

### C-02: File object persists in memory
The `File` object selected by the user MUST be held in the `useImportFlow` hook for the entire flow.
- ❌ Do NOT re-read `<input type="file">` to get the file for confirm
- ❌ Do NOT store the file as a base64 string or blob URL
- `useImportFlow` holds the `File` reference; it is reused by both `usePreview` and `useConfirm`

### C-03: Idempotent buttons during mutations
While a mutation is in-flight (`previewLoading` or `confirmLoading`):
- All action buttons MUST be disabled
- Double-clicks MUST NOT trigger additional mutations
- The `useMutation`'s built-in `isLoading` or `isPending` flag gates the disabled state

### C-04: No business logic in presentation components
`FileUploader`, `PreviewTable`, and `ImportResult` are **purely presentational**:
- ❌ No validation logic (client-side validation lives in `useImportFlow` or a composable utility)
- ❌ No state machine transitions
- ❌ No HTTP calls
- They receive `onFileSelect`, `onConfirm`, `onRetry` callbacks and render props only

## Architecture Decisions

| Decision | Choice | Alternatives | Rationale |
|----------|--------|-------------|-----------|
| State machine location | `useImportFlow` hook | Reducer in page, Zustand, context | Self-contained hook matches existing patterns; no global state needed for a single-page flow |
| API calls pattern | `useMutation` wrappers | Direct fetch in hook | Proposal REQ-07 mandates React Query mutations; wrappers keep HTTP concerns isolated from state orchestration |
| File validation location | `useImportFlow` (hook) | FileUploader (component) | C-04 prohibits business logic in components. `useImportFlow` validates on `setFile()`, stores the File (C-02), and passes errors down for display |
| Error display | Verbatim backend message | Generic replacement | REQ-08; backend 422 error detail mapped from `error.data` in the mutation's `onError` |
| FormData guard | `body instanceof FormData` | Separate `api.upload()` method | Minimal change, zero risk to existing JSON routes, single `instanceof` check |

## Data Flow

```
User                  FileUploader           useImportFlow          useMutation           importApi           Backend
 │                        │                       │                     │                    │                  │
 │  select file           │                       │                     │                    │                  │
 │───────────────────────>│  validate .csv/≤5MB   │                     │                    │                  │
 │                        │── if invalid show err │                     │                    │                  │
 │                        │                       │                     │                    │                  │
 │  click Preview         │                       │                     │                    │                  │
 │───────────────────────────────────────────────>│  idle→previewLoading │                    │                  │
 │                        │                       │────────────────────>│  importApi.preview  │                  │
 │                        │                       │                     │───────────────────>│  POST /preview   │
 │                        │                       │                     │                    │─────────────────>│
 │                        │                       │                     │                    │  PreviewResponse │
 │                        │                       │               previewReady              │<─────────────────│
 │                        │                       │<────────────────────│                    │                  │
 │  PreviewTable shown    │                       │                     │                    │                  │
 │                        │                       │                     │                    │                  │
 │  click Confirm         │                       │                     │                    │                  │
 │───────────────────────────────────────────────>│  previewReady→      │                    │                  │
 │                        │                       │  confirmLoading     │                    │                  │
 │                        │                       │────────────────────>│  importApi.confirm  │                  │
 │                        │                       │                     │───────────────────>│  POST /confirm   │
 │                        │                       │                     │                    │─────────────────>│
 │                        │                       │               confirmSuccess             │  ImportResult    │
 │                        │                       │<────────────────────│                    │<─────────────────│
 │  ImportResult shown    │                       │                     │                    │                  │
```

Error paths: both mutations set either `previewError` or `confirmError` via `onError`. Retry transitions re-enter loading states with the same file payload.

## State Machine

```
           ┌──────────────────────────────────────────────────────────┐
           │                                                          │
           │  file change / "Import another"                          │
           │                                                          │
           ▼                                                          │
    ┌──────────┐    preview click    ┌─────────────────┐   success   ┌─────────────┐
    │   idle   │ ──────────────────> │ previewLoading  │ ──────────> │ previewReady│
    │          │                     │                 │             │             │
    │ no file  │                     │ spinner +       │             │ table shown │
    │ no result│<────────────────── │ disabled btns   │             │ Confirm ON  │
    └──────────┘     retry          └─────────────────┘             └──────┬──────┘
         ▲                               │                                │
         │                 ┌─────────────┘                                │
         │                 ▼               ┌─────────────────┐            │ confirm click
         │          ┌──────────────┐       │                 │            │
         │          │ previewError │──────>│ confirmLoading  │<───────────┘
         │          │              │ retry │                 │
         │          │ error shown  │       │ spinner + all   │
         │          │ Retry ON     │       │ disabled        │
         │          └──────────────┘       └───────┬─────────┘
         │                                         │
         │                         ┌───────────────┘
         │                         ▼
         │                  ┌──────────────┐
         │                  │ confirmError │
         │                  │              │
         │                  │ error shown  │
         │                  │ Retry ON     │
         │                  └──────┬───────┘
         │                         │ retry
         │                         ▼
         │                  ┌────────────────┐
         │                  │ confirmSuccess │
         │                  │                │
         └──────────────────│ result screen  │   "Import another file"
          "Import another"  │ "Go to Dashbd" │
                            └────────────────┘
```

### Forbidden Transitions (explicitly blocked by guard conditions)

| From | To | Why |
|------|----|-----|
| `idle` | `confirmLoading` | Must preview first |
| `previewLoading` | `confirmLoading` | Must reach `previewReady` first |
| `previewLoading` | `confirmSuccess` | Impossible — confirm hasn't started |
| `previewReady` | `confirmSuccess` | Must go through `confirmLoading` |
| `confirmSuccess` | `previewReady` | Flow complete; only back to `idle` via "Import another" |

### UI Per State

| State | Shown | Buttons | File change behavior |
|-------|-------|---------|---------------------|
| `idle` | FileUploader only | Preview disabled | Already idle — accept new file |
| `previewLoading` | FileUploader + Skeleton rows | All disabled | Preview cleared, remains in loading for current |
| `previewReady` | FileUploader + PreviewTable | Confirm ON, Preview disabled on same file | Reset to `previewLoading` (new preview) |
| `previewError` | FileUploader + ErrorFallback | Retry ON, Preview disabled | Reset to `previewLoading` |
| `confirmLoading` | FileUploader + PreviewTable (static) + spinner | All disabled | Preview cleared, confirm disabled |
| `confirmSuccess` | ImportResult screen | "Go to Dashboard", "Import another" | Reset to `previewLoading` (new preview, old result cleared) |
| `confirmError` | Existing preview + ErrorFallback | Retry ON, file change allowed | Reset to `previewLoading` |

## API Client Change Specification

**File**: `frontend/src/api/client.js`
**Change**: Insert FormData guard between `const config = { headers: { ... } }` and `const response = await fetch(url, config)`.

```js
  // FormData: let browser set Content-Type (with boundary)
  if (options.body instanceof FormData) {
    delete config.headers['Content-Type'];
  }
```

**Impact**: Zero for all existing JSON calls. When any mutation passes a FormData body, the browser auto-sets `Content-Type: multipart/form-data; boundary=...`. Error handling path unchanged — `error.data` still populated for all non-ok responses.

## File-by-File Breakdown

| File | Action | Export Contract |
|------|--------|-----------------|
| `frontend/src/api/client.js` | Modify (7 lines) | Add FormData guard before fetch call |
| `frontend/src/App.jsx` | Modify (5 lines) | Add `lazy(() => import('./modules/imports/mt5/pages/ImportPage'))` + `<Route path="/imports/mt5" />` |
| `frontend/src/modules/imports/mt5/api/importApi.js` | Create | `{ preview(file: File): Promise<PreviewResponse>, confirm(file: File): Promise<ImportResult> }` — both build FormData, call `api/client.js` `post()` |
| `frontend/src/modules/imports/mt5/hooks/usePreview.js` | Create | `usePreview()` → `{ mutate, isLoading, data, error }` — wraps `importApi.preview` in `useMutation` |
| `frontend/src/modules/imports/mt5/hooks/useConfirm.js` | Create | `useConfirm()` → `{ mutate, isLoading, data, error }` — wraps `importApi.confirm` in `useMutation` |
| `frontend/src/modules/imports/mt5/hooks/useImportFlow.js` | Create | `useImportFlow()` → `{ state, file, validationError, setFile, preview, confirm, reset, clearPreview }` — tracks state machine, holds File object in memory (C-02), runs client-side validation on `setFile()`, orchestrates preview/confirm mutations, gates button enabled states |
| `frontend/src/modules/imports/mt5/components/FileUploader.jsx` | Create | `FileUploader({ file, onFileSelect, disabled, error })` — DnD zone + `<input type=file>`, purely presentational. No validation logic — calls `onFileSelect(file)` on selection, parent handles validation via `useImportFlow` |
| `frontend/src/modules/imports/mt5/components/PreviewTable.jsx` | Create | `PreviewTable({ data: PreviewResponse })` — read-only Card with row list, status badges, valid/invalid counts |
| `frontend/src/modules/imports/mt5/components/ImportResult.jsx` | Create | `ImportResult({ data: ImportResult, onReset, onGoToDashboard })` — summary Cards + action buttons |
| `frontend/src/modules/imports/mt5/pages/ImportPage.jsx` | Create | `ImportPage()` — orchestrator: wires `useImportFlow` → renders components per state, wraps in ErrorBoundary |

## Test Strategy

| Group | What | Approach |
|-------|------|----------|
| Unit: Validation | `.csv` check, ≤5MB check, single file, error messages | Pure function tests; mock File objects |
| Unit: State machine | All valid transitions, all 5 forbidden transitions, initial state, file change reset | Test `useImportFlow` transition guards in isolation |
| Integration: Preview | Successful preview renders `PreviewTable`, failed preview shows error, retry triggers mutation | Render `ImportPage` with mocked mutations |
| Integration: Confirm | Successful confirm shows `ImportResult`, failed confirm shows error, retry works | Same pattern as preview |
| Integration: Navigation | File change invalidates preview + disables confirm; "Go to Dashboard" only after success; "Import another" resets flow | State-driven assertions after simulated events |
| Integration: Error display | 422 errors shown verbatim (`error.data`), 500 shows generic message, network error fallback | Mutation mock rejects with different error shapes |
| Unit: API client | FormData skips Content-Type, JSON calls retain Content-Type | Direct test of `request()` with both body types |

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| FormData guard breaks existing JSON calls | Low | `instanceof FormData` is exact — no false positives |
| Native DnD inconsistent across browsers | Medium | `preventDefault`/`stopPropagation` on dragenter/dragleave/drop; file select always present as fallback |
| Large CSV (5000+ rows) UI freeze | Medium | Skeleton during preview; table is read-only (no pagination needed in v1) |
| Navigation during confirm loses progress | Low | Per REQ-SPEC-02: no confirm dialog, mutation auto-cancels on unmount via AbortController `signal` |
