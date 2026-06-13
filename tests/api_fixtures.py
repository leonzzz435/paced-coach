import os
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.fixture(scope="session")
def test_database_url() -> str | None:
    return os.getenv("TEST_DATABASE_URL")


@pytest.fixture
async def db_session(test_database_url: str | None) -> AsyncGenerator[AsyncSession]:
    if not test_database_url:
        pytest.skip("Set TEST_DATABASE_URL to run API integration tests")
    engine = create_async_engine(test_database_url, echo=False)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session
        await session.rollback()
    await engine.dispose()

