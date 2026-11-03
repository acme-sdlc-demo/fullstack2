# frontend/tests

## What it does

This area is the project's Playwright end-to-end test suite: it drives a real browser against the
running frontend (and, through it, the running backend API) to check that login, sign-up, password
reset, item management, user administration and user-settings flows work from a user's point of
view, rather than testing a function in isolation [cite: frontend/tests/login.spec.ts:1-9]
[cite: frontend/tests/items.spec.ts:11-17] [cite: frontend/tests/admin.spec.ts:7-13]
[cite: frontend/tests/user-settings.spec.ts:9-15]. The spec files hold the `test(...)` /
`test.describe(...)` cases (`admin.spec.ts`, `items.spec.ts`, `login.spec.ts`,
`reset-password.spec.ts`, `sign-up.spec.ts`, `user-settings.spec.ts`)
[cite: frontend/tests/admin.spec.ts:7] [cite: frontend/tests/items.spec.ts:11]
[cite: frontend/tests/login.spec.ts:19] [cite: frontend/tests/reset-password.spec.ts:10]
[cite: frontend/tests/sign-up.spec.ts:27] [cite: frontend/tests/user-settings.spec.ts:9]; the
`utils/` helpers (`user.ts`, `random.ts`, `privateApi.ts`, `mailpit.ts`) and `config.ts`,
`auth.setup.ts` are the plumbing the specs share rather than tests themselves
[cite: frontend/tests/utils/user.ts:3-17] [cite: frontend/tests/utils/random.ts:1-7]
[cite: frontend/tests/utils/privateApi.ts:10-26] [cite: frontend/tests/utils/mailpit.ts:7-46]
[cite: frontend/tests/config.ts:18-19] [cite: frontend/tests/auth.setup.ts:6-13]. Per the team, the
"veterinary clinic" line in the Project profile does not describe this repo: it is an unmodified
pilot of the generic FastAPI full-stack template (Users/Items only, no live deployment, no real
data), so these tests exercise that generic domain, not a clinic one
[cite: source:transcript-run-1416470e@r1#T3].

## Entry points

- No route, `main`, or exported symbol here is called from other areas of the repository: the code
  graph's "Used by areas" for this area lists none, and `EmailSummary`
  (`frontend/tests/utils/mailpit.ts:3`) is the only type this area defines, used only inside this
  folder [cite: frontend/tests/utils/mailpit.ts:3].
- Work instead starts from the Playwright runner, driven by the `test` script in
  `frontend/package.json` (`bunx playwright test`), which loads every `*.spec.ts` plus
  `auth.setup.ts` as the config's `testDir` [cite: frontend/playwright.config.ts:15].
- `auth.setup.ts` is itself an entry point for the suite: the config wires it as the `setup` project
  that every `chromium` test depends on, so it runs first, logs in as the first superuser, and saves
  `playwright/.auth/user.json` for tests to reuse as their default signed-in session
  [cite: frontend/playwright.config.ts:37-46] [cite: frontend/tests/auth.setup.ts:6-13].
- Each spec file's `test(...)`/`test.describe(...)` blocks are the actual entry points Playwright
  calls, one per scenario, e.g. `test("Admin page is accessible and shows correct title", ...)`
  [cite: frontend/tests/admin.spec.ts:7] and `test("Create a new item successfully", ...)`
  [cite: frontend/tests/items.spec.ts:39].

## Main flows

1. Authenticated-by-default UI flow (most specs): Playwright runs the `setup` project
   (`auth.setup.ts`), which calls `page.goto("/login")` and logs in as `firstSuperuser` from
   `config.ts`, then persists the session to `playwright/.auth/user.json`
   [cite: frontend/tests/auth.setup.ts:6-12] [cite: frontend/tests/config.ts:18-19]. Each `chromium`
   test then starts already signed in via that storage state
   [cite: frontend/playwright.config.ts:40-46], so a spec like `admin.spec.ts`'s
   `"Admin page is accessible and shows correct title"` can go straight to `page.goto("/admin")`
   and assert on the rendered page [cite: frontend/tests/admin.spec.ts:7-9]. This reads the live
   frontend app and, through its API calls, the backend/database behind it.
2. Fresh-user flow (tests that need an unauthenticated or new identity): a spec opts out of the
   saved session with `test.use({ storageState: { cookies: [], origins: [] } })`
   [cite: frontend/tests/items.spec.ts:25] [cite: frontend/tests/user-settings.spec.ts:25], generates
   a throwaway identity with `randomEmail()`/`randomPassword()`
   [cite: frontend/tests/utils/random.ts:1-7], creates the user directly through the backend's
   private API via `createUser()` in `utils/privateApi.ts`
   [cite: frontend/tests/utils/privateApi.ts:10-26], then logs in through the real UI with
   `logInUser()` from `utils/user.ts` [cite: frontend/tests/utils/user.ts:19-29] before exercising
   the feature (e.g. items CRUD in `items.spec.ts`'s `"Items management"` describe block)
   [cite: frontend/tests/items.spec.ts:24-37]. This writes a new user row through the backend API,
   then reads/writes items through the UI.
3. Password-reset email flow: `reset-password.spec.ts`'s
   `"User can reset password successfully using the link"` signs up a new user with
   `signUpNewUser()` [cite: frontend/tests/utils/user.ts:3-17], submits the recover-password form,
   then polls Mailpit's HTTP API through `waitForEmailHtml()` in `utils/mailpit.ts` for the email
   addressed to that user, extracts the reset URL from the HTML, visits it, and submits a new
   password [cite: frontend/tests/reset-password.spec.ts:32-67]
   [cite: frontend/tests/utils/mailpit.ts:7-46]. This reads the Mailpit mail-capture service over
   HTTP (`process.env.MAILPIT_HOST`) as well as the frontend/backend
   [cite: frontend/tests/utils/mailpit.ts:20-30].
4. Client-side-validation-only flow: `sign-up.spec.ts`'s
   `"Sign up with whitespace-only full name sends no request ac7"` intercepts the signup network
   call with `page.route("**/api/v1/users/signup", ...)`, fills a whitespace-only full name, submits,
   and asserts both that the client-side "Full Name is required" error shows and that no request was
   ever sent [cite: frontend/tests/sign-up.spec.ts:136-156]. This is a browser-only check; per the
   team this mirrors the backend's strip-and-reject-blank validators in `backend/app/models.py` that
   the frontend's `frontend/src/routes/signup.tsx` form re-implements on the client side
   [cite: source:transcript-run-1416470e@r1#T1].

## Where it's fragile

- `utils/mailpit.ts` is the area's hotspot (score 92 from 2 commits across 46 lines): its
  `waitForEmailHtml()` polls an external Mailpit instance with a hard 5-second default timeout and a
  100ms retry loop, so a slow or unreachable mail capture service makes
  `reset-password.spec.ts`'s email tests flaky rather than giving a clear setup error
  [cite: frontend/tests/utils/mailpit.ts:7-46]. Before changing it, rerun
  `reset-password.spec.ts`'s two email-dependent tests
  [cite: frontend/tests/reset-password.spec.ts:32-68] [cite: frontend/tests/reset-password.spec.ts:83-114]
  against a live Mailpit and check the `MAILPIT_HOST` env var is set, since nothing here validates it
  before use [cite: frontend/tests/utils/mailpit.ts:20].
- `utils/privateApi.ts` is the second hotspot (score 26): it depends on `PrivateService`, which the
  file's own comment says "is only available when generating the client for local environments"
  [cite: frontend/tests/utils/privateApi.ts:1-3], and it points `client` at `process.env.VITE_API_URL`
  with no fallback or validation [cite: frontend/tests/utils/privateApi.ts:6-8]. Every spec that
  creates a throwaway user (`items.spec.ts`, `user-settings.spec.ts`, `admin.spec.ts`) depends on this
  helper [cite: frontend/tests/items.spec.ts:2] [cite: frontend/tests/user-settings.spec.ts:3]
  [cite: frontend/tests/admin.spec.ts:3], so a change to the generated `PrivateService` shape in
  `frontend/client` (an area this one uses but does not own) can silently break several specs at
  once; check `createUser()`'s call shape against the current generated client before editing it
  [cite: frontend/tests/utils/privateApi.ts:17-24].
- `config.ts`'s `getEnvVar()` throws if `FIRST_SUPERUSER`/`FIRST_SUPERUSER_PASSWORD` are unset
  [cite: frontend/tests/config.ts:10-19], and `auth.setup.ts` and most specs that log in as the
  superuser depend on those two env vars resolving to a real, already-seeded account
  [cite: frontend/tests/auth.setup.ts:2] [cite: frontend/tests/login.spec.ts:2]
  [cite: frontend/tests/admin.spec.ts:2] [cite: frontend/tests/user-settings.spec.ts:2]; there is no
  test here for `config.ts` itself, so a bad `.env` fails every spec that imports it rather than one
  targeted test.
- Shared helpers in `utils/user.ts` (`logInUser`, `logOutUser`, `signUpNewUser`) and `utils/random.ts`
  are called from every spec file but have no dedicated unit test of their own
  [cite: frontend/tests/utils/user.ts:3] [cite: frontend/tests/utils/user.ts:19]
  [cite: frontend/tests/utils/user.ts:31] [cite: frontend/tests/utils/random.ts:1]; they are only
  exercised indirectly through the specs that call them, so a change to one (e.g. the toast text
  `logInUser()` asserts on, "Welcome back, nice to see you again!") must be checked against every
  spec that calls it, not just the one being edited [cite: frontend/tests/utils/user.ts:26-28].

## What it connects to

- Uses `frontend/client` (14 references per the code graph), specifically the generated
  `PrivateService` and `client` from `frontend/src/client` imported in `utils/privateApi.ts` to seed
  users directly through the backend's private API rather than through the UI
  [cite: frontend/tests/utils/privateApi.ts:3-4].
- No area in the repository is recorded as using this one ("Used by areas: none"): it is a leaf,
  run only by the Playwright CLI and CI, not imported by application code.
- Runs against the live frontend dev server or a deployed `PLAYWRIGHT_BASE_URL`
  [cite: frontend/playwright.config.ts:4] [cite: frontend/playwright.config.ts:88-94], which in turn
  calls the live backend API and its Postgres database (outside this folder, via the generated
  client) [cite: frontend/tests/utils/privateApi.ts:3-8].
- Calls the Mailpit mail-capture service's HTTP API at `process.env.MAILPIT_HOST` to read captured
  emails, an external dependency outside the repository's own services
  [cite: frontend/tests/utils/mailpit.ts:20-30].
- Libraries: `@playwright/test` 1.63.0 (test runner/assertions, e.g.
  [cite: frontend/tests/admin.spec.ts:1]), `playwright-core` and `playwright` 1.63.0 (browser
  automation, transitively via `@playwright/test`), `typescript` 5.9.3 and `@types/node` 26.6.3 (used
  in `config.ts`'s Node path/env handling [cite: frontend/tests/config.ts:1-3]), `axios` 1.20.0 (the
  generated client's HTTP layer, used from `utils/privateApi.ts` [cite: frontend/tests/utils/privateApi.ts:25]),
  `dotenv` (loads `.env` in `config.ts` [cite: frontend/tests/config.ts:3,8]), and `vite` (one file,
  per the graph's library list, reflecting the `VITE_API_URL` env convention
  [cite: frontend/tests/utils/privateApi.ts:7]).

## What we don't know

- `frontend/openapi-ts.config.ts`, which generates the `frontend/client` package this area's
  `utils/privateApi.ts` imports, was read for imports only, not for symbols, because the indexer's
  build doesn't include it; this analysis cannot say from the graph exactly which generated
  `PrivateService` methods exist beyond what `privateApi.ts` itself calls
  [cite: frontend/tests/utils/privateApi.ts:3-4].
- The code graph records 98 HTTP calls made across the frontend with 98 linked to a route, but does
  not attribute, call-by-call, which of this area's `page.goto`/UI actions resolve to which backend
  route; the exact request each Playwright action triggers is run-time browser behaviour, not
  something the static graph traces into this folder.
- Whether `MAILPIT_HOST`, `VITE_API_URL`, `FIRST_SUPERUSER` and `FIRST_SUPERUSER_PASSWORD` are set
  the same way in CI as locally is configuration read at start-up from `.env`/the environment
  [cite: frontend/tests/config.ts:8] [cite: frontend/tests/utils/mailpit.ts:20]
  [cite: frontend/tests/utils/privateApi.ts:7]; the graph does not read `.env` or CI secrets, so this
  is a question for whoever runs the gate's Playwright step, not something the code itself answers.
- Per the team, this repository has no live deployment and no real user data behind it; the
  "veterinary clinic" framing in the Project profile does not apply to what these tests exercise,
  which is the generic template's seed Users/Items only [cite: source:transcript-run-1416470e@r1#T3].
