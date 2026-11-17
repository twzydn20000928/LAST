import pytest
from last.quality_score import summarize
from last.quality_score import verify_inputs
import hashlib


def test_applicability_is_not_zero_and_missing_predictions_fail():
    rows = [dict(video_list=['a.mp4', 'b.mp4'])]
    result = [1, [dict(video_path='a.mp4', video_results=1), dict(video_path='b.mp4', video_results=-1)]]
    report = summarize(result, rows, 'Human_Identity')
    assert report['mean'] == 1 and report['not_applicable_units'] == 1
    assert not report['all_applicable']
    with pytest.raises(ValueError): summarize([1, result[1][:1]], rows, 'Human_Identity')
    result[1][0]['video_results'] = -1
    assert summarize(result, rows, 'Human_Identity')['mean'] is None


def test_diversity_counts_prompts_not_individual_videos():
    rows = [dict(video_list=['a.mp4', 'b.mp4']), dict(video_list=['c.mp4', 'd.mp4'])]
    result = [.3, [dict(video_path='a.mp4', video_results=.2), dict(video_path='c.mp4', video_results=.4)]]
    report = summarize(result, rows, 'Diversity')
    assert report['expected_units'] == 2 and report['unit'] == 'prompt'
    assert report['mean'] == pytest.approx(.3)


def test_scoring_rechecks_every_diversity_seed(tmp_path):
    videos = [tmp_path/'first.mp4', tmp_path/'second.mp4']
    for video in videos:
        video.write_bytes(video.name.encode())
    rows = [dict(video_list=list(map(str, videos)))]
    coverage = dict(videos=[dict(path=str(v), sha256=hashlib.sha256(v.read_bytes()).hexdigest()) for v in videos])
    assert len(verify_inputs(rows, coverage)) == 2
    videos[1].write_bytes(b'replaced after preparation')
    with pytest.raises(ValueError, match='changed'):
        verify_inputs(rows, coverage)


def test_scoring_rejects_unanchored_and_legacy_inputs(tmp_path):
    video = tmp_path/'v.mp4'; video.write_bytes(b'video')
    rows = [dict(video_list=[str(video)])]
    with pytest.raises(ValueError, match='absent'):
        verify_inputs(rows, dict(videos=[]))
    with pytest.raises(ValueError, match='regenerate'):
        verify_inputs(rows, dict(videos=[dict(video_id='old', sha256='unused')]))
    anchor = dict(path=str(video), sha256=hashlib.sha256(video.read_bytes()).hexdigest())
    with pytest.raises(ValueError, match='Duplicate video path'):
        verify_inputs(rows, dict(videos=[anchor, anchor]))
    with pytest.raises(ValueError, match='Duplicate scoring video'):
        verify_inputs(rows+rows, dict(videos=[anchor]))
