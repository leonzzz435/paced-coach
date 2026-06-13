---
name: nextjs-frontend
description: Guidelines for Next.js App Router, Server Actions, and Client Components. Use when working in web/.
---

# Next.js Frontend Patterns

## 1. App Router
-   **Structure**: Group routes by feature folder.
-   **Layouts**: Use `layout.tsx` for shared persistence.

## 2. Components
-   **Server First**: Default to Server Components. Add `use client` only for interactive leaves.
-   **Suspense**: Wrap async server components in `<Suspense>`.

## 3. Data Fetching
-   **Server**: Fetch directly in Server Components (async/await w/ fetch).
-   **Client**: Use `useQuery` (TanStack Query) for client-side data.

## 4. Styling
-   **Tailwind**: Use utility classes.
-   **Shadcn**: Use `cn()` for class merging.
