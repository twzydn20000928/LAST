import numpy as np
import pytest
from last.reextract import compare, reader_command


def test_truth_and_maps_are_not_reader_arguments():
    command = reader_command('received.mp4', 'secret.key', 'hunyuan', 'model', 'private.json')
    assert command[2:4] == ['last.extract', '--video']
    assert set(x for x in command if x.startswith('--')) == {
        '--video', '--key', '--family', '--model-dir', '--output'}


def test_changed_accuracy_is_retained_not_selected_away():
    decoded = dict(information_bits=512, message_hex='00'*64, video_sha256='video', bch_success=False, route='ccta')
    row = compare(decoded, np.zeros(512), dict(status='completed', correct_bits=500), 'video')
    assert row['correct_bits'] == 512 and row['same_correct_bit_count'] is False
    assert row['exact_message'] and not row['bch_success']
    with pytest.raises(ValueError, match='different video'):
        compare(decoded, np.zeros(512), {}, 'changed')
    with pytest.raises(ValueError, match='shape'):
        compare(decoded, np.zeros(511), {}, 'video')
