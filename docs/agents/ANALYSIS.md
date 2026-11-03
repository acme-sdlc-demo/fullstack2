# Project analysis

## At a glance

This is a two-sided demo/template app, not a deployed product: a FastAPI backend that manages
`User` accounts and generic `Item` records (create, log in, reset password, CRUD), paired with a
React single-page frontend that renders forms and tables against it. Per the team, the Project
profile's "veterinary clinic" description is stale — this repo is the unmodified FastAPI
full-stack template (Users/Items only), has no real domain data, and is not deployed anywhere;
read every point below as describing that generic template, not a clinic system
[cite: source:transcript-run-1416470e@r1#T3].

Size and shape, from the code graph's summary at commit `10d84f59ea`: 257 files / 22,117 lines
total, split as `backend` (57 files, 3,495 lines: 25 source + 14 test, all 39 code files indexed),
`frontend` (119 files, 11,674 lines: 93 source + 6 test, 98 of 99 code files indexed for symbols,
1 for imports only), and 81 files/6,948 lines outside any component (email templates, release
scripts, generator hooks) that the gate doesn't yet read for symbols [facts in the prompt's
summary]. The nine analysed areas:
- `backend` (`backend/app`): the `User`/`Item` schemas, password hashing rules and CRUD/email
  functions that the API routes call into [cite: docs/agents/analysis/backend.md].
- `backend/api` (`backend/app/api`): the 23 HTTP routes — login/JWT, users, items, utils, a
  dev-only private endpoint [cite: docs/agents/analysis/backend-api.md].
- `backend/core` (`backend/app/core`): shared config (`Settings`/`settings`), the one SQLAlchemy
  `engine`, and password/JWT security functions every other backend area depends on
  [cite: docs/agents/analysis/backend-core.md].
- `backend/alembic` (`backend/app/alembic`): the five-revision migration chain that turns
  `app/models.py` into the live Postgres schema [cite: docs/agents/analysis/backend-alembic.md].
- `frontend` (`frontend/openapi-ts.config.ts`): the one build-time config file that drives
  generation of the typed API client [cite: docs/agents/analysis/frontend.md].
- `frontend/client` (`frontend/src/client`): the fully generated Axios-based API client every UI
  call goes through [cite: docs/agents/analysis/frontend-client.md].
- `frontend/components` (`frontend/src/components`): the shadcn/Radix UI kit plus the
  Admin/Items/UserSettings/Sidebar feature components [cite: docs/agents/analysis/frontend-components.md].
- `frontend/hooks` (`frontend/src/hooks`): `useAuth`, `useCustomToast`, `useCopyToClipboard`,
  `useIsMobile` [cite: docs/agents/analysis/frontend-hooks.md].
- `frontend/lib` (`frontend/src/lib`): the single `cn()` class-merging helper
  [cite: docs/agents/analysis/frontend-lib.md].
- `frontend/routes` (`frontend/src/routes`): the ten TanStack-Router pages (dashboard, items,
  admin, settings, login/signup/recover/reset) [cite: docs/agents/analysis/frontend-routes.md].
- `frontend/tests` (`frontend/tests`): the Playwright end-to-end suite
  [cite: docs/agents/analysis/frontend-tests.md].

