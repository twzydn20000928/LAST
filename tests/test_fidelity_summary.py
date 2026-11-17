import math
import pytest
from last.fidelity_summary import summarize

def row(name,mse):
    return dict(video_id=name,rgb_mse=mse,psnr_db=-10*math.log10(mse) if mse else None,identical=mse==0,ssim=.9,frames=65,definition='fixture')

def test_video_average_is_not_pooled_error_psnr():
    result=summarize([row('a',.01),row('b',.0001)],['a','b'])
    assert result['final_mean_video_psnr_db']==30
    assert result['observed_psnr_from_mean_mse_db']<24
    assert summarize([row('a',.01)],['a','b'])['final_mean_ssim'] is None

def test_infinite_psnr_and_invalid_counts():
    result=summarize([row('a',0),row('b',.01)],['a','b'])
    assert result['final_mean_video_psnr_db'] is None and result['final_mean_video_psnr_is_infinite']
    wrong=row('a',.01);wrong['psnr_db']=80
    with pytest.raises(ValueError,match='PSNR'):summarize([wrong],['a'])
    with pytest.raises(ValueError,match='Duplicate'):summarize([row('a',.01)]*2,['a','b'])
