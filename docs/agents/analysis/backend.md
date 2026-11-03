# Area: backend (`backend/app`)

## What it does
This area is the domain core of the FastAPI template: it defines the `User` and `Item` records, the password
hashing and authentication rule, the password-reset and account-creation emails, and the one-time script that
seeds the first superuser. It does not define HTTP routes itself (those live in `backend/api`, which this area
feeds); it is the schemas and business functions that `backend/api`'s routes call. The main types are `User`,
`UserCreate`, `UserUpdate`, `Item`, `ItemCreate` and `ItemUpdate` in `backend/app/models.py:80,30,51,130,112,117`,
and the functions `crud.create_user`, `crud.authenticate`, `crud.update_user`, `crud.create_item` in
`backend/app/crud.py:10,45,20,63`. Per the team, the "veterinary clinic" line in the Project profile is stale for
this repo: there is no real domain data, only the unmodified FastAPI full-stack template's generic
Users/Items, and the app is not deployed anywhere [cite: source:transcript-run-1416470e@r1#T3].

## Entry points
- `main()` in `backend/app/initial_data.py:16` is the script entry point (`python -m app.initial_data`): it opens
  a `Session` and calls `init_db` [cite: backend/app/initial_data.py:11-19].
- `backend/api`'s route handlers are the real callers into this area; none of this area's own files declare an
  HTTP route (no `@router` here) [cite: backend/app/crud.py:1-69] [cite: backend/app/utils.py:1-126]. The
  routes that call in: `login_access_token()` calls `crud.authenticate` [cite: backend/app/api/routes/login.py:30];
  `create_user()` and `register_user()` in `backend/api/routes/users.py` call `crud.create_user`
  [cite: backend/app/api/routes/users.py:68]; `create_item()` in `backend/api/routes/items.py` builds an `Item`
  directly with `Item.model_validate` rather than calling `crud.create_item` [cite: backend/app/api/routes/items.py:68].
- `backend/app/core/db.py`'s `init_db()` is the other direct caller of `crud.create_user`, used to seed the first
  superuser [cite: backend/app/core/db.py:33].
- `UserBase`, `User`, `Message`, `UserCreate` and the other schemas in `backend/app/models.py` are imported and
  used as request/response models across 7+ files of `backend/api` and `backend/core`, per the code graph's
  "what other areas use" list (e.g. `UserBase#email` at `backend/app/models.py:14`, `User` at
  `backend/app/models.py:80`).

## Main flows
1. **Create a user (admin) / register (self-service).**
   `users.py`'s `create_user()` or `register_user()` route handler first calls `crud.get_user_by_email()`
   [cite: backend/app/api/routes/users.py:61] to reject a duplicate email, then calls `crud.create_user()`
   [cite: backend/app/api/routes/users.py:68], which validates the incoming `UserCreate` into a `User`, hashes
   the password with `get_password_hash()` and writes the row [cite: backend/app/crud.py:10-17]. If email is
   configured, the route then calls `generate_new_account_email()` and `send_email()`
   [cite: backend/app/crud.py:7] [cite: backend/app/utils.py:34,87]. Ends writing a `User` row to the database.

2. **Log in.** `login_access_token()` calls `crud.authenticate()` [cite: backend/app/api/routes/login.py:30],
   which looks the user up by email with `get_user_by_email()` [cite: backend/app/crud.py:46], verifies the
   password with `verify_password()`, and — if the stored hash was the legacy bcrypt one — rehashes it to
   argon2 and writes the upgraded hash back [cite: backend/app/crud.py:52-59]. Ends reading a `User` row, and
   conditionally rewriting its `hashed_password`.

3. **Password reset.** `recover_password()` looks the user up with `crud.get_user_by_email()`
   [cite: backend/app/api/routes/login.py:58], then `generate_password_reset_token()` signs a JWT with the
   user's email as `sub` [cite: backend/app/utils.py:105-115], `generate_reset_password_email()` renders the
   template [cite: backend/app/utils.py:70-84], and `send_email()` sends it [cite: backend/app/utils.py:34-57].
   Later, `reset_password()` calls `verify_password_reset_token()` to decode the JWT back to an email
   [cite: backend/app/api/routes/login.py:82] [cite: backend/app/utils.py:118-125], looks the user up again,
   and calls `crud.update_user()` with the new password [cite: backend/app/api/routes/login.py:92]
   [cite: backend/app/crud.py:20-31]. Ends rewriting the user's `hashed_password`.

4. **Seed the first superuser.** `app/initial_data.py`'s `main()` calls `init()`, which opens a `Session` and
   calls `init_db()` [cite: backend/app/initial_data.py:11-18]; `init_db()` (in `backend/app/core/db.py`, which
   this area depends on) checks for an existing user with `settings.FIRST_SUPERUSER`'s email and, if absent,
   builds a `UserCreate` and calls `crud.create_user()` [cite: backend/app/core/db.py:24-33]. Ends writing the
   first `User` row on a fresh database.

## Where it's fragile
- `backend/app/models.py` is the area's biggest hotspot (score 1859, 11 commits over 169 lines) and the type
  most other areas depend on (`User` used in 11 other files) — a change to a field's name, type or validator
  ripples into `backend/api` and the generated OpenAPI/frontend client. Run the full backend test suite
  (`backend/tests/crud/test_user.py` and `backend/api` tests) and check the frontend client is regenerated
  before touching it [cite: backend/app/models.py:1-169].
- The blank/whitespace-stripping validators are duplicated per schema rather than shared: `UserCreate`,
  `UserRegister`, `UserUpdate` and `UserUpdateMe` each declare their own `strip_full_name` classmethod that all
  call the same free function `_strip_full_name()`, and `ItemBase`/`ItemUpdate` each declare their own
  `strip_title` inline instead of calling a shared helper [cite: backend/app/models.py:20,33-36,44-47,58-61,68-71,103-108,121-126].
  Adding a new string field with `min_length` must repeat this pattern (per the Project's validation convention)
  [cite: docs/agents/VALIDATION_CONVENTIONS.md] — easy to forget on one of the four `User*` schemas.
  `backend/tests/crud/test_user.py` doesn't cover this (it tests CRUD, not validation); the whitespace tests live
  in `backend/tests/api/routes/test_users.py` per the callers list (e.g. `test_register_user_blank_full_name_rejected_ac1`).
- `crud.create_item()` [cite: backend/app/crud.py:63] is defined but the live route doesn't call it — `items.py`'s
  `create_item()` reimplements the same three lines (`Item.model_validate` → `session.add` → `commit` → `refresh`)
  directly [cite: backend/app/api/routes/items.py:68-71]. The code graph's callers for `app.crud/create_item()`
  found only the test helper `create_random_item()` [cite: backend/tests/utils/item.py:9-16] as a caller, not the
  route. Changing the item-creation rule in one place (e.g. adding an owner check) and not the other would be a
  silent bug; check both before changing either.
- `authenticate()`'s bcrypt→argon2 upgrade path and its constant-time "user not found" branch (`DUMMY_HASH`) are
  security-sensitive and only exercised by `test_authenticate_user_with_bcrypt_upgrades_to_argon2` and
  `test_not_authenticate_user` [cite: backend/app/crud.py:41-60] [cite: backend/tests/crud/test_user.py:30-34,96-130].
  Any change to the hashing scheme must keep both tests green, since they're the only coverage of the timing-attack
  mitigation and the hash-upgrade behaviour.
- `backend/app/utils.py` is a hotspot too (score 500, 4 commits over 125 lines); `send_email()` asserts
  `settings.emails_enabled` [cite: backend/app/utils.py:40] with a bare `assert`, so calling it when SMTP isn't
  configured raises `AssertionError` rather than a handled error — callers (`users.py`, `login.py`, `utils.py`
  routes) must check `settings.emails_enabled` first, as `create_user()` already does
  [cite: backend/app/api/routes/users.py:69].

## What it connects to
- Uses `backend/core` heavily (100 references per the graph) for `security` (password hashing, JWT) and
  `config.settings` (SMTP, JWT secret, superuser credentials) [cite: backend/app/crud.py:6] [cite: backend/app/utils.py:12-13].
- Used by `backend/api` (10 files) for its models and CRUD/email functions, and by `backend/alembic` (1 file,
  presumably importing `app.models`'s `SQLModel` metadata for migrations).
- Libraries: `sqlmodel` 0.0.48 and `SQLAlchemy` 2.1.6 for the ORM/session [cite: backend/app/crud.py:4,14];
  `fastapi` 0.162.0 and `starlette` for the app object in `main.py` [cite: backend/app/main.py:4-6];
  `pydantic` 2.14.2 for `EmailStr`/`field_validator` [cite: backend/app/models.py:4]; `PyJWT` for token
  encode/decode [cite: backend/app/utils.py:8]; `Jinja2` for email templates [cite: backend/app/utils.py:9];
  `emails` to actually send mail [cite: backend/app/utils.py:7]; `sentry-sdk` for error reporting in
  non-development environments [cite: backend/app/main.py:18-19].
- Outside the repository: a Postgres database reached through the `Session`/`engine` from `backend/core`'s
  `db.py` [cite: backend/app/core/db.py:7], and an SMTP server for `send_email()`
  [cite: backend/app/utils.py:47-56]. Per the team, this Project has no live deployment and no real data — only
  the template's seed data [cite: source:transcript-run-1416470e@r1#T3].

## What we don't know
- `main.py`'s `app.frontend("/", directory=FRONTEND_DIR)` call [cite: backend/app/main.py:36] is not a
  documented `FastAPI` method in the versions this Project pins; whether this works at runtime (or is dead/broken
  code) isn't something the graph's static read can confirm — worth running the app and hitting `/` to check.
- The graph lists `backend/app/__init__.py` as 0 lines and read for symbols, so nothing to say about it beyond
  that it's an empty package marker [cite: backend/app/__init__.py].
- 12 code files across the whole Project weren't read for symbols by the indexer (the callers/depends-on answers
  above all note "12 code files are not read for symbols, so this may be incomplete"); none of the 11 listed as
  unread lie inside `backend/app`, but any caller in one of those 12 files would be missing from the lists above.
- Whether email actually gets sent to a real inbox during manual testing depends on `SMTP_HOST`/`EMAILS_FROM_EMAIL`
  being set at runtime in `backend/core/config.py`'s `settings.emails_enabled`, which this area reads but doesn't
  define — true wiring is start-up configuration, not visible in this area's code
  [cite: backend/app/utils.py:40].
