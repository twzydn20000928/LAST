import json
from pathlib import Path
from collections import defaultdict
from last.quality_inputs import build

def test_quality_preparation_keeps_missing_denominator_and_auxiliary_questions(tmp_path):
    manifest=json.loads((Path(__file__).parents[1]/'configs/primary_manifest.json').read_text())
    prompts=defaultdict(list)
    for r in manifest['samples']:
        if r['prompt'] not in prompts[r['dimension']]:prompts[r['dimension']].append(r['prompt'])
    meta=tmp_path/'metadata'
    for dimension,lines in prompts.items():
        text=meta/'prompt_set/VBench2_aug_prompt'/f'{dimension}.txt';text.parent.mkdir(parents=True,exist_ok=True);text.write_text('\n'.join(lines))
        questions=meta/'prompt_set/meta_info'/f'{dimension}.json';questions.parent.mkdir(parents=True,exist_ok=True);questions.write_text(json.dumps([dict(auxiliary_question='keep exact question') for _ in lines]))
    runs=tmp_path/'runs';folder=runs/'hunyuan/i2v/last/paper-000';folder.mkdir(parents=True)
    (folder/'marked.mp4').write_bytes(b'fixture')
    (folder/'receipt.json').write_text(json.dumps(dict(status='completed',family='hunyuan',mode='i2v',method='last')))
    files,report=build(manifest,meta,runs,'hunyuan','i2v','last')
    assert not report['complete'] and sum(c['expected'] for c in report['coverage'].values())==400
    assert sum(c['available'] for c in report['coverage'].values())==1
    assert report['coverage']['Diversity']['expected']==60
    assert files['Camera_Motion'][0]['auxiliary_question']=='keep exact question'
