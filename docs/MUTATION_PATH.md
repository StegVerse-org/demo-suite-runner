# Governed Mutation Path Installation Notes

## Purpose

This closes the mutation bypass.

Before:

```text
./stegverse mutate deploy
```

could execute independently of the GCAT/BCAT commit gate.

After:

```text
python3 ../../scripts/governed_mutation.py deploy
```

becomes the mutation path.

## Files

Copy these files into `StegVerse-org/demo-suite-runner`:

```text
scripts/governed_mutation.py
configs/full.json
configs/mutation_governance.json
```

## What changed

The full pipeline now calls:

```text
python3 ../../scripts/governed_mutation.py deploy
```

instead of:

```text
./stegverse mutate deploy
```

## Decision behavior

```text
ALLOW
  GCAT/BCAT says the projected mutation transition is admissible.
  The wrapper delegates to ./stegverse mutate deploy.

DENY
  GCAT/BCAT says the projected mutation transition is inadmissible.
  The wrapper does not call ./stegverse mutate deploy.
  A mutation denial receipt is emitted.

FAIL_CLOSED
  No valid projection exists.
  The wrapper does not call ./stegverse mutate deploy.
  A fail-closed mutation receipt is emitted.
```

## Current expected result

Because `deploy` maps to `deploy_change`, and `deploy_change` is currently projected as inadmissible:

```text
python3 ../../scripts/governed_mutation.py deploy
```

should emit:

```text
Mutation denied: deploy
decision: DENY
```

## Verification

Run the full workflow:

```text
mode: full
reset: hard
seed: 42
samples: 50
reconstruct: true
```

Expected:

```text
full run PASS
governed_action.py deploy_change returns DENY
governed_mutation.py deploy returns DENY
matrix alignment = 1.0
sweep alignment = 1.0
```

## Important

This does not modify the SUT repository.

It seals the mutation path at the runner layer by preventing the demo runner from calling the raw mutation command directly.
