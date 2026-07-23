# Quality Rules (BD201-204)

Detect suite quality issues: duplicate definitions, missing tags, oversized
features, and inconsistent tag casing. These rules catch problems that lead
to runtime errors or make the suite hard to maintain.

---

## BD201 — duplicate-step-defs

Finds step definitions that share the same pattern (case-insensitive).
Duplicate definitions cause Behave to raise `AmbiguousStepError` at runtime.

| Attribute    | Value          |
| ------------ | -------------- |
| Severity     | error          |
| Category     | Quality        |
| Configurable | No             |

### What it detects

```python
# features/steps/auth.py
@given("the user is logged in")
def step_impl(context):
    ...

# features/steps/login.py  -- DUPLICATE!
@given("the user is logged in")
def step_impl(context):
    ...
```

### Example output

```text
BD201  ERROR  Duplicate step definition for pattern 'the user is logged in' in: features/steps/auth.py:10, features/steps/login.py:15
```

### How to fix

Remove the duplicate definition. If two modules need similar behavior,
extract the shared logic into a helper function and call it from a single
step definition.

---

## BD202 — scenario-no-tags

Finds scenarios with zero tags. Untagged scenarios cannot be selectively
run in CI and are easy to overlook when running tag-filtered suites.

| Attribute    | Value          |
| ------------ | -------------- |
| Severity     | warning        |
| Category     | Quality        |
| Configurable | No             |

### What it detects

```gherkin
# features/login.feature
Feature: Login

  Scenario: User logs in with valid credentials  # no tags!
    Given the user is on the login page
    When the user enters valid credentials
    Then the user should be redirected to the dashboard
```

### Example output

```text
BD202  WARNING  Scenario "User logs in with valid credentials" has no tags
        (features/login.feature:3)
```

### How to fix

Add at least one tag to each scenario. Common tagging conventions:

- `@smoke` — critical path scenarios run on every push.
- `@regression` — full regression suite.
- `@integration` — scenarios requiring external services.
- `@wip` — work in progress (excluded from CI).

```gherkin
@smoke
Scenario: User logs in with valid credentials
```

### When to disable

If your team intentionally doesn't use tags, disable this rule:

```toml
[tool.behave-doctor.rules.BD202]
enabled = false
```

---

## BD203 — feature-too-many-scenarios

Finds features with more than `max_scenarios` scenarios (default 20). Large
features are hard to maintain, slow to review, and often indicate that a
feature file should be split into smaller, focused files.

| Attribute    | Value                    |
| ------------ | ------------------------ |
| Severity     | warning                  |
| Category     | Quality                  |
| Configurable | `max_scenarios` (int)    |

### Configuration

```toml
[tool.behave-doctor.rules.BD203]
max_scenarios = 15  # default: 20
```

### Example output

```text
BD203  WARNING  Feature "Checkout" has 25 scenarios (max 20)
        (features/checkout.feature:1)
```

### How to fix

Split the feature file into smaller, cohesive files. For example, split
`checkout.feature` into:

- `checkout/guest_checkout.feature`
- `checkout/registered_checkout.feature`
- `checkout/payment_methods.feature`

---

## BD204 — inconsistent-tag-casing

Finds tags that appear with inconsistent casing or separator style across
the project. Tag filters in Behave are case-sensitive, so inconsistent
casing leads to missed scenarios.

| Attribute    | Value          |
| ------------ | -------------- |
| Severity     | warning        |
| Category     | Quality        |
| Configurable | No             |

### What it detects

Normalization strips `@`, underscores, and hyphens, then lowercases — so
`@SmokeTest`, `@smoke_test`, and `@smoke-test` are all considered the same
tag. If multiple variants exist, BD204 flags them.

```gherkin
# features/login.feature
@SmokeTest
Scenario: Login with valid credentials

# features/checkout.feature
@smoke_test  # inconsistent!
Scenario: Checkout as guest
```

### Example output

```text
BD204  WARNING  Inconsistent tag casing for 'smoketest': ['@SmokeTest', '@smoke_test']
```

### How to fix

Pick a single convention and apply it across the project. Common
conventions:

- `@smoke` — all lowercase, no separators.
- `@smoke_test` — snake_case.
- `@smoke-test` — kebab-case.

Use a project-wide tag convention document and enforce it in code review.
