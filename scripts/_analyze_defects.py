import gzip
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

# Read latest run state
with gzip.open(r'c:\Users\11428\Desktop\ralph\.trae\runs\run_a6f3f6cf\state.json.gz', 'rt', encoding='utf-8') as f:
    state = json.load(f)

defects = state.get('defects', [])
print(f'=== run_a6f3f6cf (6 iterations) ===')
print(f'Total defects: {len(defects)}')

type_counts = {}
for d in defects:
    t = d.get('bug_type', 'Unknown')
    type_counts[t] = type_counts.get(t, 0) + 1
print(f'Type distribution: {type_counts}')

# Check deduplication
unique_cases = set(d.get('case_id', '') for d in defects)
print(f'Unique case_ids: {len(unique_cases)}')

# Compare with previous run
try:
    with gzip.open(r'c:\Users\11428\Desktop\ralph\.trae\runs\run_5af0cc02\state.json.gz', 'rt', encoding='utf-8') as f:
        state2 = json.load(f)
    defects2 = state2.get('defects', [])
    print(f'\n=== run_5af0cc02 (3 iterations) ===')
    print(f'Total defects: {len(defects2)}')
    type_counts2 = {}
    for d in defects2:
        t = d.get('bug_type', 'Unknown')
        type_counts2[t] = type_counts2.get(t, 0) + 1
    print(f'Type distribution: {type_counts2}')
    unique_cases2 = set(d.get('case_id', '') for d in defects2)
    print(f'Unique case_ids: {len(unique_cases2)}')
    
    # Check overlap
    overlap = unique_cases & unique_cases2
    print(f'\n=== Comparison ===')
    print(f'Overlapping defects: {len(overlap)}')
    print(f'New in 6-iter: {len(unique_cases - unique_cases2)}')
    print(f'Only in 3-iter: {len(unique_cases2 - unique_cases)}')
except Exception as e:
    print(f'Failed to read previous run: {e}')

# Check iteration field if exists
print(f'\n=== Iteration analysis ===')
iter_field = None
for d in defects:
    if 'iteration' in d:
        iter_field = 'iteration'
        break
    if 'found_at_iteration' in d:
        iter_field = 'found_at_iteration'
        break

if iter_field:
    iter_counts = {}
    for d in defects:
        it = d.get(iter_field, 'unknown')
        iter_counts[it] = iter_counts.get(it, 0) + 1
    print(f'Defects by iteration: {iter_counts}')
else:
    print('No iteration field found in defects')
