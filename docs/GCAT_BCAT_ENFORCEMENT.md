# GCAT/BCAT Enforcement Addendum

## Done means

This bundle changes GCAT/BCAT from an observational alignment layer into an action-boundary enforcement layer.

A governed action now resolves as:

```text
GCAT/BCAT projection
    ↓
ALLOW / DENY / FAIL_CLOSED
    ↓
execute SUT only if ALLOW
```

## Decision meanings

```text
ALLOW
  The projected transition is admissible.
  The wrapper delegates to ./stegverse action <action>.

DENY
  The projected transition is known to be inadmissible.
  The wrapper does not call the SUT.
  A denial receipt is emitted.

FAIL_CLOSED
  The transition cannot be safely projected or evaluated.
  The wrapper does not call the SUT.
  A fail-closed receipt is emitted.
```

## DENY vs FAIL_CLOSED

Both prevent execution, but they mean different things:

```text
DENY = known inadmissible transition
FAIL_CLOSED = admissibility cannot be established
```

So the system now has:

```text
DENY_EXECUTION as the effect
DENY or FAIL_CLOSED as the reason class
```

## Files

```text
scripts/admissibility.py
scripts/governed_action.py
scripts/governance_matrix.py
scripts/governance_random_sweep.py
configs/full.json
configs/governance_matrix.json
configs/governance_random_sweep.json
```

## Verification

Run:

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
matrix_report.json exists
sweep_report.json exists
matrix alignment = 1.0
sweep alignment = 1.0
```

If reconstruction still flags the two new status lines as unexplained variance, add these patterns to `scripts/reconstruct.py` known patterns:

```text
^Governance Matrix complete\. GCAT/BCAT enforced at action boundary\.
^Random Sweep complete\. GCAT/BCAT enforced at action boundary\.
^Alignment:
```
