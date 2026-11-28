"""Acquire pinned checkpoints and hash local files without publishing weights."""
import argparse,hashlib,json
from pathlib import Path

def file_hash(path):
    digest=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):digest.update(block)
    return digest.hexdigest()

def vae_fingerprints(model_directory):
    """Fingerprint the local decoder files used by the supported checkpoints."""
    vae = Path(model_directory) / "vae"
    required = ("config.json", "diffusion_pytorch_model.safetensors")
    if any(not (vae / name).is_file() for name in required):
        raise ValueError(f"Incomplete VAE directory: {vae}")
    return {path.relative_to(vae).as_posix(): file_hash(path)
            for path in sorted(vae.rglob("*"))
            if path.is_file() and not {".git", ".cache"}.intersection(path.relative_to(vae).parts)}


def verify_checkpoint(directory, spec, manifest):
    if (manifest['repository'], manifest['revision']) != (spec['repo'], spec['revision']):
        raise ValueError('Checkpoint manifest and model catalog disagree')
    entries = {entry['path']: entry for entry in manifest['files']}
    local = {p.relative_to(directory).as_posix(): p for p in directory.rglob('*')
             if p.is_file() and not {'.cache', '.git'}.intersection(p.relative_to(directory).parts)}
    missing = sorted(name for name, entry in entries.items() if entry['required'] and name not in local)
    unexpected = sorted(local.keys() - entries.keys())
    if missing or unexpected:
        raise ValueError(f'Checkpoint inventory differs: missing={missing}, unexpected={unexpected}')
    for name, path in local.items():
        entry = entries[name]
        size = path.stat().st_size
        if size != entry['size']:
            raise ValueError(f'Wrong checkpoint file size: {name}')
        expected = entry['lfs_sha256']
        if expected:
            actual = file_hash(path)
        else:
            digest = hashlib.sha1(f'blob {size}\0'.encode())
            digest.update(path.read_bytes())
            actual, expected = digest.hexdigest(), entry['blob_id']
        if actual != expected:
            raise ValueError(f'Checkpoint digest mismatch: {name}')
    return dict(verified_files=len(local), required_files=sum(e['required'] for e in entries.values()))

def main():
    p=argparse.ArgumentParser();p.add_argument('--catalog',type=Path,default=Path('configs/models.json'));p.add_argument('--name',required=True);p.add_argument('--directory',type=Path,required=True);p.add_argument('--download',action='store_true');p.add_argument('--hash-output',type=Path)
    p.add_argument('--verify-manifest', type=Path, help='Compare files to pinned Hugging Face Git and LFS digests')
    p.add_argument('--vae-only', action='store_true', help='Download or inspect only the VAE used for extraction')
    a=p.parse_args()
    spec=json.loads(a.catalog.read_text())[a.name]
    if a.download:
        from huggingface_hub import snapshot_download
        snapshot_download(repo_id=spec['repo'],revision=spec['revision'],local_dir=a.directory,
                          allow_patterns=['vae/*'] if a.vae_only else None)
    required_files = (['vae/config.json', 'vae/diffusion_pytorch_model.safetensors'] if a.vae_only
                      else ['model_index.json','vae/config.json','scheduler/scheduler_config.json'])
    for required in required_files:
        if not (a.directory/required).is_file():raise FileNotFoundError(a.directory/required)
    report=dict(model=a.name,repository=spec['repo'],requested_revision=spec['revision'],note='Local hashes record files; they do not by themselves prove correspondence to the requested upstream revision.')
    scope = a.directory / 'vae' if a.vae_only else a.directory
    if a.vae_only:
        report['scope'] = 'vae'
    if a.verify_manifest:
        manifests = json.loads(a.verify_manifest.read_bytes())
        manifest = manifests[a.name]
        if a.vae_only:
            manifest = dict(manifest, files=[dict(entry, path=entry['path'][4:])
                            for entry in manifest['files'] if entry['path'].startswith('vae/')])
        report['verification'] = verify_checkpoint(scope, spec, manifest)
        report['verification_manifest_sha256'] = file_hash(a.verify_manifest)
    if a.hash_output:
        files=sorted(p for p in scope.rglob('*') if p.is_file() and '.cache' not in p.relative_to(a.directory).parts and '.git' not in p.relative_to(a.directory).parts)
        report['files']=[dict(path=p.relative_to(a.directory).as_posix(),bytes=p.stat().st_size,sha256=file_hash(p)) for p in files]
        a.hash_output.parent.mkdir(parents=True,exist_ok=True);a.hash_output.write_text(json.dumps(report,indent=2))
        print(json.dumps(dict(model=a.name,files=len(files),hash_output=str(a.hash_output))))
    else:print(json.dumps(report))
if __name__=='__main__':main()
