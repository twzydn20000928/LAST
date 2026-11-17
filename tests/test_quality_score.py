import pytest
from last.quality_score import summarize


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
