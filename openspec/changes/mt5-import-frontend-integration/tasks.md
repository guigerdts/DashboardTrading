# Tasks: MT5 Import Frontend Integration

> **Delivery: 2 stacked PRs**
> **PR #1 — Frontend Foundation**: ~296 lines (source only, no tests)
> **PR #2 — Frontend Tests**: ~235 lines + devDependencies (vitest + @testing-library/react)
> No new npm **runtime** packages — vitest + @testing-library/react are devDependencies (test tooling, exempted from the constraint)

---

## Dependency Graph

```
T-01 (api/client.js FormData guard) ──┐
                                       ├── T-02 (importApi service)
T-03 (Routing: App.jsx + Home.jsx) ───┤       │
                                       │       ├── T-04 (usePreview)
                                       │       ├── T-05 (useConfirm)
                                       │       └── T-06 (useImportFlow) ── depends on T-04, T-05
                                       │              │
T-07 (FileUploader) ───────────────────┤              │
T-08 (PreviewTable) ──────────────────┤              │
T-09 (ImportResult) ──────────────────┤              │
                                       │              │
                                       └── T-10 (ImportPage) ── depends on T-06, T-07, T-08, T-09, T-03
                                              │
                                              ├── T-11 (unit: validation.test)
                                              ├── T-12 (unit: state-machine.test)
                                              ├── T-13 (unit: api-client.test)
                                              ├── T-14 (integration: preview-flow.test)
                                              ├── T-15 (integration: confirm-flow.test)
                                              └── T-16 (integration: navigation-error-file-unmount.test)
```

**Parallelization opportunities:**
- T-01 + T-03 can run in parallel (independent)
- T-07, T-08, T-09 can run in parallel (independent, no shared state)
- T-04 + T-05 can run in parallel (both depend on T-02 only)
- T-11 through T-16 can run in parallel (independent test files)
- T-10 is the critical-path bottleneck — blocks all tests

---

## Phase 1: Foundation

### T-01 — Add FormData guard to API client

| Field | Value |
|-------|-------|
| **File(s)** | `frontend/src/api/client.js` |
| **Lines** | ~3 (add) |
| **Depends on** | — |
| **Blocking** | T-02 |

**Description:**
Insert a guard in the `request()` function of `api/client.js` that detects `options.body instanceof FormData` and deletes the `Content-Type` header from `config.headers` before the fetch call. This lets the browser set the correct `multipart/form-data` boundary automatically.

**Key constraints:**
- Guard must be placed after `config` construction but before `fetch(url, config)`
- Must NOT affect any existing JSON calls — `instanceof FormData` is an exact check
- Must NOT change the error handling path (`error.data` still populated for non-ok responses)

**Acceptance criteria:**
- [ ] When `body` is a `FormData` instance, `Content-Type` header is removed from the request
- [ ] When `body` is JSON string (existing behavior), `Content-Type: application/json` is preserved
- [ ] All existing `api.get`, `api.post`, `api.put`, `api.delete` calls continue to work unchanged

---

### T-02 — Create importApi service

| Field | Value |
|-------|-------|
| **File(s)** | `frontend/src/modules/imports/mt5/api/importApi.js` |
| **Lines** | ~15 |
| **Depends on** | T-01 |
| **Blocking** | T-04, T-05 |

**Description:**
Create a new API service file under `modules/imports/mt5/api/`. Define two async functions — `preview(file)` and `confirm(file)` — each taking a `File` object. Both build a `FormData` instance, append the file under the field name `file`, and call `api.post()` from `frontend/src/api/client.js`.

**Key constraints:**
- Import `api` from `../../../../api/client` (path resolves to `frontend/src/api/client.js`)
- Both functions receive `File` object (not base64, not blob URL) per C-02
- Field name must be `file` to match backend `UploadFile` parameter
- No URL construction — `api.post` handles path concatenation

**Acceptance criteria:**
- [ ] `preview(file)` builds FormData and POSTs to `/api/imports/mt5/preview`
- [ ] `confirm(file)` builds FormData and POSTs to `/api/imports/mt5/confirm`
- [ ] Both return the parsed JSON response (typed via JSDoc as `PreviewResponse` / `ImportResult`)
- [ ] Reject (throw) on non-ok responses with `error.data` populated (inherited from `api/client.js`)

