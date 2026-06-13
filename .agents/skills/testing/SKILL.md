---
name: testing
description: pytest patterns and focus for this repo (async, mocking LLM/HTTP, deterministic assertions). Use when creating/updating tests.
---

# Testing: pytest Patterns & Focus

**Applies to:** Test modules, fixtures, test strategies

## Test Business Logic, Not Frameworks

**Rule:** Only test YOUR logic, not Python/FastAPI/Pydantic behavior.

```python
# YES (tests business logic)
def test_workflow_rejects_invalid_service():
    with pytest.raises(ValidationError, match="Unknown service: invalid_service"):
        validate_service("invalid_service")

# NO (tests Pydantic)
def test_model_validates_int():
    with pytest.raises(ValidationError):
        MyModel(count="not-an-int")
```

## Async Testing

**Rule:** Use `pytest-asyncio` markers and `async` defs.

```python
@pytest.mark.asyncio
async def test_async_service():
    result = await my_service.run()
    assert result.success
```

## Mocking External Dependencies

**Rule:** Never hit real APIs in tests. Use `respx` for HTTP and `unittest.mock` for others.

### HTTP Mocking (respx)

```python
import respx

@respx.mock
async def test_provider_api_call():
    route = respx.get("https://api.example.test/activity").respond(json={"id": 123})
    
    await fetch_activity(123)
    
    assert route.called
```

### LLM Mocking

**Rule:** Mock the LLM response, not the entire LangChain chain (unless testing the chain orchestration).

```python
from unittest.mock import AsyncMock, patch

async def test_agent_reasoning():
    with patch("services.ai.llm.invoke", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = "Mocked reasoning"
        
        result = await run_agent("input")
        assert result == "Mocked reasoning"
```

## Fixtures (conftest.py)

**Rule:** Use fixtures for setup/teardown. Scope them appropriately (`function` vs `session`).

```python
# tests/conftest.py
@pytest.fixture
def sample_activity():
    return {"id": 1, "type": "running", "distance": 5000}

@pytest.fixture
async def async_client():
    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c
```

## Determinism

**Rule:** Freeze time for time-dependent tests.

```python
from time_machine import travel

@travel("2023-01-01 12:00:00", tick=False)
def test_time_sensitive_logic():
    assert datetime.now().year == 2023
```

## Factory Pattern for Data

**Rule:** Use factories (e.g., `polyfactory`) to generate test data, avoiding hardcoded dicts in tests.

```python
from polyfactory.factories.pydantic_factory import ModelFactory

class UserFactory(ModelFactory[User]):
    __model__ = User

def test_user_creation():
    user = UserFactory.build(email="test@example.com")
    assert user.email == "test@example.com"
```

## Database Testing

**Rule:** Run tests in a transaction that rolls back.

```python
@pytest.fixture
async def db_session():
    # ... setup session ...
    yield session
    await session.rollback()
```
