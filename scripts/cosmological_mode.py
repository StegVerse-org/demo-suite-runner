#!/usr/bin/env python3
"""
cosmological_mode.py -- Entity-Weighted Cosmological Integral

Computes the global information budget by sampling entities at each scalar
and weighting by their gap efficiency and oscillation parameters.
"""

import json
import random
import math
from scalar_engine import compute_scalar, compute_invariant, shannon_information, compute_scale
from entity_classifier import classify_entity, LIFE_MIN, LIFE_MAX

L_PLANCK = 1.616e-35
L_HUBBLE = 4.4e26


def generate_random_valid_simplex():
    raw = [random.random() for _ in range(4)]
    total = sum(raw)
    values = [r / total for r in raw]
    return {'g': values[0], 'c': values[1], 'a': values[2], 't': values[3]}


def generate_random_delta():
    deltas = [random.uniform(-0.2, 0.2) for _ in range(4)]
    adjustment = sum(deltas) / 4
    deltas = [d - adjustment for d in deltas]
    return {'g': deltas[0], 'c': deltas[1], 'a': deltas[2], 't': deltas[3]}


def project_state(state, delta):
    projected = {k: max(0.0, state[k] + delta[k]) for k in state}
    total = sum(projected.values())
    if total > 0:
        projected = {k: v / total for k, v in projected.items()}
    return projected


def bcat_simplex_valid(state):
    total = sum(state.values())
    return abs(total - 1.0) < 1e-9 and all(v >= 0 for v in state.values())


def classify_transition(state_before, projected_state):
    if not bcat_simplex_valid(state_before):
        return 'FAIL_CLOSED', 'Invalid initial state'
    if projected_state is None or not bcat_simplex_valid(projected_state):
        return 'FAIL_CLOSED', 'Projected state invalid'
    inv_after = compute_invariant(projected_state)
    if inv_after <= 1e-12:
        return 'ALLOW', 'I(x-prime) = ' + str(round(inv_after, 6)) + ' <= 0'
    else:
        return 'DENY', 'I(x-prime) = ' + str(round(inv_after, 6)) + ' > 0'


def load_profile(profile_name='default', config_path='config/cosmological_profiles.yaml'):
    try:
        import yaml
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config.get(profile_name, config.get('default', {}))
    except Exception:
        return {
            'scalar_centers': [0.05, 0.15, 0.25, 0.35, 0.45, 0.50, 0.55, 0.65, 0.75, 0.85, 0.95],
            'entity_density': {
                0.05: 80, 0.15: 60, 0.25: 40, 0.35: 25, 0.45: 15,
                0.50: 12, 0.55: 15, 0.65: 25, 0.75: 40, 0.85: 60, 0.95: 80
            },
            'time_fraction': {
                0.05: 0.01, 0.15: 0.02, 0.25: 0.03, 0.35: 0.05, 0.45: 0.10,
                0.50: 0.20, 0.55: 0.15, 0.65: 0.12, 0.75: 0.10, 0.85: 0.12, 0.95: 0.10
            },
            'life_band': [0.3, 0.7],
            'samples_per_scalar': 50
        }