---

### T-03 — Register route and add nav link

| Field | Value |
|-------|-------|
| **File(s)** | `frontend/src/App.jsx` (+3 lines), `frontend/src/pages/Home.jsx` (+1 line) |
| **Lines** | ~4 (add) |
| **Depends on** | — |
| **Blocking** | T-10 |

**Description:**
Two small modifications:

1. **App.jsx**: Add `lazy(() => import('./modules/imports/mt5/pages/ImportPage'))` and a `<Route path="/imports/mt5" element={<ImportPage />} />` inside the `<Routes>` block. Keep the existing lazy import pattern consistent with `DashboardPage`.

2. **Home.jsx**: Add `{ name: 'MT5 Import', path: '/imports/mt5' }` to the `modules` array. Keep alphabetical order with the existing entries.

**Acceptance criteria:**
- [ ] `/imports/mt5` route renders the `ImportPage` component (lazy-loaded)
- [ ] Navigation to `/imports/mt5` works from the Home page link
- [ ] Existing routes unchanged — no regression

---

## Phase 2: Core Logic

### T-04 — Implement usePreview mutation hook

| Field | Value |
|-------|-------|
| **File(s)** | `frontend/src/modules/imports/mt5/hooks/usePreview.js` |
| **Lines** | ~12 |
| **Depends on** | T-02 |
| **Blocking** | T-06 |

**Description:**
Create a hook wrapping `importApi.preview` in a `useMutation` from `@tanstack/react-query`. Exposes `{ mutate, isLoading, data, error }` — these are the vanilla `useMutation` return values (no renaming — `isLoading` alias for `isPending` per TanStack Query v5).

**Key constraints:**
- `mutationFn: (file) => importApi.preview(file)` — receives `File`, calls API
- Do NOT set `queryKey` — mutations don't cache (REQ-07)
- No `onSuccess`/`onError` callbacks — the orchestrator (`useImportFlow`) handles side effects via `onMutate`/`onSettled` observation or direct `mutate` calls
- Error propagation: `useMutation` sets `error` from the thrown API error automatically

**Acceptance criteria:**
- [ ] `mutate(file)` calls `importApi.preview(file)` when invoked
- [ ] `isLoading` is `true` while request is in flight
- [ ] `data` contains `PreviewResponse` on success
- [ ] `error` contains the API error on failure (with `error.data` for 422 details)
- [ ] Mutation auto-cancels on unmount (React Query default via AbortController)

---

### T-05 — Implement useConfirm mutation hook

| Field | Value |
|-------|-------|
| **File(s)** | `frontend/src/modules/imports/mt5/hooks/useConfirm.js` |
| **Lines** | ~12 |
| **Depends on** | T-02 |
| **Blocking** | T-06 |

**Description:**
Same pattern as T-04 but wrapping `importApi.confirm`. Exposes `{ mutate, isLoading, data, error }`.

**Key constraints:**
- `mutationFn: (file) => importApi.confirm(file)`
- No cache — mutation only (REQ-07)
- No `onSuccess`/`onError` callbacks — orchestration lives in `useImportFlow`

**Acceptance criteria:**
- [ ] `mutate(file)` calls `importApi.confirm(file)` when invoked
- [ ] `isLoading` is `true` while request is in flight
- [ ] `data` contains `ImportResult` on success
- [ ] `error` contains the API error on failure
- [ ] Mutation auto-cancels on unmount

---

### T-06 — Implement useImportFlow orchestrator hook

| Field | Value |
|-------|-------|
| **File(s)** | `frontend/src/modules/imports/mt5/hooks/useImportFlow.js` |
| **Lines** | ~90 |
| **Depends on** | T-04, T-05 |
| **Blocking** | T-10 |

**Description:**
This is the central piece — a hook that implements the explicit state machine (REQ-03) and orchestrates the entire import flow. It is the **single source of truth** for UI state (C-01).

