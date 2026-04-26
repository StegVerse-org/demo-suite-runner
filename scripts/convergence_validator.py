#!/usr/bin/env python3
"""
convergence_validator.py -- Convergence & Validation

Ensures results are stable, not noise.
Runs falsification tests that would refute the formalism.
"""

import math

# Predicted values from formalism
PREDICTED_ALLOW_RATE = 0.005       # ~0.5%
ALLOW_TOLERANCE = 0.002            # +/- 0.2%
MIN_SCALAR_VARIANCE = 0.001        # Scalar must vary
MAX_CV_THRESHOLD = 0.1             # Coefficient of variation for convergence


def test_allow_rate_convergence(sweep_results, tolerance=ALLOW_TOLERANCE):
    """
    Does ALLOW rate converge to ~0.5%?

    sweep_results: list of {samples, allow_count, deny_count, fail_closed_count}
    """
    if not sweep_results:
        return {'pass': False, 'reason': 'No sweep results'}

    allow_rates = []
    for result in sweep_results:
        total = result.get('allow_count', 0) + result.get('deny_count', 0) + result.get('fail_closed_count', 0)
        if total > 0:
            allow_rates.append(result.get('allow_count', 0) / total)

    if not allow_rates:
        return {'pass': False, 'reason': 'No valid allow rates'}

    mean_rate = sum(allow_rates) / len(allow_rates)
    variance = sum((r - mean_rate)**2 for r in allow_rates) / len(allow_rates)

    within_tolerance = abs(mean_rate - PREDICTED_ALLOW_RATE) <= tolerance

    return {
        'pass': within_tolerance,
        'predicted': PREDICTED_ALLOW_RATE,
        'observed': round(mean_rate, 6),
        'variance': round(variance, 6),
        'tolerance': tolerance,
        'reason': 'ALLOW rate within tolerance' if within_tolerance else f'ALLOW rate {mean_rate:.4f} outside tolerance {PREDICTED_ALLOW_RATE} +/- {tolerance}'
    }


def test_scalar_distribution(scalar_values, min_variance=MIN_SCALAR_VARIANCE):
    """
    Does scalar distribution vary (not all 0.5)?

    scalar_values: list of scalar values from runs
    """
    if not scalar_values:
        return {'pass': False, 'reason': 'No scalar values'}

    mean_s = sum(scalar_values) / len(scalar_values)
    variance = sum((s - mean_s)**2 for s in scalar_values) / len(scalar_values)

    has_variance = variance > min_variance

    return {
        'pass': has_variance,
        'mean_scalar': round(mean_s, 6),
        'variance': round(variance, 6),
        'min_variance': min_variance,
        'reason': 'Scalar varies across regimes' if has_variance else f'Scalar variance {variance:.6f} below minimum {min_variance}'
    }


def test_energy_fraction_convergence(cosmo_results, max_cv=MAX_CV_THRESHOLD):
    """
    Do energy fractions stabilize with increasing samples?

    cosmo_results: list of {samples, omega_matter, omega_dark_matter, omega_dark_energy}
    """
    if len(cosmo_results) < 2:
        return {'pass': False, 'reason': 'Need at least 2 cosmological runs'}

    om_values = [r.get('omega_matter', 0) for r in cosmo_results]
    dm_values = [r.get('omega_dark_matter', 0) for r in cosmo_results]
    de_values = [r.get('omega_dark_energy', 0) for r in cosmo_results]

    def cv(values):
        mean = sum(values) / len(values)
        if mean == 0:
            return float('inf')
        variance = sum((v - mean)**2 for v in values) / len(values)
        return math.sqrt(variance) / mean

    cv_om = cv(om_values)
    cv_dm = cv(dm_values)
    cv_de = cv(de_values)

    stable = all(cv_val < max_cv for cv_val in [cv_om, cv_dm, cv_de])

    return {
        'pass': stable,
        'cv_omega_matter': round(cv_om, 6),
        'cv_omega_dark_matter': round(cv_dm, 6),
        'cv_omega_dark_energy': round(cv_de, 6),
        'max_cv': max_cv,
        'reason': 'Energy fractions converged' if stable else f'CV too high: om={cv_om:.3f}, dm={cv_dm:.3f}, de={cv_de:.3f}'
    }


def test_life_band_not_empty(entity_results):
    """
    Is the life band populated?

    entity_results: list of entity classification dicts
    """
    if not entity_results:
        return {'pass': False, 'reason': 'No entity results'}

    life_count = sum(1 for e in entity_results if e.get('classification') == 'life')
    life_fraction = life_count / len(entity_results)

    has_life = life_count > 0

    return {
        'pass': has_life,
        'life_count': life_count,
        'total_entities': len(entity_results),
        'life_fraction': round(life_fraction, 6),
        'reason': f'Life band populated: {life_count} entities' if has_life else 'Life band empty'
    }


def falsification_tests(all_results):
    """
    Run all falsification tests.

    Returns PASS if all tests pass, FAIL otherwise.
    """
    tests = {
        'allow_rate': test_allow_rate_convergence(all_results.get('sweep', [])),
        'scalar_variance': test_scalar_distribution(all_results.get('scalars', [])),
        'energy_convergence': test_energy_fraction_convergence(all_results.get('cosmology', [])),
        'life_band': test_life_band_not_empty(all_results.get('entities', []))
    }

    all_pass = all(t['pass'] for t in tests.values())

    return {
        'overall': 'PASS' if all_pass else 'FAIL',
        'tests': tests,
        'summary': {
            'passed': sum(1 for t in tests.values() if t['pass']),
            'failed': sum(1 for t in tests.values() if not t['pass']),
            'total': len(tests)
        }
    }


if __name__ == '__main__':
    print("Convergence Validator Test")
    print("=" * 70)

    # Mock test data
    mock_results = {
        'sweep': [
            {'samples': 100, 'allow_count': 0, 'deny_count': 100, 'fail_closed_count': 0},
            {'samples': 500, 'allow_count': 4, 'deny_count': 496, 'fail_closed_count': 0},
            {'samples': 1000, 'allow_count': 5, 'deny_count': 995, 'fail_closed_count': 0},
        ],
        'scalars': [0.05, 0.15, 0.25, 0.35, 0.45, 0.50, 0.55, 0.65, 0.75, 0.85, 0.95],
        'cosmology': [
            {'samples': 100, 'omega_matter': 0.01, 'omega_dark_matter': 0.60, 'omega_dark_energy': 0.39},
            {'samples': 500, 'omega_matter': 0.005, 'omega_dark_matter': 0.62, 'omega_dark_energy': 0.375},
            {'samples': 1000, 'omega_matter': 0.003, 'omega_dark_matter': 0.61, 'omega_dark_energy': 0.387},
        ],
        'entities': [
            {'classification': 'life'},
            {'classification': 'non-life'},
            {'classification': 'life'},
        ]
    }

    result = falsification_tests(mock_results)

    print(f"Overall: {result['overall']}")
    print(f"Passed: {result['summary']['passed']}/{result['summary']['total']}")
    print()
    for test_name, test_result in result['tests'].items():
        status = "PASS" if test_result['pass'] else "FAIL"
        print(f"  [{status}] {test_name}: {test_result['reason']}")
