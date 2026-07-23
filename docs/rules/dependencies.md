# Dependency Rules (BD501-503)

Analyze import dependencies between step modules. These rules catch circular
imports, unused imports, and missing step modules — all without executing
any code.

---

## BD501 — circular-dependency

Detects circular import dependencies between step modules using depth-first
search (DFS) on the import graph. Circular imports cause `ImportError` at
runtime in Python — often intermittently, depending on import order.

| Attribute    | Value          |
| ------------ | -------------- |
| Severity     | error          |
| Category     | Dependency     |
| Configurable | No             |

### What it detects

```python
# features/steps/a.py
from features.steps.b import helper_b  # a imports b

# features/steps/b.py
from features.steps.a import helper_a  # b imports a — CIRCULAR!
```

### Example output

```text
BD501  ERROR  Circular dependency: a.py -> b.py -> a.py
```

### How to fix

- **Extract** the shared logic into a third module that both `a.py` and
  `b.py` import from.
- **Move** the import inside the function (lazy import) if the dependency
  is only needed at runtime.
- **Restructure** the modules to eliminate the cycle.

```python
# features/steps/common.py  -- new shared module
def shared_helper():
    ...

# features/steps/a.py
from features.steps.common import shared_helper  # no cycle

# features/steps/b.py
from features.steps.common import shared_helper  # no cycle
```

### Visualizing the cycle

Use the `graph` command to visualize the dependency graph:

```bash
behave-doctor graph . | dot -Tpng -o deps.png
```

The circular dependency will appear as a cycle in the graph.

---

## BD502 — unused-import

Detects imports in step modules that are never referenced in the file body.
Uses AST analysis — does not execute the module.

| Attribute    | Value          |
| ------------ | -------------- |
| Severity     | warning        |
| Category     | Dependency     |
| Configurable | No             |

### What it detects

```python
# features/steps/auth.py
import json          # never used in this file
from pathlib import Path  # never used in this file

@given("the user is logged in")
def step_impl(context):
    context.user = "test_user"
```

### Example output

```text
BD502  WARNING  Unused import "json" in auth.py
       (features/steps/auth.py:1)
BD502  WARNING  Unused import "Path" in auth.py
       (features/steps/auth.py:2)
```

### How to fix

Remove the unused import:

```python
# features/steps/auth.py
@given("the user is logged in")
def step_impl(context):
    context.user = "test_user"
```

### Notes

- behave-doctor uses AST analysis, so it detects imports that are unused
  even if they would be used at runtime via `eval` or dynamic access.
- Relative imports (`from . import helper`) and absolute imports
  (`from features.steps import helper`) are both analyzed.
- `__init__.py` re-exports are not flagged as unused.

---

## BD503 — missing-step-module

Detects when the steps directory is empty, missing, or contains no Python
files with step definitions. This usually indicates a misconfigured project
or a fresh checkout where step definitions haven't been written yet.

| Attribute    | Value          |
| ------------ | -------------- |
| Severity     | error          |
| Category     | Dependency     |
| Configurable | No             |

### What it detects

- The steps directory does not exist.
- The steps directory exists but contains no `.py` files.
- The steps directory contains `.py` files but none have step definitions
  (`@given`, `@when`, `@then` decorators).

### Example output

```text
BD503  ERROR  16 undefined step(s) and no step definitions found — the steps directory is empty or missing
```

### How to fix

- **Check** that `steps_dir` in your config points to the correct directory.
- **Create** step definitions for your feature steps.
- **Verify** that your step files use `@given`, `@when`, or `@then`
  decorators (not `@step` or other custom decorators).

```python
# features/steps/login.py
from behave import given, when, then

@given("the user is on the login page")
def step_impl(context):
    ...
```
