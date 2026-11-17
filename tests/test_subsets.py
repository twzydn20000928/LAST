import json
from pathlib import Path
from last.subsets import select

def test_subsets_are_metadata_only_balanced_and_unique():
    manifest=json.loads((Path(__file__).parents[1]/'configs/primary_manifest.json').read_text())
    ids=select(manifest);assert ids==select(manifest) and len(set(ids))==30
    rows={r['id']:r for r in manifest['samples']}
    assert len({rows[i]['dimension'] for i in ids})==18
    for row in manifest['samples']:row['irrelevant_measured_score']=0.01
    assert ids==select(manifest)