**State machine:**
```
idle
  → setFile (valid)  → file-selected (was `idle`)
  → preview           → previewLoading
  → preview success   → previewReady
  → confirm           → confirmLoading
  → confirm success   → confirmSuccess

Error branches:
  previewLoading → previewError  (via mutation onError)
  confirmLoading → confirmError  (via mutation onError)

Reset transitions:
  file change from any state        → file-selected (with new file)
  "Import another" from any state   → idle
```

**Forbidden transitions (must throw / no-op):**
- `idle` → `confirmLoading` (must preview first)
- `previewLoading` → `confirmLoading` (must reach previewReady first)
- `previewReady` → `confirmSuccess` (must go through confirmLoading)
- `confirmSuccess` → `previewReady` (flow complete — only back to idle)

**Exposed API:**
```js
const {
  state,            // string — current machine state
  file,             // File | null — held in memory (C-02)
  validationError,  // string | null — client-side validation message
  previewData,      // PreviewResponse | null — from usePreview
  confirmData,      // ImportResult | null — from useConfirm
  previewError,     // Error | null — from usePreview
  confirmError,     // Error | null — from useConfirm
  isPreviewing,     // boolean — derived from state === 'previewLoading'
  isConfirming,     // boolean — derived from state === 'confirmLoading'
  canConfirm,       // boolean — derived: previewReady && not loading
  setFile,          // (file: File | null) => void — validates, transitions
  preview,          // () => void — triggers preview mutation
  confirm,          // () => void — triggers confirm mutation
  reset,            // () => void — back to idle
  clearPreview,     // () => void — clears preview data (used by file change)
} = useImportFlow();
```

**Client-side validation (runs inside `setFile`):**
1. If `file === null` → set `validationError = 'Please select a file'`, remain in current state
2. If file extension is not `.csv` (case-insensitive) → set validation error, remain in current state
3. If file size > 5 MB → set validation error, remain in current state
4. If valid → clear validation error, transition to `file-selected`, store file in memory (C-02)

**Preview invalidation on file change (REQ-02):**
If a file is selected when one was already present (i.e., `file !== null` and a new file is chosen):
- Clear `previewData` and `previewError`
- Clear `confirmData` and `confirmError`
- Transition to `file-selected` (with new file)
- `canConfirm` becomes false until new preview succeeds

**Implementation notes:**
- Use `useReducer` for the state machine — single dispatch, all transitions explicit
- The reducer must be a pure function: transitions are deterministic, side-effect-free
- `preview` and `confirm` actions trigger side effects via `useEffect` watching state transitions
  OR call the mutation's `mutate` directly (whichever pattern is cleaner — prefer direct `mutate` calls)
- Mutations: use `usePreview()` and `useConfirm()` hooks internally
- On `onSuccess` of preview mutation → dispatch `PREVIEW_SUCCESS` with data
- On `onError` of preview mutation → dispatch `PREVIEW_ERROR` with error
- Same pattern for confirm mutation
- `canConfirm` must be `true` ONLY when `state === 'previewReady'` AND `!isPreviewing` AND `!isConfirming`
- No toast, no dialog, no auto-navigation

**Acceptance criteria:**
- [ ] Initial state is `idle` with `file: null`, `validationError: null`
- [ ] Valid `.csv` file ≤5MB → `setFile` clears validation error, stores file, transitions to `file-selected`
- [ ] Invalid file (wrong extension / >5MB) → validation error set, file NOT stored, state unchanged
- [ ] `preview()` from `file-selected` → dispatches preview mutation → state goes `previewLoading`
- [ ] Preview success → state goes `previewReady`, `previewData` populated
- [ ] Preview failure → state goes `previewError`, `previewError` populated
- [ ] `confirm()` from `previewReady` → dispatches confirm mutation → state goes `confirmLoading`
- [ ] Confirm success → state goes `confirmSuccess`, `confirmData` populated
- [ ] Confirm failure → state goes `confirmError`, `confirmError` populated
- [ ] File change after `previewReady` → preview + result cleared → state back to `file-selected`
- [ ] `reset()` from any state → returns to `idle` with all data cleared
- [ ] All 5 forbidden transitions are no-ops (do not throw, just return current state)
- [ ] `canConfirm` is `false` in every state except `previewReady`
- [ ] `canConfirm` is `false` during `previewLoading` even if data already exists
- [ ] `canConfirm` is `false` during `confirmLoading`

