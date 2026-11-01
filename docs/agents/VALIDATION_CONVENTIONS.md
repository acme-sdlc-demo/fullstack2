# Backend validation conventions

## `min_length` on API-boundary `str` fields must reject whitespace-only input

When a Pydantic/SQLModel `Field` declares `min_length` on a `str` that is read from a request (a
`UserCreate`/`UserUpdate`/`ItemCreate`-style schema used over the API boundary), `min_length` is
checked on the raw string *before* any trimming happens by default. A value made only of spaces
(e.g. `"   "`) satisfies `min_length` even though it carries no real content once trimmed.

Guard against this for every such field by doing one of:
- setting `str_strip_whitespace=True` in the model's `model_config`, or
- adding an explicit `field_validator(..., mode="before")` that strips the value before the
  length check runs.

### Pattern already in use in this codebase

`ItemBase.title` and `ItemUpdate.title` (`backend/app/models.py`) both declare
`Field(min_length=1, ...)` and pair it with a `strip_title` `field_validator(mode="before")` that
strips the incoming value first, so a title of only spaces is rejected rather than accepted as a
1-character title. Use this as the template for any new or changed `str` field that has
`min_length` and comes from a request body. [cite: backend/app/models.py]

See `docs/OPEN_QUESTIONS.md` for fields in the current codebase that declare `min_length` without
either guard.
