#!/usr/bin/env python3
"""
governance_random_sweep.py — Randomized Governance Sweep with Reality Scalar

Full state space randomization + adaptive outcome-guided sampling + reality scalar.
The scalar maps BCAT state to physical regime: 0=quantum-contracted, 1=astrophysical-expanded.

Usage:
    python governance_random_sweep.py --samples 100 --seed 42
"""

import json
import os
import random
import math
import argparse
from datetime import datetime, timezone

# === BCAT/GCAT Core ===

def bcat_simplex_valid(state):
    total = sum(state.values())
    return abs(total - 1.0) < 1e-9 and all(v >= 0 for v in state.values())

def compute_invariant(state):
    """I(x) = gc + ca + at + tg"""
    g, c, a, t = state['g'], state['c'], state['a'], state['t']
    return g*c + c*a + a*t + t*g

def lambda_capacity(state):
    return state['g'] * state['c'] * state['a'] * state['t']

def compute_scalar(state):
    """
    Reality selector scalar: 0 = quantum/contracted, 1 = astrophysical/expanded.
    """
    lam = lambda_capacity(state)
    inv = compute_invariant(state)
    lam_max = (0.25)**4  # 1/256

    if inv <= 1e-12:
        if state['g'] > 0 and state['a'] > 0:
            return 0.0
        elif state['c'] > 0 and state['t'] > 0:
            return 1.0
        else:
            return 0.5

    lam_norm = lam / lam_max if lam_max > 0 else 0.0
    inv_norm = inv / 0.25

    if inv_norm > 0:
        scalar = lam_norm / inv_norm
        scalar = min(1.0, max(0.0, scalar))
    else:
        scalar = 0.5

    return scalar

def reality_label(scalar):
    if scalar < 0.1:
        return "quantum-contracted"
    elif scalar < 0.3:
        return "quantum-mixed"
    elif scalar < 0.45:
        return "near-quantum"
    elif scalar < 0.55:
        return "classical-critical"
    elif scalar < 0.7:
        return "near-astrophysical"
    elif scalar < 0.9:
        return "astrophysical-mixed"
    else:
        return "astrophysical-expanded"

# === Generators ===

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

# === Classification ===

def classify_transition(state_before, projected_state):
    if not bcat_simplex_valid(state_before):
        return 'FAIL_CLOSED', 'Invalid initial state'
    if projected_state is None or not bcat_simplex_valid(projected_state):
        return 'FAIL_CLOSED', 'Projected state invalid'

    inv_after = compute_invariant(projected_state)
    if inv_after <= 1e-12:
        return 'ALLOW', f'I(x') = {inv_after:.6f} <= 0'
    else:
        return 'DENY', f'I(x') = {inv_after:.6f} > 0'

# === Statistics ===

def compute_entropy(counts):
    total = sum(counts.values())
    if total == 0:
        return 0.0
    entropy = 0.0
    for count in counts.values():
        if count > 0:
            p = count / total
            entropy -= p * math.log2(p)
    return entropy

def load_cumulative_stats(path='sweep_statistics.json'):
    if os.path.exists(path):
        with open(path, 'r') as f:
            data = json.load(f)
        if 'scalar_history' not in data:
            data['scalar_history'] = []
        return data
    return {
        'total_runs': 0,
        'total_samples': 0,
        'cumulative_counts': {'ALLOW': 0, 'DENY': 0, 'FAIL_CLOSED': 0},
        'scalar_history': [],
        'run_history': []
    }

def save_cumulative_stats(stats, path='sweep_statistics.json'):
    with open(path, 'w') as f:
        json.dump(stats, f, indent=2)

# === Main Sweep ===