---

## Phase 3: UI

### T-07 — Create FileUploader component

| Field | Value |
|-------|-------|
| **File(s)** | `frontend/src/modules/imports/mt5/components/FileUploader.jsx` |
| **Lines** | ~55 |
| **Depends on** | — |
| **Blocking** | T-10 |

**Description:**
Purely presentational component (C-04) rendering a native HTML5 Drag & Drop zone combined with a file input. Receives `file`, `onFileSelect`, `disabled`, and `error` props. NO validation logic — calls `onFileSelect(file)` on selection, parent handles validation.

**Key constraints:**
- Render a `<div>` that acts as the drop zone with `role="region"` and `aria-label="File upload drop zone"`
- Register `onDragEnter`, `onDragOver`, `onDragLeave`, `onDrop` handlers — all call `preventDefault()` + `stopPropagation()`
- On `onDrop`: extract `event.dataTransfer.files[0]`, call `onFileSelect(file)`
- `onDragOver` sets a visual state (Tailwind: `border-blue-400 bg-blue-50`), `onDragLeave` removes it
- Include an `<input type="file" accept=".csv">` visually hidden but accessible via label click
- Click on the drop zone triggers the file input's `click()` method
- Tab-index for keyboard accessibility: the drop zone is focusable (`tabIndex={0}`), Enter/Space activate the file picker via `onKeyDown`
- Show current file name when `file` is provided
- Show validation error text (in red) below the zone when `error` prop is set
- All interactive elements disabled when `disabled` prop is `true`
- Associate `<label>` element with the file input for screen reader support

**Acceptance criteria:**
- [ ] Drag & drop works with native HTML5 events — no dropzone library
- [ ] Click on the drop zone opens the file picker
- [ ] `.csv` filter on file picker via `accept=".csv"`
- [ ] Keyboard: Tab to focus, Enter/Space to activate
- [ ] ARIA: drop zone has `role="region"` with accessible label
- [ ] Visual drag feedback: border and background change during dragover
- [ ] Shows selected file name when `file` prop is set
- [ ] Shows error message when `error` prop is set
- [ ] All elements disabled when `disabled` is `true`
- [ ] NO validation logic — purely calls `onFileSelect(file)`, no `.csv`/size/single checks

---

### T-08 — Create PreviewTable component

| Field | Value |
|-------|-------|
| **File(s)** | `frontend/src/modules/imports/mt5/components/PreviewTable.jsx` |
| **Lines** | ~30 |
| **Depends on** | — |
| **Blocking** | T-10 |

**Description:**
Purely presentational component (C-04) that renders the preview results in a `Card` with a read-only table. Receives a `data: PreviewResponse` prop.

**Layout (top to bottom):**
1. Summary bar: `{valid_rows} valid / {invalid_rows} invalid / {total_rows} total` using the existing `Card` component with `title="Preview Results"`
2. Table with columns: `#` (row_index), Ticket (broker_ticket), Status (badge: green "valid" or red "invalid"), Errors (comma-joined `errors[]` or `—`)
3. Status badges use Tailwind: `bg-green-100 text-green-800` for valid, `bg-red-100 text-red-800` for invalid

**Key constraints:**
- Read-only — no action buttons, no selectable rows
- No pagination in v1 (per risk assessment — acceptable for <5000 rows)
- Empty state: if `total_rows === 0`, show a `Card` with "No rows found in the CSV file" message
- No business logic: receives ready-to-render data, does not transform it

**Acceptance criteria:**
- [ ] Summary bar shows valid/invalid/total counts
- [ ] Table renders all rows with row_index, broker_ticket, status badge, errors
- [ ] Valid rows show green badge, invalid rows show red badge
- [ ] Empty rows array shows "No rows found" message
- [ ] Component uses the shared `Card` from `shared/ui/Card`
- [ ] No mutation or state machine logic in the component

---

### T-09 — Create ImportResult component

