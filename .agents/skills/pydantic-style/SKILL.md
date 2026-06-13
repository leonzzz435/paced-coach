---
name: pydantic-style
description: How to write proper dataclasses and Pydantic models (validation/serialization patterns). Use when defining BaseModel/dataclasses.
---

# Pydantic Models: Validation & Serialization Patterns

**Applies to:** Pydantic model definitions (BaseModel, dataclasses)

## Model Definition

**Rule:** Keep models pure data structures; no business logic or external dependencies.

```python
# YES (pure data with validation)
class MappingInput(BaseModel):
    column_name: str
    value: str
    
    @field_validator("column_name")
    @classmethod
    def validate_column_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Column name cannot be empty")
        return v.lower()
```

## Validation vs Parsing

**Rule:** Use `model_validate` (v2) for parsing, avoid `__init__`.

```python
# YES
data = {"column_name": "  Foo  ", "value": "bar"}
model = MappingInput.model_validate(data)
assert model.column_name == "foo"
```

## Field Configuration

**Rule:** Use `Field` for metadata, constraints, and alias choices.

```python
class User(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=100)
    # Using alias for external APIs
    external_id: str = Field(alias="user_id")
    
    model_config = ConfigDict(populate_by_name=True)
```

## Immutability

**Rule:** Prefer immutable models for domain objects (Value Objects).

```python
class Money(BaseModel):
    amount: Decimal
    currency: str
    
    model_config = ConfigDict(frozen=True)
```

## Serialization

**Rule:** Use `model_dump` (v2) with `mode` argument.

```python
# To standard dict
data = user.model_dump(mode="python")

# To JSON-compatible dict (dates -> str)
json_data = user.model_dump(mode="json")
```

## Nested Models

**Rule:** Decompose complex structures into smaller, reusable models.

```python
class Address(BaseModel):
    street: str
    city: str

class UserProfile(BaseModel):
    user: User
    address: Address
```

## Environment Variables (pydantic-settings)

**Rule:** Use `BaseSettings` for config.

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    db_url: str
    api_key: SecretStr
    
    model_config = SettingsConfigDict(env_file=".env")
```
