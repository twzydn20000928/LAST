import torch
from last.evaluate import reader_nodes,extract

def test_received_order_uses_no_oracle_or_segmentation():
    nodes=reader_nodes(list(range(35)),'received')
    assert [n['start'] for n in nodes]==list(range(1,35,4))
    assert nodes[-1]['indices']==[33,34,34,34]
    assert len(reader_nodes(list(range(95)),'received'))==16
    assert reader_nodes([0],'received')==[]

def test_received_reader_uses_received_slots_even_when_identity_is_wrong():
    codes=torch.eye(4).reshape(2,2,4)
    nodes=reader_nodes(list(range(9)),'received')
    cache={tuple(nodes[0]['indices']):torch.tensor([1.,-1.,0.,0.]),tuple(nodes[1]['indices']):torch.tensor([0.,0.,2.,-2.])}
    scores,meta=extract(list(range(9)),None,None,'hunyuan',codes,'received',False,cache)
    assert torch.equal(scores,torch.tensor([3.,-3.])) and meta['groups']==2
