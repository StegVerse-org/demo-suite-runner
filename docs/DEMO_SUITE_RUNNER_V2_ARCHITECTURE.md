
================================================================================
GCAT/BCAT DEMO-SUITE-RUNNER v2.0
Full Integration Architecture
================================================================================

PURPOSE
-------
Transform the demo-suite-runner from a gate verifier into an experimental
instrument for probing the geometry of admissibility, the scalar as reality-
selector, and the gap as active workspace.

================================================================================

LAYER 0: ORIGIN (The Drawing)
================================================================================

File: docs/origin_drawing.jpg (C001F27F-ECDB-4522-BCE6-20CCBD5726EE.jpg)

The drawing is source code. It is the origin entity from which all formalism
flows. Every module references back to the drawing as its ground truth.

================================================================================

LAYER 1: CORE BCAT/GOVERNANCE (Existing -- Unchanged)
================================================================================

Modules:
  scripts/receipt_id.py          -- Deterministic receipt generation
  scripts/governed_action.py     -- Action governance boundary
  scripts/governed_mutation.py   -- Mutation governance boundary

Functions:
  bcat_simplex_valid(state)      -- Validate BCAT simplex
  compute_invariant(state)       -- I(x) = gc + ca + at + tg
  classify_transition(before, after) -- ALLOW/DENY/FAIL_CLOSED

These modules are PROVEN CORRECT. They do not change. They are the
foundation upon which all new layers build.

================================================================================

LAYER 2: SCALAR COMPUTATION (New)
================================================================================

Module: scripts/scalar_engine.py

Purpose: Compute the reality-selector scalar for any BCAT state.

Functions:
  compute_scalar(state) -> float
    Compute scalar s in [0,1] from BCAT state.
    lambda_capacity = g*c*a*t
    lambda_max = (0.25)**4
    invariant = I(x)

    If on g-a edge (I=0, g>0, a>0): return 0.0
    If on c-t edge (I=0, c>0, t>0): return 1.0
    If at corner (I=0, single vertex): return 0.5

    Otherwise:
      s = (lambda/lambda_max) / (invariant/0.25)
      return clamp(s, 0.0, 1.0)

  reality_label(s) -> str
    Map scalar to human-readable regime.
    s < 0.1:  "quantum-contracted"
    s < 0.3:  "quantum-mixed"
    s < 0.45: "near-quantum"
    s < 0.55: "classical-critical"
    s < 0.7:  "near-astrophysical"
    s < 0.9:  "astrophysical-mixed"
    else:      "astrophysical-expanded"

  gap_efficiency(s) -> float
    Compute c_eff = c_0 * |s - 0.5|.
    return C_0 * abs(s - 0.5)

  scale(s, alpha=1.0) -> float
    Physical scale as function of scalar.
    log_ratio = log(L_HUBBLE / L_PLANCK)
    exponent = alpha * abs(s - 0.5) * log_ratio
    return L_PLANCK * exp(exponent)

Integration:
  - receipt_id.py: receipt includes scalar value
  - governed_action.py: action log includes scalar regime
  - governed_mutation.py: mutation receipt includes scalar
  - sweep output: scalar distribution per run

================================================================================

LAYER 3: GAP INSTRUMENTATION (New)
================================================================================

Module: scripts/gap_instrument.py

Purpose: Measure the active workspace between irreversibility and reality.

Gap Variables (computed per transition):
  coherence_budget       -- fidelity(state_before, projected_state)
  obscurity_gradient     -- I(projected) - I(state_before)
  negotiation_depth      -- count of reversible operations before commitment
  commitment_latency     -- time from last reversible op to contact
  entropy_debt           -- H(projected) - H(state_before)
  information_content    -- shannon_information(projected_state)

Functions:
  compute_coherence_budget(state_before, projected) -> float
    Dot product of normalized state vectors.
    return sum(state_before[k] * projected[k] for k in state_before)

  compute_obscurity_gradient(state_before, projected) -> float
    Change in invariant across transition.
    return compute_invariant(projected) - compute_invariant(state_before)

  compute_entropy_debt(state_before, projected) -> float
    Shannon entropy increase (information lost to obscurity).
    return max(0.0, shannon_entropy(projected) - shannon_entropy(state_before))

  compute_negotiation_depth(sequence) -> int
    Count reversible operations in transition sequence.
    depth = 0
    for step in sequence:
      if is_reversible(step):
        depth += 1
      else:
        break
    return depth

  compute_commitment_latency(sequence) -> float
    Time from last reversible step to irreversible contact.
    last_reversible_time = max(t for t, step in sequence if is_reversible(step))
    contact_time = sequence[-1].timestamp
    return contact_time - last_reversible_time

