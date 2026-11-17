import pytest
from last.reader_ablation import writer_method


def test_shared_frontend_only_and_completed_matched_family():
    for method in ('last','lfg-c'):
        assert writer_method(dict(status='completed',method=method,family='hunyuan'),'hunyuan')==method
    for record in (dict(status='completed',method='lfg',family='hunyuan'),
                   dict(status='failed',method='last',family='hunyuan'),
                   dict(status='completed',method='last',family='wan22')):
        with pytest.raises(ValueError):writer_method(record,'hunyuan')
