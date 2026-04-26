#!/usr/bin/env python3
"""Test cosmological_mode.py"""
import sys
sys.path.insert(0, '../scripts')
from cosmological_mode import run_cosmological_integral, test_convergence

def test_basic():
    result = run_cosmological_integral(samples_per_scalar=20, seed=42)
    assert 'energy_budget' in result
    assert 'life_fraction' in result
    om = result['energy_budget']['ordinary_matter']
    assert 0.0 <= om <= 1.0, "omega_matter should be in [0,1]"
    print(f"PASS: cosmological integral (Om={om*100:.2f}%)")

def test_convergence():
    result = test_convergence(sample_sizes=[50, 100], seed=42)
    assert 'convergence_series' in result
    print(f"PASS: convergence test (CV_om={result['coefficient_of_variation']['omega_matter']:.3f})")

if __name__ == '__main__':
    test_basic()
    test_convergence()
    print("All cosmological_mode tests passed")
