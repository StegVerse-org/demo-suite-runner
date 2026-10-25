cd scripts
python -c "
from receipt_id import init_session, get_receipt, reset_session, ReceiptGenerator
reset_session()
init_session('test-seed-001', 'deterministic')
r1 = get_receipt({'action': 'test'}, 'GCAT')
assert r1.startswith('REC-GCAT-'), f'Bad format: {r1}'
r2 = get_receipt({'action': 'test'}, 'GCAT')
assert r1 != r2, f'Collision: {r1} == {r2}'
r3 = get_receipt({'action': 'other'}, 'BCAT')
assert r3.startswith('REC-BCAT-')
gen = ReceiptGenerator('val-seed')
assert gen.validate_format('REC-GCAT-123-abc')
assert not gen.validate_format('BAD-FORMAT')
print('=== RECEIPT ID TESTS PASSED ===')
"
