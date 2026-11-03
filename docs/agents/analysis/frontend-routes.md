# Area analysis: frontend/routes

## What it does

This area is the app's page layer: each file is one URL a user can visit — the dashboard, items, admin users, settings, and the public login/signup/password flows — wired up by TanStack Router's file-based routing. The main types doing this are the `Route` objects each file exports via `createFileRoute`/`createRootRoute` (e.g. `export const Route = createFileRoute("/_layout/items")` [cite: frontend/src/routes/_layout/items.tsx:20], `export const Route = createRootRoute({...})` [cite: frontend/src/routes/__root.tsx:7]), plus the page components they render, like `Dashboard()` [cite: frontend/src/routes/_layout/index.tsx:16], `Items()` [cite: frontend/src/routes/_layout/items.tsx:57], `Admin()` [cite: frontend/src/routes/_layout/admin.tsx:59], `Login()` [cite: frontend/src/routes/login.tsx:53], and `SignUp()` [cite: frontend/src/routes/signup.tsx:60]. The team confirmed this repo is the generic FastAPI full-stack template (Users/Items), not a real veterinary-clinic app, so these routes should be read as that generic template's pages, not as clinic-specific screens [cite: source:transcript-run-1416470e@r1#T3].

## Entry points

- The app's single `main.tsx` builds the router from the generated route tree and mounts `RouterProvider`, which is how every file in this area is actually reached at runtime: `const router = createRouter({ routeTree })` then `<RouterProvider router={router} />` [cite: frontend/src/main.tsx:40,51]. `routeTree` is generated from these files by the router's file-based convention (not itself hand-written code reviewed here).
- `__root.tsx` is the router's root: it renders `<Outlet />` for whichever child route matched, plus devtools, and owns the app-wide not-found/error components [cite: frontend/src/routes/__root.tsx:7-17].
- `_layout.tsx` is the entry point for every authenticated page (`/`, `/items`, `/admin`, `/settings`): its `beforeLoad` redirects to `/login` unless `isLoggedIn()` is true, gating the whole sidebar-shell layout [cite: frontend/src/routes/_layout.tsx:12-20].
- The public auth pages are reached directly by URL: `/login` [cite: frontend/src/routes/login.tsx:35], `/signup` [cite: frontend/src/routes/signup.tsx:42], `/recover-password` [cite: frontend/src/routes/recover-password.tsx:33], `/reset-password` [cite: frontend/src/routes/reset-password.tsx:49] — each guarded the other way, redirecting to `/` if already `isLoggedIn()` [cite: frontend/src/routes/login.tsx:37-42].
- No other area calls into these files as a library (the graph's "Entry points: none found" for this area beyond the router itself) — the only "other area" usage recorded is each file's own `Route`/namespace self-reference, which is the router's file convention, not a real external caller [cite: frontend/src/routes/_layout/admin.tsx:20].

## Main flows

**Login:**
1. User submits the form on `/login`; `onSubmit` calls `loginMutation.mutate(data)` from `useAuth()` [cite: frontend/src/routes/login.tsx:65-68].
2. `useAuth`'s `loginMutation` calls `LoginService.loginAccessToken` and stores the token: `localStorage.setItem("access_token", response.data.access_token)` [cite: frontend/src/hooks/useAuth.ts:41-46].
3. On success it navigates to `/` [cite: frontend/src/hooks/useAuth.ts:50-52], which re-enters `_layout.tsx`'s `beforeLoad` guard, now passing because `isLoggedIn()` reads the stored token [cite: frontend/src/routes/_layout.tsx:14-19, frontend/src/hooks/useAuth.ts:14-16].
4. Writes: `localStorage["access_token"]`. Reads on every guarded route: the same key via `isLoggedIn()`.

**Signup (mirrors backend validation):**
1. `signup.tsx`'s zod `formSchema` requires `full_name` non-empty after trim and matching passwords before the form will submit [cite: frontend/src/routes/signup.tsx:23-38].
2. `onSubmit` strips `confirm_password` and calls `signUpMutation.mutate(submitData)` [cite: frontend/src/routes/signup.tsx:74-80].
3. `useAuth`'s `signUpMutation` posts to `UsersService.registerUser` and, on success, navigates to `/login` [cite: frontend/src/hooks/useAuth.ts:29-34].
4. This client-side `full_name` check is a frontend mirror of the backend's own strip-and-reject-blank validator for the same field, per the team [cite: source:transcript-run-1416470e@r1#T1]; the backend still re-validates (`strip_full_name`/`_strip_full_name` on `UserRegister`) independently [cite: source:transcript-run-1416470e@r1#T1].
5. Writes: a new user row via the backend API (outside this area); on success, navigation state only (no localStorage write here).

**Password recovery and reset:**
1. `/recover-password` submits `{ email }` to `LoginService.recoverPassword` via a local `useMutation`, showing a success toast and resetting the form [cite: frontend/src/routes/recover-password.tsx:60-73].
2. The emailed link lands on `/reset-password?token=...`; `validateSearch: searchSchema` parses the `token` query param, and `beforeLoad` redirects to `/login` if no token is present [cite: frontend/src/routes/reset-password.tsx:28-59].
3. Submitting the new-password form calls `LoginService.resetPassword({ body: { new_password, token } })`; on success it toasts, resets the form and navigates to `/login` [cite: frontend/src/routes/reset-password.tsx:84-97].
4. Writes: a password change via the backend API; reads: the `token` route search param [cite: frontend/src/routes/reset-password.tsx:70].

**Items / Admin tables (authenticated, data-fetching):**
1. `/items` and `/admin` both sit under `_layout.tsx`'s login guard [cite: frontend/src/routes/_layout.tsx:14-19].
2. `admin.tsx` additionally checks superuser status in its own `beforeLoad`, calling `UsersService.readUserMe()` and redirecting to `/` if `!user.is_superuser` [cite: frontend/src/routes/_layout/admin.tsx:22-29].
3. Each page's table component uses `useSuspenseQuery` with a `queryFn` calling `ItemsService.readItems` or `UsersService.readUsers` [cite: frontend/src/routes/_layout/items.tsx:12-18, frontend/src/routes/_layout/admin.tsx:12-18], rendered through a `Suspense` boundary with a `Pending*` fallback [cite: frontend/src/routes/_layout/items.tsx:49-55, frontend/src/routes/_layout/admin.tsx:51-56].
4. Reads: items/users lists from the backend API (`skip: 0, limit: 100`, no pagination UI) [cite: frontend/src/routes/_layout/items.tsx:15, frontend/src/routes/_layout/admin.tsx:15].

## Where it's fragile

- `signup.tsx` is the area's hotspot (5 commits across its 187 lines) [cite: frontend/src/routes/signup.tsx], and its zod schema is a second copy of validation rules the backend also enforces (full_name non-blank, password length, password match) [cite: frontend/src/routes/signup.tsx:23-38]. Changing either side without the other reintroduces the whitespace-only-name or password-mismatch bugs the project's validation conventions exist to prevent [cite: docs/agents/VALIDATION_CONVENTIONS.md]; check both `backend/app/models.py`'s validators and this schema together, and run the Playwright e2e suite, which exercises signup end to end.
- `recover-password.tsx` and `reset-password.tsx` are also comparatively hot (2 and 1 commits respectively, but 100% of the file each time) [cite: frontend/src/routes/recover-password.tsx] [cite: frontend/src/routes/reset-password.tsx]. `reset-password.tsx`'s `beforeLoad` silently redirects to `/login` whenever the `token` search param is missing or fails `searchSchema`'s `.catch("")` fallback [cite: frontend/src/routes/reset-password.tsx:28-29,56-58]; a change to the email link format or the query-param name would fail silently (redirect, no error shown) rather than loudly, so check this path manually after any change to the email templates outside this area.
- The login/logged-in guard (`isLoggedIn()`) is duplicated as a `beforeLoad` check in five separate files (`_layout.tsx`, `login.tsx`, `recover-password.tsx`, `reset-password.tsx`, `signup.tsx`) rather than centralised in one route [cite: frontend/src/routes/_layout.tsx:14-19, frontend/src/routes/login.tsx:37-42, frontend/src/routes/recover-password.tsx:35-40, frontend/src/routes/reset-password.tsx:52-55, frontend/src/routes/signup.tsx:44-49]; a change to how "logged in" is determined (e.g. moving off `localStorage`) must touch all five call sites plus `isLoggedIn` itself [cite: frontend/src/hooks/useAuth.ts:14-16].
- None of these ten files has its own `*.test.ts`/`*.spec.ts` in this folder (the layout rules put frontend tests in `*.test.ts`/`*.spec.ts`/`__tests__`, and the graph lists 0 test files for this area's indexed files); route-level behaviour (guards, redirects, form submission) is only covered, if at all, by the Playwright suite run as part of the gate, not by unit tests in this folder — treat any change here as needing that e2e run.

## What it connects to

- Uses `frontend/components` the most heavily (238 references): page-level composition (`DataTable`, `AddUser`, `AddItem`, `AuthLayout`, the `ui/form` and `ui/*` primitives) [cite: frontend/src/routes/_layout/items.tsx:6-9, frontend/src/routes/login.tsx:11-22].
- Uses `frontend/hooks` (43 references): `useAuth` for login/signup/logout mutations and current user [cite: frontend/src/routes/_layout/index.tsx:3,17] and `useCustomToast` for success/error toasts [cite: frontend/src/routes/recover-password.tsx:24,58].
- Uses `frontend/client` (35 references): the generated API services — `LoginService`, `UsersService`, `ItemsService` — and their request/response types [cite: frontend/src/routes/_layout/items.tsx:6, frontend/src/routes/_layout/admin.tsx:5, frontend/src/routes/recover-password.tsx:11].
- Used by `frontend` (1 file): `main.tsx` is the only file outside this area that pulls these routes together, via the generated `routeTree` [cite: frontend/src/main.tsx:15,40].
- Libraries: `@tanstack/react-router` (routing/`Route`/`Outlet`/`redirect`, all 10 files) [cite: frontend/src/routes/__root.tsx:2], `@tanstack/react-query` / `@tanstack/query-core` (`useSuspenseQuery`, `useMutation`) [cite: frontend/src/routes/_layout/admin.tsx:1], `react-hook-form` + `@hookform/resolvers/zod` + `zod` for all four forms [cite: frontend/src/routes/login.tsx:1,7,8], `lucide-react` for the empty-state icon on `/items` [cite: frontend/src/routes/_layout/items.tsx:3], `@radix-ui/react-tabs` via the settings page's `Tabs` component [cite: frontend/src/routes/_layout/settings.tsx:6].
- Outside the repository: no direct network/database/file access in this area; all backend access goes through the generated `frontend/src/client` services called from these files (e.g. `UsersService.readUserMe()` [cite: frontend/src/routes/_layout/admin.tsx:23]), and browser `localStorage` is read/written only via `isLoggedIn`/`useAuth`, not directly in these route files [cite: frontend/src/hooks/useAuth.ts:14-16,45].

## What we don't know

- `frontend/src/routeTree.gen.ts`, which actually wires these ten files into the router `main.tsx` uses, is generated and wasn't itself analysed here as hand-written logic — a mismatch between a route's file path and its registered URL would only show up at build/run time, not in this review [cite: frontend/src/main.tsx:15].
- `frontend/openapi-ts.config.ts`, which configures generation of the `frontend/src/client` services these routes call, was read for imports only, not symbols, by the indexer, so its effect on what `LoginService`/`UsersService`/`ItemsService` expose isn't verified here beyond reading the generated client's call sites directly.
- Whether the Playwright e2e suite actually exercises every guard/redirect in this area (logged-in redirect, missing-token redirect, superuser redirect) wasn't checked here — reading `frontend/tests` (a separate area) would be needed to confirm coverage before relying on it as a safety net for changes flagged above.
- The profile's description of this Project as "a veterinary clinic web app" does not match what the code or the team describes; per the team this is the unmodified generic template (Users/Items, no live deployment, no real data), so this analysis follows that correction rather than the profile [cite: source:transcript-run-1416470e@r1#T3].
