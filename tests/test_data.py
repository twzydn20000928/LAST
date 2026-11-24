import copy,json
from pathlib import Path
import pytest
from last.data import validate

def test_primary_allocation_and_invalid_seed():
    path=Path(__file__).resolve().parents[1]/'configs/primary_manifest.json'
    manifest=json.loads(path.read_text(encoding='utf-8'))
    summary=validate(manifest)
    assert summary['prompt_slots']==88 and summary['unique_prompt_texts']==84
    bad=copy.deepcopy(manifest);bad['samples'][0]['seed']+=1
    with pytest.raises(ValueError,match='assignment'):validate(bad)
    first, second = manifest['samples'][:2]
    first['id'], second['id'] = second['id'], first['id']
    with pytest.raises(ValueError, match='frozen index'):
        validate(manifest)
