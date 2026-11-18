from pathlib import Path
import json
import sys
import numpy as np
import pytest
from last.controlled_evaluate import commands,READERS,CONDITIONS
from last import controlled_evaluate as workflow


def cmd(reader,calibration=None):
    return commands(reader,*[Path(n) for n in ('received.mp4','attack.json','codes.pt','model')],
                    'hunyuan',Path('cache'),Path('read'),calibration)


def test_four_readers_share_readout_and_only_oracle_acquires_map():
    assert CONDITIONS==('clean','drop','compression')
    for reader in READERS:
        acquisition,extraction=cmd(reader,Path('calibration.json'))
        assert extraction[2]=='last.controlled_extract'
        assert ('--attack-receipt' in acquisition)==(reader=='oracle')
        assert '--attack-receipt' not in extraction
        assert ('--calibration' in extraction)==(reader=='calibrated_energy')
        assert not any('message' in item or 'truth' in item for item in acquisition+extraction)
    assert cmd('ccta')[0]==cmd('calibrated_energy',Path('calibration.json'))[0]


def test_full_reader_cannot_silently_replace_missing_calibration():
    with pytest.raises(ValueError,match='calibration'):cmd('calibrated_energy')
    with pytest.raises(ValueError):cmd('unknown')


@pytest.mark.parametrize('mutate_truth',[False,True])
def test_workflow_artifacts_cache_reuse_and_changed_input_rejection(tmp_path,monkeypatch,mutate_truth):
    """Synthetic subprocess artifacts test orchestration, not actual VAE performance."""
    run=tmp_path/'run';run.mkdir();(run/'attacks').mkdir()
    model=tmp_path/'model';(model/'vae').mkdir(parents=True)
    (model/'vae/config.json').write_text('{}')
    (run/'marked.mp4').write_bytes(b'synthetic-video')
    (run/'codes.pt').write_bytes(b'synthetic-unused-codebook')
    np.save(run/'message.npy',np.zeros(512,dtype=np.uint8))
    (run/'receipt.json').write_text(json.dumps(dict(status='completed',method='last',family='hunyuan')))
    for condition in CONDITIONS:
        (run/'attacks'/(condition+'.json')).write_text('{}')
        if condition!='clean':(run/'attacks'/(condition+'.mp4')).write_bytes(condition.encode())
    calibration=tmp_path/'calibration.json';calibration.write_text('{}')
    output=tmp_path/'output';calls=[]
    monkeypatch.setattr(workflow,'verified_attack',lambda r,c,g:({},r/'marked.mp4' if c=='clean' else r/'attacks'/(c+'.mp4')))
    class Child:
        pid=123
        def __init__(self,command,**kwargs):
            calls.append(command);dest=Path(command[command.index('--output')+1]);dest.mkdir()
            if command[2]=='last.controlled_extract':
                reader=command[command.index('--reader')+1]
                decoded=dest/'decoded-private.json';decoded.write_text(json.dumps(dict(information_bits=[0]*512)))
                receipt=dict(status='completed',blind=reader!='oracle',decoded_sha256=workflow.digest(decoded),selection={})
                if mutate_truth:np.save(run/'message.npy',np.ones(512,dtype=np.uint8))
            else:receipt=dict(status='completed')
            (dest/'receipt.json').write_text(json.dumps(receipt))
        def wait(self):return 0
    monkeypatch.setattr(workflow.subprocess,'Popen',Child)
    monkeypatch.setattr(sys,'argv',['controlled_evaluate','--run',str(run),'--model-dir',str(model),
                                  '--output',str(output),'--family','hunyuan','--calibration',str(calibration)])
    if mutate_truth:
        with pytest.raises(ValueError,match='changed'):workflow.main()
        receipt=json.loads((output/'receipt.json').read_text())
        assert receipt['status']=='failed' and receipt['rows']==[]
        assert (output/'clean-received-read/decoded-private.json').exists()
    else:
        workflow.main();receipt=json.loads((output/'receipt.json').read_text())
        assert receipt['status']=='completed' and receipt['complete_reader_set']
        assert len(receipt['rows'])==12
        assert len([c for c in calls if c[2]=='last.controlled_extract'])==12
        assert len([c for c in calls if c[2]!='last.controlled_extract'])==9
        assert {(r['condition'],r['reader']) for r in receipt['rows']}=={(c,r) for c in CONDITIONS for r in READERS}
        assert all(r['blind']==(r['reader']!='oracle') for r in receipt['rows'])
