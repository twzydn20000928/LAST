import json,os,subprocess,sys
from pathlib import Path

def test_private_state_is_complete_and_cannot_be_overwritten(tmp_path):
    manifest=Path(__file__).resolve().parents[1]/'configs/primary_manifest.json'
    output=tmp_path/'state'
    cmd=[sys.executable,'-m','last.prepare','--manifest',str(manifest),'--output',str(output)]
    subprocess.run(cmd,check=True,capture_output=True)
    keys=list((output/'keys').glob('*.key'));messages=list((output/'messages').glob('*.bin'))
    assert len(keys)==8 and all(p.stat().st_size==32 for p in keys)
    assert len(messages)==400 and all(p.stat().st_size==64 for p in messages)
    original=keys[0].read_bytes()
    assert subprocess.run(cmd,capture_output=True).returncode!=0
    assert keys[0].read_bytes()==original
    if os.name=='posix':assert output.stat().st_mode&0o077==0


def test_development_state_requires_primary_exclusion_and_keeps_keys_disjoint(tmp_path):
    configs=Path(__file__).resolve().parents[1]/'configs'
    primary=tmp_path/'primary';development=tmp_path/'development'
    subprocess.run([sys.executable,'-m','last.prepare','--manifest',str(configs/'primary_manifest.json'),'--output',str(primary)],check=True,capture_output=True)
    command=[sys.executable,'-m','last.prepare','--manifest',str(configs/'development_manifest.json'),'--output',str(development)]
    assert subprocess.run(command,capture_output=True).returncode!=0
    assert not development.exists()
    subprocess.run(command+['--primary-manifest',str(configs/'primary_manifest.json'),'--exclude-state',str(primary)],check=True,capture_output=True)
    a={p.read_bytes() for p in (primary/'keys').glob('*.key')}
    b={p.read_bytes() for p in (development/'keys').glob('*.key')}
    assert len(b)==8 and not a&b
    assert len(list((development/'messages').glob('*.bin')))==80
