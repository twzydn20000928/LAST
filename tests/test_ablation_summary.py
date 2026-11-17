import pytest
from last.ablation_summary import summarize

def row(variant='full'):
    return dict(video_id='a',condition='clean',variant=variant,status='completed',correct_bits=500,total_bits=512,
                exact_message=False,video_sha256='v',source_sha256='s',codes_sha256='c',implementation_sha256={'reader':'x'},writer_method='last')

def test_missing_cases_do_not_inflate_final_score():
    result=summarize([row()],['a','b'])
    cell=next(c for c in result['cells'] if c['condition']=='clean' and c['variant']=='full')
    assert cell['observed_bit_accuracy']==500/512 and cell['final_bit_accuracy'] is None
    assert cell['missing']==1 and len(result['cells'])==28 and not result['complete']

def test_reject_unpaired_files_and_versions():
    a=row();b=row('without_cgc');b['video_sha256']='changed'
    with pytest.raises(ValueError,match='identical'):summarize([a,b],['a'])
    b=row('without_cgc');b['implementation_sha256']={'reader':'new'}
    with pytest.raises(ValueError,match='revisions'):summarize([a,b],['a'])
    with pytest.raises(ValueError,match='duplicate'):summarize([a,a],['a'])
