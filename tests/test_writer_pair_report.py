import json
import pytest
from last.writer_pair_report import CONDITIONS, digest, report


def write(path, value):
    path.write_text(json.dumps(value))


@pytest.fixture
def pair(tmp_path):
    left, right = tmp_path/'minimum', tmp_path/'fixed'
    common = dict(status='completed', method='last', family='hunyuan', mode='i2v',
                  settings={'steps': 50}, seed=2028, case_sha256='case', mu=.5, uniform_profile=False)
    for folder, fixed in ((left, False), (right, True)):
        (folder/'attacks').mkdir(parents=True)
        for name in ('endpoint.pt','codes.pt','secret.key','message.npy','reference.mp4'):
            (folder/name).write_bytes(name.encode())
        (folder/'marked.mp4').write_bytes(str(fixed).encode())
        row = dict(common, fixed_target=fixed, marked_sha256=digest(folder/'marked.mp4'))
        if not fixed: row['endpoint_sha256'] = digest(folder/'endpoint.pt')
        else:
            row['paired_endpoint_sha256'] = digest(left/'endpoint.pt')
            row['source_artifact_sha256'] = {n:digest(left/n) for n in ('receipt.json','endpoint.pt','codes.pt','secret.key','message.npy','reference.mp4')}
        write(folder/'receipt.json', row)
        write(folder/'quality.json', dict(reference_sha256=digest(folder/'reference.mp4'), marked_sha256=row['marked_sha256'],
                                         definition='same', psnr_db=30., ssim=.93))
        for condition in CONDITIONS:
            received = folder/'marked.mp4'
            if condition != 'clean':
                received = folder/'attacks'/(condition+'.mp4');received.write_bytes(condition.encode())
            write(folder/'attacks'/(condition+'.json'), dict(status='completed',condition=condition,method='last',video_id='paper-003',
                  source_sha256=row['marked_sha256'],received_sha256=digest(received),map_seed=0,attack_map=[0,1],frames=2,
                  correct_bits=500,total_bits=512,exact_message=False))
    return left, right


def test_complete_pair_and_private_state_excluded(pair):
    result = report(*pair)
    assert len(result['variants']['fixed-target']['conditions']) == 7
    assert result['variants']['minimum-margin']['conditions'][0]['bit_accuracy'] == 500/512
    assert 'secret.key' not in json.dumps(result)


@pytest.mark.parametrize('change', ['map', 'video', 'key', 'missing'])
def test_reject_unpaired_or_incomplete_evidence(pair, change):
    left, right = pair
    if change == 'map':
        path=right/'attacks/drop.json';row=json.loads(path.read_text());row['attack_map']=[2,3];write(path,row)
    elif change == 'video': (right/'attacks/drop.mp4').write_bytes(b'tampered')
    elif change == 'key': (right/'secret.key').write_bytes(b'changed')
    else: (right/'attacks/clip.json').unlink()
    with pytest.raises((ValueError, FileNotFoundError)): report(left, right)
