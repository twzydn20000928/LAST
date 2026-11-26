import hashlib
import json
import sys
import pytest
from last.baseline_evaluate import check_extraction


def test_reused_native_extraction_requires_matching_video_and_state():
    record=dict(status='completed_extraction',method='videoshield',mode='i2v',family='hunyuan',video_sha256='video',state_sha256='state',temporal=False)
    check_extraction(record,'videoshield','i2v','video','state',False)
    for key,value in [('state_sha256','other'),('video_sha256','other'),('temporal',True),('status','failed')]:
        with pytest.raises(ValueError):check_extraction(dict(record,**{key:value}),'videoshield','i2v','video','state',False)


@pytest.mark.parametrize('family',['hunyuan','wan22'])
def test_native_reuse_cannot_cross_model_families(family):
    record=dict(status='completed_extraction',method='videomark',mode='i2v',family=family,
                video_sha256='same-video',state_sha256='same-state',temporal=True)
    check_extraction(record,'videomark','i2v','same-video','same-state',True,family)
    other='wan22' if family=='hunyuan' else 'hunyuan'
    with pytest.raises(ValueError):
        check_extraction(record,'videomark','i2v','same-video','same-state',True,other)
    del record['family']
    with pytest.raises(ValueError):
        check_extraction(record,'videomark','i2v','same-video','same-state',True,family)



def test_single_retry_recounts_saved_prediction_without_inversion(tmp_path, monkeypatch):
    from last import baseline_evaluate as evaluator
    def sha(data):
        return hashlib.sha256(data).hexdigest()
    run = tmp_path / 'run'
    attacks = run / 'attacks'
    attacks.mkdir(parents=True)
    prior = tmp_path / 'prior'
    prior.mkdir()
    out = tmp_path / 'recount'
    generation = dict(method='sigmark', family='hunyuan', mode='i2v',
                      status='completed_generation_only', video_sha256=sha(b'marked'))
    (run / 'receipt.json').write_text(json.dumps(generation))
    (run / 'marked.mp4').write_bytes(b'marked')
    (run / 'message.bin').write_bytes(bytes(64))
    (run / 'maintained_private.pkl').write_bytes(b'state')
    (attacks / 'noise.mp4').write_bytes(b'noisy')
    failed = dict(status='failed', video_id='paper-000', method='sigmark', family='hunyuan',
                  condition='noise', map_seed=0, source_sha256=sha(b'marked'), state_sha256=sha(b'state'),
                  received_sha256=sha(b'noisy'), attack_map=None, codec_command=['test'])
    original = json.dumps(failed).encode()
    (attacks / 'noise.json').write_bytes(original)
    decoded = bytes([1]) + bytes(63)
    extracted = dict(status='completed_extraction', method='sigmark', family='hunyuan', mode='i2v',
                     temporal=False, video_sha256=sha(b'noisy'), state_sha256=sha(b'state'),
                     decoded_sha256=sha(decoded))
    (prior / 'receipt.json').write_text(json.dumps(extracted))
    (prior / 'decoded.bin').write_bytes(decoded)
    monkeypatch.setattr(evaluator.os, 'umask', lambda mode: 0)
    monkeypatch.setattr(evaluator, 'load_mp4', lambda path: [None] * 65)
    monkeypatch.setattr(evaluator.subprocess, 'run', lambda *a, **kw: pytest.fail('unexpected inversion'))
    monkeypatch.setattr(sys, 'argv', ['evaluate', '--run', str(run), '--model-dir', '.', '--upstream', '.',
                        '--video-id', 'paper-000', '--retry-condition', 'noise', '--retry-output', str(out),
                        '--retry-extraction', str(prior)])
    evaluator.main()
    score = json.loads((out / 'noise.json').read_bytes())
    assert score['reused_extraction'] and score['correct_bits'] == 511 and not score['exact_message']
    assert score['retry_of_sha256'] == sha(original)
    assert (attacks / 'noise.json').read_bytes() == original
    assert (out / 'noise-extract/receipt.json').read_bytes() == (prior / 'receipt.json').read_bytes()
