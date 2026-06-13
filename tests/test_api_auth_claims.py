import uuid

import pytest
from fastapi import HTTPException, Request


class _AuthSettings:
    def __init__(self, *, auth_mode: str = "local", local_owner_user_id: str = ""):
        self.auth_mode = auth_mode
        self.local_owner_user_id = local_owner_user_id
        self.local_owner_email = "local-owner@paced.local"
        self.local_owner_key = "local-owner"
        self.allow_local_auth_public_access = False
        self.local_auth_context_is_safe = True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_local_auth_creates_owner_without_bearer_token(monkeypatch):
    from api import deps

    monkeypatch.setattr(deps, "settings", _AuthSettings(auth_mode="local"))

    class _ScalarResult:
        def scalar_one_or_none(self):
            return None

        def scalars(self):
            return self

        def all(self):
            return []

    class _Db:
        async def execute(self, _stmt):
            return _ScalarResult()

        def add(self, user):
            assert user.local_owner_key == "local-owner"
            assert user.email == "local-owner@paced.local"
            user.id = "local-user-id"

        async def flush(self):
            return None

    user_id = await deps.get_current_user(
        request=Request(scope={"type": "http", "headers": []}),
        db=_Db(),  # type: ignore[arg-type]
    )
    assert user_id == "local-user-id"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_local_auth_rejects_removed_hosted_auth_mode(monkeypatch):
    from api import deps

    monkeypatch.setattr(deps, "settings", _AuthSettings(auth_mode="hosted"))

    class _Db:
        async def execute(self, _stmt):
            raise AssertionError("invalid auth mode should fail before querying")

    with pytest.raises(HTTPException) as exc_info:
        await deps.get_current_user(
            request=Request(scope={"type": "http", "headers": []}),
            db=_Db(),  # type: ignore[arg-type]
        )

    assert exc_info.value.status_code == 500
    assert "AUTH_MODE" in str(exc_info.value.detail)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_local_auth_adopts_single_existing_training_owner_before_empty_local_owner(monkeypatch):
    from api import deps

    training_owner_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    empty_local_owner_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    monkeypatch.setattr(deps, "settings", _AuthSettings(auth_mode="local"))

    class _ScalarResult:
        def __init__(self, value=None, values=None):
            self._value = value
            self._values = values or []

        def scalar_one_or_none(self):
            return self._value

        def scalars(self):
            return self

        def all(self):
            return self._values

    class _User:
        id = empty_local_owner_id

    class _Db:
        async def execute(self, stmt):
            sql = str(stmt)
            if "FROM active_weekly_plans" in sql:
                return _ScalarResult(values=[training_owner_id])
            if "FROM users" in sql and "users.local_owner_key" in sql:
                return _ScalarResult(value=_User())
            return _ScalarResult()

        def add(self, _user):
            raise AssertionError("local auth should not create a new owner when training data exists")

    user_id = await deps.get_current_user(
        request=Request(scope={"type": "http", "headers": []}),
        db=_Db(),  # type: ignore[arg-type]
    )
    assert user_id == training_owner_id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_local_auth_uses_configured_existing_owner(monkeypatch):
    from api import deps

    owner_id = "11111111-1111-1111-1111-111111111111"
    monkeypatch.setattr(deps, "settings", _AuthSettings(auth_mode="local", local_owner_user_id=owner_id))

    class _User:
        id = owner_id

    class _ScalarResult:
        def scalar_one_or_none(self):
            return _User()

    class _Db:
        async def execute(self, _stmt):
            return _ScalarResult()

        def add(self, _user):
            raise AssertionError("configured owner should not create a new user")

    user_id = await deps.get_current_user(
        request=Request(scope={"type": "http", "headers": []}),
        db=_Db(),  # type: ignore[arg-type]
    )
    assert user_id == owner_id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_local_auth_invalid_configured_owner_fails_loudly(monkeypatch):
    from api import deps

    monkeypatch.setattr(deps, "settings", _AuthSettings(auth_mode="local", local_owner_user_id="not-a-uuid"))

    class _Db:
        async def execute(self, _stmt):
            raise AssertionError("invalid owner id should fail before querying")

    with pytest.raises(HTTPException) as exc_info:
        await deps.get_current_user(
            request=Request(scope={"type": "http", "headers": []}),
            db=_Db(),  # type: ignore[arg-type]
        )

    assert exc_info.value.status_code == 500
    assert "LOCAL_OWNER_USER_ID" in str(exc_info.value.detail)
