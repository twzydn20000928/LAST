import pytest
from last.reader_timing import compute_pids, measure


def test_warmups_excluded_and_synchronization_encloses_operation():
    events=[]; clock=iter([10,12,20,23])
    result=measure(lambda:events.append('read'),lambda:events.append('sync'),
                   lambda:events.append('guard'),2,2,lambda:next(clock))
    assert result==[2,3]
    assert events[:8]==['guard','read','sync','guard']*2
    assert events[8:]==['guard','sync','read','sync','guard']*2


def test_contention_invalidates_measurement():
    checks=iter([None,None,RuntimeError('another process')])
    def guard():
        failure=next(checks)
        if failure:raise failure
    with pytest.raises(RuntimeError,match='another process'):
        measure(lambda:None,lambda:None,guard,1,2)
    assert compute_pids('123\n456\n123\n')=={123,456}


def test_prediction_parity_checks_bit_positions_and_video(tmp_path):
    import json
    import numpy as np
    from last.reader_timing import verify_prediction

    bits = np.zeros(512, dtype=np.uint8)
    bits[0] = 1
    path = tmp_path / 'ordinary.json'
    path.write_text(json.dumps(dict(family='wan22', video_sha256='video', information_bits=512,
                                    message_hex=np.packbits(bits).tobytes().hex())))
    verify_prediction(path, 'video', 'wan22', bits)
    with pytest.raises(ValueError):
        verify_prediction(path, 'different-video', 'wan22', bits)
    with pytest.raises(ValueError):
        verify_prediction(path, 'video', 'wan22', np.roll(bits, 1))


def test_prepared_lfg_carriers_preserve_scores(monkeypatch):
    import torch
    import last.lfg as lfg
    torch.set_num_threads(2)
    # Broadcast fixtures keep the production geometry without allocating eight matrices.
    prepared=[torch.tensor(float(1 if p%2 else -1)).expand(1184,16384) for p in range(8)]
    monkeypatch.setattr(lfg,'carriers',lambda key,p:prepared[p])
    encoded=torch.arange(17,dtype=torch.float32).view(1,1,17,1,1).expand(1,16,17,64,64)
    expected=lfg.scores(encoded,b'x'*32)
    def forbidden(*args):raise AssertionError('Key setup repeated inside timed reader')
    monkeypatch.setattr(lfg,'carriers',forbidden)
    assert torch.equal(expected,lfg.scores(encoded,b'x'*32,prepared))