Gap Ledger (per run):
  Maintains a sequence of gap operations:
    [
      {timestamp, operation, reversible, scalar, entropy_change},
      ...
    ]

  The ledger is erased if FAIL_CLOSED (gap broken).
  The ledger is committed if ALLOW (reality touched).
  The ledger is suspended if DENY (negotiation incomplete).

Integration:
  - governed_action.py: action sequence logs to gap ledger
  - governed_mutation.py: mutation sequence logs to gap ledger
  - sweep output: gap statistics per phase (mean depth, mean latency, etc.)

================================================================================

LAYER 4: ENTITY CLASSIFICATION (New)
================================================================================

Module: scripts/entity_classifier.py

Purpose: Classify entities by scalar oscillation pattern.

Life Band Definition:
  LIFE_MIN = 0.3
  LIFE_MAX = 0.7

  An entity is ALIVE if:
    1. Its scalar oscillates within [LIFE_MIN, LIFE_MAX]
    2. The oscillation is sustained (not transient)
    3. The amplitude A > 0 and frequency omega > 0

Functions:
  classify_entity(scalar_history) -> dict
    Classify entity from scalar time series.

    Fit: s(t) = 0.5 + A * sin(omega*t + phi)
    A, omega, phi = fit_oscillation(scalar_history)

    mean_s = mean(scalar_history)
    variance_s = variance(scalar_history)

    is_life = (LIFE_MIN <= mean_s <= LIFE_MAX and 
               A > 0 and omega > 0 and 
               variance_s > 0.001)

    return {
      'classification': 'life' if is_life else 'non-life',
      'life_category': reality_label(mean_s) if is_life else None,
      'amplitude': A,
      'frequency': omega,
      'phase': phi,
      'mean_scalar': mean_s,
      'variance': variance_s,
      'gap_efficiency': gap_efficiency(mean_s)
    }

  compute_life_fraction(entity_results) -> float
    Fraction of entities classified as life.
    life_count = sum(1 for e in entity_results if e['classification'] == 'life')
    return life_count / len(entity_results)

Entity Types (from scalar signature):
  s ~ 0, omega -> inf:     "quantum event" -- not life (too fast)
  s ~ 0.2, omega ~ 1Hz: "neural entity" -- life (human-scale)
  s ~ 0.5, omega ~ 0:   "static entity" -- not life (no oscillation)
  s ~ 0.5, omega ~ 0.01Hz: "sloth" -- life (slow oscillation)
  s ~ 0.8, omega ~ 10^9Hz: "AI entity" -- life-like (fast, narrow)
  s = 0.5, A = 0:   "black hole" -- not life (frozen)

Integration:
  - sweep output: entity classification table
  - cumulative stats: life fraction over runs
  - report: life-bearing regimes identified

================================================================================

LAYER 5: COSMOLOGICAL MODE (New)
================================================================================

Module: scripts/cosmological_mode.py

Purpose: Entity-weighted cosmological integral for energy budget prediction.

Configuration:
  scalar_centers: [0.05, 0.15, 0.25, 0.35, 0.45, 0.50, 0.55, 0.65, 0.75, 0.85, 0.95]
  entity_density: {s_center: log10_density}  -- configurable
  time_fraction: {s_center: fraction}  -- configurable
  life_band: [0.3, 0.7]
  samples_per_scalar: 50 (default)

