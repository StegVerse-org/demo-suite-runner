#!/usr/bin/env python3
"""
scalar_engine.py -- Reality-Selector Scalar Computation

Computes the scalar s in [0,1] from any BCAT state.
The scalar measures gap efficiency: how fast the entity closes
the gap between irreversibility and touching reality.

References:
  - docs/origin_drawing.jpg (ground truth)
  - GCAT_BCAT_Formalism_Documentation.txt (full math)
"""

import math

# Physical constants
L_PLANCK = 1.616e-35   # meters
L_HUBBLE = 4.4e26      # meters (Hubble radius)
C_0 = 299792458.0      # m/s (speed of light, gap closure max rate)


def compute_invariant(state):
    """I(x) = g*c + c*a + a*t + t*g"""
    g, c, a, t = state['g'], state['c'], state['a'], state['t']
    return g*c + c*a + a*t + t*g


def lambda_capacity(state):
    """lambda(x) = g * c * a * t"""
    return state['g'] * state['c'] * state['a'] * state['t']


def compute_scalar(state):
    """
    Compute scalar s in [0,1] from BCAT state.

    s = 0.0: quantum-contracted (g-a edge)
    s = 0.5: classical-critical (corner or center)
    s = 1.0: astrophysical-expanded (c-t edge)
    """
    lam = lambda_capacity(state)
    inv = compute_invariant(state)
    lam_max = (0.25)**4  # 1/256

    # On the admissible edges: I(x) = 0
    if inv <= 1e-12:
        if state['g'] > 0 and state['a'] > 0:
            return 0.0   # g-a edge: quantum-contracted
        elif state['c'] > 0 and state['t'] > 0:
            return 1.0   # c-t edge: astrophysical-expanded
        else:
            return 0.5   # corner: maximally ambiguous

    # Interior: compute from lambda/invariant ratio
    lam_norm = lam / lam_max if lam_max > 0 else 0.0
    inv_norm = inv / 0.25   # max invariant at center

    if inv_norm > 0:
        scalar = lam_norm / inv_norm
        scalar = min(1.0, max(0.0, scalar))
    else:
        scalar = 0.5

    return scalar


def reality_label(scalar):
    """Map scalar to human-readable regime."""
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


def gap_efficiency(scalar):
    """
    Compute c_eff = c_0 * |s - 0.5|.
    Maximum at extremes (fast closure), zero at center (frozen).
    """
    return C_0 * abs(scalar - 0.5)


def compute_scale(scalar, alpha=1.0):
    """
    Physical scale as function of scalar.
    s=0.5 -> Planck scale (minimum)
    s=0 or 1 -> Hubble scale (maximum)
    """
    log_ratio = math.log(L_HUBBLE / L_PLANCK)
    exponent = alpha * abs(scalar - 0.5) * log_ratio
    return L_PLANCK * math.exp(exponent)


def shannon_information(state):
    """Information content = -sum(p_i * log2(p_i))."""
    info = 0.0
    for v in state.values():
        if v > 0:
            info -= v * math.log2(v)
    return info


def shannon_entropy(state):
    """Same as information content for probability distributions."""
    return shannon_information(state)


if __name__ == '__main__':
    # Test with sample states
    test_states = [
        {'g': 0.5, 'c': 0.0, 'a': 0.5, 't': 0.0},   # g-a edge
        {'g': 0.0, 'c': 0.5, 'a': 0.0, 't': 0.5},   # c-t edge
        {'g': 0.25, 'c': 0.25, 'a': 0.25, 't': 0.25},  # center
        {'g': 0.4, 'c': 0.3, 'a': 0.2, 't': 0.1},   # interior
    ]

    print("Scalar Engine Test")
    print("=" * 60)
    for state in test_states:
        s = compute_scalar(state)
        label = reality_label(s)
        c_eff = gap_efficiency(s)
        scale = compute_scale(s)
        info = shannon_information(state)
        print(f"g={state['g']:.2f} c={state['c']:.2f} a={state['a']:.2f} t={state['t']:.2f}")
        print(f"  scalar={s:.4f} | {label}")
        print(f"  c_eff={c_eff:.3e} m/s | scale={scale:.3e} m | info={info:.4f}")
        print()
