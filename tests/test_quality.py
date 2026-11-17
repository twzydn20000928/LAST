import numpy as np
import pytest
from last.quality import fidelity

def test_identity_offset_and_length_mismatch():
    a=np.full((16,16,3),100,dtype=np.uint8)
    exact=fidelity([a],[a]);assert exact['identical'] and exact['ssim']==pytest.approx(1)
    shifted=fidelity([a],[a+10]);assert shifted['psnr_db']==pytest.approx(20*np.log10(25.5))
    assert 0<shifted['ssim']<1
    with pytest.raises(ValueError):fidelity([a,a],[a])
