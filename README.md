# GCAT/BCAT Demo Suite Runner v2.0

Experimental instrument for probing the geometry of admissibility,
the scalar as reality-selector, and the gap as active workspace.

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

The GitHub Actions workflow is in `.github/workflows/demo-suite-runner-v2.yml`.

## Origin

The formalism originates from `docs/origin_drawing.jpg` — the ground truth from which all mathematics flows.
