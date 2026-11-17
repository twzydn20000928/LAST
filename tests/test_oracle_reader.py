import pytest
from last.oracle_reader import oracle_nodes


def test_oracle_uses_only_received_same_group_frames_and_skips_foreign_pixels():
    mapping=[0,4,-1,1,4,9,10,11,12]
    nodes=oracle_nodes(mapping)
    assert [n['group'] for n in nodes]==[0,2]
    assert nodes[0]['indices']==[3,3,1,1]
    assert nodes[0]['observed']==2 and nodes[0]['filled']==2
    assert nodes[1]['indices']==[5,6,7,8]
    assert all(i not in (0,2,4) for n in nodes for i in n['indices'])
    assert oracle_nodes([-1,-1,0])==[]
    with pytest.raises(ValueError):oracle_nodes([65])
