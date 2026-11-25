"""Report verified input coverage for the Table 1 quality pipelines."""
import argparse
import hashlib
import json
from pathlib import Path

from last.quality_inputs import build
from last.upstream import verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata-root", required=True, type=Path)
    parser.add_argument("--run-root", required=True, type=Path)
    parser.add_argument("--configs", type=Path, default=Path("configs"))
    methods = ("last", "reference", "lfg", "sigmark", "videoshield", "videomark")
    parser.add_argument("--methods", nargs="+", choices=methods, default=methods)
    args = parser.parse_args()
    verify(args.metadata_root, json.loads((args.configs / "quality_metadata_manifest.json").read_bytes()))
    raw = (args.configs / "primary_manifest.json").read_bytes()
    manifest = json.loads(raw)
    pipelines = []
    for family in ("hunyuan", "wan22"):
        for mode in ("i2v", "t2v"):
            for method in dict.fromkeys(args.methods):
                _, report = build(manifest, args.metadata_root, args.run_root, family, mode, method)
                dimensions = {name: {key: counts[key] for key in ("available", "expected")}
                              for name, counts in sorted(report["coverage"].items())}
                pipelines.append(dict(family=family, mode=mode, method=method,
                                      available_videos=len(report["videos"]), dimensions=dimensions))
    print(json.dumps(dict(manifest_sha256=hashlib.sha256(raw).hexdigest(), pipelines=pipelines), indent=2))


if __name__ == "__main__":
    main()
