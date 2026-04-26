#!/usr/bin/env python3
"""
entity_classifier.py -- Entity Classification by Scalar Oscillation

Classifies entities as life or non-life based on their scalar time series.
Life is defined as sustained oscillation within the viable band [0.3, 0.7].

Entity types:
  quantum event:     s~0, omega->inf     -- not life (too fast)
  neural entity:     s~0.2, omega~1Hz    -- life (human-scale)
  static entity:     s~0.5, omega~0      -- not life (no oscillation)
  sloth:             s~0.5, omega~0.01Hz -- life (slow oscillation)
  AI entity:         s~0.8, omega~10^9Hz -- life-like (fast, narrow)
  black hole:        s=0.5, A=0          -- not life (frozen)
"""

import math
from scalar_engine import reality_label, gap_efficiency

# Life band definition
LIFE_MIN = 0.3
LIFE_MAX = 0.7
MIN_AMPLITUDE = 0.001
MIN_FREQUENCY = 0.001
MIN_VARIANCE = 0.0001


def fit_oscillation(scalar_history):
    """
    Fit scalar history to: s(t) = 0.5 + A * sin(omega*t + phi)

    Uses simple period detection and amplitude estimation.
    Returns (A, omega, phi) or (0, 0, 0) if no oscillation detected.
    """
    if len(scalar_history) < 3:
        return 0.0, 0.0, 0.0

    n = len(scalar_history)
    mean_s = sum(scalar_history) / n

    # Amplitude: half the range
    A = (max(scalar_history) - min(scalar_history)) / 2.0

    # Frequency: count zero-crossings around mean
    zero_crossings = 0
    for i in range(1, n):
        if (scalar_history[i-1] - mean_s) * (scalar_history[i] - mean_s) < 0:
            zero_crossings += 1

    # Period ~ n / (zero_crossings / 2) samples per cycle
    if zero_crossings > 0:
        period = n / (zero_crossings / 2.0)
        omega = 2 * math.pi / period if period > 0 else 0.0
    else:
        omega = 0.0

    # Phase: estimated from first point
    if A > MIN_AMPLITUDE:
        phi = math.asin((scalar_history[0] - 0.5) / A) if abs((scalar_history[0] - 0.5) / A) <= 1 else 0.0
    else:
        phi = 0.0

    return A, omega, phi


def classify_entity(scalar_history):
    """
    Classify entity from scalar time series.

    Returns dict with:
      - classification: 'life' or 'non-life'
      - life_category: reality label if life, None otherwise
      - amplitude, frequency, phase
      - mean_scalar, variance
      - gap_efficiency
    """
    if not scalar_history:
        return {
            'classification': 'non-life',
            'life_category': None,
            'amplitude': 0.0,
            'frequency': 0.0,
            'phase': 0.0,
            'mean_scalar': 0.5,
            'variance': 0.0,
            'gap_efficiency': 0.0
        }

    A, omega, phi = fit_oscillation(scalar_history)
    mean_s = sum(scalar_history) / len(scalar_history)

    # Variance
    if len(scalar_history) > 1:
        variance = sum((s - mean_s)**2 for s in scalar_history) / len(scalar_history)
    else:
        variance = 0.0

    # Life classification
    is_life = (
        LIFE_MIN <= mean_s <= LIFE_MAX and
        A > MIN_AMPLITUDE and
        omega > MIN_FREQUENCY and
        variance > MIN_VARIANCE
    )

    return {
        'classification': 'life' if is_life else 'non-life',
        'life_category': reality_label(mean_s) if is_life else None,
        'amplitude': round(A, 6),
        'frequency': round(omega, 6),
        'phase': round(phi, 6),
        'mean_scalar': round(mean_s, 6),
        'variance': round(variance, 6),
        'gap_efficiency': round(gap_efficiency(mean_s), 6)
    }


def compute_life_fraction(entity_results):
    """Fraction of entities classified as life."""
    if not entity_results:
        return 0.0
    life_count = sum(1 for e in entity_results if e.get('classification') == 'life')
    return life_count / len(entity_results)


def entity_type_description(entity):
    """Human-readable description of entity type from scalar signature."""
    s = entity.get('mean_scalar', 0.5)
    omega = entity.get('frequency', 0)
    A = entity.get('amplitude', 0)

    if s == 0.5 and A == 0:
        return "black hole -- frozen, no oscillation"
    elif s < 0.1 and omega > 100:
        return "quantum event -- too fast for life"
    elif 0.15 < s < 0.25 and 0.5 < omega < 10:
        return "neural entity -- human-scale life"
    elif 0.45 < s < 0.55 and 0.001 < omega < 0.1:
        return "sloth -- slow life"
    elif 0.75 < s < 0.85 and omega > 1e6:
        return "AI entity -- fast, narrow life-like"
    elif 0.45 < s < 0.55 and omega == 0:
        return "static entity -- no oscillation, not life"
    else:
        return f"custom entity -- s={s:.3f}, omega={omega:.3f}, A={A:.3f}"


if __name__ == '__main__':
    print("Entity Classifier Test")
    print("=" * 60)

    # Test cases
    test_cases = [
        # Human-like oscillation
        [0.45, 0.48, 0.52, 0.55, 0.53, 0.50, 0.47, 0.45],
        # Static (no oscillation)
        [0.50, 0.50, 0.50, 0.50, 0.50],
        # Quantum (too fast, low mean)
        [0.05, 0.08, 0.03, 0.06, 0.04],
        # Sloth (slow oscillation)
        [0.48, 0.49, 0.50, 0.51, 0.52, 0.51, 0.50, 0.49],
    ]

    for i, history in enumerate(test_cases):
        result = classify_entity(history)
        desc = entity_type_description(result)
        print(f"
Test case {i+1}: {desc}")
        print(f"  Classification: {result['classification']}")
        print(f"  Mean scalar: {result['mean_scalar']}")
        print(f"  Amplitude: {result['amplitude']}")
        print(f"  Frequency: {result['frequency']}")
        print(f"  Variance: {result['variance']}")
