# Project

## Purpose and users

- The profile states the purpose as "Full-stack web app template: a FastAPI backend (users, items,
  login, emails) on Postgres and a React frontend, hosted on GitHub to try Connect's CI baseline"
  [cite: profile:purpose]. The team confirmed this is the accurate description of this repo: an
  unmodified FastAPI full-stack template with generic `User` and `Item` CRUD, kept to exercise the
  platform's CI baseline — not a product serving real users
  [cite: source:transcript-run-1416470e@r1#T3].
- The profile also carries a line describing this as "a pilot: a veterinary clinic web app"
  [cite: profile:regulatory_context]. The team explicitly says this is wrong for this repo — it was
  carried over from a different ("petclinic") pilot — and asked that the write-up record the code
  as it is (generic Users/Items), not invent a clinic domain
  [cite: source:transcript-run-1416470e@r1#T3]. See `docs/OPEN_QUESTIONS.md` for this as a
  documents-vs-profile discrepancy.
- There are two "user" populations the code actually distinguishes: a regular authenticated
  `User` (signs up, logs in, owns `Item` rows) and a superuser/admin (can list/manage all users and
  see all items, not just their own) [cite: backend/app/models.py] [cite: backend/app/api/routes/items.py].
  There is no end-user-facing domain beyond that — `Item` is a generic titled/described record with
  no veterinary or clinic-specific fields [cite: backend/app/models.py].
- Per the team, there is no real deployment and no real data behind this Project: only the
  template's seed data (a first superuser and test items), no live clinic or other customer
  [cite: source:transcript-run-1416470e@r1#T3].

## Domain and constraints (regulations, safety, performance, platforms)

- Regulatory context: "None" per the profile [cite: profile:regulatory_context]. The "veterinary
  clinic" phrasing in that same field is, per the team, stale and inapplicable to this repo
  [cite: source:transcript-run-1416470e@r1#T3]; there is no regulatory regime (e.g. clinical records,
  animal-health rules) actually enforced anywhere in the code — no such checks were found in
  `backend/app` or `frontend/src`.
- Safety class: "none" per the profile [cite: profile:safety_class]. Nothing in the code adds a
  safety-critical path (e.g. no device control, no medical dosing logic) — the app is CRUD over
  `User`/`Item` [cite: backend/app/models.py].
- Performance: nothing in the sources or code states a performance target, SLA, or load
  expectation. Nothing in the sources.
- Security/input handling: requests are untrusted input and must be validated at the API boundary
  [cite: CLAUDE.md]. The one written convention is that any `str` `Field(min_length=...)` read from
  a request must strip whitespace before the length check, so whitespace-only input can't satisfy
  `min_length` [cite: docs/agents/VALIDATION_CONVENTIONS.md], following the existing `strip_title`/
  `strip_full_name` pattern in `backend/app/models.py` [cite: backend/app/models.py]. This rule is
  not yet applied to password fields — see `docs/OPEN_QUESTIONS.md`.
- Platforms: backend is Python (pytest, FastAPI/SQLModel/Postgres) [cite: profile:languages]
  [cite: CLAUDE.md]; frontend is TypeScript/Node (Jest/Vitest config present but, per the codebase
  map, only Playwright e2e tests actually exist today) [cite: profile:languages]
  [cite: docs/agents/CODEBASE_MAP.md]. Checks run on GitHub Actions; a PR needs them green plus an
  approval before merge [cite: source:transcript-run-1416470e@r1#T1]. Two deploy paths exist in the
  repo — a `compose.yml` Docker Compose stack (Postgres/Traefik/Adminer) and a GitHub Actions
  `deploy.yml` job targeting FastAPI Cloud — but per the team **neither is used**; both are the
  template's unmodified defaults, kept as-is, and this Project is not deployed anywhere
  [cite: source:transcript-run-1416470e@r1#T3].

## Decisions so far (and why)

- **Treat the profile's "veterinary clinic" line as inapplicable to this repo.** The team
  identified it as carried over from a different ("petclinic") pilot and asked that this Project be
  documented as the generic FastAPI full-stack template instead of inventing a clinic domain
  [cite: source:transcript-run-1416470e@r1#T3].
- **Neither deploy path is live.** `compose.yml` (Postgres, Traefik, Adminer, a `backend` container
  with env-injected secrets) and `.github/workflows/deploy.yml` (push to FastAPI Cloud) both exist
  in the repo but are unused template defaults, per the team — kept rather than removed
  [cite: source:transcript-run-1416470e@r1#T3] [cite: compose.yml] [cite: .github/workflows/deploy.yml].
- **Email sending is optional/config-gated**, so the app runs without a real SMTP server: `emails_enabled`
  is true only when both `SMTP_HOST` and `EMAILS_FROM_EMAIL` are set
  [cite: backend/app/core/config.py] [cite: source:transcript-run-1416470e@r1#T1].
- **The frontend API client (`frontend/src/client`) is generated from the backend's OpenAPI schema
  and is never hand-edited** — a backend model change must flow through regeneration
  (`scripts/generate-client.sh`) before the frontend compiles against the new shape
  [cite: source:transcript-run-1416470e@r1#T1] [cite: docs/agents/CODEBASE_MAP.md].
- **Strip-and-reject-blank validation is the one written backend coding convention**: any
  API-boundary `str` field with `min_length` must strip whitespace first, modelled on `ItemBase`/
  `ItemUpdate`'s `strip_title` and `UserCreate`/`UserRegister`/`UserUpdate`/`UserUpdateMe`'s
  `strip_full_name` [cite: docs/agents/VALIDATION_CONVENTIONS.md] [cite: backend/app/models.py].
  Why: without it, a whitespace-only value (e.g. `"   "`) satisfies `min_length` even though it
  carries no real content once trimmed [cite: docs/agents/VALIDATION_CONVENTIONS.md].
- **Checks run on GitHub Actions; a PR needs them green and an approval** before merge — the
  platform's gate mirrors this (ruff/ty/mypy/biome lint, backend+frontend build, pytest with a 90%
  coverage floor, full Playwright e2e) [cite: source:transcript-run-1416470e@r1#T1] [cite: CLAUDE.md].

## Glossary

- **`User`**: the account/auth domain type — email, password hash, `is_active`, `is_superuser`,
  optional `full_name`; owns zero or more `Item` rows [cite: backend/app/models.py].
- **`Item`**: the only other domain type — a `title` (required, non-blank) and optional
  `description`, owned by a `User` via `owner_id` [cite: backend/app/models.py]. Generic, with no
  clinic-specific (or any other domain-specific) fields.
- **Superuser**: a `User` with `is_superuser=True`; bypasses the item-ownership check and can list
  all users [cite: backend/app/api/routes/items.py] [cite: backend/app/models.py].
- **`CurrentUser`/`SessionDep`/`TokenDep`**: FastAPI dependency aliases in `backend/app/api/deps.py`
  used by nearly every route for auth and DB access [cite: backend/app/api/deps.py].
- **`access_token`**: the JWT the frontend stores in browser `localStorage` after login and sends as
  a bearer token on every authenticated request [cite: docs/agents/CODEBASE_MAP.md].
- **Strip-and-reject-blank validation**: the convention that any API-boundary `str` field declaring
  `min_length` must strip whitespace before the length check, so whitespace-only input is rejected
  rather than accepted [cite: docs/agents/VALIDATION_CONVENTIONS.md].
- **The generated client** (`frontend/src/client/**.gen.ts`): the Axios-based API client produced
  from the backend's OpenAPI schema by `scripts/generate-client.sh`; never hand-edited
  [cite: source:transcript-run-1416470e@r1#T1] [cite: docs/agents/CODEBASE_MAP.md].
- **The gate**: the platform's enforced set of checks (lint, build, test, coverage) that must pass
  on every change, listed in `CLAUDE.md` [cite: CLAUDE.md].
