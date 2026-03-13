# demo_suite_runner

A headless runner harness for validating `stegverse-demo-suite` as an external user.

## Purpose

This repository treats `stegverse-demo-suite` as the system under test and provides:

- fresh-environment resets
- headless command execution
- stdout/stderr capture
- structured run artifacts
- markdown and JSON reports

## Supported Modes

- `execution_governance`
- `mutation_governance`
- `full`

## Reset Modes

- `soft` — delete `.stegverse_runtime/` only
- `hard` — delete working copy and reclone repo

## Quick Start

```bash
python runner/main.py --mode execution_governance --reset hard
python runner/main.py --mode mutation_governance --reset hard
```

## Output

Each run creates a timestamped folder in `runs/` containing:

- `commands.log`
- `stdout.log`
- `stderr.log`
- `summary.json`
- `report.md`

A latest report copy is also written to `reports/`.
