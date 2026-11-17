"""Compare installed Python source files with wheel RECORD hashes without imports."""
import argparse,base64,csv,hashlib,json
from pathlib import Path


def audit(directory):
    directory=Path(directory).resolve();record=directory/'RECORD'
    if not record.is_file():raise ValueError('Expected an installed .dist-info directory with RECORD')
    root=directory.parent;changed=[];missing=[];checked=0;unhashed=[]
    for name,digest,size in csv.reader(record.read_text().splitlines()):
        if not name.endswith('.py'):continue
        path=(root/name).resolve()
        if not path.is_relative_to(root):raise ValueError('Source RECORD entry escapes installation root')
        if not path.is_file():missing.append(name);continue
        if not digest:unhashed.append(name);continue
        algorithm,expected=digest.split('=',1)
        actual=base64.urlsafe_b64encode(hashlib.new(algorithm,path.read_bytes()).digest()).decode().rstrip('=')
        checked+=1
        if actual!=expected:changed.append(dict(path=name,expected_record_hash=digest,actual_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    return dict(distribution=directory.name,record_sha256=hashlib.sha256(record.read_bytes()).hexdigest(),checked_python_files=checked,changed=changed,missing=missing,unhashed=unhashed,scope='Integrity relative to local wheel RECORD, not upstream authenticity or binary compatibility')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dist-info',type=Path,nargs='+',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():p.error('Output exists; preserve previous audit')
    result=[audit(d) for d in a.dist_info]
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2))
    print(json.dumps([{k:r[k] for k in ('distribution','checked_python_files','changed','missing')} for r in result]))


if __name__=='__main__':main()