| Field | Value |
|-------|-------|
| **File(s)** | `frontend/src/modules/imports/mt5/components/ImportResult.jsx` |
| **Lines** | ~25 |
| **Depends on** | — |
| **Blocking** | T-10 |

**Description:**
Purely presentational component (C-04) showing the final import result. Receives `{ data: ImportResult, onReset, onGoToDashboard }`.

**Layout:**
1. Header: "Import Complete" (`<h2>`)
2. Summary Cards (using the shared `Card`):
   - Total rows
   - Imported rows (green highlight)
   - Skipped rows (yellow/amber highlight)
   - Error rows (red highlight)
3. Action buttons row:
   - "Import another file" button → calls `onReset` (returns to idle)
   - "Go to Dashboard" button → calls `onGoToDashboard` (navigates to `/dashboard`)
   - Both buttons use Tailwind `rounded bg-* px-4 py-2 text-sm`

**Key constraints:**
- No auto-navigation — buttons must be explicit user actions (REQ-05)
- "Go to Dashboard" only shown when `onGoToDashboard` is provided (always in this flow)
- No business logic — receives pre-computed data, renders it

**Acceptance criteria:**
- [ ] Shows "Import Complete" heading
- [ ] Four summary cards: total, imported, skipped, error rows
- [ ] "Import another file" button visible and calls `onReset` on click
- [ ] "Go to Dashboard" button visible and calls `onGoToDashboard` on click
- [ ] No auto-navigation — both buttons require explicit user action

---

### T-10 — Create ImportPage orchestrator

| Field | Value |
|-------|-------|
| **File(s)** | `frontend/src/modules/imports/mt5/pages/ImportPage.jsx` |
| **Lines** | ~50 |
| **Depends on** | T-06, T-07, T-08, T-09, T-03 |
| **Blocking** | All test tasks |

**Description:**
The page component that wires `useImportFlow` hook to the presentational components based on the current state. Wrapped in `ErrorBoundary` from `shared/components/ErrorBoundary`.

**State → UI mapping:**
| State | Rendered |
|-------|----------|
| `idle` | `FileUploader` only |
| `file-selected` | `FileUploader` + "Preview" button (enabled if no validation error) |
| `previewLoading` | `FileUploader` (disabled) + `Skeleton` rows (3 skeleton rows) |
| `previewReady` | `FileUploader` + `PreviewTable` + "Confirm" button (enabled) |
| `previewError` | `FileUploader` + `ErrorFallback` with retry calling `preview()` |
| `confirmLoading` | `FileUploader` (disabled) + `PreviewTable` (static, faded) + spinner overlay |
| `confirmSuccess` | `ImportResult` with `onReset → reset()` and `onGoToDashboard → navigate('/dashboard')` |
| `confirmError` | `FileUploader` (disabled) + `PreviewTable` + `ErrorFallback` with retry calling `confirm()` |

**Key constraints:**
- Import and use `useNavigate` from `react-router-dom` for the dashboard navigation
- Wrap the entire page in `ErrorBoundary` from `shared/components/ErrorBoundary`
- The "Preview" button label: "Preview Import" — disabled when `!file` or `validationError`
- The "Confirm" button label: "Confirm Import" — disabled when `!canConfirm`
- Skeleton loading: use `Skeleton` from `shared/components/Skeleton` with `variant="rect"` and `height="2rem"` for 3 placeholder rows
- All derived disabled states come from `useImportFlow` — no extra booleans (C-01)

**Acceptance criteria:**
- [ ] `idle`: FileUploader shown, no buttons, no preview
- [ ] `file-selected`: FileUploader + "Preview Import" button enabled
- [ ] `previewLoading`: FileUploader disabled + 3 skeleton rows, "Preview Import" disabled
- [ ] `previewReady`: FileUploader + PreviewTable + "Confirm Import" enabled
- [ ] `previewError`: FileUploader + ErrorFallback with retry
- [ ] `confirmLoading`: FileUploader disabled + PreviewTable faded + all buttons disabled
- [ ] `confirmSuccess`: ImportResult with both action buttons
- [ ] `confirmError`: FileUploader disabled + PreviewTable + ErrorFallback with retry
- [ ] ErrorBoundary wraps the entire page content

