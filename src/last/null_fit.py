"""Fit the disclosed energy reconstruction only from all80 audited LAST clips."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import numpy as np
from .development import validate_development
from .energy_calibration import fit
from .feature_cache import load, sha


def validate_index(index, development, primary):
    validate_development(development, primary)
    expected={x['id'] for x in development['samples']}
    ids=[x['video_id'] for x in index]
    if len(ids)!=80 or len(set(ids))!=80 or set(ids)!=expected:
        raise ValueError('Require exactly all80 development videos, without duplicates or test IDs')


def fit_files(index, development_path, primary_path, development_state, primary_state):
    read=lambda p:json.loads(Path(p).read_text())
    dev,primary=read(development_path),read(primary_path)
    validate_index(index,dev,primary)
    fingerprints={};real=[]
    for state,manifest in ((Path(development_state),development_path),(Path(primary_state),primary_path)):
        if read(state/'state.json')['manifest_sha256']!=sha(manifest):
            raise ValueError('Private registry belongs to another manifest')
        fingerprints[str(state/'state.json')]=sha(state/'state.json')
        for slot in range(8):
            path=state/'keys'/f'{slot:02}.key';key=path.read_bytes()
            if len(key)!=32:raise ValueError('Malformed real key')
            real.append(hashlib.sha256(key).hexdigest());fingerprints[str(path)]=sha(path)
    if len(set(real))!=16:raise ValueError('Development and primary keys overlap')
    real=sorted(real);arrays=[];ids=[];common=None;records=[]
    rows={x['id']:x for x in dev['samples']}
    for item in index:
        run,cache,response=map(Path,(item['run'],item['features'],item['responses']))
        video=run/'marked.mp4';g=read(run/'receipt.json');case=read(run/'case.json');row=rows[item['video_id']]
        if g['status']!='completed' or g['method']!='last' or g['mode']!='i2v' or g['marked_sha256']!=sha(video):
            raise ValueError('Require completed LAST I2V generation and unchanged video')
        if g.get('mu')!=.5 or g.get('fixed_target') is not False or g.get('uniform_profile') is not False:
            raise ValueError('Require the unchanged LAST operating point')
        if any(case.get(k)!=row[v] for k,v in (('video_id','id'),('seed','seed'),('prompt','prompt'),('key_slot','key_slot'))):
            raise ValueError('Generation does not match development sample')
        if case.get('development_manifest_sha256')!=sha(development_path) or g.get('case_sha256')!=sha(run/'case.json'):
            raise ValueError('Unbound development case')
        expected_key=Path(development_state)/'keys'/f"{row['key_slot']:02}.key"
        if sha(run/'secret.key')!=sha(expected_key):raise ValueError('Generation key differs from registered development slot')
        fingerprints[str(run/'secret.key')]=sha(run/'secret.key')
        values,nodes,features=load(cache,video);r=read(response/'receipt.json')
        if r['status']!='completed' or r['video_sha256']!=sha(video) or r['energies_sha256']!=sha(response/'energies.npy'):
            raise ValueError('Invalid null-response artifacts')
        inputs=r['input_sha256']
        for path in (video,cache/'receipt.json',cache/'features.npy',cache/'nodes.json'):
            if inputs.get(str(path.resolve()))!=sha(path):raise ValueError('Responses are not bound to this feature cache')
        if any(sha(Path(path))!=digest for path,digest in inputs.items()):raise ValueError('Null acquisition input changed')
        evidence=r['evidence'];wrong=evidence['wrong_key_sha256']
        if len(wrong)!=64 or len(set(wrong))!=64 or set(wrong)&set(real) or evidence['excluded_real_key_sha256']!=real:
            raise ValueError('Incomplete or inconsistent wrong-key exclusion registry')
        signature=dict(family=g['family'],writer_source=g['source_sha256'],generation_settings=g['settings'],feature_family=features['family'],reader=features['reader'],scan=features['scan'],vae=features['vae_files_sha256'],feature_source=features['source_sha256'],null_source=r['source_sha256'],wrong_keys=wrong)
        if signature['family']!=signature['feature_family'] or signature['reader']!='ccta' or not signature['scan']:
            raise ValueError('Expected matching family and full CCTA candidate scan')
        if common is None:common=signature
        elif signature!=common:raise ValueError('Mixed model, reader, source or wrong-key bank')
        energies=np.load(response/'energies.npy',allow_pickle=False)
        if energies.shape!=(len(nodes),64,16):raise ValueError('Candidate/null dimensions differ')
        arrays.append(energies);ids.extend([item['video_id']]*len(values))
        for path in (video,run/'receipt.json',run/'case.json',cache/'receipt.json',cache/'features.npy',cache/'nodes.json',response/'receipt.json',response/'energies.npy'):
            fingerprints[str(path)]=sha(path)
        fingerprints.update(inputs)
        records.append(dict(video_id=item['video_id'],video_sha256=sha(video),response_receipt_sha256=sha(response/'receipt.json')))
    result=fit(np.concatenate(arrays),ids,dev,primary)
    if any(sha(Path(p))!=h for p,h in fingerprints.items()):raise ValueError('Input changed during fit')
    result.update(acquisition_audited=True,inputs=records,shared_protocol=common,
                  development_manifest_sha256=sha(development_path),primary_manifest_sha256=sha(primary_path),
                  scope='All80 audited development acquisition fitted; explicit median/MAD reconstruction, not original-author formula or test/AUROC validation')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('index','development','primary','development-state','primary-state','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();os.umask(0o077)
    result=fit_files(json.loads(a.index.read_text()),a.development,a.primary,a.development_state,a.primary_state)
    with a.output.open('x') as f:json.dump(result,f,indent=2)


if __name__=='__main__':main()
