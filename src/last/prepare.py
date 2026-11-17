"""Create reader-owned private keys/messages for a fixed manifest, once."""
import argparse,hashlib,json,os,secrets
from pathlib import Path
from .data import validate

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--primary-manifest',type=Path);p.add_argument('--exclude-state',type=Path);a=p.parse_args()
    manifest=json.loads(a.manifest.read_text());excluded_keys=set()
    if manifest.get('split')=='development':
        from .development import validate_development
        if a.primary_manifest is None or a.exclude_state is None:p.error('Development requires --primary-manifest and --exclude-state')
        validate_development(manifest,json.loads(a.primary_manifest.read_text()))
        state=json.loads((a.exclude_state/'state.json').read_text())
        if state['manifest_sha256']!=hashlib.sha256(a.primary_manifest.read_bytes()).hexdigest():raise ValueError('Excluded state is not the primary manifest state')
        excluded_keys={(a.exclude_state/'keys'/f'{slot:02}.key').read_bytes() for slot in range(8)}
        if len(excluded_keys)!=8 or any(len(k)!=32 for k in excluded_keys):raise ValueError('Invalid primary keys')
    else:validate(manifest)
    os.umask(0o077);a.output.mkdir(parents=True,exist_ok=False,mode=0o700)
    keys=a.output/'keys';keys.mkdir(mode=0o700)
    messages=a.output/'messages';messages.mkdir(mode=0o700)
    for slot in range(8):
        key=secrets.token_bytes(32)
        while key in excluded_keys:key=secrets.token_bytes(32)
        (keys/f'{slot:02}.key').write_bytes(key);excluded_keys.add(key)
    for row in manifest['samples']:(messages/(row['id']+'.bin')).write_bytes(secrets.token_bytes(64))
    count=len(manifest['samples'])
    protocol=dict(schema_version=1,manifest_sha256=hashlib.sha256(a.manifest.read_bytes()).hexdigest(),split=manifest.get('split'),keys=8,messages=count,information_bits=512,message_format='64bytes MSB-first',assignment='manifest.key_slot',reuse='Same keys/messages across methods and backbones within this split; never regenerate during a comparison')
    if a.exclude_state:protocol['excluded_primary_state_sha256']=hashlib.sha256((a.exclude_state/'state.json').read_bytes()).hexdigest()
    (a.output/'state.json').write_text(json.dumps(protocol,indent=2))
    print(json.dumps(dict(created=str(a.output),keys=8,messages=count,note='Private directory; keep outside the repository and back it up securely.')))
if __name__=='__main__':main()