def run_randomized_sweep(samples_per_phase=100, seed=None, stats_path='sweep_statistics.json'):
    if seed is not None:
        random.seed(seed)

    cumulative = load_cumulative_stats(stats_path)

    results = []
    counts = {'ALLOW': 0, 'DENY': 0, 'FAIL_CLOSED': 0}
    boundary_proximities = []
    scalars = []
    scalar_by_outcome = {'ALLOW': [], 'DENY': [], 'FAIL_CLOSED': []}

    for i in range(samples_per_phase):
        state_before = generate_random_valid_simplex()
        delta = generate_random_delta()
        projected = project_state(state_before, delta)

        outcome, reason = classify_transition(state_before, projected)
        counts[outcome] += 1

        scalar = compute_scalar(projected) if projected else None
        if scalar is not None:
            scalars.append(scalar)
            scalar_by_outcome[outcome].append(scalar)

        if outcome == 'DENY':
            boundary_proximities.append(compute_invariant(projected))

        results.append({
            'sample': i,
            'state_before': state_before,
            'delta': delta,
            'projected_state': projected,
            'outcome': outcome,
            'reason': reason,
            'scalar': scalar,
            'reality': reality_label(scalar) if scalar is not None else None,
            'invariant_before': compute_invariant(state_before),
            'invariant_after': compute_invariant(projected) if projected else None,
            'lambda_before': lambda_capacity(state_before),
            'lambda_after': lambda_capacity(projected) if projected else None
        })

    total = sum(counts.values())
    frequencies = {k: v / total for k, v in counts.items()}
    entropy = compute_entropy(counts)
    admissible_volume = frequencies.get('ALLOW', 0.0)

    if scalars:
        mean_scalar = sum(scalars) / len(scalars)
        min_scalar = min(scalars)
        max_scalar = max(scalars)
        var_scalar = sum((s - mean_scalar)**2 for s in scalars) / len(scalars)
    else:
        mean_scalar = min_scalar = max_scalar = var_scalar = None

    scalar_stats = {}
    for outcome in ['ALLOW', 'DENY', 'FAIL_CLOSED']:
        vals = scalar_by_outcome[outcome]
        if vals:
            scalar_stats[outcome] = {
                'mean': round(sum(vals) / len(vals), 6),
                'min': round(min(vals), 6),
                'max': round(max(vals), 6),
                'count': len(vals)
            }
        else:
            scalar_stats[outcome] = None

    if boundary_proximities:
        mean_proximity = sum(boundary_proximities) / len(boundary_proximities)
        min_proximity = min(boundary_proximities)
        max_proximity = max(boundary_proximities)
    else:
        mean_proximity = min_proximity = max_proximity = None

    run_record = {
        'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'seed': seed,
        'samples': samples_per_phase,
        'counts': counts,
        'frequencies': {k: round(v, 6) for k, v in frequencies.items()},
        'entropy': round(entropy, 6),
        'admissible_volume_estimate': round(admissible_volume, 6),
        'scalar': {
            'mean': round(mean_scalar, 6) if mean_scalar else None,
            'min': round(min_scalar, 6) if min_scalar else None,
            'max': round(max_scalar, 6) if max_scalar else None,
            'variance': round(var_scalar, 6) if var_scalar else None,
            'by_outcome': scalar_stats
        },
        'boundary_proximity': {
            'mean': round(mean_proximity, 6) if mean_proximity else None,
            'min': round(min_proximity, 6) if min_proximity else None,
            'max': round(max_proximity, 6) if max_proximity else None,
            'count': len(boundary_proximities)
        }
    }

    cumulative['total_runs'] += 1
    cumulative['total_samples'] += samples_per_phase
    for outcome in counts:
        cumulative['cumulative_counts'][outcome] += counts[outcome]

    allow_scalar_data = scalar_stats.get('ALLOW', {})
    cumulative['scalar_history'].append({
        'run': cumulative['total_runs'],
        'mean_scalar': round(mean_scalar, 6) if mean_scalar else None,
        'allow_scalars': allow_scalar_data if allow_scalar_data else {}
    })
    cumulative['run_history'].append(run_record)

    cum_total = cumulative['total_samples']
    cumulative['cumulative_frequencies'] = {
        k: round(v / cum_total, 6)
        for k, v in cumulative['cumulative_counts'].items()
    }
    cumulative['cumulative_entropy'] = round(
        compute_entropy(cumulative['cumulative_counts']), 6
    )

    save_cumulative_stats(cumulative, stats_path)

    # User-facing output
    print("=" * 70)
    print("RANDOMIZED GOVERNANCE SWEEP — Full State Space + Reality Scalar")
    print("=" * 70)
    print(f"Samples this run: {samples_per_phase}")
    print(f"Random seed: {seed}")
    print()
    print("OUTCOME DISTRIBUTION (this run):")
    for outcome in ['ALLOW', 'DENY', 'FAIL_CLOSED']:
        pct = frequencies.get(outcome, 0.0) * 100
        print(f"  {outcome:12s}: {counts[outcome]:3d} ({pct:5.2f}%)")
    print()
    print(f"Entropy: {entropy:.4f} bits (max 1.585 for uniform 3-way)")
    print(f"Admissible region volume estimate: {admissible_volume*100:.2f}%")
    if mean_proximity:
        print(f"DENY boundary proximity — mean I(x'): {mean_proximity:.6f}")
    print()
    print("REALITY SCALAR (this run):")
    if mean_scalar:
        print(f"  Mean scalar: {mean_scalar:.4f} → {reality_label(mean_scalar)}")
        print(f"  Range: [{min_scalar:.4f}, {max_scalar:.4f}]")
        print(f"  Variance: {var_scalar:.6f}")
    print()
    print("SCALAR BY OUTCOME:")
    for outcome in ['ALLOW', 'DENY', 'FAIL_CLOSED']:
        stats = scalar_stats.get(outcome)
        if stats:
            label = reality_label(stats['mean'])
            print(f"  {outcome:12s}: mean={stats['mean']:.4f} ({label})  n={stats['count']}")
        else:
            print(f"  {outcome:12s}: no samples")
    print()
    print("CUMULATIVE (all runs):")
    print(f"  Total runs: {cumulative['total_runs']}")
    print(f"  Total samples: {cumulative['total_samples']}")
    for outcome in ['ALLOW', 'DENY', 'FAIL_CLOSED']:
        cum_count = cumulative['cumulative_counts'][outcome]
        cum_pct = cumulative['cumulative_frequencies'][outcome] * 100
        print(f"  {outcome:12s}: {cum_count:4d} ({cum_pct:5.2f}%)")
    print(f"  Cumulative entropy: {cumulative['cumulative_entropy']:.4f}")
    print("=" * 70)

    return {
        'test': 'governance_random_sweep_randomized',
        'mode': 'enforced',
        'seed': seed,
        'samples': samples_per_phase,
        'counts': counts,
        'frequencies': frequencies,
        'entropy': entropy,
        'admissible_volume_estimate': admissible_volume,
        'scalar': {
            'mean': mean_scalar,
            'min': min_scalar,
            'max': max_scalar,
            'variance': var_scalar,
            'by_outcome': scalar_by_outcome
        },
        'boundary_proximity': run_record['boundary_proximity'],
        'results': results,
        'cumulative': cumulative
    }

# === CLI ===

def main():
    parser = argparse.ArgumentParser(description='Randomized Governance Sweep with Reality Scalar')
    parser.add_argument('--samples', type=int, default=100, help='Samples per phase')
    parser.add_argument('--seed', type=int, default=None, help='Random seed')
    parser.add_argument('--stats', type=str, default='sweep_statistics.json', help='Cumulative stats file')
    args = parser.parse_args()

    result = run_randomized_sweep(
        samples_per_phase=args.samples,
        seed=args.seed,
        stats_path=args.stats
    )

    with open('sweep_randomized_results.json', 'w') as f:
        json.dump(result, f, indent=2)

    print("
Detailed results saved to: sweep_randomized_results.json")
    print("Cumulative statistics saved to: sweep_statistics.json")

if __name__ == '__main__':
    main()