def run_cosmological_integral(profile=None, samples_per_scalar=None, seed=None, alpha=1.0):
    if seed is not None:
        random.seed(seed)

    if profile is None:
        profile = load_profile()

    scalar_centers = profile.get('scalar_centers', [0.05, 0.15, 0.25, 0.35, 0.45, 0.50, 0.55, 0.65, 0.75, 0.85, 0.95])
    entity_density = profile.get('entity_density', {})
    time_fraction = profile.get('time_fraction', {})
    life_band = profile.get('life_band', [0.3, 0.7])
    n_samples = samples_per_scalar or profile.get('samples_per_scalar', 50)

    results = []
    total_information = 0.0
    total_life_information = 0.0

    for s_center in scalar_centers:
        s_samples = []
        info_samples = []

        for _ in range(n_samples):
            best_state = None
            best_score = float('inf')
            for _ in range(100):
                state = generate_random_valid_simplex()
                s = compute_scalar(state)
                score = abs(s - s_center)
                if score < best_score:
                    best_score = score
                    best_state = state
                if score < 0.05:
                    break

            if best_state:
                delta = generate_random_delta()
                projected = project_state(best_state, delta)
                outcome, _ = classify_transition(best_state, projected)

                if projected and bcat_simplex_valid(projected):
                    info = shannon_information(projected)
                    s_actual = compute_scalar(projected)
                    s_samples.append(s_actual)
                    info_samples.append(info)

        if s_samples:
            mean_s = sum(s_samples) / len(s_samples)
            mean_info = sum(info_samples) / len(info_samples)

            density = 10 ** entity_density.get(s_center, 12)
            time_frac = time_fraction.get(s_center, 0.1)
            weighted_info = mean_info * density * time_frac

            is_life = life_band[0] <= mean_s <= life_band[1]

            if is_life:
                total_life_information += weighted_info

            total_information += weighted_info

            results.append({
                'scalar_center': s_center,
                'mean_scalar': round(mean_s, 4),
                'mean_information': round(mean_info, 4),
                'entity_density_log': entity_density.get(s_center, 12),
                'time_fraction': time_fraction.get(s_center, 0.1),
                'weighted_information': weighted_info,
                'is_life': is_life,
                'life_category': 'life' if is_life else 'non-life'
            })

    ordinary_matter = 0.0
    dark_matter = 0.0
    dark_energy = 0.0

    for r in results:
        s = r['mean_scalar']
        w = r['weighted_information']

        if r['is_life']:
            ordinary_matter += w * 0.5
            dark_matter += w * 0.3
            dark_energy += w * 0.2
        else:
            if s < 0.5:
                dark_matter += w * 0.7
                dark_energy += w * 0.3
            else:
                dark_energy += w * 0.8
                dark_matter += w * 0.2

    total_budget = ordinary_matter + dark_matter + dark_energy
    if total_budget > 0:
        omega_m = ordinary_matter / total_budget
        omega_dm = dark_matter / total_budget
        omega_de = dark_energy / total_budget
    else:
        omega_m = omega_dm = omega_de = 0.0

    life_fraction = total_life_information / total_information if total_information > 0 else 0.0

    return {
        'scalar_bins': results,
        'total_information': total_information,
        'total_life_information': total_life_information,
        'life_fraction': life_fraction,
        'energy_budget': {
            'ordinary_matter': round(omega_m, 6),
            'dark_matter': round(omega_dm, 6),
            'dark_energy': round(omega_de, 6)
        },
        'life_entities': [r for r in results if r['is_life']],
        'non_life_entities': [r for r in results if not r['is_life']]
    }


def test_convergence(profile=None, sample_sizes=None, seed=None):
    if sample_sizes is None:
        sample_sizes = [100, 250, 500, 1000, 2500, 5000]

    convergence_results = []

    for n in sample_sizes:
        result = run_cosmological_integral(
            profile=profile,
            samples_per_scalar=max(1, n // len(profile.get('scalar_centers', [0.5]))),
            seed=seed
        )
        convergence_results.append({
            'samples': n,
            'omega_matter': result['energy_budget']['ordinary_matter'],
            'omega_dark_matter': result['energy_budget']['dark_matter'],
            'omega_dark_energy': result['energy_budget']['dark_energy'],
            'life_fraction': result['life_fraction']
        })

    om_values = [r['omega_matter'] for r in convergence_results]
    dm_values = [r['omega_dark_matter'] for r in convergence_results]
    de_values = [r['omega_dark_energy'] for r in convergence_results]

    def cv(values):
        mean = sum(values) / len(values)
        if mean == 0:
            return float('inf')
        variance = sum((v - mean)**2 for v in values) / len(values)
        return math.sqrt(variance) / mean

    return {
        'convergence_series': convergence_results,
        'coefficient_of_variation': {
            'omega_matter': round(cv(om_values), 6),
            'omega_dark_matter': round(cv(dm_values), 6),
            'omega_dark_energy': round(cv(de_values), 6)
        },
        'stable': all(cv([om_values, dm_values, de_values][i]) < 0.1 for i in range(3))
    }


if __name__ == '__main__':
    print("Cosmological Mode Test")
    print("=" * 70)

    result = run_cosmological_integral(samples_per_scalar=50, seed=42)

    print("Total information: " + str(result['total_information']))
    print("Life information: " + str(result['total_life_information']))
    print("Life fraction: " + str(round(result['life_fraction']*100, 4)) + "%")
    print()
    print("Energy Budget:")
    for k, v in result['energy_budget'].items():
        print("  " + k + ": " + str(round(v*100, 2)) + "%")
    print()
    print("Life-bearing regimes:")
    for e in result['life_entities']:
        print("  s=" + str(e['scalar_center']) + " | " + e['life_category'] + " | info=" + str(e['weighted_information']))
