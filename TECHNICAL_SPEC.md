# Technical Specification

> For engineers, control systems thinkers, security auditors, and anyone who needs to inspect the machinery.


---

## System Architecture

```
SDK (external entry)
    |
    v
demo-suite-runner (this repo) -- validates from outside
    |
    +-- runner/main.py          orchestration engine
    +-- configs/*.json          command sequences per mode
    +-- scripts/                test implementations
    |       governance_matrix.py      deterministic ALLOW/DENY/FAIL_CLOSED
    |       governance_random_sweep.py  seeded weighted input sweep
    |       reconstruct.py            confidence analysis + timeline
    |       replay.py                 determinism verification
    +-- runs/                   per-run artifacts (timestamped)
    +-- reports/                latest summarized outputs
    |
    v
stegverse-demo-suite (system under test)
    |
    v
artifacts: stdout, stderr, receipts, state transitions
```

---

## Confidence Score: Technical Specification

### What It Measures (Weighted Axes)

| Axis | Weight | Verification Target |
|------|--------|---------------------|
| State continuity | 25% | State transitions form valid chain (state0 -> state1 -> ... -> state4) |
| Receipt integrity | 20% | Receipt IDs are unique and properly formatted (16-char hex) |
| Artifact consistency | 15% | Governed artifacts unlock in sequence matching state progression |
| Output completeness | 15% | Every command has captured stdout/stderr in logs |
| Command fidelity | 10% | Recorded command sequence matches executed sequence |
| Unexplained variance | 15% | No output patterns exist outside the known model |

### What It Explicitly Does NOT Measure

These are listed as **unchecked constraints** in every reconstruction report:

- Internal SUT logic correctness (not observable from outputs)
- Side effects outside captured stdout/stderr
- Cryptographic validity of receipt hashes (format validation only)
- Temporal ordering precision beyond second-level granularity
- Environmental determinism (OS, Python version, filesystem state)
- Intent behind any decision (only observable behavior is measured)

### Why These Weights

The weights reflect **observability**, not importance. State continuity and receipt integrity are heavily weighted because they are fully observable from stdout. Unexplained variance is weighted because detecting unknown-unknowns is critical for long-term trust, even though the current implementation is heuristic.

### Score Interpretation Thresholds

| Range | Label | Meaning for Compliance |
|-------|-------|------------------------|
| 95-100% | High | Record suitable for audit, regulatory submission, or contractual evidence |
| 80-94% | Moderate | Record usable with documented caveats; recommend human review of flagged gaps |
| <80% | Low | Record insufficient for formal purposes; investigate before reliance |

### Federal and Corporate Relevance

For **NIST AI RMF**, **EU AI Act**, and **corporate governance frameworks**, the confidence score provides:

1. **Measurable transparency** — a number that can be thresholded in policy
2. **Bounded trust** — explicit documentation of what is and is not verified
3. **Reproducible evidence** — seeded random sweeps and deterministic replay enable third-party validation
4. **Gap identification** — low scores flag where human oversight is required

---

## How Reconstruction Works

### Phase 1: Parse

`reconstruct.py` reads:
- `summary.json` — command sequence, commit hash, mode
- `stdout.log` — per-command output blocks
- `stderr.log` — error capture

### Phase 2: Extract

Regex-based extraction of:
- State transitions (`State transition: stateN -> stateM`)
- Receipts (`receipt_id: XXXXXXXXXXXXXXXX`)
- Artifact unlocks (`Unlocked document: filename.md`)
- Final state (`current_state: stateN`)

### Phase 3: Validate (Per Axis)

Each axis runs independent validation:
- State continuity: builds chain, checks against expected sequence
- Receipt integrity: uniqueness check, format validation
- Artifact consistency: set comparison against expected manifest
- Output completeness: presence check in log files
- Command fidelity: count match against summary
- Unexplained variance: pattern matching against known regexes

### Phase 4: Score and Report

Weighted average produces overall score. Report includes:
- Axis breakdown table
- Reconstructed timeline
- Unchecked constraints list
- Unknown-unknown assessment
- Real-world application mapping

---

## Replay and Determinism

```bash
# Replay a recorded run against the same commit
python scripts/replay.py runs/2026-04-24T13-14-00Z_full work/stegverse-demo-suite
```

Replay:
1. Reads `summary.json` for command sequence and commit hash
2. Checks out the recorded commit
3. Re-executes commands in identical order
4. Compares return codes and output structure
5. Reports match/mismatch

