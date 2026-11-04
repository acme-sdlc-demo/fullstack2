# Area: backend/api

## What it does
This area is the HTTP surface of the template app: it authenticates users, issues and checks JWT access tokens, and serves CRUD for the two domain objects the template ships — `User` accounts and their `Item`s — plus password-recovery emails and a couple of utility/test endpoints. The team confirmed this is the generic FastAPI full-stack template (Users + Items), not a real veterinary-clinic domain, so read the endpoints literally rather than assuming clinic-specific meaning [cite: source:transcript-run-1416470e@r1#T3]. The main types doing this work are the route modules under `backend/app/api/routes/` — `items.py`, `login.py`, `users.py`, `utils.py`, `private.py` — wired together by `api_router` in `backend/app/api/main.py:6-10,13-14`, and the shared FastAPI dependencies `SessionDep`, `TokenDep` and `CurrentUser` defined in `backend/app/api/deps.py:26-27,49`.

## Entry points
All routes are registered on `api_router` and mounted by the `backend` app; `api_router` itself is the one place another area (`backend/app/main.py`) uses this area, importing and including it [cite: backend/app/main.py:8] [cite: backend/app/main.py:35].

- `GET /items`, `read_items()` [cite: backend/app/api/routes/items.py:13]
- `GET /items/{id}`, `read_item()` [cite: backend/app/api/routes/items.py:48]
- `POST /items`, `create_item()` [cite: backend/app/api/routes/items.py:61]
- `PUT /items/{id}`, `update_item()` [cite: backend/app/api/routes/items.py:75]
- `DELETE /items/{id}`, `delete_item()` [cite: backend/app/api/routes/items.py:99]
- `POST /login/access-token`, `login_access_token()` [cite: backend/app/api/routes/login.py:23]
- `POST /login/test-token`, `test_token()` [cite: backend/app/api/routes/login.py:45]
- `POST /password-recovery/{email}`, `recover_password()` [cite: backend/app/api/routes/login.py:53]
- `POST /reset-password/`, `reset_password()` [cite: backend/app/api/routes/login.py:77]
- `POST /password-recovery-html-content/{email}`, `recover_password_html_content()` [cite: backend/app/api/routes/login.py:105]
- `POST /private/users/`, `create_user()` (only mounted when `FASTAPI_ENV == "development"`) [cite: backend/app/api/routes/private.py:23] [cite: backend/app/api/main.py:13-14]
- `GET /users`, `read_users()` [cite: backend/app/api/routes/users.py:33]
- `POST /users`, `create_user()` [cite: backend/app/api/routes/users.py:55]
- `PATCH /users/me`, `update_user_me()` [cite: backend/app/api/routes/users.py:81]
- `PATCH /users/me/password`, `update_password_me()` [cite: backend/app/api/routes/users.py:103]
- `GET /users/me`, `read_user_me()` [cite: backend/app/api/routes/users.py:124]
- `DELETE /users/me`, `delete_user_me()` [cite: backend/app/api/routes/users.py:132]
- `POST /users/signup`, `register_user()` [cite: backend/app/api/routes/users.py:146]
- `GET /users/{user_id}`, `read_user_by_id()` [cite: backend/app/api/routes/users.py:162]
- `PATCH /users/{user_id}`, `update_user()` [cite: backend/app/api/routes/users.py:187]
- `DELETE /users/{user_id}`, `delete_user()` [cite: backend/app/api/routes/users.py:214]
- `POST /utils/test-email/`, `test_email()` [cite: backend/app/api/routes/utils.py:11-16]
- `GET /utils/health-check/`, `health_check()` [cite: backend/app/api/routes/utils.py:29]

## Main flows

**1. Log in and get a token**
1. A client posts credentials to `POST /login/access-token` [cite: backend/app/api/routes/login.py:23].
2. `login_access_token()` calls `crud.authenticate()` with the submitted email/password [cite: backend/app/api/routes/login.py:30-32], which looks the user up and verifies the password hash, running a dummy verify even for a missing user to resist timing attacks [cite: backend/app/crud.py:45-54].
3. If the user is missing or inactive it raises a 400 [cite: backend/app/api/routes/login.py:33-36]; otherwise it calls `security.create_access_token()` to sign a JWT with the user id as subject [cite: backend/app/api/routes/login.py:39-41] [cite: backend/app/core/security.py:22-26].
4. Ends with: a signed `Token` returned to the client [cite: backend/app/api/routes/login.py:38]; no database write.

**2. Authenticate a request (the `CurrentUser` dependency, used by most routes)**
1. FastAPI resolves `CurrentUser = Annotated[User, Depends(get_current_user)]` for any route parameter typed that way [cite: backend/app/api/deps.py:49], e.g. `items.py` and `users.py` handlers [cite: backend/app/api/routes/items.py:15] [cite: backend/app/api/routes/users.py:83].
2. `get_current_user()` decodes the bearer token with `jwt.decode()` using `settings.SECRET_KEY` [cite: backend/app/api/deps.py:30-34].
3. It builds a `TokenPayload` from the decoded claims and, on success, loads the `User` row by id with `session.get(User, token_data.sub)` [cite: backend/app/api/deps.py:35,41], raising 404/400 if the user is missing or inactive [cite: backend/app/api/deps.py:42-45].
4. Ends with: either a `User` row read from the database, or an HTTP error — no write.
   - The `except` clause lists two exception types without wrapping them in a tuple, `except InvalidTokenError, ValidationError:` [cite: backend/app/api/deps.py:36]. This is valid Python here, not a `SyntaxError`: `backend/pyproject.toml:5` pins `requires-python = ">=3.14,<4.0"` [cite: backend/pyproject.toml:5], and PEP 758 (Python 3.14) allows several exception types in an `except` clause without parentheses.

**3. Password recovery (two routes working together)**
1. `POST /password-recovery/{email}` looks the user up by email [cite: backend/app/api/routes/login.py:58] [cite: backend/app/crud.py:34-37], and — only if found — generates a reset token and emails a reset link, always returning the same message either way to avoid leaking which emails are registered [cite: backend/app/api/routes/login.py:60-74].
2. The token is built by `generate_password_reset_token()` and the email body by `generate_reset_password_email()`, then sent by `send_email()` [cite: backend/app/api/routes/login.py:63-71].
3. Later, `POST /reset-password/` verifies that token with `verify_password_reset_token()`, re-loads the user by email, and on success calls `crud.update_user()` with a `UserUpdate(password=...)` to rehash and store the new password [cite: backend/app/api/routes/login.py:82-96] [cite: backend/app/crud.py:20-31].
4. Ends with: either an email sent (step 1) or the user's `hashed_password` column overwritten (step 3) — both are external-effect/database writes.

**4. Item CRUD, scoped by ownership**
1. Each of `read_items`, `read_item`, `create_item`, `update_item`, `delete_item` depends on both `SessionDep` and `CurrentUser` [cite: backend/app/api/routes/items.py:14-15,49,62-63,76-81,100-101].
2. Non-superusers are restricted to their own rows: `read_items` filters by `Item.owner_id == current_user.id` when not superuser [cite: backend/app/api/routes/items.py:28-32], and `read_item`/`update_item`/`delete_item` each repeat the same `not current_user.is_superuser and (item.owner_id != current_user.id)` ownership check [cite: backend/app/api/routes/items.py:56,89,109].
3. `create_item` stamps the new row's `owner_id` to the caller via `Item.model_validate(item_in, update={"owner_id": current_user.id})` [cite: backend/app/api/routes/items.py:68].
4. Ends with: reads or writes to the `items` table, always scoped to the caller unless they are a superuser.

## Where it's fragile
- `backend/app/api/deps.py:36` reads `except InvalidTokenError, ValidationError:` (no tuple parentheses), which looks at a glance like Python 2 syntax but is valid here: `backend/pyproject.toml:5` pins `requires-python = ">=3.14,<4.0"` [cite: backend/pyproject.toml:5], and PEP 758 (Python 3.14) allows several exception types in an `except` clause without parentheses [cite: backend/app/api/deps.py:36]. Almost every route module still imports from `app.api.deps` — `items.py:7`, `login.py:9`, `users.py:8-12`, `utils.py:4` — so it remains the area's widest-blast-radius file if it's ever broken for some other reason; the backend tests already import `app.api.deps` and pass, confirming today's line is not that reason.
- `backend/app/api/deps.py` is also the area's one commit-churn hotspot (its current state is the product of a single commit touching all of its lines) [cite: backend/app/api/deps.py:1-57], and `backend/app/api/main.py` is the other [cite: backend/app/api/main.py:1-14]; both are small files used by every route, so a mistake here (like the one above) has the widest blast radius in the area.
- The item-ownership rule — "superuser, or the row's `owner_id` is mine" — is duplicated across three handlers instead of centralised in a dependency: `backend/app/api/routes/items.py:56`, `:89`, `:109`. Changing who may touch an item means updating all three call sites and their tests in `backend/tests/api/routes/test_items.py`; a reviewer should check all three stayed in sync.
- `private.py`'s `create_user()` takes an unauthenticated `PrivateUserCreate` with an `is_verified` field [cite: backend/app/api/routes/private.py:16-20], but the handler body never reads `user_in.is_verified` when building the `User` row [cite: backend/app/api/routes/private.py:29-33] — the field is accepted but silently dropped. Confirm with the team whether that's intentional before relying on it; this route is also only mounted in `FASTAPI_ENV == "development"` [cite: backend/app/api/main.py:13-14], so it is absent unless that env var is set (the gate's backend test/build commands do set it).
- `delete_user()` issues a raw `delete(Item).where(col(Item.owner_id) == user_id)` before deleting the `User` row [cite: backend/app/api/routes/users.py:228-230]; this manual cleanup duplicates whatever cascade behaviour (if any) is defined on the `Item`/`User` relationship in `backend/app/models.py` — check that file before changing either side so the two don't drift apart.
- All of these flows are covered by existing tests (`backend/tests/api/routes/test_items.py`, `test_login.py`, `test_private.py`, `test_users.py`, totalling 218+191+26+796 lines per the area's file list) [cite: backend/tests/api/routes/test_items.py:1] [cite: backend/tests/api/routes/test_login.py:1] [cite: backend/tests/api/routes/test_private.py:1] [cite: backend/tests/api/routes/test_users.py:1]; per CLAUDE.md none of those may be skipped, deselected or weakened, so any change here must keep them green and add new tests beside them for new behaviour.

## What it connects to
- Uses area `backend` (626 references from here): the `User`/`Item`/`UserCreate`/`ItemCreate`/`Message`/`Token` models in `backend/app/models.py` (e.g. `User` at `backend/app/models.py:80`, `Item` at `backend/app/models.py:130`), and the `crud` helpers `authenticate`, `get_user_by_email`, `create_user`, `update_user` in `backend/app/crud.py:10,20,34,45`, and the email helpers in `backend/app/utils.py` (`send_email`, `generate_*_email`, token generate/verify) [cite: backend/app/api/routes/login.py:13-18] [cite: backend/app/api/routes/users.py:27].
- Uses area `backend/core` (231 references): `security.create_access_token/verify_password/get_password_hash` [cite: backend/app/core/security.py:22,29,35], and `settings` (`SECRET_KEY`, `API_V1_STR`, `emails_enabled`, `FASTAPI_ENV`) [cite: backend/app/api/deps.py:12,17] [cite: backend/app/core/config.py:61] [cite: backend/app/api/main.py:13], plus the shared SQLAlchemy `engine` for `SessionDep` [cite: backend/app/api/deps.py:13,21-23].
- Used by area `backend` (1 file): `app/main.py` imports and mounts `api_router` under `settings.API_V1_STR` [cite: backend/app/main.py:8] [cite: backend/app/main.py:35].
- Libraries: fastapi 0.162.0 (`APIRouter`, `Depends`, `HTTPException`) [cite: backend/app/api/deps.py:5], PyJWT 2.15.1 (`jwt.decode`) [cite: backend/app/api/deps.py:4,32], pydantic 2.14.2 (`ValidationError`, `pydantic.networks.EmailStr`) [cite: backend/app/api/deps.py:8] [cite: backend/app/api/routes/utils.py:2], sqlmodel 0.0.48 / SQLAlchemy 2.1.6 (`Session`, `select`, `col`, `func`) [cite: backend/app/api/deps.py:9,21] [cite: backend/app/api/routes/items.py:5], starlette 1.10.0 (`HTMLResponse`) [cite: backend/app/api/routes/login.py:5], pwdlib 0.3.1 only appears in the login test [cite: backend/tests/api/routes/test_login.py:137], httpx2 2.16.0 only in the item tests [cite: backend/tests/api/routes/test_items.py:101].
- Outside the repository: a Postgres database reached through the `engine`/`Session` used by `SessionDep` [cite: backend/app/api/deps.py:21-23], and an SMTP server reached through `app.utils.send_email()` called from `login.py` and `users.py` [cite: backend/app/api/routes/login.py:67] [cite: backend/app/api/routes/users.py:73] — neither is configured inside this area.

## What we don't know
- Whether `PrivateUserCreate.is_verified` [cite: backend/app/api/routes/private.py:20] was meant to be stored on the created `User` and is a bug, or is deliberately unused scaffolding — the handler ignores it [cite: backend/app/api/routes/private.py:29-33].
- Run-time wiring the graph cannot see: how `FASTAPI_ENV` is actually set for each deployment target, since the team said neither `compose.yml` nor the GitHub Actions `deploy.yml` is actually used for this pilot and the repo is not deployed anywhere [cite: source:transcript-run-1416470e@r1#T3] — so in practice this area is only ever exercised locally and in CI with `FASTAPI_ENV=development`, per the gate commands in CLAUDE.md, and the `private.py` router's production-mode behaviour is untested here.
- The frontend's generated API client in `frontend/src/client` is produced from this area's OpenAPI schema and is not hand-edited [cite: source:transcript-run-1416470e@r1#T1]; this analysis did not read that generation step or confirm the client is currently in sync with the routes listed above.
