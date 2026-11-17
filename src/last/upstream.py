"""Acquire/verify unchanged baseline Python files against pinned Git blob IDs."""
import argparse,hashlib,json,urllib.request
from pathlib import Path

def verify(root,manifest):
    root=Path(root).resolve()
    for entry in manifest['files']:
        target=(root/entry['path']).resolve()
        if not target.is_relative_to(root):raise ValueError('Unsafe upstream path')
        raw=target.read_bytes();blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        if blob!=entry['sha']:raise ValueError(f'Upstream source changed:{entry["path"]}')
    return dict(commit=manifest['commit'],verified_files=len(manifest['files']))

def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,default=Path('configs/sigmark_source_manifest.json'));p.add_argument('--directory',type=Path,required=True);p.add_argument('--download',action='store_true');a=p.parse_args()
    manifest=json.loads(a.manifest.read_text());root=a.directory.resolve()
    if a.download:
        for entry in manifest['files']:
            target=(root/entry['path']).resolve()
            if not target.is_relative_to(root):raise ValueError('Unsafe upstream path')
            if target.exists():continue
            url=f"https://raw.githubusercontent.com/JeremyZhao1998/SIGMark-release/{manifest['commit']}/{entry['path']}"
            with urllib.request.urlopen(url,timeout=120) as response:raw=response.read()
            actual=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
            if actual!=entry['sha']:raise ValueError('Downloaded blob checksum mismatch')
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    print(json.dumps(verify(root,manifest)))
if __name__=='__main__':main()
