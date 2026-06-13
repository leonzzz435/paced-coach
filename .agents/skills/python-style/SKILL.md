---
name: python-style
description: General Python engineering conventions for this repo (ruff, typing, imports, async, etc.). Apply when editing or reviewing Python modules.
---

# Python Style: General Engineering Conventions

**Applies to:** All Python modules  
**Precedence:** Repository signals > these conventions  
**Tooling:** Ruff (linter + formatter)

## Type Hints (Python 3.12+)

**Use modern syntax:**
```python
# YES
def process(items: list[str]) -> dict[str, int]:
    ...

def fetch_user(id: str) -> User | None:
    ...

# NO (old syntax)
from typing import List, Dict, Optional

def process(items: List[str]) -> Dict[str, int]:
    ...

def fetch_user(id: str) -> Optional[User]:
    ...
````

**Omit `-> None` for procedures:**

```python
# YES
def log_event(message: str):
    logger.info(message)

# NO
def log_event(message: str) -> None:
    logger.info(message)
```

## Variable Clarity (No Single Letters)

**Exceptions:** Standard math (`x` in lambda), loop indices (`i`, `j`)

```python
# YES
for service_name, config in service_configs.items():
    handler = create_handler(config)

# NO
for s, c in service_configs.items():
    h = create_handler(c)
```

## Dependency Minimization

**Rule:** Import only essential dependencies; avoid heavy libraries for trivial operations.

```python
# YES (pandas native)
df["normalized"] = pd.Series(default_value, index=df.index)

# NO (unnecessary numpy import)
import numpy as np
df["normalized"] = np.full(len(df), default_value)
```

**Consider native alternatives:**

* `pandas` methods over `numpy` for DataFrame operations
* Built-in `dict`/`list` over `pandas.DataFrame` for small lookups
* `str` methods over regex for simple string ops

## Type Inference (Avoid Over-Specification)

**Rule:** Don't explicitly specify generic types when they can be inferred.

```python
# YES (inferred from arguments)
config = ConfigSpec(
    name="example",
    processor=my_processor,
    model_class=MyDataType,
)

# NO (redundant explicit type)
config = ConfigSpec[MyDataType](
    name="example",
    processor=my_processor,
    model_class=MyDataType,
)
```

## Imports at Module Level (Strengthen)

**Rule:** NEVER import inside constructors or methods (except circular dependencies).

```python
# YES (module level)
from shared.utils import helper_function

class MyClass:
    def __init__(self):
        self.helper = helper_function

# NO (constructor import)
class MyClass:
    def __init__(self):
        from shared.utils import helper_function  # ❌ VIOLATION
        self.helper = helper_function
```

**Exception:** Circular dependencies that cannot be resolved via refactoring.

## Eliminate Intermediate Variables

**Rule:** If used only once, inline it.

```python
# YES
return perform_operation(get_repository())

# NO
repository = get_repository()
result = perform_operation(repository)
return result
```

**Exception:** Improves readability or represents meaningful domain concept.

```python
# ACCEPTABLE (domain clarity)
llm_response = await agent.ainvoke(prompt)
parsed_value = extract_value(llm_response)
validated = validate_against_catalog(parsed_value)
return validated
```

## Return Data Structures Directly

**Rule:** Return what callers need; avoid forcing conversions.

```python
# YES - Callers need dict
def load_services() -> dict[str, Service]:
    return {s.name: s for s in _load_all_services()}

# NO - Callers must convert
def load_services() -> list[Service]:
    return _load_all_services()

# Caller forced to do:
services_dict = {s.name: s for s in load_services()}
```

## Async Patterns

**Rule:** All I/O-bound operations use `async`/`await`.

```python
# YES
async def map_value(input: MappingInput) -> MappingResult:
    workflow = get_workflow("v1")
    return await workflow.ainvoke(input)

# NO (blocks event loop)
def map_value(input: MappingInput) -> MappingResult:
    workflow = get_workflow("v1")
    return workflow.invoke(input)
```

## Repo hygiene (public vs private)

**Rule:** Do not add or modify code paths that would require committing secrets or environment-specific files.

Practical guidance:
* Prefer `os.environ[...]` / runtime env injection over checked-in `.env` files.
* If you introduce a new env var, update an example template (e.g. `web/app/.env.example`) instead of adding real values to git.
* Be extra cautious with “quick fixes” in web/API/worker that could accidentally leak operational details into the public core repo.

## String Literals

**Rule:** Double quotes only (consistency with Ruff defaults).

```python
# YES
message = "Processing FAV mapping"
service_name = "vehicle_access"

