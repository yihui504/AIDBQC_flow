import gzip
import json

data = json.loads(gzip.open('.trae/runs/run_b2d70730/state.json.gz').read())
defects = data.get('defects', [])
failed = [d for d in defects if d.get('verification_status') == 'failed']

print(f'Total defects: {len(defects)}')
print(f'Failed defects: {len(failed)}')

print('\nDefects:')
for d in defects[:10]:
    print(f"  Case: {d.get('case_id')}, Status: {d.get('verification_status')}")
