import uuid
from datetime import UTC, datetime

from pydantic import EmailStr, field_validator
from sqlmodel import Field, Relationship, SQLModel


def get_datetime_utc() -> datetime:
    return datetime.now(UTC)


def strip_full_name(value: str | None) -> str | None:
    if isinstance(value, str):
        return value.strip()
    return value


def strip_optional_full_name(value: str | None) -> str | None:
    """Like ``strip_full_name``, but an empty string means "not given".

    Some clients (the admin add/edit user forms) submit an empty string for
    an optional ``full_name`` left blank, rather than omitting the field.
    Treat that the same as the field being absent (``None``), while a name
    of only whitespace (at least one space, tab or newline) still strips to
    an empty string and so still fails the ``min_length=1`` check below,
    and is refused with 422.
    """
    if value == "":
        return None
    return strip_full_name(value)


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, min_length=1, max_length=255)

    @field_validator("full_name", mode="before")
    @classmethod
    def strip_full_name_before_validation(cls, value: str | None) -> str | None:
        return strip_optional_full_name(value)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, min_length=1, max_length=255)

    @field_validator("full_name", mode="before")
    @classmethod
    def strip_full_name_before_validation(cls, value: str | None) -> str | None:
        return strip_full_name(value)


# Properties to receive via API on update, all are optional
class UserUpdate(SQLModel):
    email: EmailStr | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    is_superuser: bool | None = None
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)

    @field_validator("full_name", mode="before")
    @classmethod
    def strip_full_name_before_validation(cls, value: str | None) -> str | None:
        return strip_optional_full_name(value)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)

    @field_validator("full_name", mode="before")
    @classmethod
    def strip_full_name_before_validation(cls, value: str | None) -> str | None:
        return strip_optional_full_name(value)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    # Always reload a User's columns from the database instead of trusting
    # a copy already cached in a session's identity map: a full_name (or
    # other field) changed through a different session/request must be
    # visible the next time this session loads the same user, not a value
    # from before that change.
    __mapper_args__ = {"always_refresh": True}

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime | None = Field(default_factory=get_datetime_utc)
    items: list[Item] = Relationship(back_populates="owner", cascade_delete=True)


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID
    created_at: datetime | None = None


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# Shared properties
class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)

    @field_validator("title", mode="before")
    @classmethod
    def strip_title(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip()
        return value


# Properties to receive on item creation
class ItemCreate(ItemBase):
    pass


# Properties to receive on item update
class ItemUpdate(SQLModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)

    @field_validator("title", mode="before")
    @classmethod
    def strip_title(cls, value: str | None) -> str | None:
        if isinstance(value, str):
            return value.strip()
        return value


# Database model, database table inferred from class name
class Item(ItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(default_factory=get_datetime_utc)
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="items")


# Properties to return via API, id is always required
class ItemPublic(ItemBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime | None = None


class ItemsPublic(SQLModel):
    data: list[ItemPublic]
    count: int


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)
