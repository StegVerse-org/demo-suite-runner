python -c "
import json
with open('demo_result.json') as f:
    data = json.load(f)
assert 'seed' in data
assert 'total_tests' in data
total = data['total_tests']
allow = data['allow_count']
deny = data['deny_count']
fail = data['fail_closed_count']
assert total == allow + deny + fail
assert data['statistics']['determinism_check']['collision_free']
pass_nums = [r['pass_num'] for r in data['results']]
assert 1 in pass_nums and 2 in pass_nums and 3 in pass_nums
print(f'Total={total}, ALLOW={allow}, DENY={deny}, FAIL={fail}')
print('=== DEMO SUITE OUTPUT VALIDATED ===')
"