---

## Phase 4: Setup — ESLint + Test Runner

### T-00 — Install dev dependencies and configure tooling

| Field | Value |
|-------|-------|
| **File(s)** | `package.json`, `eslint.config.js`, `vitest.config.js`, `.eslintignore` |
| **Lines** | Config only |
| **Depends on** | — |
| **Blocking** | All test tasks |

**Description:**
Install and configure static analysis + test runner for the frontend.

**Dev dependencies to install:**
```bash
npm install --save-dev \
  vitest \
  @testing-library/react \
  @testing-library/jest-dom \
  jsdom \
  eslint \
  @eslint/js \
  eslint-plugin-react \
  eslint-plugin-react-hooks
```

**ESLint config** (`eslint.config.js`): Flat config for React 19 + JSX support. Rules: `no-unused-vars: warn`, `react/jsx-uses-react: off` (React 19), `react-hooks/rules-of-hooks: error`.

**Vitest config** (`vitest.config.js`): Extends `vite.config.js`, sets `test.environment: 'jsdom'`, `test.globals: true`, `test.setupFiles` for `@testing-library/jest-dom`.

**package.json scripts** to add:
```json
{
  "scripts": {
    "test": "vitest run",
    "test:watch": "vitest",
    "lint": "eslint src/"
  }
}
```

**Acceptance criteria:**
- [x] `npm run lint` passes — 0 errors, only pre-existing warnings
- [x] `npm test` (vitest run) — all 50 tests pass across 6 test files
- [x] `npm run build` still passes
- [x] ESLint config is flat config (compatible with ESLint v9+)

## Phase 5: Tests

### T-11 — Unit tests: client-side validation

| Field | Value |
|-------|-------|
| **File(s)** | `frontend/src/modules/imports/mt5/__tests__/validation.test.js` |
| **Lines** | ~30 |
| **Depends on** | T-06 (validation logic in useImportFlow) |

**Description:**
Pure function tests for the client-side validation that runs in `setFile`. Since validation lives inside `useImportFlow`, extract it into a testable pure utility or test the validation path through the hook with mocked File objects.

Test cases:
1. `.csv` file (case-insensitive: `.CSV`, `.Csv`) passes validation
2. `.xlsx` file fails validation with appropriate error message
3. `.csv` file >5MB fails validation
4. `.csv` file ≤5MB passes validation
5. `null` file sets "Please select a file" error
6. Single file passes (no multi-file guard — the input is `accept=".csv"` single by nature, but edge-case test)

**Acceptance criteria:**
- [x] All 8 test cases pass (6 required + 2 edge cases: .Csv mixed case, exact 5MB boundary)
- [x] No API calls are made during validation tests (pure function tests)
- [x] Error messages match expected strings from REQ-01

---

### T-12 — Unit tests: state machine transitions

| Field | Value |
|-------|-------|
| **File(s)** | `frontend/src/modules/imports/mt5/__tests__/state-machine.test.js` |
| **Lines** | ~45 |
| **Depends on** | T-06 |

**Description:**
Test the state machine reducer/transitions in isolation. Mock the mutation hooks so only the state logic is verified.

**Test cases:**
1. Initial state is `idle`
2. `idle → setFile(valid) → file-selected`
3. `file-selected → preview → previewLoading`
4. `previewLoading → onSuccess → previewReady`
5. `previewLoading → onError → previewError`
6. `previewReady → confirm → confirmLoading`
7. `confirmLoading → onSuccess → confirmSuccess`
8. `confirmLoading → onError → confirmError`
9. `previewError → retry (preview) → previewLoading`
10. `confirmError → retry (confirm) → confirmLoading`
11. All 5 forbidden transitions are no-ops (state unchanged)
12. File change from `previewReady` → state resets to `file-selected`, preview cleared, confirm disabled
13. `reset()` from any state → `idle`

**Acceptance criteria:**
- [x] All 20 test cases pass (13 required + 7 edge cases: invalid file no state change, mixed case, boundary, retry paths, unknown action)
- [x] State transitions are deterministic (no async race conditions)
- [x] Forbidden transitions do not throw — they silently return current state

