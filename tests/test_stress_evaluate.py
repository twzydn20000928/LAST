import hashlib,json
import pytest
from last.stress_evaluate import verify_attack
from last.stress_evaluate import verify_completed
from last.stress_evaluate import recount,verify_counts
import numpy as np
import sys
from pathlib import Path
from last import stress_evaluate as workflow

def test_stress_verifier_rejects_replaced_video_and_wrong_source(tmp_path):
    video=tmp_path/'received.mp4';video.write_bytes(b'fixture')
    row=dict(status='completed_attack_export',source_sha256='source',received_sha256=hashlib.sha256(video.read_bytes()).hexdigest())
    (tmp_path/'attack.json').write_text(json.dumps(row))
    assert verify_attack(tmp_path,'source')[1]==video
    with pytest.raises(ValueError,match='source mismatch'):verify_attack(tmp_path,'other')
    video.write_bytes(b'replaced')
    with pytest.raises(ValueError,match='changed'):verify_attack(tmp_path,'source')


def test_cached_result_binds_private_output_inputs_and_source(tmp_path):
    decoded=tmp_path/'prediction.json';decoded.write_bytes(b'private fixture')
    inputs={'video':'video-hash','key':'key-hash','vae':'model-hash'}
    sources={'extract.py':'source-hash'}
    record=dict(status='completed',input_sha256=inputs,source_sha256_files=sources,
                decoded_sha256=hashlib.sha256(decoded.read_bytes()).hexdigest())
    verify_completed(record,inputs,sources,decoded)
    for changed in ({**inputs,'key':'other'},{**inputs,'vae':'other'}):
        with pytest.raises(ValueError,match='provenance'):
            verify_completed(record,changed,sources,decoded)
    with pytest.raises(ValueError,match='provenance'):
        verify_completed(record,inputs,{'extract.py':'changed'},decoded)
    decoded.write_bytes(b'replaced')
    with pytest.raises(ValueError,match='prediction changed'):
        verify_completed(record,inputs,sources,decoded)


def test_legacy_completed_receipt_is_not_silently_reused(tmp_path):
    with pytest.raises(ValueError,match='new output directory'):
        verify_completed({'status':'completed'},{'video':'hash'},{'extract.py':'hash'},tmp_path/'absent')


def test_saved_count_is_recomputed_and_attack_identity_checked():
    truth=np.zeros(512,dtype=np.uint8)
    bits=truth.copy();bits[:7]=1
    prediction=dict(video_sha256='video',family='hunyuan',information_bits=512,
                    message_hex=np.packbits(bits).tobytes().hex())
    measured=recount(prediction,truth,'video','hunyuan')
    assert measured==dict(correct_bits=505,total_bits=512,exact_message=False)
    attack=dict(attack='drop45',seed=0,video_id='case',received_sha256='video')
    record=dict(attack='drop45',seed=0,video_id='case',**measured)
    verify_counts(record,prediction,truth,attack,'hunyuan')
    with pytest.raises(ValueError,match='counts disagree'):
        verify_counts(dict(record,correct_bits=512),prediction,truth,attack,'hunyuan')
    with pytest.raises(ValueError,match='condition mismatch'):
        verify_counts(dict(record,seed=1),prediction,truth,attack,'hunyuan')
    with pytest.raises(ValueError,match='identity mismatch'):
        recount(prediction,truth,'video','wan22')


@pytest.mark.parametrize('mutate_truth',[False,True])
@pytest.mark.parametrize('relative',['drop45','drop45/map0'])
def test_full_workflow_resume_and_input_change(tmp_path,monkeypatch,mutate_truth,relative):
    """Synthetic process outputs exercise orchestration, not video accuracy."""
    run=tmp_path/'run';run.mkdir()
    (run/'marked.mp4').write_bytes(b'original fixture')
    (run/'secret.key').write_bytes(b'k'*32)
    np.save(run/'message.npy',np.zeros(512,dtype=np.uint8))
    (run/'receipt.json').write_text(json.dumps(dict(status='completed',method='last',
        family='hunyuan',marked_sha256=workflow.digest(run/'marked.mp4'))))
    model=tmp_path/'model';(model/'vae').mkdir(parents=True)
    (model/'vae/config.json').write_text('{}')
    attacks=tmp_path/'attacks';folder=attacks/relative;folder.mkdir(parents=True)
    video=folder/'received.mp4';video.write_bytes(b'edited fixture')
    attack=dict(status='completed_attack_export',source_sha256=workflow.digest(run/'marked.mp4'),
                received_sha256=workflow.digest(video),attack='drop45',seed=0,video_id='case')
    (folder/'attack.json').write_text(json.dumps(attack))
    out=tmp_path/'output';calls=[]
    def child(command,**kwargs):
        calls.append(command)
        assert '--key' in command and '--video' in command
        assert str(run/'message.npy') not in command and str(folder/'attack.json') not in command
        destination=Path(command[command.index('--output')+1])
        destination.write_text(json.dumps(dict(video_sha256=workflow.digest(video),family='hunyuan',
            information_bits=512,message_hex=bytes(64).hex(),bch_success=True,route='fixture',groups=4)))
        if mutate_truth:np.save(run/'message.npy',np.ones(512,dtype=np.uint8))
    monkeypatch.setattr(workflow.subprocess,'run',child)
    monkeypatch.setattr(sys,'argv',['stress_evaluate','--run',str(run),'--attacks',str(attacks),
                                  '--model-dir',str(model),'--family','hunyuan','--output',str(out)])
    receipt=out/relative/'evaluation.json'
    if mutate_truth:
        with pytest.raises(SystemExit):workflow.main()
        row=json.loads(receipt.read_text())
        assert row['status']=='failed' and 'changed during extraction' in row['error']
        assert 'correct_bits' not in row
        assert (out/relative/'decoded_private.json').exists()
    else:
        workflow.main()
        row=json.loads(receipt.read_text())
        assert row['status']=='completed' and row['correct_bits']==512
        workflow.main()
        assert len(calls)==1
        row['correct_bits']=511;receipt.write_text(json.dumps(row))
        with pytest.raises(ValueError,match='counts disagree'):workflow.main()
        assert len(calls)==1
