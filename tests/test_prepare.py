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
