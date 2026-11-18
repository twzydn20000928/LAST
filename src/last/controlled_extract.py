"""Controlled cached readout; oracle mode is explicitly non-blind (CPU only)."""
import argparse,json,os,time,traceback
from pathlib import Path
import torch
from .feature_cache import load,sha
from .controlled_reader import decode,decode_oracle


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('video','cache','codes','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--reader',choices=['received','ccta','calibrated_energy','oracle'],required=True)
    p.add_argument('--calibration',type=Path)
    a=p.parse_args();os.umask(0o077);torch.set_num_threads(4)
    if (a.reader=='calibrated_energy')!=(a.calibration is not None):p.error('Only calibrated_energy requires --calibration')
    values,nodes,features=load(a.cache,a.video)
    expected=a.reader if a.reader in ('received','oracle') else 'ccta'
    if features['reader']!=expected or (expected=='ccta' and not features['scan']):
        raise ValueError('Reader requires its own correctly constructed candidate cache')
    if expected=='oracle' and features.get('blind') is not False:
        raise ValueError('Oracle cache must disclose true-map assistance')
    codes=torch.load(a.codes,map_location='cpu',weights_only=True)
    if not isinstance(codes,torch.Tensor) or codes.shape!=(16,592,1776) or not torch.isfinite(codes).all():
        raise ValueError('Expected finite16x592x1776 secret codebook')
    calibration=None
    if a.calibration:
        calibration=json.loads(a.calibration.read_text())
        if not calibration.get('acquisition_audited') or len(set(calibration.get('videos',[])))!=80:
            raise ValueError('Require audited full80 development calibration')
        shared=calibration['shared_protocol']
        if (shared['feature_family']!=features['family'] or shared['vae']!=features['vae_files_sha256']
                or shared['feature_source']!=features['source_sha256']):
            raise ValueError('Calibration uses another feature/VAE protocol')
    paths=[a.video,a.codes,a.cache/'receipt.json',a.cache/'features.npy',a.cache/'nodes.json']
    if a.calibration:paths.append(a.calibration)
    fingerprints={str(p.resolve()):sha(p) for p in paths}
    source=Path(__file__).parent
    sources={name:sha(source/name) for name in ('controlled_extract.py','controlled_reader.py','controlled_fusion.py','calibrated_reader.py','energy_calibration.py','ccta.py','coding.py','feature_cache.py')}
    a.output.mkdir(parents=True,exist_ok=False)
    blind=a.reader!='oracle'
    record=dict(status='running',reader=a.reader,blind=blind,input_sha256=fingerprints,source_sha256=sources,
                scope=('Controlled shared-fusion extraction; no truth message or attack map read, not primary performance or authentication'
                       if blind else 'True-map-assisted cached evidence; not blind or primary performance'))
    started=time.monotonic()
    def save():
        record['seconds']=time.monotonic()-started
        temp=a.output/'receipt.tmp';temp.write_text(json.dumps(record,indent=2));temp.replace(a.output/'receipt.json')
    save()
    try:
        corr=torch.einsum('nd,gmd->ngm',torch.from_numpy(values).float(),codes.float())
        if a.reader=='oracle':
            groups=[n['group'] for n in nodes]
            rows=torch.stack([corr[i,g] for i,g in enumerate(groups)]) if groups else corr.new_empty((0,592))
            bits,_,metadata=decode_oracle(rows,groups)
        else:bits,_,metadata=decode(corr,nodes,a.reader,calibration)
        if any(sha(Path(p))!=h for p,h in fingerprints.items()) or any(sha(source/n)!=h for n,h in sources.items()):
            raise ValueError('Inputs or implementation changed during extraction')
        result=a.output/'decoded-private.json';result.write_text(json.dumps(dict(information_bits=bits.tolist())))
        record.update(status='completed',decoded_sha256=sha(result),selection=metadata,candidates=len(nodes));save()
        print(json.dumps(dict(status='completed',candidates=len(nodes),groups=metadata['groups'],blind=blind)))
    except BaseException:
        record.update(status='failed',error=traceback.format_exc());save();raise


if __name__=='__main__':main()
