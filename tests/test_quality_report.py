import pytest
from last.quality_report import aggregate, CATEGORIES


def test_five_categories_are_equally_weighted_not_eighteen_dimensions():
    rows={d:dict(status='completed',mean=0) for ds in CATEGORIES.values() for d in ds}
    for d in CATEGORIES['Creativity']: rows[d]['mean']=1
    assert aggregate(rows,True)['v_score']==pytest.approx(.2)
    assert aggregate(rows,False)['v_score'] is None
    rows['Human_Identity']['mean']=None
    result=aggregate(rows,True)
    assert result['v_score'] is None and result['missing_or_invalid_dimensions']==['Human_Identity']
    rows['Human_Identity']=dict(status='failed',mean=0)
    assert not aggregate(rows,True)['complete']
