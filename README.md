# LAST

Training-free, inversion-free video watermarking with endpoint latent-frequency margin coding (ELMC) and cross-group consistency temporal alignment (CCTA).

## Reproduction status

This repository is being constructed from a frozen manuscript protocol. Full-paper experiments have **not** been reproduced yet. Historical pilot results are not full-benchmark results, and manuscript values are not used as measured outputs.

The reproduction targets 512 information bits, two video backbones (HunyuanVideo and Wan-2.2 A14B), both T2V and I2V, matched baselines, spatial/temporal attacks, quality evaluation and ablations. Runs record model revisions, software versions, seed schedules, codec settings, raw counts, failures and hardware differences.

Generation is being verified on an NVIDIA L40; the manuscript specifies A800 generation. This hardware difference is recorded. Timing runs use an idle L40.

Secret keys, private messages, credentials and model weights are not committed.

## Install (Linux, Python3.10, CUDA-capable NVIDIA GPU)

```bash
git clone https://github.com/twzydn20000928/LAST.git
cd LAST
python -m venv .venv
source .venv/bin/activate
pip install -e '.[video,test]'
pytest -q
```

The numerical core implements masked1776-coordinate orthonormal DCT-II carriers, deterministic keyed QR, minimum signed margins, truth-free CCTA, an energy-spacing fallback and shortened BCH. It is distinct from earlier pilot implementations. See [the reproduction contract](docs/REPRODUCTION.md) and [frozen settings](configs/paper_v1.json).

## Fresh end-to-end smoke check

First follow [data preparation](docs/DATA.md) for the frozen400sample manifest
and verified conditioning images. See [release acceptance](docs/RELEASE_CHECKLIST.md)
for the complete paper-code deliverable and outstanding work.

Download a pinned checkpoint from `configs/models.json`. Supply a JSON case containing `prompt`, `seed` and, for I2V, a local `image` path. Keep output outside version control:

```bash
python -m last.smoke --family hunyuan --mode i2v \
  --model-dir /path/to/checkpoint --case /path/to/case.json \
  --output /private/runs/smoke-hunyuan-i2v --memory-gib 12 --offload sequential
```

Wan uses `--family wan22 --memory-gib 42 --offload model`. The smoke run generates a fresh secret/message, generates an unmarked endpoint, embeds LAST, exports CRF18 MP4, rereads it and blindly extracts512informationbits. It saves an honest receipt and private key material. **A smoke run is not a400-video benchmark.** The generated keys/messages/predictions and videos must not be committed.

Evaluate the seven primary attack conditions on that exported video:

```bash
python -m last.evaluate --family hunyuan --model-dir /path/to/checkpoint \
  --run /private/runs/smoke-hunyuan-i2v --video-id integration-case-0
```

Use the same `--video-id` across methods to share attack maps. Each condition
records a separate receipt; failed conditions remain failures, not zero accuracy.
See [implementation choices and reuse policy](docs/REUSE_AUDIT.md).

## Implementation and result status

Core tests are available. Fresh GPU integration checks are in progress. Dataset manifests, baseline adapters, complete attack runners, confidence intervals, supplemental controls and full-benchmark result bundles are release gates. No fabricated table or historical pilot value is shipped as a new measurement. Do not interpret this repository as a completed or independently validated reproduction.