---

### T-13 — Unit tests: API client FormData guard

| Field | Value |
|-------|-------|
| **File(s)** | `frontend/src/api/__tests__/client.test.js` |
| **Lines** | ~25 |
| **Depends on** | T-01 |

**Description:**
Test the FormData guard in `api/client.js` by mocking `fetch` and verifying headers.

**Test cases:**
1. POST with `FormData` body → `Content-Type` header is NOT set in fetch config (browser sets it automatically)
2. POST with JSON string body → `Content-Type: application/json` IS set in fetch config
3. GET request → default headers preserved
4. Non-ok response with FormData → `error.data` is populated correctly
5. Non-ok response with JSON → `error.data` is populated correctly

**Acceptance criteria:**
- [x] All 5 test cases pass
- [x] `fetch` is properly mocked and restored
- [x] No real API calls during tests

---

### T-14 — Integration tests: preview flow

| Field | Value |
|-------|-------|
| **File(s)** | `frontend/src/modules/imports/mt5/__tests__/preview-flow.test.js` |
| **Lines** | ~40 |
| **Depends on** | T-10 |

**Description:**
Integration tests rendering `ImportPage` with mocked mutations. Test the preview-specific flow end-to-end.

**Test cases:**
1. Successful preview renders `PreviewTable` with row data
2. Failed preview shows `ErrorFallback` with error message
3. Retry after preview error triggers preview mutation again
4. Preview with 0 valid rows shows table but Confirm button is disabled (from `canConfirm`)
5. Preview with 0 total rows shows "No rows found" message

**Acceptance criteria:**
- [x] All 5 test cases pass
- [x] Components render correctly for each preview outcome
- [x] ErrorFallback appears on failure with retry button
- [x] Retry button calls the preview mutation again

---

### T-15 — Integration tests: confirm flow

| Field | Value |
|-------|-------|
| **File(s)** | `frontend/src/modules/imports/mt5/__tests__/confirm-flow.test.js` |
| **Lines** | ~35 |
| **Depends on** | T-10 |

**Description:**
Integration tests rendering `ImportPage` with mocked mutations. Test the confirm-specific flow end-to-end, assuming a successful preview has already occurred.

**Test cases:**
1. Successful confirm renders `ImportResult` with summary counts
2. Failed confirm shows `ErrorFallback` with error message
3. Retry after confirm error triggers confirm mutation again
4. All buttons disabled during `confirmLoading` (no double-submit)

**Acceptance criteria:**
- [x] All 4 test cases pass
- [x] ImportResult shows correctly on success
- [x] ErrorFallback appears on failure with retry
- [x] All action buttons are disabled during loading

---

### T-16 — Integration tests: navigation, error display, file change, unmount

| Field | Value |
|-------|-------|
| **File(s)** | `frontend/src/modules/imports/mt5/__tests__/navigation-error-file-unmount.test.js` |
| **Lines** | ~60 |
| **Depends on** | T-10 |

**Description:**
Integration tests for navigation constraints, error display formats, file replacement behavior, and unmount cancellation.

**Test cases:**
1. **Error display (422):** Backend returns 422 with `error.data.detail` — the detail is shown verbatim (not a generic message)
2. **Error display (500):** Backend returns 500 — generic "Server error" message shown (REQ-08)
3. **Error display (Network):** Fetch fails with network error — "Connection error" message shown
4. **File change after preview:** User changes file after `previewReady` → preview cleared, confirm disabled, state back to `file-selected` (REQ-02)
5. **File change after confirm success:** User changes file → flow resets to `file-selected`, old result cleared
6. **"Go to Dashboard" button:** Only visible in `confirmSuccess` state (REQ-05)
7. **"Import another" button:** Resets to `idle` (REQ-05)
8. **Unmount cancellation:** No dialog shown on unmount (mutation auto-cancels via React Query)

**Acceptance criteria:**
- [x] All 8 test cases pass
- [x] 422 errors show verbatim backend message
- [x] 500 errors show generic server error
- [x] Network errors show "Connection error"
- [x] File change resets preview + disables confirm
- [x] "Go to Dashboard" only present after confirm success
- [x] "Import another" resets to idle
- [x] No dialog or blocking prompt on navigation away (just verify mutation cleanup)

