# Open questions

## Password fields declare `min_length` but don't strip whitespace

Raised by: the new validation convention itself, checked against the existing fields
[cite: docs/agents/VALIDATION_CONVENTIONS.md] [cite: backend/app/models.py].

The convention says any API-boundary `str` `Field` with `min_length` must also strip whitespace
first (`str_strip_whitespace=True` or a stripping `field_validator`), so a whitespace-only value
can't satisfy `min_length` [cite: docs/agents/VALIDATION_CONVENTIONS.md]. The password fields in
`backend/app/models.py` don't do this: `UserCreate.password`, `UserRegister.password`,
`UserUpdate.password`, `UpdatePassword.current_password`, `UpdatePassword.new_password`, and
`NewPassword.new_password` all declare `Field(min_length=8, max_length=128)` with no stripping
[cite: backend/app/models.py]. As written, a password made of 8 spaces passes `min_length`.

Applying the rule literally would mean stripping passwords too, but trimming a password is itself
debatable: a user may intend leading/trailing spaces as part of the password, and silently altering
it before hashing changes what the user can later log in with. **Who can answer:** the team/product
owner needs to decide whether the fix is to strip passwords like `title`/`full_name`, or instead to
reject (without altering) a whitespace-only or leading/trailing-whitespace password. Until decided,
this is a known gap against the written convention [cite: docs/agents/VALIDATION_CONVENTIONS.md].

## `private.py`'s `create_user()` accepts but never uses `PrivateUserCreate.is_verified`

Raised by: the code-graph analysis of the dev-only private route [cite: docs/agents/ANALYSIS.md].

The schema takes an `is_verified` field but the handler never reads it when building the `User` row
[cite: backend/app/api/routes/private.py]. **Who can answer:** whoever introduced this field needs
to say whether dropping it is intentional (field reserved for future use) or a bug — this route
backs the Playwright suite's test-user seeding (`frontend/tests/utils/privateApi.ts`)
[cite: docs/agents/CODEBASE_MAP.md], so a fix would need the e2e suite re-run.

## Should the profile be corrected?

Raised by: the team's own correction during interview [cite: source:transcript-run-1416470e@r1#T3],
contradicting the profile text itself [cite: profile:regulatory_context].

The team says the profile's "veterinary clinic" framing is stale, carried over from a different
pilot, and this repo should be documented as the generic FastAPI/React template instead
[cite: source:transcript-run-1416470e@r1#T3]. This write-up follows that instruction, but the
profile field itself has not been edited to match. **Who can answer:** whoever maintains this
Project's profile (likely the team member who set it up, "bob" in the transcript) should update or
remove the veterinary-clinic line so future Runs don't need to re-discover and re-correct it.

## Documents vs code

- **Profile "veterinary clinic" purpose vs. the actual repo**: the profile's
  `profile:regulatory_context` field describes this Project as "a pilot: a veterinary clinic web
  app" [cite: profile:regulatory_context], but the code contains only a generic `User`/`Item`
  template with no clinic-, animal-, or healthcare-specific field, route, or table anywhere in
  `backend/app/models.py` or `backend/app/api/routes/*.py` [cite: backend/app/models.py], and the
  team explicitly confirms this profile line is wrong for this repo, carried over from a different
  ("petclinic") pilot [cite: source:transcript-run-1416470e@r1#T3]. This write-up treats the
  profile line as stale/inapplicable per the team's instruction, not as a design fact.
- **Two deploy paths exist in the repo but the team says neither is used**: `compose.yml`
  (Postgres/Traefik/Adminer self-hosted stack) and `.github/workflows/deploy.yml` (push to FastAPI
  Cloud) are both present and functional-looking in the code [cite: compose.yml]
  [cite: .github/workflows/deploy.yml], but the team states this Project is not deployed anywhere
  and both files are just the template's unmodified defaults, kept as-is
  [cite: source:transcript-run-1416470e@r1#T3]. Not a contradiction once read with that context, but
  worth flagging so a future reader doesn't assume either path is live from the code alone.
- **`backend/app/api/deps.py:36` is valid Python, not a `SyntaxError`**: the line reads
  `except InvalidTokenError, ValidationError:`, which looks at a glance like Python 2 syntax, but
  `backend/pyproject.toml:5` pins `requires-python = ">=3.14,<4.0"` [cite: backend/pyproject.toml:5],
  and PEP 758 (landed in Python 3.14) allows catching several exception types in an `except` clause
  without wrapping them in a tuple, so the line is valid under that pin. The gate's own backend
  tests import `app.api.deps` (every route module depends on it) and pass — 88 passed on the
  default branch — confirming this import succeeds in practice, not just in theory
  [cite: backend/app/api/deps.py:36]. None found: there is no discrepancy here once the pin is read
  alongside the line; an earlier draft of this analysis mistakenly treated this as a live
  `SyntaxError` breaking every route's import and listed it as a separate open question (a Python
  version-pin mismatch against the code graph's recorded `python-stdlib` 3.11 usage) — that claim
  and that question are both withdrawn, and the risk is dropped from this write-up per the review
  that caught it [cite: backend/pyproject.toml:5] [cite: backend/app/api/deps.py:36].
</content>
