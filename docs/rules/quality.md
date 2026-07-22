# Quality Rules (BD201-204)

Detect suite quality issues: duplicate definitions, missing tags, oversized
features, and inconsistent tag casing.

## BD201 — duplicate-step-defs

Finds step definitions that share the same pattern (case-insensitive).
Duplicate definitions cause Behave to raise `AmbiguousStepError` at runtime.

| Attribute   | Value                              |
| ----------- | ---------------------------------- |
| Severity    | error                              |
| Category    | Quality                            |
| Configurable| No                                 |

## BD202 — scenario-no-tags

Finds scenarios with zero tags. Untagged scenarios cannot be selectively
run in CI and are easy to overlook.

| Attribute   | Value          |
| ----------- | -------------- |
| Severity    | warning        |
| Category    | Quality        |
| Configurable| No             |

## BD203 — feature-too-many-scenarios

Finds features with more than `max_scenarios` scenarios (default 20).
Large features are hard to maintain and slow to review.

| Attribute   | Value                    |
| ----------- | ------------------------ |
| Severity    | warning                  |
| Category    | Quality                  |
| Configurable| `max_scenarios` (int)    |

```toml
[tool.behave-doctor.rules.BD203]
max_scenarios = 15
```

## BD204 — inconsistent-tag-casing

Finds tags that appear with inconsistent casing or separator style across
the project (e.g. `@SmokeTest` vs `@smoke_test`). Tag filters in Behave are
case-sensitive, so inconsistent casing leads to missed scenarios.

Normalization strips `@`, underscores, and hyphens, then lowercases — so
`@SmokeTest`, `@smoke_test`, and `@smoke-test` are all considered the same
tag.

| Attribute   | Value          |
| ----------- | -------------- |
| Severity    | warning        |
| Category    | Quality        |
| Configurable| No             |
