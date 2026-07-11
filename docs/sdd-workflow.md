# SDD Workflow

This project uses **Spec-Driven Development (SDD)**, a structured workflow where every feature follows a defined lifecycle from exploration to archive.

This document describes how SDD is applied in the DashboardTrading project: what each phase does, how artifacts are stored, and what tooling is integrated.

---

## Workflow Phases

```
Discovery → Proposal → Spec → Design → Tasks → Apply → Verify → Archive
```

### Discovery
Investigate a domain area before committing to a change. Answer domain questions, map existing code, identify risks and constraints.

**Goal:** Understand before deciding.

### Proposal
Define intent, scope, deliverables, and approach at a product/feature level. No technical design yet.

**Goal:** Stakeholder alignment on WHAT and WHY.

### Spec
Write detailed acceptance criteria (Given/When/Then), use cases, contracts, and performance requirements using RFC 2119 keywords (MUST, SHALL, SHOULD, MAY).

**Goal:** Unambiguous requirements that can be tested against.

### Design
Technical architecture, module boundaries, data flow, sequence diagrams, ADRs. Covers HOW without repeating WHAT.

**Goal:** Implementation-ready technical plan.

### Tasks
Break spec + design into numbered implementation tasks grouped by phase. Each task is completable in one session and independently testable.

**Goal:** Clear execution plan with workload forecast.

### Apply
Implement tasks in order. Commits follow conventional commits (`feat:`, `fix:`, `test:`, `chore:`). Each commit is a reviewable work unit.

**Goal:** Working, tested, committed code.

### Verify
Run full test suite, lint, build. Validate against spec acceptance criteria. Prove no regressions.

**Goal:** Green light for merge.

### Archive
Reconcile task checkboxes, sync delta specs to main specs, persist archive report, tag release.

**Goal:** Formal closure and audit trail.

---

## Artifact Storage

Artifacts are stored in **Engram** (cross-session persistent memory) and mirrored in the repository for reference:

| Artifact | Engram Topic | Local File |
|----------|-------------|------------|
| Init | `sdd-init/{project}` | — |
| Discovery | `sdd/{change-name}/explore` | `.sdd/discoveries/` |
| Proposal | `sdd/{change-name}/proposal` | `.sdd/proposals/` |
| Spec | `sdd/{change-name}/spec` | `.sdd/specs/` |
| Design | `sdd/{change-name}/design` | `.sdd/designs/` |
| Tasks | `sdd/{change-name}/tasks` | `.sdd/tasks/` |
| Apply progress | `sdd/{change-name}/apply-progress` | — |
| Verify report | `sdd/{change-name}/verify-report` | — |
| Archive report | `sdd/{change-name}/archive-report` | `.sdd/archive/` |

Main specs are also synced to `openspec/specs/{domain}/spec.md` when using hybrid storage mode.

---

## Tooling

### CodeGraph (structural exploration)

**When to use:** Before writing or editing any code. One call for symbol resolution, call flow, blast radius, and current source.

**Rule:** CodeGraph before Grep. CodeGraph before Read. CodeGraph before Write.

### Context7 (documentation)

**When to use:** Only when there are doubts about framework/library behavior: React Query API, Recharts props, FastAPI patterns, Vitest/Testing Library semantics.

**Rule:** Not a general-purpose search engine. Used only for targeted API/behavior validation.

---

## Change Naming

Changes are named in kebab-case with a short descriptive name:

```
trade-context-classification
analytics-dashboard-v1
equity-performance-analytics
```

---

## Branch and PR Strategy

- **Stacked PRs to `main`** for changes exceeding 400 lines.
- **Single PR with `size:exception`** for cohesive features under 400 lines.
- **Conventional commits** (`feat:`, `fix:`, `test:`, `chore:`, `refactor:`).
- Each PR targets `main` (stacked) or a feature branch (chained).

---

## Verification Gate

Before any merge:

1. `npm run lint` — zero errors
2. `npm test` — zero failures (105+ tests)
3. `npm run build` — clean build (778+ modules)
4. No regressions in existing tests
5. New features have loading/empty/error state coverage

---

## Role Definitions

| Role | Who | Responsibility |
|------|-----|---------------|
| **Orchestrator** | gentle-orchestrator agent | Routes SDD phases, runs preflight/init gates, delegates to sub-agents, validates phase outputs |
| **Executors** | sdd-apply, sdd-design, sdd-spec, etc. | Execute one phase with a fresh context, read/write artifacts, return structured result |
| **Reviewers** | review-risk, review-readability, etc. | Adversarial read-only review of implementation diffs |
