from pathlib import Path
import pytest
from last.controlled_evaluate import commands,READERS,CONDITIONS


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
