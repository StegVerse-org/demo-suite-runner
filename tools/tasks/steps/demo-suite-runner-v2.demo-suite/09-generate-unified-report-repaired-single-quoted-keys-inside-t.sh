python -c "
import json

report = {
  'version': '2.0',
  'layers_run': {
    'scalar': '${{ github.event.inputs.run_scalar }}' != 'false',
    'gap': '${{ github.event.inputs.run_gap }}' != 'false',
    'entity': '${{ github.event.inputs.run_entity }}' != 'false',
    'cosmology': '${{ github.event.inputs.run_cosmology }}' != 'false',
    'validation': '${{ github.event.inputs.run_validation }}' != 'false'
  }
}

# Load outputs if available
try:
  with open('outputs/scalar_distribution.json') as f:
    report['scalar'] = json.load(f)
except: pass

try:
  with open('outputs/cosmological_report.json') as f:
    report['cosmology'] = json.load(f)
except: pass

with open('outputs/sweep_report_v2.md', 'w') as f:
  f.write('# GCAT/BCAT Demo Suite Report v2.0\n\n')
  f.write(f'**Validation:** {report.get('validation', {}).get('overall', 'N/A')}\n\n')
  f.write('## Energy Budget\n\n')
  if 'cosmology' in report:
    eb = report['cosmology'].get('energy_budget', {})
    for k, v in eb.items():
      f.write(f'- **{k}:** {v*100:.2f}%\n')
  f.write('\n## Life Fraction\n\n')
  if 'cosmology' in report:
    lf = report['cosmology'].get('life_fraction', 0)
    f.write(f'{lf*100:.4f}%\n')

print('Unified report generated')
"
