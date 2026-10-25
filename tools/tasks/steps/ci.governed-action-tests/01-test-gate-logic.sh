cd scripts
python -c "
from receipt_id import reset_session, init_session
from governed_action import create_gate, GateResult
reset_session()
init_session('gate-test', 'deterministic')
gate = create_gate('GCAT')
result = gate.evaluate({'action': 'query', 'payload': {'data': 'test'}})
assert result['receipt_id'].startswith('REC-')
assert result['result'] == GateResult.ALLOW
assert 0 <= result['confidence'] <= 1
assert len(result['reasoning']) > 0
result2 = gate.evaluate({'invalid': 'input'})
assert result2['result'] == GateResult.FAIL_CLOSED
assert result2['receipt_id'].startswith('REC-')
assert len(gate.history) >= 2
print('=== GOVERNED ACTION TESTS PASSED ===')
"
