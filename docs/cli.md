# CLI Reference

## Synopsis

```
behave-doctor [--version] {scan,list-rules,explain,stats,graph} ...
```

When no subcommand is given, `scan` is implied. For example,
`behave-doctor .` is equivalent to `behave-doctor scan .`.

## Global options

| Option       | Description                |
| ------------ | -------------------------- |
| `--version`  | Show version and exit.     |
| `-h`, `--help` | Show help and exit.      |

## `scan`

Run all enabled rules and print a diagnostic report.

```
behave-doctor scan [PATH] [OPTIONS]
```

### Options

| Option             | Default  | Description                                      |
| ------------------ | -------- | ------------------------------------------------ |
| `PATH`             | `.`      | Project root directory.                          |
| `--features-dir`   | `features` | Relative path to features directory.           |
| `--steps-dir`      | `features/steps` | Relative path to step definitions.        |
| `--config`         | auto     | Path to `pyproject.toml` config file.            |
| `--format`         | `text`   | Output format: `text`, `json`, `sarif`.          |
| `-o`, `--output`   | stdout   | Write report to a file instead of stdout.        |
| `--rules`          | all      | Comma-separated rule IDs to run.                 |
| `--exclude-rules`  | none     | Comma-separated rule IDs to skip.                |
| `--severity`       | `hint`   | Minimum severity: `error`, `warning`, `info`, `hint`. |
| `--no-color`       | off      | Disable ANSI color codes (text only).            |
| `-q`, `--quiet`    | off      | Only show errors (text only).                    |
| `-v`, `--verbose`  | off      | Show suggestions and metadata (text only).       |

### Exit codes

| Code | Meaning                              |
| ---- | ------------------------------------ |
| 0    | No errors or warnings found.         |
| 1    | One or more errors/warnings found.   |
| 2    | Scan failed (missing features dir).  |

## `list-rules`

List all available diagnostic rules.

```bash
behave-doctor list-rules
```

## `explain`

Show details for a specific rule.

```bash
behave-doctor explain BD301
```

## `stats`

Print project statistics only (no diagnostics).

```bash
behave-doctor stats [PATH]
```

## `graph`

Output the module dependency graph in DOT format.

```bash
behave-doctor graph [PATH]
```

The output can be rendered with Graphviz:

```bash
behave-doctor graph . | dot -Tpng -o deps.png
```
