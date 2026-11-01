# Open questions

## User-facing text fields other than item title are not stripped

`docs/agents/CODEBASE_MAP.md` records the convention — introduced for `ItemBase.title` /
`ItemUpdate.title` — that a user-facing text field in `backend/app/models.py` should strip
whitespace before validation, so a value made only of spaces is rejected rather than stored.
[cite: docs/agents/CODEBASE_MAP.md]

The code does not yet apply this to every such field: `UserBase.full_name`
(and the matching `full_name` fields on `UserRegister`, `UserUpdate`, `UserUpdateMe`) have no
`field_validator` stripping whitespace, so a user can register or update with a `full_name` of
only spaces. [cite: backend/app/models.py]

Flagging this as a gap between the recorded convention and the current code; not changed here
because this knowledge update's scope is documentation, not a code fix.
