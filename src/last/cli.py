import argparse,json,os,secrets
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description='LAST research reproduction utilities')
    s=p.add_subparsers(dest='command',required=True)
    k=s.add_parser('keygen');k.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.command=='keygen':
        a.output.parent.mkdir(parents=True,exist_ok=True)
        fd=os.open(a.output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as f:f.write(secrets.token_bytes(32))
        print(json.dumps({'created':str(a.output),'note':'Keep this file private; never commit it.'}))

if __name__=='__main__':main()