---

## Lines Estimate Summary

### PR #1 — Frontend Foundation (~296 lines)

| Phase | Tasks | Lines |
|:------|:------|:-----:|
| 1. Foundation | T-01 to T-03 | ~22 |
| 2. Core Logic | T-04 to T-06 | ~114 |
| 3. UI | T-07 to T-10 | ~160 |
| **PR #1 Total** | | **~296** |

### PR #2 — Frontend Tests + ESLint (~250 lines + config)

| Phase | Tasks | Lines |
|:------|:------|:-----:|
| Setup | ESLint config + vitest config + devDependencies | ~setup |
| 4. Tests | T-11 to T-16 | ~235 |
| **PR #2 Total** | | **~250 + config** |

---

## Review Workload Forecast

| Metric | Value |
|--------|-------|
| **Total lines (source + tests)** | **~531 lines across 2 PRs** |
| **Files changed** | 2 modified (`api/client.js`, `App.jsx`, `Home.jsx`) + 9 new files |
| **PR #1 complexity** | Low–Medium — self-contained module, no backend, tightly coupled but small (~296 lines) |
| **PR #2 complexity** | Low — test setup + standard test patterns (~235 lines) |

### PR #1 — Frontend Foundation (~296 lines)

| Task | File | Lines | Risk |
|:-----|:-----|:-----:|:----:|
| T-01 | `api/client.js` | 3 | 🔴 FormData guard — backward compat |
| T-02 | `importApi.js` | 15 | 🟢 Standard pattern |
| T-03 | `App.jsx` + `Home.jsx` | 4 | 🟢 Trivial |
| T-04 | `usePreview.js` | 12 | 🟢 Standard useMutation |
| T-05 | `useConfirm.js` | 12 | 🟢 Standard useMutation |
| T-06 | `useImportFlow.js` | 90 | 🔴 State machine correctness |
| T-07 | `FileUploader.jsx` | 55 | 🟡 DnD + accessibility |
| T-08 | `PreviewTable.jsx` | 30 | 🟢 Read-only table |
| T-09 | `ImportResult.jsx` | 25 | 🟢 Summary cards |
| T-10 | `ImportPage.jsx` | 50 | 🟡 State → UI mapping |
| **Total PR #1** | | **~296** | |

### PR #2 — Frontend Tests + ESLint (~250 lines + config)

| Task | File | Lines | Description |
|:-----|:-----|:-----:|:------------|
| Setup | `eslint.config.js` | ~config | ESLint flat config for React + imports |
| Setup | `vitest.config.js` + deps | ~config | vitest + @testing-library/react |
| T-11 | `validation.test.js` | 30 | Client-side validation tests |
| T-12 | `state-machine.test.js` | 45 | State machine transitions |
| T-13 | `client.test.js` | 25 | API client FormData guard |
| T-14 | `preview-flow.test.js` | 40 | Integration: preview |
| T-15 | `confirm-flow.test.js` | 35 | Integration: confirm |
| T-16 | `navigation-error-file-unmount.test.js` | 60 | Navigation + errors + file change |
| **Total PR #2** | | **~250 + config** | |

**Reviewers needed**: 1 (frontend) — no backend changes to validate

---

## Rollback Note

Each PR is a single commit. Rollback independently via `git revert <sha>`:

### PR #1 revert
- Removes: 9 new files under `frontend/src/modules/imports/mt5/`
- Reverts: `api/client.js` (FormData guard removed, original 39 lines restored)
- Reverts: `App.jsx` (MT5 Import lazy import + route removed)
- Reverts: `Home.jsx` (MT5 Import nav link removed)

### PR #2 revert
- Removes: 6 test files + `vitest.config.js` + `eslint.config.js` + `.eslintignore`
- Reverts: `package.json` (vitest, @testing-library/react, eslint and plugins removed from devDependencies)

### Data safety
No data migration needed (preview is read-only, confirm is the only write — trades already in DB are idempotent)
