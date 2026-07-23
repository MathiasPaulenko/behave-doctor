# Structure Rules (BD101-104)

Informational metrics about the project. These rules never fail the build
(severity `info`) and exist to give you a quick overview of suite size.

They are useful for dashboards, trend tracking, and understanding the
overall shape of your Behave suite. If you find them noisy, you can disable
them individually or set `min_severity = "warning"` to suppress all `info`
diagnostics.

---

## BD101 — feature-count

Reports the total number of `.feature` files found under the features
directory.

| Attribute    | Value          |
| ------------ | -------------- |
| Severity     | info           |
| Category     | Structure      |
| Configurable | No             |

### Example output

```text
BD101  INFO  12 features found
```

### When this matters

- Tracking suite growth over time.
- Detecting sudden spikes in feature count (e.g. a large import).
- Establishing baselines for CI dashboards.

---

## BD102 — scenario-count

Reports the total number of scenarios across all features, including
Scenario Outlines (each example row counts as one scenario).

| Attribute    | Value          |
| ------------ | -------------- |
| Severity     | info           |
| Category     | Structure      |
| Configurable | No             |

### Example output

```text
BD102  INFO  47 scenarios found
```

### When this matters

- Estimating test execution time.
- Tracking suite growth.
- Comparing scenario count vs. step definition count (coverage ratio).

---

## BD103 — step-count

Reports the total number of steps across all scenarios (Given/When/Then
lines, including `And` and `But` continuations).

| Attribute    | Value          |
| ------------ | -------------- |
| Severity     | info           |
| Category     | Structure      |
| Configurable | No             |

### Example output

```text
BD103  INFO  213 steps found
```

### When this matters

- Estimating test execution time.
- Detecting scenarios with unusually high step counts (see BD401).
- Tracking the ratio of steps to step definitions (reuse rate).

---

## BD104 — tag-coverage

Reports the number of unique tags and total tag usages across all scenarios.

| Attribute    | Value          |
| ------------ | -------------- |
| Severity     | info           |
| Category     | Structure      |
| Configurable | No             |

### Example output

```text
BD104  INFO  8 unique tags, 34 total tag usages
```

### When this matters

- Understanding tag distribution.
- Identifying tags used only once (potential candidates for removal).
- Tracking tagging practices across the team.

### Related rules

- [BD204](quality.md#bd204-inconsistent-tag-casing) — inconsistent tag casing.
- [BD303](coverage.md#bd303-unused-tag) — unused tags.
- [BD304](coverage.md#bd304-orphan-scenario) — orphan scenarios (no tag
  filter selects them).