Functions:
  run_cosmological_integral(config) -> dict
    Compute entity-weighted energy budget.

    For each scalar_center in config.scalar_centers:
      Sample states near this scalar
      Compute mean information content
      Weight by entity_density * time_fraction

      If scalar in life_band:
        Add to life_information

      Add to total_information

    Compute energy fractions:
      ordinary_matter = sum(life_entities * 0.5)
      dark_matter = sum(non-life, s<0.5 * 0.7) + sum(life * 0.3)
      dark_energy = sum(non-life, s>0.5 * 0.8) + sum(life * 0.2)

    Normalize to total_budget

    Return {
      'energy_budget': {'ordinary_matter': Om, 'dark_matter': Odm, 'dark_energy': Ode},
      'life_fraction': life_info / total_info,
      'scalar_distribution': per-bin results,
      'convergence': stability_metric
    }

  test_convergence(config, sample_sizes=[100, 250, 500, 1000, 2500, 5000]) -> dict
    Test whether fractions stabilize with increasing samples.
    For each n in sample_sizes:
      result = run_cosmological_integral(config with n samples)
      Record fractions

    Compute variance across sample sizes
    Return convergence report

Integration:
  - New workflow step: cosmological-sweep
  - Output: cosmological_report.md with energy fractions and life requirement
  - Comparison: predicted vs. observed (when available)

================================================================================

LAYER 6: CONVERGENCE & VALIDATION (New)
================================================================================

Module: scripts/convergence_validator.py

Purpose: Ensure results are stable, not noise.

Functions:
  test_allow_rate_convergence(sweep_results) -> dict
    Does ALLOW rate converge to ~0.5%?
    Compute ALLOW rate at increasing sample sizes
    Test against predicted 0.5% +/- tolerance

  test_scalar_distribution_convergence(sweep_results) -> dict
    Does scalar distribution stabilize?
    Compute mean, variance, entropy at increasing samples
    Test variance decrease

  test_energy_fraction_convergence(cosmo_results) -> dict
    Do Om, Odm, Ode stabilize?
    Compute fractions at increasing samples
    Test coefficient of variation < threshold

  falsification_tests(all_results) -> dict
    Tests that would refute the formalism.

    FAIL if:
      - ALLOW rate >> 0.5% under pure random sampling
      - Scalar = 0.5 everywhere (no regime distinction)
      - Energy fractions don't converge with entity weighting
      - Life band is empty

    PASS if all tests pass

Integration:
  - Final workflow step: validation
  - Output: validation_report.md with PASS/FAIL per test
  - CI gate: workflow fails if falsification tests fail

================================================================================

WORKFLOW INTEGRATION
================================================================================

New workflow: .github/workflows/demo-suite-runner-v2.yml

Steps:
  1. Cache clear (existing)
  2. Checkout (existing)
  3. Setup Python (existing)
  4. Install dependencies (existing)
  5. Run base governance tests (existing)
     - receipt_id.py
     - governed_action.py
     - governed_mutation.py
  6. Run scalar computation (NEW)
     - scalar_engine.py on all transitions
     - Output: scalar_distribution.json
  7. Run gap instrumentation (NEW)
     - gap_instrument.py on action/mutation sequences
     - Output: gap_ledger.json
  8. Run entity classification (NEW)
     - entity_classifier.py on scalar histories
     - Output: entity_classification.json
  9. Run cosmological mode (NEW)
     - cosmological_mode.py with configured profiles
     - Output: cosmological_report.json
  10. Run convergence validation (NEW)
      - convergence_validator.py on all outputs
      - Output: validation_report.md
  11. Generate unified report (NEW)
      - Combine all outputs into sweep_report_v2.md
      - Include scalar distribution, gap stats, life fraction, cosmology
  12. Upload artifacts (existing + new)

================================================================================

FILE STRUCTURE
================================================================================

demo-suite-runner/
├── .github/
│   └── workflows/
│       ├── demo-suite-runner.yml          (existing)
│       └── demo-suite-runner-v2.yml       (NEW)
├── scripts/
│   ├── receipt_id.py                      (existing, PROVEN)
│   ├── governed_action.py                 (existing, PROVEN)
│   ├── governed_mutation.py               (existing, PROVEN)
│   ├── scalar_engine.py                   (NEW -- Layer 2)
│   ├── gap_instrument.py                  (NEW -- Layer 3)
│   ├── entity_classifier.py               (NEW -- Layer 4)
│   ├── cosmological_mode.py               (NEW -- Layer 5)
│   └── convergence_validator.py           (NEW -- Layer 6)
├── docs/
│   ├── origin_drawing.jpg                 (NEW -- Layer 0)
│   ├── GCAT_BCAT_Formalism_Documentation.txt  (NEW)
│   └── architecture.md                    (NEW -- this document)
├── config/
│   └── cosmological_profiles.yaml         (NEW -- entity density, time fraction)
├── tests/
│   ├── test_scalar_engine.py              (NEW)
│   ├── test_gap_instrument.py             (NEW)
│   ├── test_entity_classifier.py          (NEW)
│   ├── test_cosmological_mode.py          (NEW)
│   └── test_convergence_validator.py      (NEW)
└── outputs/
    ├── scalar_distribution.json           (NEW)
    ├── gap_ledger.json                    (NEW)
    ├── entity_classification.json         (NEW)
    ├── cosmological_report.json           (NEW)
    ├── validation_report.md               (NEW)
    └── sweep_report_v2.md                 (NEW)

