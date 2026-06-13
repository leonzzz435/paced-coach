import pytest

from api import deps


class _FakeSession:
    def __init__(self):
        self.info: dict[str, object] = {}
        self.commit_calls = 0
        self.rollback_calls = 0

    async def commit(self):
        self.commit_calls += 1

    async def rollback(self):
        self.rollback_calls += 1


class _FakeSessionMaker:
    def __init__(self, session: _FakeSession):
        self._session = session

    def __call__(self):
        return self

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        _ = (exc_type, exc, tb)
        return False


@pytest.mark.asyncio
async def test_get_db_skips_auto_commit_when_flagged(monkeypatch):
    session = _FakeSession()
    monkeypatch.setattr(deps, "async_session_maker", _FakeSessionMaker(session))

    db_gen = deps.get_db()
    yielded = await anext(db_gen)
    assert id(yielded) == id(session)
    session.info[deps.DB_SKIP_AUTO_COMMIT_FLAG] = True

    with pytest.raises(StopAsyncIteration):
        await anext(db_gen)

    assert session.commit_calls == 0
    assert session.rollback_calls == 0


@pytest.mark.asyncio
async def test_get_db_auto_commits_by_default(monkeypatch):
    session = _FakeSession()
    monkeypatch.setattr(deps, "async_session_maker", _FakeSessionMaker(session))

    db_gen = deps.get_db()
    _ = await anext(db_gen)

    with pytest.raises(StopAsyncIteration):
        await anext(db_gen)

    assert session.commit_calls == 1
    assert session.rollback_calls == 0
