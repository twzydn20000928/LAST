"""CLI safety checks run without weights or CUDA; not numerical adapter parity."""
import json
import sys
import pytest
from last import generation_timing


def argv(tmp_path, method, family='hunyuan'):
    args = ['generation_timing', '--family', family, '--mode', 'i2v',
            '--method', method, '--model-dir', str(tmp_path/'no-model'),
            '--case', str(tmp_path/'no-case'), '--message', str(tmp_path/'no-message'),
            '--order', 'AB', '--protocol', 'supplement', '--output', str(tmp_path/'out')]
    args += ['--key', str(tmp_path/'no-key')] if method in ('last', 'lfg') else ['--upstream', str(tmp_path/'no-upstream')]
    return args


@pytest.mark.parametrize('method', ['last','lfg','sigmark','videoshield','videomark'])
def test_occupied_gpu_preserves_failed_receipt_before_any_asset_load(tmp_path, monkeypatch, method):
    monkeypatch.setattr(sys, 'argv', argv(tmp_path, method))
    def reject():
        raise RuntimeError('occupied GPU test sentinel')
    monkeypatch.setattr(generation_timing, 'require_exclusive', reject)
    # All input paths deliberately do not exist. The exclusive-GPU failure must
    # precede model imports, secret reads, and expensive native key construction.
    with pytest.raises(RuntimeError, match='occupied GPU test sentinel'):
        generation_timing.main()
    record = json.loads((tmp_path/'out/receipt.json').read_text())
    assert record['status'] == 'failed' and record['pairs'] == []
    assert 'occupied GPU test sentinel' in record['error']
    with pytest.raises(FileExistsError):
        generation_timing.main()


@pytest.mark.parametrize('method', ['sigmark','videoshield','videomark'])
def test_unsupported_native_wan_is_rejected_without_output(tmp_path, monkeypatch, method):
    monkeypatch.setattr(sys, 'argv', argv(tmp_path, method, family='wan22'))
    with pytest.raises(SystemExit) as exc:
        generation_timing.main()
    assert exc.value.code == 2
    assert not (tmp_path/'out').exists()