**Note:** Receipt IDs may differ between runs if generated from timestamps or entropy. This is expected and not a determinism failure. The check validates *structure*, not *content identity*.

---

## Supported Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `execution_governance` | Baseline execution validation | Quick sanity check |
| `mutation_governance` | State mutation + receipt validation | Verify mutation paths |
| `governance_matrix` | Deterministic ALLOW/DENY/FAIL_CLOSED (Test 5) | Compliance proof |
| `governance_random_sweep` | Seeded bounded input sweep with weighted phases (Test 6) | Robustness proof |
| `full` | All tests combined | Complete validation |

### Governance Matrix (Test 5)

Fixed cases:

| Action | Expected Outcome |
|--------|-----------------|
| `deploy_change` (valid, correct state) | ALLOW |
| `unauthorized_change` (known but inadmissible) | DENY |
| `malformed_request` (outside valid input space) | FAIL_CLOSED |

Pass condition: `expected == actual` for all cases.

### Random Sweep (Test 6)

- **Seed:** fixed (default 42)
- **Samples:** N per phase (default 50)
- **Phase 1 weights:** 50% ALLOW / 40% DENY / 10% FAIL_CLOSED
- **Phase 2 weights:** 10% ALLOW / 15% DENY / 75% FAIL_CLOSED

Pass condition: all classifications match expected rules.

---

## Device-Agnostic Design

This system is designed to run from any device, including mobile phones, via GitHub Actions:

1. Navigate to **Actions** tab in GitHub mobile app or browser
2. Select **"Run Demo Suite"** workflow
3. Choose mode from dropdown (no typing required)
4. Tap **"Run workflow"**
5. Receive notification when complete
6. Download artifacts directly

No local installation, no command-line knowledge, no dependencies.

---

## For Control Systems Thinkers

### Feedback Loops

The runner implements a closed-loop validation system:

```
[Propose] -> [Execute] -> [Capture] -> [Reconstruct] -> [Score] -> [Compare against threshold] -> [Accept / Flag for review]
```

The confidence score is the **sensor output** of this loop. It does not control the system — it reports on the system's observability.

### Safety Instrumented System (SIS) Analogy

| SIS Concept | Demo Equivalent |
|-------------|-----------------|
| Safety function | Governance evaluation (ALLOW/DENY/FAIL_CLOSED) |
| Sensor | stdout/stderr capture |
| Logic solver | Reconstruction engine |
| Final element | Confidence score threshold (human review trigger) |
| Proof test | Replay verification |

The confidence score serves as a **diagnostic coverage factor** — it tells you what fraction of the system's behavior is observable and verifiable.

---

## For Developers

### Local CLI

```bash
# Quick run
python runner/main.py --mode execution_governance --reset hard

# With reconstruction (default)
python runner/main.py --mode full --reset hard

# Skip reconstruction for speed
python runner/main.py --mode full --reset hard --no-reconstruct

# Custom sweep parameters
python runner/main.py --mode governance_random_sweep --reset hard --seed 42 --samples 100

# Replay previous run
python scripts/replay.py runs/2026-04-24T13-14-00Z_full work/stegverse-demo-suite

# Reconstruct previous run
python scripts/reconstruct.py runs/2026-04-24T13-14-00Z_full
```

### Repository Structure

```
demo-suite-runner/
├── runner/
│   └── main.py              # orchestration engine
├── configs/
│   ├── default.json         # repo URL, default ref
│   ├── execution_governance.json
│   ├── mutation_governance.json
│   ├── governance_matrix.json
│   ├── governance_random_sweep.json
│   └── full.json
├── scripts/
│   ├── governance_matrix.py       # Test 5
│   ├── governance_random_sweep.py # Test 6
│   ├── reconstruct.py             # confidence analysis
│   └── replay.py                  # determinism check
├── runs/                    # timestamped run artifacts
├── reports/                 # latest per-mode summaries
└── README.md                # this file
```

### Adding a New Mode

1. Create `configs/your_mode.json` with command sequence
2. Add mode to `runner/main.py` `choices` list
3. Add mapping in `load_mode_commands()`
4. Update README mode table

### Extending Confidence Axes

Edit `scripts/reconstruct.py`:
1. Add validation function (e.g., `validate_your_axis()`)
2. Add weight to `compute_overall_confidence()`
3. Add row to report generation
4. Document in README technical section

---
