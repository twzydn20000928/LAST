"""Acquire an exact upstream source archive without executing or modifying it."""
import argparse, hashlib, json, shutil, stat, urllib.request, zipfile
from pathlib import Path, PurePosixPath


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(8*1024**2),b''):h.update(block)
    return h.hexdigest()


def unpack(archive, destination, manifest):
    if digest(archive)!=manifest['sha256']:raise ValueError('Source archive checksum mismatch')
    destination=Path(destination).resolve()
    with zipfile.ZipFile(archive) as z:
        entries=[]
        for entry in z.infolist():
            name=PurePosixPath(entry.filename)
            if name.is_absolute() or '..' in name.parts or '\\' in entry.filename or ':' in entry.filename:
                raise ValueError('Unsafe archive path')
            if not name.parts or name.parts[0]!=manifest['archive_root']:
                raise ValueError('Unexpected source archive root')
            if stat.S_ISLNK(entry.external_attr>>16):raise ValueError('Source archive symlink rejected')
            if entry.is_dir():continue
            relative=Path(*name.parts[1:])
            if not relative.parts:raise ValueError('Invalid archive entry')
            target=(destination/relative).resolve()
            if not target.is_relative_to(destination):raise ValueError('Path escaped output')
            entries.append((entry,relative,target))
        if len({str(p) for _,p,_ in entries})!=len(entries):raise ValueError('Duplicate archive paths')
        destination.mkdir(parents=True,exist_ok=False)
        hashes={}
        for entry,relative,target in entries:
            target.parent.mkdir(parents=True,exist_ok=True)
            with z.open(entry) as src,target.open('wb') as dst:shutil.copyfileobj(src,dst)
            hashes[relative.as_posix()]=digest(target)
    record=dict(repository=manifest['repository'],commit=manifest['commit'],archive_sha256=manifest['sha256'],files=hashes)
    (destination/'LAST_SOURCE_RECEIPT.json').write_text(json.dumps(record,indent=2))
    return record


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',type=Path,default=Path('configs/vbench_source.json'))
    p.add_argument('--archive',type=Path,required=True)
    p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--download',action='store_true');a=p.parse_args()
    manifest=json.loads(a.manifest.read_text())
    if a.download and not a.archive.exists():
        a.archive.parent.mkdir(parents=True,exist_ok=True)
        partial=a.archive.with_suffix(a.archive.suffix+'.partial')
        with urllib.request.urlopen(manifest['url'],timeout=120) as src,partial.open('wb') as dst:
            shutil.copyfileobj(src,dst)
        if digest(partial)!=manifest['sha256']:raise ValueError('Downloaded checksum mismatch; partial retained')
        partial.replace(a.archive)
    result=unpack(a.archive,a.directory,manifest)
    print(json.dumps(dict(commit=result['commit'],verified_files=len(result['files']))))


if __name__=='__main__':main()
