"""Use the same bundled scorer dependencies for diagnostics and execution."""
from pathlib import Path


def scorer_paths(upstream):
    upstream = Path(upstream).resolve()
    third = upstream/'vbench2/third_party'
    if not (upstream/'vbench2').is_dir():
        raise ValueError('Missing official vbench2 source directory')
    return [upstream, third, third/'LLaVA_NeXT', third/'YOLO-World', third/'Instance_detector']
