import json
from pathlib import Path
import pytest
from last.null_fit import validate_index,fit_files
from last.feature_cache import sha
import hashlib
import numpy as np


def test_partial_duplicate_or_test_ids_rejected_before_file_access():
    root=Path(__file__).resolve().parents[1]/'configs'
    devpath=root/'development_manifest.json';primarypath=root/'primary_manifest.json'
    dev=json.loads(devpath.read_text());primary=json.loads(primarypath.read_text())
    index=[dict(video_id=r['id']) for r in dev['samples']]
    validate_index(index,dev,primary)
    for bad in (index[:-1],index[:-1]+[index[0]],index[:-1]+[dict(video_id='paper-000')]):
        with pytest.raises(ValueError,match='all80'):
            fit_files(bad,devpath,primarypath,'nonexistent-development','nonexistent-primary')


@pytest.fixture
def acquisition(tmp_path):
    # Synthetic files exercise provenance/aggregation only; no generated videos
    # or real QR projections are claimed by this test.
    configs=Path(__file__).resolve().parents[1]/'configs'
    devpath=configs/'development_manifest.json';primarypath=configs/'primary_manifest.json'
    dev=json.loads(devpath.read_text());states=[];real=[]
    dump=lambda p,v:p.write_text(json.dumps(v))
    for split,manifest,offset in [('dev',devpath,1),('primary',primarypath,9)]:
        state=tmp_path/split;(state/'keys').mkdir(parents=True)
        dump(state/'state.json',dict(manifest_sha256=sha(manifest)))
        for slot in range(8):
            key=(offset+slot).to_bytes(32,'big');(state/'keys'/f'{slot:02}.key').write_bytes(key)
            real.append(hashlib.sha256(key).hexdigest())
        states.append(state)
    wrong=[hashlib.sha256(i.to_bytes(32,'big')).hexdigest() for i in range(100,164)]
    index=[]
    for row in dev['samples']:
        base=tmp_path/row['id'];run=base/'run';cache=base/'cache';response=base/'response'
        for p in (run,cache,response):p.mkdir(parents=True)
        (run/'marked.mp4').write_bytes(('synthetic-'+row['id']).encode())
        (run/'secret.key').write_bytes((states[0]/'keys'/f"{row['key_slot']:02}.key").read_bytes())
        dump(run/'case.json',dict(video_id=row['id'],prompt=row['prompt'],seed=row['seed'],key_slot=row['key_slot'],development_manifest_sha256=sha(devpath)))
        dump(run/'receipt.json',dict(status='completed',method='last',mode='i2v',family='hunyuan',mu=.5,fixed_target=False,uniform_profile=False,marked_sha256=sha(run/'marked.mp4'),case_sha256=sha(run/'case.json'),source_sha256='synthetic-writer',settings={'steps':50}))
        np.save(cache/'features.npy',np.ones((1,1776),np.float32));dump(cache/'nodes.json',[[0,0]])
        dump(cache/'receipt.json',dict(status='completed',video_sha256=sha(run/'marked.mp4'),family='hunyuan',reader='ccta',scan=True,vae_files_sha256={'model':'synthetic'},source_sha256={'feature':'synthetic'},files_sha256={n:sha(cache/n) for n in ('features.npy','nodes.json')}))
        energies=np.broadcast_to(np.linspace(1,3,64)[None,:,None],(1,64,16)).copy()
        np.save(response/'energies.npy',energies)
        inputs={str(p.resolve()):sha(p) for p in (run/'marked.mp4',cache/'receipt.json',cache/'features.npy',cache/'nodes.json')}
        dump(response/'receipt.json',dict(status='completed',video_sha256=sha(run/'marked.mp4'),energies_sha256=sha(response/'energies.npy'),input_sha256=inputs,source_sha256={'null':'synthetic'},evidence=dict(wrong_key_sha256=wrong,excluded_real_key_sha256=sorted(real))))
        index.append(dict(video_id=row['id'],run=str(run),features=str(cache),responses=str(response)))
    return index,devpath,primarypath,*states


def test_complete_artifact_flow_fits_expected_center(acquisition):
    result=fit_files(*acquisition)
    assert result['acquisition_audited'] and result['reconstruction']
    assert len(result['videos'])==80 and len(result['inputs'])==80
    assert np.allclose(result['center'],2.)


@pytest.mark.parametrize('kind',['video','key','features','energies','profile','wrong_registry'])
def test_changed_artifact_or_protocol_rejected(acquisition,kind):
    item=acquisition[0][0];run=Path(item['run']);cache=Path(item['features']);response=Path(item['responses'])
    paths={'video':run/'marked.mp4','key':run/'secret.key','features':cache/'features.npy','energies':response/'energies.npy'}
    if kind in paths:
        with paths[kind].open('ab') as f:f.write(b'changed')
    elif kind=='profile':
        p=run/'receipt.json';r=json.loads(p.read_text());r['mu']=1.;p.write_text(json.dumps(r))
    else:
        p=response/'receipt.json';r=json.loads(p.read_text());r['evidence']['excluded_real_key_sha256']=[];p.write_text(json.dumps(r))
    with pytest.raises(ValueError):fit_files(*acquisition)
