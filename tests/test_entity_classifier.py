#!/usr/bin/env python3
"""Test entity_classifier.py"""
import sys
sys.path.insert(0, '../scripts')
from entity_classifier import classify_entity, compute_life_fraction

def test_life():
    # Human-like oscillation
    history = [0.45, 0.48, 0.52, 0.55, 0.53, 0.50, 0.47, 0.45]
    result = classify_entity(history)
    assert result['classification'] == 'life', "human-like oscillation should be life"
    print(f"PASS: life classification (A={result['amplitude']:.3f})")

def test_non_life():
    # Static
    history = [0.50, 0.50, 0.50, 0.50, 0.50]
    result = classify_entity(history)
    assert result['classification'] == 'non-life', "static should be non-life"
    print("PASS: non-life classification")

def test_life_fraction():
    entities = [
        classify_entity([0.45, 0.48, 0.52, 0.55]),
        classify_entity([0.50, 0.50, 0.50]),
        classify_entity([0.45, 0.48, 0.52, 0.55])
    ]
    lf = compute_life_fraction(entities)
    assert 0.5 <= lf <= 0.7, "life fraction should be around 2/3"
    print(f"PASS: life fraction = {lf:.2f}")

if __name__ == '__main__':
    test_life()
    test_non_life()
    test_life_fraction()
    print("All entity_classifier tests passed")
