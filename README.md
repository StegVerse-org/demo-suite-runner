# StegVerse Demo Suite Runner

> **Proof that AI can be held accountable.**

Every day, AI systems make decisions that affect people's lives. Right now, most of those decisions happen in a black box. StegVerse changes that.

Before any AI action happens, it is **proposed, evaluated, and either allowed or denied**. Every decision leaves a **receipt** — proof that someone checked. Every run can be **reconstructed** later to see exactly what happened. Every reconstruction gets a **confidence score** — an honest number that says how sure we are.

---

## Try It in 30 Seconds

1. Go to **Actions** tab above
2. Tap **"Run Demo Suite"**
3. Select **"full"** mode, **"hard"** reset
4. Tap **"Run workflow"**
5. Wait ~2 minutes
6. Download the results

You will get a folder with a **report**, **reconstruction timeline**, and **confidence score**.

---

## The Confidence Score

A number between 0% and 100% that answers one question:

> *"Based only on what we can observe, how sure are we that the reconstructed record matches what actually happened?"*

| Range | Label | Meaning |
|-------|-------|---------|
| 95-100% | High | Reliable for audit, compliance, or legal evidence |
| 80-94% | Moderate | Usable with documented caveats; human review recommended |
| <80% | Low | Insufficient for formal purposes; investigate before reliance |

For **NIST AI RMF**, **EU AI Act**, and corporate governance frameworks, this provides measurable transparency, bounded trust, and reproducible evidence.

---

## Artifacts

| File | Audience |
|------|----------|
| `report.md` | Everyone — pass/fail summary |
| `reconstruction.md` | Everyone — step-by-step timeline + confidence score |
| `reconstruction.json` | Developers — structured data for tools |
| `summary.json` | Developers — technical metadata |
| `commands.log` | Auditors — every command that ran |
| `stdout.log` | Auditors — every output captured |
| `stderr.log` | Auditors — every error or warning |

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

## Supported Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `execution_governance` | Baseline execution validation | Quick sanity check |
| `mutation_governance` | State mutation + receipt validation | Verify mutation paths |
| `governance_matrix` | Deterministic ALLOW/DENY/FAIL_CLOSED | Compliance proof |
| `governance_random_sweep` | Seeded bounded input sweep | Robustness proof |
| `full` | All tests combined | Complete validation |

---

## Quick CLI

```bash
# Full run with reconstruction
python runner/main.py --mode full --reset hard

# Replay a previous run
python scripts/replay.py runs/2026-04-24T13-14-00Z_full work/stegverse-demo-suite

# Reconstruct a previous run
python scripts/reconstruct.py runs/2026-04-24T13-14-00Z_full
```

---

## Documentation

| Topic | File |
|-------|------|
| Receipt ID determinism | [`docs/RECEIPT_ID_DETERMINISM.md`](docs/RECEIPT_ID_DETERMINISM.md) |
| Mutation path governance | [`docs/MUTATION_PATH.md`](docs/MUTATION_PATH.md) |
| GCAT/BCAT enforcement | [`docs/GCAT_BCAT_ENFORCEMENT.md`](docs/GCAT_BCAT_ENFORCEMENT.md) |
| Reconstruction patches | [`docs/RECONSTRUCTION_PATCHES.md`](docs/RECONSTRUCTION_PATCHES.md) |
| Full technical specification | [`docs/TECHNICAL_SPEC.md`](docs/TECHNICAL_SPEC.md) |

---

## Notes

- This repository validates the pipeline, not the full production system.
- Deterministic tests prove correctness; random sweeps prove robustness.
- All runs are reproducible via seed and reset mode.
- Confidence scores are heuristic, not cryptographic. They reflect observable boundaries.
- For questions: see [StegVerse SDK documentation](https://github.com/StegVerse-org/StegVerse-SDK)
