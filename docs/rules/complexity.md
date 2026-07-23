# Complexity Rules (BD401-403)

Enforce size and complexity limits on scenarios, step definitions, and
feature files. These rules help keep your Behave suite readable,
maintainable, and fast to review.

All complexity rules are configurable — you can adjust the thresholds to
match your team's standards.

---

## BD401 — scenario-too-many-steps

Finds scenarios with more than `max_steps` steps (default 10). Long
scenarios are hard to read, slow to debug, and often violate the
"one behavior per scenario" principle.

| Attribute    | Value              |
| ------------ | ------------------ |
| Severity     | warning            |
| Category     | Complexity         |
| Configurable | `max_steps` (int)  |

### Configuration

```toml
[tool.behave-doctor.rules.BD401]
max_steps = 8  # default: 10
```

### What it detects

```gherkin
Scenario: Complete checkout  # 12 steps — exceeds the default limit of 10
  Given the user is logged in
  And the cart has items
  When the user goes to checkout
  And enters shipping address
  And selects shipping method
  And enters payment details
  And confirms the order
  Then the order should be created
  And the user should see the confirmation
  And the inventory should be updated
  And the payment should be processed
  And the email should be sent
```

### Example output

```text
BD401  WARNING  Scenario "Complete checkout" has 12 steps (max 10)
        (features/checkout.feature:8)
```

### How to fix

Split the scenario into smaller, focused scenarios that each test one
behavior:

```gherkin
Scenario: User completes checkout
  Given the user is logged in with items in cart
  When the user completes the checkout process
  Then the order should be confirmed

Scenario: Inventory is updated after checkout
  Given an order is completed
  Then the inventory should reflect the change
```

---

## BD402 — step-too-many-params

Finds step definitions whose pattern has more than `max_params` parameters
(default 5). Step patterns with many parameters are fragile, hard to read,
and produce confusing error messages when they fail to match.

| Attribute    | Value                |
| ------------ | -------------------- |
| Severity     | warning              |
| Category     | Complexity           |
| Configurable | `max_params` (int)   |

### Configuration

```toml
[tool.behave-doctor.rules.BD402]
max_params = 3  # default: 5
```

### What it detects

```python
# 6 parameters — exceeds the default limit of 5
@when('the user fills the form with "{name}", "{email}", "{phone}", "{address}", "{city}", "{zip}"')
def step_impl(context, name, email, phone, address, city, zip):
    ...
```

### Example output

```text
BD402  WARNING  Step pattern has 6 parameters (max 5)
        (features/steps/forms.py:15)
```

### How to fix

- **Split** the step into multiple smaller steps.
- **Use** a table or doc string for complex data instead of inline
  parameters.
- **Extract** data into a helper function called from a simpler step.

```gherkin
# Instead of one step with 6 params:
When the user fills the form with "John", "john@example.com", ...

# Use a data table:
When the user fills the form with
  | name    | John             |
  | email   | john@example.com |
  | phone   | 555-1234         |
  | address | 123 Main St      |
  | city    | Springfield      |
  | zip     | 12345            |
```

---

## BD403 — feature-too-large

Finds feature files with more than `max_lines` lines (default 300). Large
feature files are hard to navigate, slow to review, and often indicate that
multiple unrelated features are crammed into a single file.

| Attribute    | Value              |
| ------------ | ------------------ |
| Severity     | warning            |
| Category     | Complexity         |
| Configurable | `max_lines` (int)  |

### Configuration

```toml
[tool.behave-doctor.rules.BD403]
max_lines = 200  # default: 300
```

### Example output

```text
BD403  WARNING  Feature file has 342 lines (max 300)
        (features/checkout.feature)
```

### How to fix

Split the feature file into smaller, cohesive files organized by domain:

```
features/
  checkout/
    guest_checkout.feature
    registered_checkout.feature
    payment_methods.feature
    shipping.feature
```

Each file should focus on a single aspect of the feature, making it easier
to find, review, and maintain.
