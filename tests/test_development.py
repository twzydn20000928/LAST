import json
from collections import Counter
from pathlib import Path
from last.development import select,normalize


def test_development_selection_excludes_primary_and_balances_new_key_slots():
    primary=json.loads((Path(__file__).parents[1]/'configs/primary_manifest.json').read_text())
    existing=primary['samples'][0]['prompt']
    prompts={f'dim{i}':[existing.upper(),f'new prompt {i} a',f'new prompt {i} b'] for i in range(18)}
    result=select(primary,prompts)
    assert result==select(primary,dict(reversed(list(prompts.items()))))
    rows=result['samples'];assert len(rows)==80
    assert len({r['prompt'] for r in rows})==20
    assert all(normalize(r['prompt'])!=normalize(existing) for r in rows)
    assert Counter(r['key_slot'] for r in rows)==dict.fromkeys(range(8),10)
    assert len({r['seed'] for r in rows})==80
