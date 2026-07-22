# Coverage Rules (BD301-304)

Detect unused step definitions, undefined feature steps, unused tags, and
orphan scenarios.

## BD301 — unused-step-def

Finds step definitions that are never matched by any feature step. Unused
definitions are dead code — they add noise and maintenance burden.

| Attribute   | Value          |
| ----------- | -------------- |
| Severity    | warning        |
| Category    | Coverage       |
| Configurable| No             |

## BD302 — undefined-step

Finds feature steps with no matching step definition. These steps will
raise `UndefinedStepError` when Behave runs them.

| Attribute   | Value          |
| ----------- | -------------- |
| Severity    | error          |
| Category    | Coverage       |
| Configurable| No             |

## BD303 — unused-tag

Finds tags that appear only once in the entire project. Tags used only
once cannot serve as reusable CI filters.

Tags listed in `exclude_tags` are skipped.

| Attribute   | Value                |
| ----------- | -------------------- |
| Severity    | info                 |
| Category    | Coverage             |
| Configurable| `exclude_tags` (list)|

```toml
[tool.behave-doctor]
exclude_tags = ["@smoke", "@wip"]
```

## BD304 — orphan-scenario

Finds scenarios whose tags are all unique to that scenario (each tag appears
on only one scenario). Such scenarios are effectively untagged for filtering
purposes — no tag filter will select them along with other scenarios.

Scenarios with no tags are skipped (see BD202 for that).

| Attribute   | Value          |
| ----------- | -------------- |
| Severity    | warning        |
| Category    | Coverage       |
| Configurable| No             |
