# GCAT/BCAT Demo Suite Runner v2.0

Experimental instrument for probing the geometry of admissibility,
the scalar as reality-selector, and the gap as active workspace.

## Formal Testing Route

This repository is the formal demo runner route. It should consume datasets only after they have been ingested through `StegVerse-org/StegVerse-SDK` and bound to a manifest and intake receipt.

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

## Quick Start

```bash
# Run scalar computation
python scripts/scalar_engine.py

# Run gap instrumentation
python scripts/gap_instrument.py

# Run entity classification
python scripts/entity_classifier.py

# Run cosmological mode
python scripts/cosmological_mode.py

# Run all tests
python tests/test_scalar_engine.py
python tests/test_gap_instrument.py
python tests/test_entity_classifier.py
python tests/test_cosmological_mode.py
python tests/test_convergence_validator.py
```

## Architecture

See `docs/architecture.md` for full 6-layer integration spec.

## Documentation

See `docs/formalism_documentation.txt` for complete mathematical documentation.

## Configuration

Edit `config/cosmological_profiles.yaml` to adjust entity density and time fraction distributions.

## Workflow

The GitHub Actions workflow is in the repository workflow directory as `github/workflows/demo-suite-runner-v2.yml` in this prose reference. The actual repository path must include the leading dot for GitHub Actions to run.

## Origin

The formalism originates from `docs/origin_drawing.jpg` — the ground truth from which all mathematics flows.
