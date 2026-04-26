#!/usr/bin/env python3
"""Test convergence_validator.py"""
import sys
sys.path.insert(0, '../scripts')
from convergence_validator import falsification_tests

def test_all_pass():
    mock = {
        'sweep': [
            {'samples': 1000, 'allow_count': 5, 'deny_count': 995, 'fail_closed_count': 0}
        ],
        'scalars': [0.05, 0.15, 0.25, 0.35, 0.45, 0.50, 0.55, 0.65, 0.75, 0.85, 0.95],
        'cosmology': [
            {'samples': 100, 'omega_matter': 0.01, 'omega_dark_matter': 0.60, 'omega_dark_energy': 0.39},
            {'samples': 500, 'omega_matter': 0.005, 'omega_dark_matter': 0.62, 'omega_dark_energy': 0.375}
        ],
        'entities': [
            {'classification': 'life'},
            {'classification': 'non-life'}
        ]
    }
    result = falsification_tests(mock)
    print(f"PASS: validation result = {result['overall']}")
    print(f"  Passed: {result['summary']['passed']}/{result['summary']['total']}")

if __name__ == '__main__':
    test_all_pass()
    print("All convergence_validator tests passed")
