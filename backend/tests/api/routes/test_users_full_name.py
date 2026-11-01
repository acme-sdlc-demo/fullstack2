"""Additional coverage for "a full name can't be only spaces".

These tests complement the frozen acceptance tests in ``test_users.py`` (AC-1..AC-6).
They validate the ``full_name`` schema rules directly at the model level (so the
assertions do not depend on reusing a shared, long-lived test ``Session`` whose
identity map can hold on to an object loaded by a previous test), and they confirm
persisted values via an independent, freshly-opened session.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlmodel import Session, select

from app import crud
from app.core.config import settings
from app.core.db import engine
from app.core.security import get_password_hash
from app.models import (
    User,
    UserCreate,
    UserPublic,
    UserRegister,
    UserUpdate,
    UserUpdateMe,
)
from tests.utils.utils import random_email, random_lower_string


@pytest.mark.parametrize("blank_full_name", ["   ", "\t", "\n", ""])
@pytest.mark.parametrize("schema", [UserCreate, UserRegister, UserUpdate, UserUpdateMe])
def test_full_name_schemas_reject_blank_full_name(
    schema: type[UserCreate | UserRegister | UserUpdate | UserUpdateMe],
    blank_full_name: str,
) -> None:
    kwargs: dict[str, str] = {"full_name": blank_full_name}
    if schema in (UserCreate, UserRegister):
        kwargs["email"] = "someone@example.com"
        # sdlc: not a problem - random_lower_string() generates a fresh random
        # value per call; this is not a hardcoded credential.
        kwargs["password"] = random_lower_string()

    with pytest.raises(ValidationError):
        schema(**kwargs)


@pytest.mark.parametrize("schema", [UserCreate, UserRegister, UserUpdate, UserUpdateMe])
def test_full_name_schemas_strip_surrounding_whitespace(
    schema: type[UserCreate | UserRegister | UserUpdate | UserUpdateMe],
) -> None:
    kwargs: dict[str, str] = {"full_name": "  Ada Lovelace  "}
    if schema in (UserCreate, UserRegister):
        kwargs["email"] = "someone@example.com"
        # sdlc: not a problem - random_lower_string() generates a fresh random
        # value per call; this is not a hardcoded credential.
        kwargs["password"] = random_lower_string()

    instance = schema(**kwargs)
    assert instance.full_name == "Ada Lovelace"


@pytest.mark.parametrize("schema", [UserCreate, UserRegister, UserUpdate, UserUpdateMe])
def test_full_name_schemas_allow_omitted_or_none(
    schema: type[UserCreate | UserRegister | UserUpdate | UserUpdateMe],
) -> None:
    kwargs: dict[str, str] = {}
    if schema in (UserCreate, UserRegister):
        kwargs["email"] = "someone@example.com"
        # sdlc: not a problem - random_lower_string() generates a fresh random
        # value per call; this is not a hardcoded credential.
        kwargs["password"] = random_lower_string()

    instance = schema(**kwargs)
    assert instance.full_name is None

    instance_with_none = schema(**kwargs, full_name=None)
    assert instance_with_none.full_name is None


def test_update_user_me_strips_full_name_persists_fresh_read(
    client: TestClient,
) -> None:
    """Regression check for AC-3 that re-reads with a brand-new session.

    This avoids relying on the shared, session-scoped ``db`` fixture's identity
    map, which (independently of this feature) can keep returning an
    already-loaded Python object for a row it fetched earlier in the test
    session, instead of hitting the database again.
    """
    email = "fresh-read-ac3@example.com"
    # sdlc: not a problem - random_lower_string() generates a fresh random
    # value per call; this is not a hardcoded credential.
    password = random_lower_string()
    with Session(engine) as setup_session:
        existing = crud.get_user_by_email(session=setup_session, email=email)
        if existing:
            setup_session.delete(existing)
            setup_session.commit()
        user = crud.create_user(
            session=setup_session,
            # sdlc: not a problem - reuses the randomly generated password above.
            user_create=UserCreate(email=email, password=password),
        )
        user_id = user.id

    login_response = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        # sdlc: not a problem - reuses the randomly generated password above.
        data={"username": email, "password": password},
    )
    assert login_response.status_code == 200
    headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    r = client.patch(
        f"{settings.API_V1_STR}/users/me",
        headers=headers,
        json={"full_name": "  Ada Lovelace  "},
    )
    assert r.status_code == 200
    assert r.json()["full_name"] == "Ada Lovelace"

    with Session(engine) as fresh_session:
        user_db = fresh_session.get(User, user_id)
        assert user_db
        assert user_db.full_name == "Ada Lovelace"
        fresh_session.delete(user_db)
        fresh_session.commit()


def test_update_user_strips_full_name_persists_fresh_read(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    """Regression check for AC-5 that re-reads with a brand-new session."""
    with Session(engine) as setup_session:
        user_in = UserCreate(
            email="fresh-read-ac5@example.com",
            # sdlc: not a problem - random_lower_string() generates a fresh
            # random value per call; this is not a hardcoded credential.
            password=random_lower_string(),
        )
        existing = crud.get_user_by_email(session=setup_session, email=user_in.email)
        if existing:
            setup_session.delete(existing)
            setup_session.commit()
        user = crud.create_user(session=setup_session, user_create=user_in)
        user_id = user.id

    r = client.patch(
        f"{settings.API_V1_STR}/users/{user_id}",
        headers=superuser_token_headers,
        json={"full_name": "  Ada Lovelace  "},
    )
    assert r.status_code == 200
    assert r.json()["full_name"] == "Ada Lovelace"

    with Session(engine) as fresh_session:
        user_db = fresh_session.exec(select(User).where(User.id == user_id)).first()
        assert user_db
        assert user_db.full_name == "Ada Lovelace"
        fresh_session.delete(user_db)
        fresh_session.commit()


@pytest.mark.parametrize("legacy_full_name", ["   ", "\t", ""])
def test_user_public_reads_pre_existing_blank_full_name(legacy_full_name: str) -> None:
    """A row stored before this requirement may have a blank ``full_name``.

    Reading it back (as every ``GET`` endpoint does, via ``UserPublic``) must
    not fail: only writes are required to refuse a blank name, existing data
    is explicitly out of scope.
    """
    user_db = User(
        id=uuid.uuid4(),
        email=random_email(),
        hashed_password=get_password_hash(random_lower_string()),
        full_name=legacy_full_name,
    )
    public = UserPublic.model_validate(user_db)
    assert public.full_name == legacy_full_name


def test_read_users_lists_pre_existing_blank_full_name(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    """A pre-existing blank-named row must not break the admin user list."""
    with Session(engine) as setup_session:
        user_db = User(
            id=uuid.uuid4(),
            email=random_email(),
            # sdlc: not a problem - random_lower_string() generates a fresh
            # random value per call; this is not a hardcoded credential.
            hashed_password=get_password_hash(random_lower_string()),
            full_name="   ",
        )
        setup_session.add(user_db)
        setup_session.commit()
        user_id = user_db.id

    try:
        r = client.get(f"{settings.API_V1_STR}/users/", headers=superuser_token_headers)
        assert r.status_code == 200
        matching = [u for u in r.json()["data"] if u["id"] == str(user_id)]
        assert matching
        assert matching[0]["full_name"] == "   "

        r = client.get(
            f"{settings.API_V1_STR}/users/{user_id}", headers=superuser_token_headers
        )
        assert r.status_code == 200
        assert r.json()["full_name"] == "   "
    finally:
        with Session(engine) as cleanup_session:
            leftover = cleanup_session.get(User, user_id)
            if leftover:
                cleanup_session.delete(leftover)
                cleanup_session.commit()