Stack and pinned versions, named exactly as the build files and the graph's library list give
them: backend is Python `>=3.14,<4.0` [cite: backend/pyproject.toml:5] with `fastapi[standard]`
0.162.0 [cite: docs/agents/analysis/backend.md], `sqlmodel` 0.0.48 and `SQLAlchemy` 2.1.6
[cite: docs/agents/analysis/backend-core.md], `pydantic` 2.14.2 and `pydantic-settings` 2.16.2
[cite: docs/agents/analysis/backend-core.md], `alembic` 1.20.1 [cite: docs/agents/analysis/backend-alembic.md],
`PyJWT` 2.15.1 and `pwdlib` 0.3.1 (Argon2 + bcrypt) [cite: docs/agents/analysis/backend-core.md].
Frontend is Node/TypeScript `^6.0.3` [cite: frontend/package.json:62] on React `^19.3.0`
[cite: frontend/package.json:40], `@tanstack/react-router` 1.170.39 and `@tanstack/react-query`
5.104.0 [cite: docs/agents/analysis/frontend-routes.md], `react-hook-form` 7.89.0 /
`@hookform/resolvers/zod` / `zod` 4.6.5 for every form [cite: docs/agents/analysis/frontend-components.md],
`axios` 1.20.0 as the generated client's transport [cite: docs/agents/analysis/frontend-client.md],
`@playwright/test` 1.63.0 for e2e [cite: docs/agents/analysis/frontend-tests.md], and
`@hey-api/openapi-ts` 0.97.3 as the devDependency that generates the client
[cite: frontend/package.json:52]. One disagreement worth flagging: `backend/pyproject.toml`
pins `requires-python = ">=3.14,<4.0"` [cite: backend/pyproject.toml:5], but the code graph's
library list records usage of `python-stdlib` version `3.11` across 22 backend files [facts in
the prompt's summary] — the indexer evidently ran against a 3.11 environment, not the pinned
3.14; this is worth reconciling before trusting any Python-version-sensitive detail from the
graph.

Testing: the gate enforces backend lint (`ruff check`/`ruff format --check`, `ty check`, `mypy`),
a migration build step, `pytest` under coverage with a 90% floor, and a full Playwright e2e run;
frontend lint is `biome check` and the build is `tsc`+`vite build` [cite: CLAUDE.md]. By area,
backend routes have substantial pytest coverage (`test_items.py`, `test_login.py`,
`test_private.py`, `test_users.py` totalling 1,231+ lines) [cite: docs/agents/analysis/backend-api.md],
but `backend/app/core` and `backend/app/alembic` have no dedicated test file of their own — they're
only exercised indirectly through the route tests and the gate's own `alembic upgrade head` step
[cite: docs/agents/analysis/backend-core.md] [cite: docs/agents/analysis/backend-alembic.md].
On the frontend, **no area has a Jest/Vitest unit test** — `frontend/lib`, `frontend/hooks` and
`frontend/components` all report zero `*.test.ts`/`*.spec.ts` files found, so all frontend coverage
is the browser-driven Playwright suite in `frontend/tests`
[cite: docs/agents/analysis/frontend-lib.md] [cite: docs/agents/analysis/frontend-hooks.md]
[cite: docs/agents/analysis/frontend-components.md] [cite: docs/agents/analysis/frontend-tests.md].

## How it works

**1. Sign up and log in.**
1. A visitor fills `/signup`; a zod schema checks `full_name` is non-blank after trim and the
   passwords match before submitting [cite: frontend/src/routes/signup.tsx:23-38].
2. `useAuth`'s `signUpMutation` calls the generated `UsersService.registerUser`
   [cite: frontend/src/hooks/useAuth.ts:29-31], which the backend's `register_user()` route
   receives [cite: backend/app/api/routes/users.py:146].
3. The route calls `crud.get_user_by_email()` to reject a duplicate, then `crud.create_user()`,
   which validates the `UserCreate` into a `User`, hashes the password with
   `get_password_hash()` and writes the row [cite: backend/app/crud.py:10-17]
   [cite: docs/agents/analysis/backend.md]. Ends: a new `User` row written to Postgres.
4. The visitor then logs in at `/login`; `loginMutation` calls `LoginService.loginAccessToken`
   [cite: frontend/src/hooks/useAuth.ts:41-46], hitting `login_access_token()`
   [cite: backend/app/api/routes/login.py:23], which calls `crud.authenticate()`
   [cite: backend/app/crud.py:45] — this looks the user up, verifies the password hash (running a
   dummy verify against a constant `DUMMY_HASH` even for a missing user, to resist timing attacks)
   [cite: backend/app/crud.py:48-54], and — if the stored hash was legacy bcrypt — rehashes it to
   Argon2 and writes it back [cite: backend/app/crud.py:55-59]. On success
   `security.create_access_token()` signs a JWT with the user id as `sub`
   [cite: backend/app/core/security.py:22-26].
5. The frontend writes the returned token to `localStorage["access_token"]`
   [cite: frontend/src/hooks/useAuth.ts:45] and navigates to `/`, where `_layout.tsx`'s
   `beforeLoad` guard now passes because `isLoggedIn()` reads that key
   [cite: frontend/src/routes/_layout.tsx:12-20] [cite: frontend/src/hooks/useAuth.ts:14-16]. The
   graph's diagram will show this login→token→guard loop as an edge; what it won't show is *which*
   key (`access_token`) or *where* (browser `localStorage`, not a cookie) the state actually lives —
   that's the detail above.

**2. Every later authenticated call.**
1. The one shared `client` instance (built once, `throwOnError: true`) is configured at app
   start-up: `main.tsx` calls `client.setConfig({ baseURL: import.meta.env.VITE_API_URL, auth: () =>
   localStorage.getItem("access_token") })` [cite: frontend/src/main.tsx:17-20]
   [cite: frontend/src/client/client.gen.ts:16].
2. Any generated service method whose OpenAPI spec declares a bearer scheme — e.g.
   `UsersService.readUserMe`, `ItemsService.readItems` — has its request's `Authorization: Bearer
   <token>` header filled by that `auth` callback before the request leaves the browser
   [cite: frontend/src/client/client/client.gen.ts:52-53] [cite: frontend/src/client/core/auth.gen.ts:22-33].
3. On the backend, `get_current_user()` (the `CurrentUser` dependency used by nearly every route)
   decodes that bearer token with `jwt.decode(token, settings.SECRET_KEY, algorithms=[security.ALGORITHM])`
   [cite: backend/app/api/deps.py:30-34], builds a `TokenPayload`, and loads the `User` row by id
   [cite: backend/app/api/deps.py:41], raising 404/400 if missing or inactive
   [cite: backend/app/api/deps.py:42-45]. **This step is currently broken in this worktree** — see
   "Where it's fragile" below; the graph's call-graph edges from every route into `get_current_user`
   are real, but the function as written cannot run.
4. Ends: a `User` row read (no write), or an HTTP error back to the browser.

**3. Item CRUD, scoped by ownership.**
1. A route under `/items` or a component in `frontend/src/components/Items` calls
   `ItemsService.createItem`/`readItems`/`updateItem`/`deleteItem`
   [cite: docs/agents/analysis/frontend-client.md] [cite: docs/agents/analysis/frontend-components.md],
   reaching `backend/app/api/routes/items.py`'s handlers, all behind `SessionDep` + `CurrentUser`
   [cite: backend/app/api/routes/items.py:14-15,49,62-63,76-81,100-101].
2. Non-superusers see/touch only their own rows: `read_items` filters by `Item.owner_id ==
   current_user.id` [cite: backend/app/api/routes/items.py:28-32], and `read_item`/`update_item`/
   `delete_item` each repeat an inline `not current_user.is_superuser and (item.owner_id !=
   current_user.id)` check [cite: backend/app/api/routes/items.py:56,89,109].
3. `create_item` stamps `owner_id` to the caller via `Item.model_validate(item_in, update={"owner_id":
   current_user.id})` directly in the route — notably *not* via `crud.create_item()`, which exists
   but is unused by the live route [cite: backend/app/api/routes/items.py:68]
   [cite: docs/agents/analysis/backend.md].
4. React Query's cache is invalidated on `["items"]` after a mutation so the table re-fetches
   [cite: docs/agents/analysis/frontend-components.md]. Ends: reads/writes to the `items` table,
   always owner-scoped unless the caller is a superuser.

**4. Password recovery by email.**
1. `/recover-password` posts an email to `LoginService.recoverPassword`
   [cite: frontend/src/routes/recover-password.tsx:60-73], reaching `recover_password()`
   [cite: backend/app/api/routes/login.py:53], which looks the user up, generates a signed JWT
   reset token (`generate_password_reset_token()`, `sub` = email) and a rendered email
   (`generate_reset_password_email()`), then sends it via `send_email()`
   [cite: backend/app/api/routes/login.py:60-71] [cite: backend/app/utils.py:70-84,105-115]. It
   always returns the same message whether or not the email exists, to avoid leaking which emails
   are registered [cite: backend/app/api/routes/login.py:60-74].
2. The emailed link lands on `/reset-password?token=...`; the route's `beforeLoad` redirects to
   `/login` if the token search param is missing [cite: frontend/src/routes/reset-password.tsx:28-59].
3. Submitting calls `LoginService.resetPassword`, reaching `reset_password()`
   [cite: backend/app/api/routes/login.py:77], which calls `verify_password_reset_token()` to
   decode the JWT back to an email [cite: backend/app/api/routes/login.py:82]
   [cite: backend/app/utils.py:118-125], re-loads the user, and calls `crud.update_user()` with the
   new password — rehashing and overwriting `hashed_password` [cite: backend/app/api/routes/login.py:92]
   [cite: backend/app/crud.py:20-31]. Ends: a DB write and, upstream, an SMTP send (both external
   effects the graph's static diagram cannot show happening or not — `send_email()` only fires if
   `settings.emails_enabled`, itself dependent on `.env` values set at start-up
   [cite: backend/app/utils.py:40] [cite: docs/agents/analysis/backend.md]).

**5. Schema change → migration → generated client (the cross-cutting flow).**
1. A developer changes a field in `backend/app/models.py`.
2. `alembic revision --autogenerate` diffs the live DB against `SQLModel.metadata` via `env.py`
   and writes a new file under `backend/app/alembic/versions/`, chained to the previous `head` by
   `revision`/`down_revision` [cite: docs/agents/analysis/backend-alembic.md]; the gate's build
   step then applies it with `alembic upgrade head` [cite: CLAUDE.md].
3. Separately (or via the `generate-frontend-sdk` pre-commit hook), `scripts/generate-client.sh`
   dumps the running app's OpenAPI JSON (`app.main.app.openapi()`), moves it to
   `frontend/openapi.json`, and runs `openapi-ts`, which reads `frontend/openapi-ts.config.ts` and
   rewrites every file under `frontend/src/client/**.gen.ts`
   [cite: docs/agents/analysis/frontend.md]. The graph's diagram will show the frontend areas
   depending on `frontend/client`'s types, but not that those types are regenerated, not hand-edited,
   per the team [cite: source:transcript-run-1416470e@r1#T1] — a model change is only "live" on the
   frontend after this regeneration step actually runs.

## Where it's fragile

Ranked by how many other places would break and how little test coverage currently guards them:

1. **`backend/app/api/deps.py:36` has invalid Python syntax right now**: `except InvalidTokenError,
   ValidationError:` is missing the tuple parentheses, which is a `SyntaxError` under Python 3
   (confirmed by reading the file directly). Nearly every route module imports from `app.api.deps`
   (`items.py`, `login.py`, `users.py`, `utils.py`) [cite: docs/agents/analysis/backend-api.md], so
   as written the whole API fails to import. Before anything else in this repo, fix this (wrap in
   a tuple: `except (InvalidTokenError, ValidationError):`) and confirm `$python -m pytest tests/`
   even runs — do not trust any other finding here until that's green
   [cite: docs/agents/analysis/backend-api.md].
2. **`backend/app/models.py`** is the single biggest hotspot in the repo by commit churn (score
   1859: 11 commits × 169 lines) [cite: docs/agents/analysis/backend.md] and its `User` type is
   used in 11 other files [facts in the prompt's summary]; a field rename ripples through
   `backend/api`, the OpenAPI schema and the generated frontend client. The whitespace-stripping
   validators are also duplicated per schema (`UserCreate`/`UserRegister`/`UserUpdate`/
   `UserUpdateMe` each declare their own `strip_full_name`, `ItemBase`/`ItemUpdate` their own
   `strip_title`) [cite: docs/agents/analysis/backend.md] [cite: docs/agents/VALIDATION_CONVENTIONS.md] —
   and this pattern is **not yet applied** to the password fields: `UserCreate.password`,
   `UserRegister.password`, `UserUpdate.password`, `UpdatePassword.current_password`/
   `new_password`, and `NewPassword.new_password` all declare `min_length=8` with no stripping, so
   an 8-space password currently passes validation [cite: docs/OPEN_QUESTIONS.md]. Run the full
   backend suite and check the frontend client is regenerated before touching any of these.
3. **`frontend/src/client/types.gen.ts`** is the single highest-churn file in the whole repo (score
   1894: 2 commits × 947 lines) [cite: docs/agents/analysis/frontend-client.md], and every
   component/route/hook that calls the API depends on its shapes. It's entirely generated, has no
   test of its own, and a hand-edit is lost on regeneration — a schema change must flow from
   `backend/app/models.py` through `scripts/generate-client.sh`, not be patched here directly
   [cite: docs/agents/analysis/frontend-client.md].
4. **The item-ownership check is duplicated three times** (`read_item`, `update_item`,
   `delete_item` in `backend/app/api/routes/items.py:56,89,109`) instead of centralised in a
   dependency, and **`crud.create_item()` is defined but unused** by the live route, which
   reimplements the same create logic inline [cite: backend/app/api/routes/items.py:68]
   [cite: docs/agents/analysis/backend.md]. A change to who may touch an item, or to the create
   rule, must be made in step with all these call sites and their tests
   (`backend/tests/api/routes/test_items.py`).
5. **`frontend/src/components/Admin/AddUser.tsx` and `EditUser.tsx`** are the two hottest
   frontend-components files (6 and 5 commits over 239 lines each)
   [cite: docs/agents/analysis/frontend-components.md] and carry near-duplicate zod password rules
   (required on create, optional-and-must-match on edit); run `admin.spec.ts`'s password tests
   after touching either. The same component area's frontend validation is weaker than the
   backend's: `title`/`full_name` fields use `z.string().min(1)` without trimming, so a
   whitespace-only value passes the client check and is only rejected server-side, surfacing as a
   generic toast instead of a field error [cite: docs/agents/analysis/frontend-components.md].
6. **No frontend area has a unit test.** `frontend/lib`'s `cn()` (the most-depended-on symbol in
   the whole codebase, used in 27 files [facts in the prompt's summary]), all four `frontend/hooks`,
   and every `frontend/components` file are exercised only indirectly via Playwright — a pure
   regression (e.g. a changed class-merge order) would surface as a visual difference, not a
   failing test, unless the e2e suite happens to assert on it
   [cite: docs/agents/analysis/frontend-lib.md] [cite: docs/agents/analysis/frontend-hooks.md]
   [cite: docs/agents/analysis/frontend-components.md].
7. **`backend/app/core/config.py`** is the backend's second churn hotspot (score 637: 7 commits ×
   91 lines) [cite: docs/agents/analysis/backend-core.md] and `settings` is read in 16 other files
   [facts in the prompt's summary]; a field rename ripples into routes, deps, alembic and tests
   that read it by name, and there is no test file dedicated to `app/core` itself
   [cite: docs/agents/analysis/backend-core.md].
8. **`backend/app/alembic`**'s `d98dd8ec85a3` migration (integer→UUID primary keys) runs raw
   `op.execute` SQL with an order-dependent rename and has zero automated tests; the only check is
   actually running `alembic upgrade head`/`downgrade` end to end, which the gate does once per run
   [cite: docs/agents/analysis/backend-alembic.md].
9. **`frontend/openapi-ts.config.ts`** is excluded from the TypeScript build the gate runs (`bun
   run build` doesn't type-check it) and has no test; a bad edit is only caught when
   `generate-client.sh` is actually run [cite: docs/agents/analysis/frontend.md].

## What it connects to

- **Other Projects:** none recorded — `docs/agents/CODEBASE_MAP.md` does not exist yet in this
  repository (it "arrives with the Project's Knowledge Run" per `CLAUDE.md`, and this run found
  only `VALIDATION_CONVENTIONS.md` and `OPEN_QUESTIONS.md` under `docs/`), so there is nothing to
  report here as a cross-Project "Connections" list; this Project's own interview explicitly
  confirms it has no live deployment to connect to anything [cite: source:transcript-run-1416470e@r1#T3].
- **External services (per the team, configured but never actually exercised live):** a Postgres
  database reached via `settings.DATABASE_URL` through the shared SQLAlchemy `engine`
  [cite: backend/app/core/config.py:31] [cite: docs/agents/analysis/backend-core.md], used by
  every route via `SessionDep` and by every Alembic migration; an SMTP server for password-reset
  and new-account emails, gated behind `settings.emails_enabled` (true only when `SMTP_HOST` and
  `EMAILS_FROM_EMAIL` are set) [cite: source:transcript-run-1416470e@r1#T1]
  [cite: docs/agents/analysis/backend.md]; Sentry, if `SENTRY_DSN` is set
  [cite: docs/agents/analysis/backend-core.md]; and, only in the Playwright suite, a Mailpit
  mail-capture HTTP service read by `utils/mailpit.ts` to verify reset emails
  [cite: docs/agents/analysis/frontend-tests.md]. Per the team, `compose.yml` (Postgres + Traefik
  + Adminer) and the GitHub Actions `deploy.yml` (FastAPI Cloud) are both the template's unmodified
  defaults and neither is actually used [cite: source:transcript-run-1416470e@r1#T3].
- **Database:** the one SQL database in this system is Postgres, accessed only through SQLModel/
  SQLAlchemy's `engine` and session objects — there is no secondary database anywhere in the
  graph's library list [cite: docs/agents/analysis/backend-core.md] [facts in the prompt's
  summary].
- **Caches, queues:** none — no cache layer or message queue appears in the graph's library list
  or any area's analysis [facts in the prompt's summary].
- **Key libraries and versions** (full list under "At a glance"): backend —
  `fastapi[standard]` 0.162.0, `sqlmodel` 0.0.48, `SQLAlchemy` 2.1.6, `pydantic` 2.14.2,
  `pydantic-settings` 2.16.2, `alembic` 1.20.1, `PyJWT` 2.15.1, `pwdlib` 0.3.1 (Argon2+bcrypt),
  `Jinja2`, `emails`, `sentry-sdk` [cite: docs/agents/analysis/backend.md]
  [cite: docs/agents/analysis/backend-core.md] [cite: docs/agents/analysis/backend-alembic.md];
  frontend — `react` ^19.3.0, `@tanstack/react-router` 1.170.39, `@tanstack/react-query` 5.104.0,
  `react-hook-form` 7.89.0, `zod` 4.6.5, `axios` 1.20.0, `clsx` 2.1.1, `tailwind-merge` 3.7.0,
  `@hey-api/openapi-ts` 0.97.3 (dev), `@playwright/test` 1.63.0
  [cite: docs/agents/analysis/frontend-client.md] [cite: docs/agents/analysis/frontend-lib.md]
  [cite: docs/agents/analysis/frontend-tests.md] [cite: frontend/package.json:52].

## What we don't know

- The code graph did not read 12 code files for their symbols: 11 because their folder ("no
  component") isn't named in the gate — `hooks/post_gen_project.py`, the four
  `packages/react-email/emails/*.tsx` templates, the five `packages/react-email/ui/*.tsx`
  components, and `scripts/add_latest_release_date.py`/`prepare_release.py` — and one,
  `frontend/openapi-ts.config.ts`, read for imports only because no tsconfig/source-set in the
  frontend build names it [facts in the prompt's summary]. Anything those files call or are called
  by is invisible to every "callers"/"dependents" answer above; in particular, the email templates
  under `packages/react-email` are rendered by `backend/app/utils.py`'s email-generation functions
  [cite: docs/agents/analysis/backend.md] but weren't themselves analysed as an area.
- **Run-time-only wiring the graph cannot see:** which `.env` values (`SECRET_KEY`,
  `DATABASE_URL`, SMTP credentials, `FIRST_SUPERUSER*`, `VITE_API_URL`, `MAILPIT_HOST`) are set in
  any given run; whether `FASTAPI_ENV` is actually `"development"` outside the gate's own commands;
  and whether `main.py`'s `app.frontend("/", directory=FRONTEND_DIR)` call — not a documented
  `FastAPI` method in the pinned version — works at all, since this is static analysis, not a run
  [cite: docs/agents/analysis/backend.md] [cite: docs/agents/analysis/backend-core.md].
- **Two concrete current-state questions, not yet confirmed by a human:** (a) whether
  `backend/app/api/deps.py:36`'s invalid `except` syntax (see "Where it's fragile" #1) is a live
  regression on the default branch, since it would make the whole API fail to import as written
  [cite: docs/agents/analysis/backend-api.md]; (b) whether `private.py`'s `create_user()` silently
  dropping the incoming `PrivateUserCreate.is_verified` field is an intentional no-op or a bug
  [cite: docs/agents/analysis/backend-api.md].
- **An explicit open design question the team has not resolved:** whether password fields that
  declare `min_length` should be stripped like `title`/`full_name` (risking silently changing a
  user's intended password) or instead rejected-but-not-altered when whitespace-only — see
  `docs/OPEN_QUESTIONS.md` for the full argument [cite: docs/OPEN_QUESTIONS.md].
- **A numeric mismatch inside one area's own analysis, unresolved:** `docs/agents/analysis/frontend.md`
  reports the graph's aggregate "uses"/"used by" counts for the `frontend` area (routes 60,
  components 9, client 5 used; components 14, routes 10, hooks 1 using) even though its one file,
  `openapi-ts.config.ts`, imports only `defineConfig` and exports nothing — that area's own writeup
  flags this as unresolved from the file alone and recommends asking whoever maintains the graph
  tooling whether those aggregates are scoped to the file or to the whole component by name
  collision [cite: docs/agents/analysis/frontend.md].
- **A version mismatch between the pin and what the graph recorded:** `backend/pyproject.toml`
  requires Python `>=3.14,<4.0` [cite: backend/pyproject.toml:5], but the graph's library list
  shows `python-stdlib` `3.11` used across 22 backend files [facts in the prompt's summary] — which
  one the indexer actually ran against, versus what CI/the gate installs, is not resolved here.
- **No `docs/agents/CODEBASE_MAP.md` exists yet** in this worktree, so this analysis cannot cite a
  cross-Project "Connections" list; per `CLAUDE.md` that file "comes with the Project's Knowledge
  Run," which this run is producing alongside this document [cite: CLAUDE.md].

## What this means for you

**For a change:** Start by reading the area analysis for the folder you're touching
(`docs/agents/analysis/<area>.md`) and the build files it names, per `CLAUDE.md`'s own instruction
to do that before the code map exists [cite: CLAUDE.md]. If you touch `backend/app/models.py`,
grep every `settings.<FIELD>`/model field use first, regenerate the frontend client
(`bash scripts/generate-client.sh`), and run both the backend suite and `bun run build`
[cite: docs/agents/analysis/backend.md] [cite: docs/agents/analysis/frontend-client.md]. If you
touch anything under `backend/app/api`, first confirm the module even imports cleanly given the
`deps.py:36` issue above. For any backend change, run the gate's own commands locally:
`$python -m ruff check .`, `$python -m ruff format --check .`, `$python -m ty check app`,
`$python -m mypy app`, `FASTAPI_ENV=development $python -m alembic upgrade head`, then
`FASTAPI_ENV=development $python -m coverage run -m pytest tests/` and
`$python -m coverage report --fail-under=90` [cite: CLAUDE.md]. For a frontend change, run
`npm ci`/`bun ci` from the lock file, `bunx biome check`, `bun run build`, and the Playwright suite
described in `CLAUDE.md`'s gate commands — there is no unit-test net to catch a regression in
`frontend/lib`, `frontend/hooks` or `frontend/components`, so the e2e run is the only automated
check [cite: CLAUDE.md] [cite: docs/agents/analysis/frontend-lib.md].

**For a migration:** Backend and frontend move together through exactly one seam: a change to
`backend/app/models.py` or a route's response shape requires regenerating
`frontend/src/client/**.gen.ts` via `scripts/generate-client.sh` before the frontend areas that
depend on it (`frontend/components`, `frontend/routes`, `frontend/hooks`) will compile correctly
[cite: docs/agents/analysis/frontend.md] [cite: docs/agents/analysis/frontend-client.md]. Watch
the pinned-version seams specifically: Python is pinned `>=3.14,<4.0` but the graph recorded
`python-stdlib` 3.11 usage, so confirm which interpreter CI actually uses before assuming either
[cite: backend/pyproject.toml:5]; TypeScript is `^6.0.3` and the frontend build is `tsc -p
tsconfig.build.json && vite build` with Vite `^8.3.1` — a major bump to either, or to
`@tanstack/react-router`/`react-query` (file-based routing and query invalidation touch nearly
every route file), should be done with the full Playwright suite green before and after
[cite: frontend/package.json:62,8,63] [cite: docs/agents/analysis/frontend-routes.md]. Migrating
off the template's assumptions (e.g. adding real deployment) should also revisit the
`localStorage`-held `access_token` pattern, which the team accepts for a template demo but flags
as worth reconsidering for a real deployment [cite: docs/agents/analysis/frontend-hooks.md]
[cite: source:transcript-run-1416470e@r1#T3].

**For a newcomer:** Read, in order: this document; `docs/agents/analysis/backend.md` and
`docs/agents/analysis/backend-api.md` for the domain model and the 23 routes it serves; then
`docs/agents/analysis/frontend-routes.md` and `frontend-components.md` for how the UI calls those
routes; then `docs/agents/VALIDATION_CONVENTIONS.md` and `docs/OPEN_QUESTIONS.md`, since the
strip-and-reject-blank validation rule is the one coding convention the team has explicitly
written down and it currently has a known, undecided gap (passwords)
[cite: docs/agents/VALIDATION_CONVENTIONS.md] [cite: docs/OPEN_QUESTIONS.md]. Treat the Project
profile's "veterinary clinic" framing as wrong for this repo — it's the generic FastAPI
full-stack template with Users and Items, no real data, and no live deployment — per the team's
own correction [cite: source:transcript-run-1416470e@r1#T3].
</content>
