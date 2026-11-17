import pytest
from last.message_outcomes import summarize,wilson


def row(i,bits,success):
    return dict(video_id=str(i),status='completed',correct_bits=bits,total_bits=512,exact_message=bits==512,bch_success=success,raw_information_correct=bits)


def test_decoder_status_is_distinct_from_exact_message_and_missing_not_zero():
    data=[row(0,512,True),row(1,512,False),row(2,511,True),row(3,500,False)]
    r=summarize(data,['0','1','2','3'])
    assert r['exact_messages']==2 and r['wrong_decoder_success']==1 and r['wrong_decoder_failure']==1
    assert r['exact_despite_decoder_failure']==1 and r['decoder_failures']==2
    assert r['post_bch_error_bits']==13 and r['post_bch_ber_quantiles']['median']==0
    assert r['post_bch_ber_quantiles']['p95']==12/512
    assert summarize(data,['0','1','2','3','4'])['final_bit_accuracy'] is None
    with pytest.raises(ValueError):summarize(data+data[:1],['0','1','2','3'])


def test_perfect_recovery_wilson_bound_is_not_degenerate():
    low,high=wilson(400,400)
    assert .99<low<1 and high==pytest.approx(1)
    assert wilson(0,400)[1]>0