================================================================================

CONFIGURATION: cosmological_profiles.yaml
================================================================================

default:
  description: "Standard cosmological model"
  scalar_centers: [0.05, 0.15, 0.25, 0.35, 0.45, 0.50, 0.55, 0.65, 0.75, 0.85, 0.95]
  entity_density:
    0.05: 80    # Quantum particles
    0.15: 60
    0.25: 40
    0.35: 25
    0.45: 15
    0.50: 12    # Human-scale (critical)
    0.55: 15
    0.65: 25
    0.75: 40
    0.85: 60
    0.95: 80    # Cosmological
  time_fraction:
    0.05: 0.01
    0.15: 0.02
    0.25: 0.03
    0.35: 0.05
    0.45: 0.10
    0.50: 0.20   # Longest epoch
    0.55: 0.15
    0.65: 0.12
    0.75: 0.10
    0.85: 0.12
    0.95: 0.10
  life_band: [0.3, 0.7]
  samples_per_scalar: 50

early_universe:
  description: "Primordial, quantum-dominated"
  # Shift entity density toward quantum, time fraction toward early
  entity_density:
    0.05: 90
    0.15: 70
    0.25: 50
    0.35: 20
    0.45: 10
    0.50: 5
    0.55: 5
    0.65: 10
    0.75: 20
    0.85: 40
    0.95: 60
  time_fraction:
    0.05: 0.20
    0.15: 0.15
    0.25: 0.12
    0.35: 0.10
    0.45: 0.08
    0.50: 0.05
    0.55: 0.05
    0.65: 0.08
    0.75: 0.05
    0.85: 0.05
    0.95: 0.07
  life_band: [0.3, 0.7]
  samples_per_scalar: 50

late_universe:
  description: "Dark energy dominated"
  # Shift entity density toward astrophysical, time fraction toward late
  entity_density:
    0.05: 60
    0.15: 40
    0.25: 20
    0.35: 10
    0.45: 5
    0.50: 5
    0.55: 10
    0.65: 20
    0.75: 40
    0.85: 60
    0.95: 90
  time_fraction:
    0.05: 0.05
    0.15: 0.05
    0.25: 0.05
    0.35: 0.05
    0.45: 0.05
    0.50: 0.05
    0.55: 0.08
    0.65: 0.10
    0.75: 0.12
    0.85: 0.15
    0.95: 0.25
  life_band: [0.3, 0.7]
  samples_per_scalar: 50

================================================================================

BACKWARD COMPATIBILITY
================================================================================

The v2 workflow is additive. All existing tests continue to run unchanged.
The new layers are opt-in via workflow configuration:

  run_scalar: true/false
  run_gap: true/false
  run_entity: true/false
  run_cosmology: true/false
  run_validation: true/false

Default: all true for v2, all false for v1 compatibility.

================================================================================

CONSTANTS DERIVED FROM SPECIAL CASES
================================================================================

The formalism generates mathematical constants from symmetry-enhanced cases:

  Circle condition (equal obscurity):     pi -- rotational symmetry
  Critical point (s=0.5):                phi (golden ratio) -- self-similarity
  Edge collapse (continuous limit):       e -- continuous compounding
  Corner (singular limit):                gamma (Euler-Mascheroni) -- divergence
  Tetrahedral symmetry:                   sqrt(2), sqrt(3) -- spatial ratios

The origin constant (prior to any breakdown): 1 -- pure unity

All other constants are departures from 1, measuring how much symmetry
was lost in each breaking.

================================================================================

DOCUMENT END
================================================================================
