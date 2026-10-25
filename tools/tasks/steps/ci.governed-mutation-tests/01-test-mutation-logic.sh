cd scripts
python -c "
from receipt_id import reset_session, init_session
from governed_action import create_gate
from governed_mutation import GovernedMutation
reset_session()
init_session('mutation-test', 'deterministic')
gate = create_gate('GCAT')
mutator = GovernedMutation(gate, {'key1': 'initial_value'})
result = mutator.mutate('update', 'key1', 'new_value')
assert result['receipt_id'].startswith('REC-')
if result['result'].value == 'ALLOW':
    assert mutator.get_state_snapshot()['key1'] == 'new_value'
    success = mutator.rollback(result['receipt_id'])
    assert success
    assert mutator.get_state_snapshot()['key1'] == 'initial_value'
query_result = mutator.query('key1')
assert query_result['receipt_id'].startswith('REC-')
assert len(mutator.mutation_log) > 0
print('=== GOVERNED MUTATION TESTS PASSED ===')
"