# NO
message = 'Processing FAV mapping'
```

## Import Organization

**Order:** Standard library → Third-party → Project modules

```python
# YES
import logging
from pathlib import Path

from fastapi import HTTPException
from pydantic import BaseModel

from shared.models import MappingInput
from shared.config import get_settings

# NO (mixed ordering)
from fastapi import HTTPException
import logging
from shared.models import MappingInput
```

**Use specific imports:**

```python
# YES
from shared.exceptions import ValidationError

# NO (pollutes namespace)
from shared.exceptions import *
```

## Line Length

**Maximum:** 120 characters (enforced by Ruff)

**Break within parentheses for chains:**

```python
# YES
result = (
    workflow
    .filter_services(input.column_name)
    .match_value(input.value)
    .rank_results()
)

# NO (exceeds 120)
result = workflow.filter_services(input.column_name).match_value(input.value).rank_results()
```

## Comprehensions Over Loops

**Rule:** Use comprehensions for data structure creation.

```python
# YES
service_names = [s.name for s in services if s.is_active]
config_map = {s.name: s.config for s in services}

# NO
service_names = []
for s in services:
    if s.is_active:
        service_names.append(s.name)
```

## Dict-Based String Building (Optional Fields)

**Rule:** When building strings with many optional fields, use dict to handle None cleanly.

```python
# YES (maintainable)
attrs = {"Name": obj.name}
if obj.field1:
    attrs["Field1"] = obj.field1
if obj.field2:
    attrs["Field2"] = obj.field2
return "\n".join(f"{k}: {v}" for k, v in attrs.items())

# NO (repetitive string concat)
parts = [f"Name: {obj.name}"]
if obj.field1:
    parts.append(f"Field1: {obj.field1}")
if obj.field2:
    parts.append(f"Field2: {obj.field2}")
return "\n".join(parts)
```

**Use when:** 3+ optional fields with consistent formatting.

## Delete Unused Code Immediately

**Rule:** If not referenced, delete it.

* Unused imports → Remove
* Unused functions → Delete
* Unused class fields → Delete
* Commented-out code → Delete (use git history)

## Documentation Discipline (ZERO TOLERANCE)

**Rule:** No docstrings or inline comments unless they add **exceptional** value beyond what code expresses.

```python
# YES (self-documenting code)
def normalize_equipment_type(raw_value: str) -> str:
    return raw_value.upper().replace("'", "").replace("FT", "")

# NO (redundant docstring)
def normalize_equipment_type(raw_value: str) -> str:
    """Normalizes equipment type by uppercasing and removing quotes."""
    return raw_value.upper().replace("'", "").replace("FT", "")

# NO (obvious comment)
def process_mapping(input: MappingInput) -> MappingResult:
    # Get the workflow
    workflow = get_workflow("v1")
    # Invoke the workflow  <-- Captain Obvious
    return await workflow.ainvoke(input)
```

**Exceptions (rare):**

* Complex algorithm that isn't obvious (e.g., custom FAV matching score)
* External API contract that code can't express (e.g., "Azure expects format X")
* TODO with issue number: `# TODO(#123): Refactor when v2 catalog available`

**Not exceptions:**

* Describing what a function does (name should be clear)
* Explaining Python syntax (team knows Python)
* Narrating the code flow (structure should be obvious)

## Refactoring Threshold

**Rule:** Methods >50 lines doing multiple things → Extract helpers.

```python
# YES (focused methods)
async def process_sample(self, sample: Sample) -> Result:
    if sample.type == "categorical":
        return await self._process_categorical(sample)
    elif sample.type == "range":
        return await self._process_range(sample)

# NO (long monolithic method)
async def process_sample(self, sample: Sample) -> Result:
    if sample.type == "categorical":
        # 30 lines of categorical logic
        ...
    elif sample.type == "range":
        # 30 lines of range logic
        ...
```

## Exception Handling

**Rule:** Catch specific exceptions only.

```python
# YES
try:
    result = await llm.ainvoke(prompt)
except ValidationError as e:
    logger.error("Invalid prompt: %s", e)
    raise
except TimeoutError as e:
    logger.error("LLM timeout: %s", e)
    raise ServiceUnavailable()

# NO (too broad)
try:
    result = await llm.ainvoke(prompt)
except Exception as e:
    logger.error("Something went wrong: %s", e)
```

## Verification

If `{LINTER}` resolved (ruff):

```bash
ruff check {file}
ruff format --check {file}
```

If unresolved, note: `[SKIP] Linting unavailable - manual review required`
