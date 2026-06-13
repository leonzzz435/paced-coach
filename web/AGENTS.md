# AGENTS.md — Frontend (web)

## Role: Frontend Engineer
**Scope**: `web/app/**`, `web/components/**`, `web/lib/**`

## Context
This is the Next.js local-first web application using:
-   **Framework**: Next.js 14+ (App Router)
-   **Styling**: Tailwind CSS
-   **Auth**: Local-first single-owner mode. Do not add hosted auth providers to the default runtime path.

## Rules
1.  **Server Components by Default**: Use "use client" only when interactivity is required.
2.  **Auth**: Use the local backend owner resolved by `api.deps.get_current_user`; do not add browser login dependencies.
3.  **API**: access backend via `/api/proxy/...` or Server Actions calling the backend service.
4.  **Forms**: Use `react-hook-form` + `zod` for validation.
5.  **Schema Versioning**: UI rendering must route by `schema_version` using versioned renderers.
    - Add new renderers under `web/app/src/components/plan-viewer/versioned/`.
    - Update `web/app/src/components/plan-viewer/versioned/plan-renderer.tsx` when adding new versions.
6.  **Design-heavy work**: For dashboard hierarchy, landing pages, empty states, or broader UI direction, activate `frontend-design`.

## Local Runbook
-   **Start Dev Server**: `npm run dev` (runs on localhost:3000)
-   **Lint/Check**: `npm run lint`
-   **Build Check**: `npm run build` (verifies types + build output)

## Definition of Done
-   [ ] `npm run lint` passes
-   [ ] `npm run build` succeeds locally
-   [ ] No new hydration errors
-   [ ] Responsive design checked (mobile/desktop)
