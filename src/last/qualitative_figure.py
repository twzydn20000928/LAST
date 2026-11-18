"""Render the two paired examples in the Figure 3 layout from generated MP4s."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw
from .quality_inputs import verified_video
from .video import load_mp4


GROUPS = [('reference', 'No Watermark'), ('videomark', 'VideoMark'),
          ('videoshield', 'VideoShield'), ('sigmark', 'SIGMark'),
          ('lfg', 'LFG'), ('last', 'LAST')]
FRAMES = (4, 16)


def render(index):
    cases = json.loads(index.read_bytes())
    if len(cases) != 2 or len({c['video_id'] for c in cases}) != 2:
        raise ValueError('Figure 3 requires two distinct examples')
    tile = 512
    group_width = 2*tile + 4
    figure = Image.new('RGB', (6*group_width + 5*16, 2*tile + 110), 'white')
    draw = ImageDraw.Draw(figure)
    evidence = []
    for col, (method, label) in enumerate(GROUPS):
        x = col*(group_width+16)
        draw.text((x+tile, 8), label, fill='black', anchor='mt', font_size=32)
        for offset, frame in enumerate(FRAMES):
            draw.text((x+offset*(tile+4)+tile//2, 50), f'Frame {frame}', fill='black', anchor='mt', font_size=22)
    for row, item in enumerate(cases):
        case_path = index.parent / item['case']
        case_data = case_path.read_bytes()
        case = json.loads(case_data)
        if case['video_id'] != item['video_id']:
            raise ValueError('Case identity mismatch')
        case_hash = hashlib.sha256(case_data).hexdigest()
        for col, (method, _) in enumerate(GROUPS):
            source = 'last' if method == 'reference' else method
            folder = index.parent / item['runs'][source]
            rec = json.loads((folder/'receipt.json').read_bytes())
            if (rec['status'] not in ('completed','completed_generation_only') or
                (rec['method'],rec['family'],rec['mode'],rec['seed'],rec['case_sha256']) !=
                (source,item['family'],item['mode'],case['seed'],case_hash)):
                raise ValueError(f'Unmatched generation for {method} on {item["video_id"]}')
            reference = method == 'reference'
            video = folder/('reference.mp4' if reference else 'marked.mp4')
            digest, anchor = verified_video(folder, rec, reference)
            frames = load_mp4(video)
            if len(frames) != 65 or any(f.size != (tile,tile) for f in frames):
                raise ValueError('Expected 65 frames at the paper resolution')
            for offset, frame in enumerate(FRAMES):
                figure.paste(frames[frame], (col*(group_width+16)+offset*(tile+4), 84+row*(tile+20)))
            evidence.append(dict(video_id=item['video_id'],family=item['family'],mode=item['mode'],
                                 method=method,case_sha256=case_hash,video_sha256=digest,anchor=anchor))
    return figure, evidence


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--index', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    figure, rows = render(args.index)
    args.output.mkdir(parents=True, exist_ok=False)
    figure.save(args.output/'figure3.png')
    (args.output/'sources.json').write_text(json.dumps(dict(zero_based_frames=FRAMES,videos=rows),indent=2))


if __name__ == '__main__':
    main()
