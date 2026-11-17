import numpy as np
import pytest
pytest.importorskip('cv2')
pytest.importorskip('PIL')
from PIL import Image
from last.evaluate import attacked

def test_temporal_edits_preserve_source_order_and_exact_count():
    frames=[Image.fromarray(np.full((8,8,3),i,dtype=np.uint8)) for i in range(65)]
    for name, count in [('drop',35),('clip',35),('insert',95)]:
        out,mapping=attacked(frames,name,'unit')
        assert len(out)==count
        assert [i for i in mapping if i>=0]==sorted(i for i in mapping if i>=0)
        for im,index in zip(out,mapping):
            if index>=0:assert np.all(np.asarray(im)==index)
        if name=='insert':assert mapping.count(-1)==30
    a,_=attacked(frames,'noise','unit');b,_=attacked(frames,'noise','unit')
    assert all(np.array_equal(x,y) for x,y in zip(a,b))
