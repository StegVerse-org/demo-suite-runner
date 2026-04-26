#!/usr/bin/env python3
"""Test gap_instrument.py"""
import sys
sys.path.insert(0, '../scripts')
from gap_instrument import GapLedger, compute_coherence_budget, compute_entropy_debt

def test_ledger():
    ledger = GapLedger()
    ledger.add_operation('test', True, 0.5, 0.01)
    ledger.commit('ALLOW')
    stats = ledger.get_stats()
    assert stats['status'] == 'committed'
    assert stats['negotiation_depth'] == 1
    print("PASS: gap ledger")

def test_coherence():
    before = {'g': 0.3, 'c': 0.3, 'a': 0.2, 't': 0.2}
    after = {'g': 0.3, 'c': 0.3, 'a': 0.2, 't': 0.2}
    assert compute_coherence_budget(before, after) > 0.9, "identical states should have high coherence"
    print("PASS: coherence budget")

if __name__ == '__main__':
    test_ledger()
    test_coherence()
    print("All gap_instrument tests passed")
