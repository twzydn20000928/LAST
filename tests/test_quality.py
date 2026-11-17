import numpy as np
import pytest
from last.quality import fidelity

def test_identity_offset_and_length_mismatch():
    a=np.full((16,16,3),100,dtype=np.uint8)
    exact=fidelity([a],[a]);assert exact['identical'] and exact['ssim']==pytest.approx(1)
    shifted=fidelity([a],[a+10]);assert shifted['psnr_db']==pytest.approx(20*np.log10(25.5))
    assert 0<shifted['ssim']<1
    with pytest.raises(ValueError):fidelity([a,a],[a])

def test_ssim_matches_explicit_eleven_pixel_kernel():
    from scipy.signal import convolve2d
    rng=np.random.default_rng(9)
    a=rng.integers(0,256,(24,24,3),dtype=np.uint8)
    b=rng.integers(0,256,(24,24,3),dtype=np.uint8)
    g=np.exp(-np.arange(-5,6)**2/(2*1.5**2));g/=g.sum();kernel=np.outer(g,g)
    values=[]
    for c in range(3):
        x=a[:,:,c]/255.;y=b[:,:,c]/255.
        f=lambda z:convolve2d(z,kernel,mode='valid')
        mx,my=f(x),f(y);vx=f(x*x)-mx*mx;vy=f(y*y)-my*my;cov=f(x*y)-mx*my
        values.append((((2*mx*my+.01**2)*(2*cov+.03**2))/((mx*mx+my*my+.01**2)*(vx+vy+.03**2))).mean())
    assert fidelity([a],[b])['ssim']==pytest.approx(np.mean(values),abs=1e-12)
