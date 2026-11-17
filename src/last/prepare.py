"""Create reader-owned private keys/messages for a fixed manifest, once."""
import argparse,hashlib,json,os,secrets
from pathlib import Path
from .data import validate

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    manifest=json.loads(a.manifest.read_text());validate(manifest)
    os.umask(0o077);a.output.mkdir(parents=True,exist_ok=False,mode=0o700)
    keys=a.output/'keys';keys.mkdir(mode=0o700)
    messages=a.output/'messages';messages.mkdir(mode=0o700)
    for slot in range(8):(keys/f'{slot:02}.key').write_bytes(secrets.token_bytes(32))
    for row in manifest['samples']:(messages/(row['id']+'.bin')).write_bytes(secrets.token_bytes(64))
    protocol=dict(schema_version=1,manifest_sha256=hashlib.sha256(a.manifest.read_bytes()).hexdigest(),keys=8,messages=400,information_bits=512,message_format='64bytes MSB-first',assignment='manifest.key_slot',reuse='Same keys/messages across methods and backbones; never regenerate during a comparison')
    (a.output/'state.json').write_text(json.dumps(protocol,indent=2))
    print(json.dumps(dict(created=str(a.output),keys=8,messages=400,note='Private directory; keep outside the repository and back it up securely.')))
if __name__=='__main__':main()
