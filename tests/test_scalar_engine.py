#!/usr/bin/env python3
"""Test scalar_engine.py"""
import sys
sys.path.insert(0, '../scripts')
from scalar_engine import compute_scalar, reality_label, gap_efficiency, compute_scale

def test_edge_cases():
    # g-a edge
    state = {'g': 0.5, 'c': 0.0, 'a': 0.5, 't': 0.0}
    assert compute_scalar(state) == 0.0, "g-a edge should be 0.0"

    # c-t edge
    state = {'g': 0.0, 'c': 0.5, 'a': 0.0, 't': 0.5}
    assert compute_scalar(state) == 1.0, "c-t edge should be 1.0"

    # Corner
    state = {'g': 1.0, 'c': 0.0, 'a': 0.0, 't': 0.0}
    assert compute_scalar(state) == 0.5, "corner should be 0.5"

    print("PASS: edge cases")

def test_interior():
    state = {'g': 0.25, 'c': 0.25, 'a': 0.25, 't': 0.25}
    s = compute_scalar(state)
    assert 0.0 <= s <= 1.0, "interior scalar should be in [0,1]"
    print(f"PASS: interior scalar = {s:.4f}")

def test_labels():
    assert reality_label(0.05) == "quantum-contracted"
    assert reality_label(0.50) == "classical-critical"
    assert reality_label(0.95) == "astrophysical-expanded"
    print("PASS: reality labels")

if __name__ == '__main__':
    test_edge_cases()
    test_interior()
    test_labels()
    print("All scalar_engine tests passed")
