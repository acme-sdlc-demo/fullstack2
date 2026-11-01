# Open questions

## Password fields declare `min_length` but don't strip whitespace

The rule in `docs/agents/VALIDATION_CONVENTIONS.md` [cite: docs/agents/VALIDATION_CONVENTIONS.md]
says any API-boundary `str` `Field` with `min_length` must also strip whitespace first (via
`str_strip_whitespace=True` or a `field_validator`), so a whitespace-only value can't satisfy
`min_length`.

The password fields in `backend/app/models.py` do not do this: `UserCreate.password`,
`UserRegister.password`, `UserUpdate.password`, `UpdatePassword.current_password`,
`UpdatePassword.new_password`, and `NewPassword.new_password` all declare
`Field(min_length=8, max_length=128)` with no `str_strip_whitespace` and no stripping
`field_validator` [cite: backend/app/models.py]. As written, a password made of 8 spaces passes
`min_length` validation.

Applying the rule literally would mean stripping these too, but trimming a password is itself
debatable (a user may intend leading/trailing spaces as part of the password, and silently
altering it before hashing changes what the user can log in with). It's open whether the right
fix for passwords is to strip them like `title`, or instead to reject whitespace-only/leading-or-
trailing-whitespace passwords without altering the value (e.g. a validator that rejects rather
than strips). Until decided, these fields are a known gap against the new rule.
