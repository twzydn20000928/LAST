import json,hashlib
import pytest
from pathlib import Path
from collections import defaultdict
from last.quality_inputs import build,verified_video

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
    row=manifest['samples'][0]
    case=json.dumps(dict(prompt=row['prompt'],seed=row['seed'],video_id=row['id'])).encode()
    (folder/'case.json').write_bytes(case)
    (folder/'receipt.json').write_text(json.dumps(dict(status='completed',family='hunyuan',mode='i2v',method='last',seed=row['seed'],case_sha256=hashlib.sha256(case).hexdigest(),marked_sha256=hashlib.sha256(b'fixture').hexdigest())))
    files,report=build(manifest,meta,runs,'hunyuan','i2v','last')
    assert not report['complete'] and sum(c['expected'] for c in report['coverage'].values())==400
    assert sum(c['available'] for c in report['coverage'].values())==1
    assert report['coverage']['Diversity']['expected']==60
    assert files['Camera_Motion'][0]['auxiliary_question']=='keep exact question'
    folder.rename(folder.with_name('paper-001'))
    with pytest.raises(ValueError,match='frozen manifest'):
        build(manifest,meta,runs,'hunyuan','i2v','last')


def test_replaced_quality_video_is_rejected(tmp_path):
    (tmp_path/'marked.mp4').write_bytes(b'original')
    record={'video_sha256':hashlib.sha256(b'original').hexdigest()}
    (tmp_path/'receipt.json').write_text(json.dumps(record))
    assert verified_video(tmp_path,record)[1]['kind']=='generation'
    (tmp_path/'marked.mp4').write_bytes(b'replaced')
    with pytest.raises(ValueError,match='changed'):verified_video(tmp_path,record)


def test_legacy_reference_requires_existing_matching_pair(tmp_path):
    (tmp_path/'reference.mp4').write_bytes(b'ref')
    (tmp_path/'marked.mp4').write_bytes(b'marked')
    record={'marked_sha256':hashlib.sha256(b'marked').hexdigest()}
    (tmp_path/'receipt.json').write_text(json.dumps(record))
    with pytest.raises(ValueError,match='lacks recorded'):verified_video(tmp_path,record,True)
    pair=dict(marked_sha256=record['marked_sha256'],reference_sha256=hashlib.sha256(b'ref').hexdigest())
    (tmp_path/'quality.json').write_text(json.dumps(pair))
    assert verified_video(tmp_path,record,True)[1]['kind']=='paired_fidelity'
    (tmp_path/'marked.mp4').write_bytes(b'other')
    with pytest.raises(ValueError,match='different marked'):verified_video(tmp_path,record,True)


def test_recorded_reference_cannot_be_replaced(tmp_path):
    (tmp_path/'reference.mp4').write_bytes(b'ref')
    record={'reference_sha256':hashlib.sha256(b'ref').hexdigest()}
    (tmp_path/'receipt.json').write_text(json.dumps(record))
    verified_video(tmp_path,record,True)
    (tmp_path/'reference.mp4').write_bytes(b'other')
    with pytest.raises(ValueError):verified_video(tmp_path,record,True)
