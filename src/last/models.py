"""Acquire pinned checkpoints and hash local files without publishing weights."""
import argparse,hashlib,json
from pathlib import Path

def file_hash(path):
    digest=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):digest.update(block)
    return digest.hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--catalog',type=Path,default=Path('configs/models.json'));p.add_argument('--name',required=True);p.add_argument('--directory',type=Path,required=True);p.add_argument('--download',action='store_true');p.add_argument('--hash-output',type=Path);a=p.parse_args()
    spec=json.loads(a.catalog.read_text())[a.name]
    if a.download:
        from huggingface_hub import snapshot_download
        snapshot_download(repo_id=spec['repo'],revision=spec['revision'],local_dir=a.directory)
    for required in ['model_index.json','vae/config.json','scheduler/scheduler_config.json']:
        if not (a.directory/required).is_file():raise FileNotFoundError(a.directory/required)
    report=dict(model=a.name,repository=spec['repo'],requested_revision=spec['revision'],note='Local hashes record files; they do not by themselves prove correspondence to the requested upstream revision.')
    if a.hash_output:
        files=sorted(p for p in a.directory.rglob('*') if p.is_file() and '.cache' not in p.relative_to(a.directory).parts and '.git' not in p.relative_to(a.directory).parts)
        report['files']=[dict(path=p.relative_to(a.directory).as_posix(),bytes=p.stat().st_size,sha256=file_hash(p)) for p in files]
        a.hash_output.parent.mkdir(parents=True,exist_ok=True);a.hash_output.write_text(json.dumps(report,indent=2))
        print(json.dumps(dict(model=a.name,files=len(files),hash_output=str(a.hash_output))))
    else:print(json.dumps(report))
if __name__=='__main__':main()
