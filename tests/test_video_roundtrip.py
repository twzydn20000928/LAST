import numpy as np
import pytest
cv2=pytest.importorskip('cv2')
pytest.importorskip('PIL');pytest.importorskip('imageio_ffmpeg')
from PIL import Image
from last.video import export_mp4,load_mp4

def test_ffmpeg_export_opencv_reread_preserves_geometry_order_and_rate(tmp_path):
    frames=[Image.fromarray(np.full((32,32,3),(30+20*i,80,130),dtype=np.uint8)) for i in range(5)]
    path=tmp_path/'codec.mp4';command=export_mp4(frames,path,crf=18,fps=8)
    result=load_mp4(path)
    assert len(result)==5 and all(image.size==(32,32) for image in result)
    assert '-crf' in command and 'yuv420p' in command
    red=[np.asarray(image)[:,:,0].mean() for image in result]
    assert all(a<b for a,b in zip(red,red[1:]))
    assert max(np.abs(np.asarray(a).astype(float)-np.asarray(b)).mean() for a,b in zip(frames,result))<8
    capture=cv2.VideoCapture(str(path))
    try:assert capture.get(cv2.CAP_PROP_FPS)==pytest.approx(8)
    finally:capture.release()
