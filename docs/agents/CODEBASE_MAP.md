# Code map

This page summarizes conventions in the codebase that are not obvious from the build files alone. It is maintained by Knowledge Runs; until a full Knowledge Run populates it, read the build files and the folders your change touches before changing them (see `CLAUDE.md`).

## backend/app/models.py — text field normalisation

SQLModel schema classes that accept user-facing text must strip leading/trailing whitespace from
that text *before* it is persisted or validated against length constraints, so that a title made
only of spaces is rejected rather than stored as whitespace.

- `ItemBase.title` and `ItemUpdate.title` each have a `field_validator("title", mode="before")`
  that strips the incoming string (returning it unchanged if it isn't a `str`), run before the
  `min_length=1` constraint is checked. [cite: backend/app/models.py]
- Tests for this behaviour live in `backend/tests/api/routes/test_items.py`
  (`test_create_item_whitespace_only_title_rejected`,
  `test_create_item_strips_surrounding_whitespace_from_title`,
  `test_update_item_whitespace_only_title_rejected`,
  `test_update_item_strips_surrounding_whitespace_from_title`). [cite: backend/tests/api/routes/test_items.py]
- Convention for this file going forward: any new or changed SQLModel text field in
  `backend/app/models.py` that is user-facing (titles, names, free-text labels, etc.) should get
  the same "strip before validation" `field_validator`, and a test asserting that a
  whitespace-only value is rejected and that surrounding whitespace is stripped. This keeps
  `min_length` constraints meaningful and keeps stored values free of incidental padding.
  [cite: backend/app/models.py]

### Open point

`UserBase.full_name` and `UserRegister.full_name`/`UserUpdate.full_name`/`UserUpdateMe.full_name`
do not currently have an equivalent strip validator, so a user's full name can still be saved as
whitespace-only. See `docs/OPEN_QUESTIONS.md` for this gap.
