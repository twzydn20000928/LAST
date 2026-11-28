"""Explicit FFmpeg H.264 round trips; no in-memory result substituted for MP4."""
from pathlib import Path
import subprocess
import numpy as np

def export_mp4(frames, path, crf=18, fps=8, *, demo_codec_threads=False):
    import imageio_ffmpeg
    first=np.asarray(frames[0],dtype=np.uint8);h,w=first.shape[:2]
    command=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{w}x{h}','-r',str(fps),'-i','pipe:0','-an','-c:v','libx264','-crf',str(crf),'-pix_fmt','yuv420p',str(path)]
    if demo_codec_threads:
        options = command.index("-crf")
        command[options:options] = ["-threads", "16", "-x264-params", "lookahead_threads=2"]
    process=subprocess.Popen(command,stdin=subprocess.PIPE)
    try:
        for frame in frames:
            a=np.asarray(frame,dtype=np.uint8)
            if a.shape!=first.shape:raise ValueError('Inconsistent frame shape')
            process.stdin.write(a.tobytes())
        process.stdin.close()
        if process.wait()!=0:raise RuntimeError('FFmpeg export failed')
    except BaseException:
        process.kill();process.wait();raise
    return command

def load_mp4(path):
    import cv2
    from PIL import Image
    cap=cv2.VideoCapture(str(path));frames=[]
    while True:
        ok,frame=cap.read()
        if not ok:break
        frames.append(Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)))
    cap.release()
    if not frames:raise ValueError(f'No decodable frames: {path}')
    return frames
