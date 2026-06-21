# GCAT/BCAT Demo Suite Runner

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)

Experimental formal runner for probing admissibility behavior, GCAT/BCAT fixture behavior, scalar computations, gap instrumentation, entity classification, convergence validation, and cosmological mode fixtures.

This repository is a formalism runner. It does not replace SDK intake, sandbox execution, or authority-bearing admission logic.

---

## Formal testing route

This repository should consume datasets only after they have been ingested through `StegVerse-org/StegVerse-SDK` and bound to a manifest and intake receipt.

```text
Dataset / fixture / governance artifact
→ StegVerse-org/StegVerse-SDK ingestion
→ manifest binding
→ receipt binding
→ formal demo runner route
→ deterministic runner result receipt
```

Route role:

```text
SDK ingests.
Demo-suite demonstrates.
Demo-suite-runner probes formalism behavior.
Receipts bind every transition.
```

More adversarial or entity-specific cases should route to `StegGhost/entity-sandbox-runner`. Standing-specific stale-state and authority-rebinding cases should route to `StegVerse-Labs/Standing-Proof-Engine`. Boundary declaration and GLM-style composability cases should route to `StegVerse-Labs/Boundary-Test` after private-review-first concerns are resolved.

---

## Quick start

```bash
python scripts/scalar_engine.py
python scripts/gap_instrument.py
python scripts/entity_classifier.py
python scripts/cosmological_mode.py
```

Run tests:

```bash
python tests/test_scalar_engine.py
python tests/test_gap_instrument.py
python tests/test_entity_classifier.py
python tests/test_cosmological_mode.py
python tests/test_convergence_validator.py
```

---

## Architecture

See:

```text
docs/architecture.md
```

---

## Documentation

See:

```text
docs/formalism_documentation.txt
```

---

## Configuration

Edit:

```text
config/cosmological_profiles.yaml
```

---

## Workflow

The GitHub Actions workflow is stored under the repository workflow directory. In prose references, leading-dot paths may be shown without the leading dot for iOS compatibility. The actual GitHub Actions path must be:

```text
.github/workflows/<workflow-name>.yml
```

---

## Boundary rule

Runner output is not execution authority. Formalism behavior is not reviewer endorsement, compatibility recognition, provenance recognition, collaboration, or validation. Results are bounded demonstrations unless a separate authority-bearing route admits consequence.

---

## Origin

The formalism originates from:

```text
docs/origin_drawing.jpg
```
