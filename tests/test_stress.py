import numpy as np
import pytest
pytest.importorskip('cv2');pytest.importorskip('PIL')
from PIL import Image
from last.stress import edit,midpoint
from last.temporal import attack_map

def test_supplement_counts_determinism_and_primary_map_consistency():
    frames=[Image.fromarray(np.full((16,16,3),i,dtype=np.uint8)) for i in range(65)]
    for attack,count in [('drop10',55),('drop30',35),('drop45',20),('duplicate30',95),('interpolate30',95),('drop30_crf28',35)]:
        out,m=edit(frames,attack,'v');again,m2=edit(frames,attack,'v')
        assert len(out)==count and m==m2
        assert all(np.array_equal(a,b) for a,b in zip(out,again))
    assert edit(frames,'drop30','v')[1]['source_indices']==attack_map('v','drop')
    assert edit(frames,'drop30_crf28','v')[1]==edit(frames,'drop30','v')[1]
    donor=[Image.fromarray(np.full((16,16,3),200,dtype=np.uint8))]*40
    out,m=edit(frames,'natural30','v',donor=donor)
    assert len(out)==95 and sum(np.asarray(f)[0,0,0]==200 for f in out)==30
    with pytest.raises(ValueError):edit(frames,'natural30','v')
    assert np.array_equal(midpoint(frames[20],frames[30]),np.full((16,16,3),25,dtype=np.uint8))
