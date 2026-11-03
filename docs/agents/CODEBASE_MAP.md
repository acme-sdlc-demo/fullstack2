# Codebase map

Built from `docs/agents/ANALYSIS.md` and the per-area files under `docs/agents/analysis/`, the code
graph at commit `10d84f59ea`, and direct reads where the analysis flagged something to confirm. Per
the team, disregard the Project profile's "veterinary clinic" framing: this repo is the unmodified
FastAPI full-stack template (generic `User`/`Item` CRUD), with no real domain data and no live
deployment [cite: source:transcript-run-1416470e@r1#T3].

## Purpose

A two-sided demo/template app: a FastAPI backend managing `User` accounts and generic `Item`
records (signup/login/JWT, password reset by email, CRUD, an admin-only user list) on Postgres, and
a React single-page frontend (TanStack Router + Query, shadcn/Radix UI) that renders forms and
tables against it through a generated Axios API client [cite: docs/agents/ANALYSIS.md]. It exists to
try the platform's CI baseline (Connect), not to run a real clinic or any other product
[cite: source:transcript-run-1416470e@r1#T3].

## Solution layout

| Path | Purpose | Depends on |
|---|---|---|
| `backend/app/models.py` | `User`/`Item` SQLModel schemas (`UserBase`, `UserCreate`, `UserUpdate`, `Item`, `ItemCreate`, ...), the strip-and-reject-blank validators | pydantic, sqlmodel [cite: docs/agents/analysis/backend.md] |
| `backend/app/crud.py` | `create_user`, `authenticate` (bcrypt→argon2 upgrade, timing-safe), `update_user`, `create_item` (unused by the live route) | `backend/app/models.py`, `backend/app/core/security.py` [cite: docs/agents/analysis/backend.md] |
| `backend/app/utils.py` | Password-reset/new-account email rendering (`Jinja2`) and sending (`emails`), JWT reset-token generate/verify | `backend/app/core/config.py` [cite: docs/agents/analysis/backend.md] |
| `backend/app/api/routes/*.py` | The 23 HTTP routes: `items.py`, `login.py`, `users.py`, `utils.py`, `private.py` (dev-only) | `backend/app` (models/crud/utils), `backend/app/core` [cite: docs/agents/analysis/backend-api.md] |
| `backend/app/api/deps.py` | `SessionDep`, `TokenDep`, `CurrentUser` — shared FastAPI dependencies every route imports | `backend/app/core`, `backend/app/models.py` [cite: docs/agents/analysis/backend-api.md] |
| `backend/app/core/config.py` | `Settings`/`settings` — env-driven config (SMTP, JWT secret, DB URL, superuser) | pydantic-settings [cite: docs/agents/analysis/backend-core.md] |
| `backend/app/core/db.py` | The one SQLAlchemy `engine`, `init_db()` (seeds first superuser) | `backend/app/core/config.py`, `backend/app/crud.py` [cite: docs/agents/analysis/backend-core.md] |
| `backend/app/core/security.py` | `create_access_token`, `verify_password`, `get_password_hash` (Argon2+bcrypt) | PyJWT, pwdlib [cite: docs/agents/analysis/backend-core.md] |
| `backend/app/alembic/versions/*` | 5-revision migration chain, `app/models.py` → live Postgres schema | alembic, `backend/app/core/config.py` [cite: docs/agents/analysis/backend-alembic.md] |
| `backend/tests/**` | pytest suite: `crud/test_user.py`, `api/routes/test_{items,login,private,users}.py` | — [cite: docs/agents/analysis/backend-api.md] |
| `frontend/src/client/**.gen.ts` | **Generated** Axios API client (service classes, types) from the backend's OpenAPI schema; never hand-edited | `@hey-api/*`, axios [cite: docs/agents/analysis/frontend-client.md] |
| `frontend/openapi-ts.config.ts` | Build-time generator config read by `openapi-ts` CLI (not type-checked by `bun run build`) | `@hey-api/openapi-ts` [cite: docs/agents/analysis/frontend.md] |
| `frontend/src/components/**` | shadcn/Radix UI kit + feature components: `Admin/*`, `Items/*`, `UserSettings/*`, `Sidebar/*` | `frontend/src/client`, `frontend/src/hooks`, `frontend/src/lib` [cite: docs/agents/analysis/frontend-components.md] |
| `frontend/src/hooks/*` | `useAuth` (session/JWT), `useCustomToast`, `useCopyToClipboard`, `useIsMobile` | `frontend/src/client` [cite: docs/agents/analysis/frontend-hooks.md] |
| `frontend/src/lib/utils.ts` | `cn()` — Tailwind class-merge helper, most-depended-on symbol in the repo (27 files) | clsx, tailwind-merge [cite: docs/agents/analysis/frontend-lib.md] |
| `frontend/src/routes/**` | TanStack file-based pages: dashboard, `/items`, `/admin`, `/settings`, login/signup/recover/reset | `frontend/src/components`, `frontend/src/hooks`, `frontend/src/client` [cite: docs/agents/analysis/frontend-routes.md] |
| `frontend/tests/**` | Playwright e2e specs (`admin`, `items`, `login`, `reset-password`, `sign-up`, `user-settings`) + `utils/` plumbing (`mailpit.ts`, `privateApi.ts`) | `frontend/src/client`'s `PrivateService`, a live backend+Mailpit [cite: docs/agents/analysis/frontend-tests.md] |
| `packages/react-email/**`, `hooks/post_gen_project.py`, `scripts/{add_latest_release_date,prepare_release}.py` | Email templates / cookiecutter / release scripts — outside any component, **not indexed for symbols** | — [cite: docs/agents/ANALYSIS.md] |

## Key concepts

- **`User` / `Item`** (the only two domain types): defined in `backend/app/models.py:80,130`, each
  with `Base`/`Create`/`Update`/`Public` schema variants; `User` is used in 11 other files, the
  single most depended-on backend type [cite: docs/agents/analysis/backend.md].
- **Strip-and-reject-blank validation**: the Project's one written convention — any API-boundary
  `str` `Field(min_length=...)` must strip whitespace before the length check
  (`strip_title`/`strip_full_name` pattern) [cite: docs/agents/VALIDATION_CONVENTIONS.md]. **Known
  gap:** password fields (`UserCreate.password`, `UserRegister.password`, `UserUpdate.password`,
  `UpdatePassword.*`, `NewPassword.new_password`) declare `min_length=8` without it, so an
  8-space password currently validates — open design question, not yet decided
  [cite: docs/OPEN_QUESTIONS.md].
- **`CurrentUser` / `SessionDep` / `TokenDep`** (`backend/app/api/deps.py:26-27,49`): the FastAPI
  dependencies nearly every route uses for auth and DB access [cite: docs/agents/analysis/backend-api.md].
- **Item ownership rule**: "superuser, or the row's `owner_id` is mine" — duplicated inline in three
  handlers (`read_item`, `update_item`, `delete_item`) in `backend/app/api/routes/items.py:56,89,109`
  rather than centralised [cite: docs/agents/analysis/backend-api.md].
- **The one shared Axios `client`** (`frontend/src/client/client.gen.ts:16`): configured once in
  `frontend/src/main.tsx:17-20` with `baseURL`/`auth` reading `localStorage["access_token"]`; every
  generated service call goes through it [cite: docs/agents/analysis/frontend-client.md].
- **`access_token` in `localStorage`**: the one piece of client session state, written by
  `useAuth.ts`'s `login`, read by `isLoggedIn()`, duplicated as a route guard in five files
  (`_layout.tsx`, `login.tsx`, `signup.tsx`, `recover-password.tsx`, `reset-password.tsx`)
  [cite: docs/agents/analysis/frontend-routes.md] [cite: docs/agents/analysis/frontend-hooks.md].
- **Schema → migration → generated client**, the one cross-cutting flow: a change to
  `backend/app/models.py` needs an `alembic revision --autogenerate` under
  `backend/app/alembic/versions/` and a run of `scripts/generate-client.sh` to refresh
  `frontend/src/client/**.gen.ts` before the frontend compiles against the new shape
  [cite: docs/agents/ANALYSIS.md].

## Where to change what

| Change | Files | Tests | Cite |
|---|---|---|---|
| Add/rename a `User`/`Item` field | `backend/app/models.py` (schema + validator if `str`+`min_length`); new file in `backend/app/alembic/versions/` via `alembic revision --autogenerate`; then `scripts/generate-client.sh` to refresh `frontend/src/client/**.gen.ts` | `backend/tests/crud/test_user.py`, `backend/tests/api/routes/test_users.py`/`test_items.py`; `bun run build` on frontend after regen | [cite: docs/agents/analysis/backend.md] [cite: docs/agents/analysis/backend-alembic.md] [cite: docs/agents/analysis/frontend-client.md] |
| Add/change a backend route | `backend/app/api/routes/<module>.py`; wire in `backend/app/api/main.py:6-14` if new | `backend/tests/api/routes/test_<module>.py` | [cite: docs/agents/analysis/backend-api.md] |
| Change the item-ownership rule | all three sites in `backend/app/api/routes/items.py:56,89,109` | `backend/tests/api/routes/test_items.py` | [cite: backend/app/api/routes/items.py:56] [cite: docs/agents/analysis/backend-api.md] |
| Change password hashing/JWT | `backend/app/core/security.py`; keep `ALGORITHM`/`SECRET_KEY` in sync between sign (`create_access_token`) and verify (`get_current_user` in `backend/app/api/deps.py:30-34`) | `backend/tests/crud/test_user.py` (bcrypt→argon2, `test_not_authenticate_user`), `backend/tests/api/routes/test_login.py` | [cite: docs/agents/analysis/backend-core.md] [cite: docs/agents/analysis/backend-api.md] |
| Change a config/env field | `backend/app/core/config.py`; grep every `settings.<FIELD>` use first (16 files read it) | run full `pytest tests/` with `FASTAPI_ENV=development` (no dedicated `app/core` test file) | [cite: docs/agents/analysis/backend-core.md] |
| Add a frontend page | new file under `frontend/src/routes/**` (TanStack file-route convention); add guards (`isLoggedIn()`/superuser check) matching existing routes | a new `frontend/tests/*.spec.ts` | [cite: docs/agents/analysis/frontend-routes.md] |
| Add/change a form | the component under `frontend/src/components/<Area>/*.tsx` (zod schema + react-hook-form), mirroring the backend's strip/reject rule | the relevant `frontend/tests/*.spec.ts` (e.g. `admin.spec.ts`'s password cases) | [cite: docs/agents/analysis/frontend-components.md] |
| Change shared styling helper | `frontend/src/lib/utils.ts` (`cn()`, used in 27 files) — no unit-test net exists; check `button.tsx`, `card.tsx`, `Logo.tsx` after | none exists; Playwright is the only net | [cite: docs/agents/analysis/frontend-lib.md] |
| Change session/auth handling | `frontend/src/hooks/useAuth.ts`; update all five `isLoggedIn()` guard sites listed above if the key/mechanism changes | `frontend/tests/login.spec.ts`, `sign-up.spec.ts` | [cite: docs/agents/analysis/frontend-hooks.md] [cite: docs/agents/analysis/frontend-routes.md] |
| Regenerate the API client | run `bash scripts/generate-client.sh` (needs a runnable backend); never hand-edit `frontend/src/client/**.gen.ts` | `bun run build`, then the Playwright suite | [cite: docs/agents/analysis/frontend-client.md] [cite: scripts/generate-client.sh] |

## Build and test

Full gate commands are in `CLAUDE.md` (*enforced*, don't change them). Summary:
- Backend lint/type: `ruff check`, `ruff format --check`, `ty check app`, `mypy app`
  [cite: CLAUDE.md].
- Backend build/test: `alembic upgrade head`, then `coverage run -m pytest tests/`, then
  `coverage report --fail-under=90` [cite: CLAUDE.md].
- Frontend lint/build: `biome check`, `bun run build` (`tsc -p tsconfig.build.json && vite build`)
  [cite: docs/agents/ANALYSIS.md].
- Frontend e2e: boots the backend (`alembic upgrade head` + `initial_data.py` to seed the first
  superuser), then runs the full Playwright suite against it [cite: CLAUDE.md].
- To iterate on one area without the full gate: `$python -m pytest tests/api/routes/test_items.py`
  (etc.) for backend; `bunx playwright test items.spec.ts` (etc.) for frontend — but the gate's own
  commands are what's actually enforced, so run them before finishing a change.

## Risky areas

1. **`backend/app/api/deps.py:36` has invalid Python syntax**: `except InvalidTokenError,
   ValidationError:` is missing tuple parentheses — confirmed by reading the file directly, not just
   the analysis [cite: backend/app/api/deps.py:36]. This is a `SyntaxError` under Python 3, and
   almost every route module imports from `app.api.deps`, so as written the whole API — and hence
   `pytest`/the coverage gate — fails at import/collection. This is the single highest-priority thing
   to check before trusting any other backend finding or any green/red gate result in this worktree
   [cite: docs/agents/analysis/backend-api.md].
2. **`backend/app/models.py`** is the repo's top commit-churn hotspot (score 1859: 11 commits × 169
   lines) and `User` is used in 11 other files [cite: backend/app/models.py:1-169]. The
   strip-and-reject-blank validators are duplicated per schema rather than shared, and password
   fields don't yet follow the rule at all (see Key concepts) [cite: docs/OPEN_QUESTIONS.md].
3. **`frontend/src/client/types.gen.ts`** is the single highest-churn file in the whole repo (score
   1894: 2 commits × 947 lines), entirely generated with no test of its own; every component/route
   depends on its shapes [cite: docs/agents/analysis/frontend-client.md].
4. **Item-ownership check duplicated 3×** and **`crud.create_item()` defined but unused** by the live
   route (which reimplements create inline) — a change to one must be checked against the other
   [cite: backend/app/api/routes/items.py:68] [cite: docs/agents/analysis/backend.md].
5. **`frontend/src/components/Admin/AddUser.tsx`/`EditUser.tsx`** are the hottest frontend-component
   files (6/5 commits, 239 lines each) with near-duplicate, subtly different password zod rules
   [cite: docs/agents/analysis/frontend-components.md].
6. **No frontend unit-test framework**: `cn()` (27 callers), all 4 hooks, and every component are
   exercised only via Playwright — a pure logic regression surfaces as a visual diff, not a failing
   test, unless e2e happens to assert on it [cite: docs/agents/analysis/frontend-lib.md].
7. **`backend/app/core/config.py`** is the backend's second churn hotspot (7 commits × 91 lines);
   `settings` is read in 16 other files with no dedicated test file for `app/core` itself
   [cite: docs/agents/analysis/backend-core.md].
8. **`backend/app/alembic`'s `d98dd8ec85a3`** migration (int→UUID PKs) runs raw, order-dependent SQL
   with zero automated test; only `alembic upgrade head`/`downgrade` end-to-end (run once per gate)
   checks it [cite: docs/agents/analysis/backend-alembic.md].
9. **`frontend/openapi-ts.config.ts`** is excluded from the TypeScript build the gate runs (no
   tsconfig/source-set names it) and has no test; a bad edit is only caught when
   `scripts/generate-client.sh` actually runs [cite: docs/agents/analysis/frontend.md].
10. **Version mismatch, unresolved**: `backend/pyproject.toml` pins Python `>=3.14,<4.0`
    [cite: backend/pyproject.toml:5], but the code graph recorded `python-stdlib` `3.11` usage across
    22 backend files — which interpreter the indexer (and CI) actually used is unconfirmed
    [cite: docs/agents/ANALYSIS.md].
11. **12 code files were never read for symbols** by the graph (11 outside any component —
    `packages/react-email/**`, `hooks/post_gen_project.py`, `scripts/{add_latest_release_date,
    prepare_release}.py` — plus `frontend/openapi-ts.config.ts` for imports only): any caller/callee
    relationship touching them is invisible to "callers"/"dependents" answers from the code graph
    tool; read those files directly before changing them or assuming nothing calls them
    [cite: docs/agents/ANALYSIS.md].
12. **`private.py`'s `create_user()`** accepts `PrivateUserCreate.is_verified` but never reads it when
    building the `User` row — unconfirmed whether this is a bug or deliberate; this dev-only route
    (`FASTAPI_ENV=="development"`) is what `frontend/tests/utils/privateApi.ts` depends on for test
    user seeding [cite: backend/app/api/routes/private.py:16-20,29-33] [cite: docs/agents/analysis/backend-api.md].

## Connections

### Provides
- None found: no entry in the Vertical's registry names this Project, and nothing in the code or the
  team's interview indicates another Project builds on this one — per the team this pilot "is not
  deployed anywhere" [cite: source:transcript-run-1416470e@r1#T3]. The backend's 23 HTTP routes
  [cite: docs/agents/analysis/backend-api.md] and the frontend it serves are only ever called by this
  repo's own generated client and Playwright suite, per the code graph's HTTP links (98 of 98 calls
  linked to a route in this same repo) [cite: docs/agents/ANALYSIS.md].

### Uses
- None found: the registry is empty and the team confirmed neither deploy path
  (`compose.yml`'s Postgres/Traefik/Adminer stack, or the GitHub Actions `deploy.yml` to FastAPI
  Cloud) is actually used, so there is no live external Postgres, SMTP, or Sentry project this
  Project depends on in practice — only its own local/CI-only instances
  [cite: source:transcript-run-1416470e@r1#T3] [cite: docs/agents/analysis/backend-core.md].
