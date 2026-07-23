# Coverage Rules (BD301-304)

Detect unused step definitions, undefined feature steps, unused tags, and
orphan scenarios. These rules ensure that every step in your feature files
has a matching implementation and every step definition is actually used.

---

## BD301 — unused-step-def

Finds step definitions that are never matched by any feature step. Unused
definitions are dead code — they add noise, increase maintenance burden, and
can mislead developers into thinking a step is tested when it isn't.

| Attribute    | Value          |
| ------------ | -------------- |
| Severity     | warning        |
| Category     | Coverage       |
| Configurable | No             |

### What it detects

```python
# features/steps/auth.py
@given("the user clicks submit")  # never used in any .feature file
def step_impl(context):
    ...
```

### Example output

```text
BD301  WARNING  Unused step definition: "the user clicks submit"
       (features/steps/auth.py:42)
```

### How to fix

- **Remove** the step definition if it's truly dead code.
- **Add** a feature step that exercises it if it was supposed to be tested.

### Metadata

| Key       | Value                              |
| --------- | ---------------------------------- |
| `pattern` | The step pattern string.           |
| `matcher` | The matcher type (`parse`, `re`, etc.). |

---

## BD302 — undefined-step

Finds feature steps with no matching step definition. These steps will
raise `UndefinedStepError` when Behave runs them — the test will fail or be
skipped silently.

| Attribute    | Value          |
| ------------ | -------------- |
| Severity     | error          |
| Category     | Coverage       |
| Configurable | No             |

### What it detects

```gherkin
# features/login.feature
Scenario: Login
  Given the database is seeded  # no @given("the database is seeded") exists
```

### Example output

```text
BD302  ERROR  Undefined step: "Given the database is seeded"
      (features/login.feature:18)
```

### How to fix

Create a step definition that matches the pattern:

```python
# features/steps/database.py
@given("the database is seeded")
def step_impl(context):
    ...
```

Or fix the step text in the feature file to match an existing definition.

### Metadata

| Key       | Value                              |
| --------- | ---------------------------------- |
| `pattern` | The step text as it appears in the feature file. |
| `keyword` | The step keyword (`Given`, `When`, `Then`). |

---

## BD303 — unused-tag

Finds tags that appear only once in the entire project. Tags used only once
cannot serve as reusable CI filters — they're effectively just labels on a
single scenario.

Tags listed in `exclude_tags` are skipped.

| Attribute    | Value                  |
| ------------ | ---------------------- |
| Severity     | info                   |
| Category     | Coverage               |
| Configurable | `exclude_tags` (list)  |

### Configuration

```toml
[tool.behave-doctor]
exclude_tags = ["@smoke", "@wip", "@manual"]
```

Tags in `exclude_tags` are considered "intentionally unused" and will not
be flagged by BD303.

### Example output

```text
BD303  INFO  Tag "@flaky" is used only once
      (features/checkout.feature:5)
```

### How to fix

- **Remove** the tag if it's not needed.
- **Apply** the tag to other scenarios if it represents a real category.
- **Add** the tag to `exclude_tags` if it's intentionally unique.

---

## BD304 — orphan-scenario

Finds scenarios whose tags are all unique to that scenario (each tag
appears on only one scenario). Such scenarios are effectively untagged for
filtering purposes — no tag filter will select them along with other
scenarios.

Scenarios with no tags are skipped (see [BD202](quality.md#bd202-scenario-no-tags)
for that).

| Attribute    | Value          |
| ------------ | -------------- |
| Severity     | warning        |
| Category     | Coverage       |
| Configurable | No             |

### What it detects

```gherkin
# This scenario has tags, but each tag appears on only this one scenario
@checkout @guest
Scenario: Guest checkout
  ...
```

If `@checkout` and `@guest` don't appear on any other scenario, running
`behave --tags @checkout` will only select this one scenario — defeating
the purpose of tagging.

### Example output

```text
BD304  WARNING  Scenario "Guest checkout" has only unique tags — no tag
        filter will group it with other scenarios
        (features/checkout.feature:5)
```

### How to fix

- **Share tags** across scenarios — use `@checkout` on all checkout-related
  scenarios so `--tags @checkout` selects them as a group.
- **Remove unique tags** if they don't serve a filtering purpose.
- **Accept** the orphan status if the scenario genuinely needs a unique tag
  (e.g. `@manual` for scenarios that can only be run manually).
