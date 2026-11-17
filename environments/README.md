# Rebuilding the measured environment

`video-linux-py310-cu124.txt` pins the complete observed dependency set from
the new Linux x86_64 Python 3.10.22 virtual environment. Installation, `pip check`,
59 tests at installation time, and CUDA/L40 detection passed. Subsequent core
tests reached 64 passes. This is an observed version lock, not a wheel-hash
lock or a guarantee for Windows, macOS, other Python versions or GPU drivers.
The CUDA wheel runtime is 12.4; the host must supply a compatible NVIDIA driver.

From a fresh checkout, record the exact commit and create an isolated environment:

```bash
git rev-parse HEAD
python3.10 -m venv .venv
source .venv/bin/activate
unset PYTHONPATH
export PYTHONNOUSERSITE=1
python -m pip install -r environments/video-linux-py310-cu124.txt
python -m pip install --no-deps -e .
python -m pip check
python -m pytest -q
python -m last.doctor --strict --output /private/environment.json
```

Then follow the README's pinned-model acquisition and real-video smoke/extraction
commands. The published installation receipt used an editable working checkout;
the full fresh-checkout generation walkthrough remains an acceptance gate. Do
not interpret this file as evidence that every paper experiment has completed.

This lock covers the numerical core, video generation/extraction and tests.
Native baseline extras and the official VBench quality stack are separate;
their additional environments are not covered by the video-only lock. A native
baseline lock and its narrower validation scope are documented below. Do not add historical server
overlay directories to `PYTHONPATH` to conceal missing dependencies. Keep
failed installation logs and report differences rather than silently relaxing
versions. Model weights, secret state and input datasets are not dependencies
bundled in this lock.
# Wan text preprocessing dependency correction

`last.doctor` also records cuDNN, TF32, attention backend and deterministic-
algorithm switches, plus explicitly allowlisted numerical environment variables.
It does not enable deterministic algorithms or change the paper settings.
Matching version strings alone is insufficient evidence of bitwise reproduction;
the report describes its own process, not unrecorded historical flags. Keep the
report with each acquisition environment and retain discrepancies when comparing
independently generated videos.

The first formal Wan run in the clean environment failed before sampling with
`NameError: name 'ftfy' is not defined`. Diffusers conditionally imports this
optional dependency, so package import and `pip check` alone did not catch it.
The video extra and observed lock now include `ftfy==6.3.1` and
`wcwidth==0.2.13`. Existing installations can add those exact versions without
changing model weights or numerical generation settings. The original failed
receipt is retained; it is not a measured watermark-accuracy result.

`tests/test_wan_text.py` exercises both the I2V and T2V prompt cleaners without
loading weights, including HTML and malformed Unicode. It runs in the video CI
job. Historical 59-package installation evidence remains historical; this
correction adds two packages and does not by itself prove full Wan generation.

## Native comparison environment

`native-linux-py310-cu124.txt` records 80 observed distributions from a separate
Linux Python3.10 environment. Installation, `pip check`, and all three pinned
native original-noise interfaces passed without historical `PYTHONPATH` overlays.
See `results/native_clean_environment.json`: VideoShield, VideoMark and SIGMark
each recovered512/512 bits; VideoMark used a400-candidate diagnostic registry.
These are CPU noise tests, not generated-video or attack results.

```bash
python3.10 -m venv .venv-native
source .venv-native/bin/activate
unset PYTHONPATH
export PYTHONNOUSERSITE=1
python -m pip install -r environments/native-linux-py310-cu124.txt
python -m pip install --no-deps --no-build-isolation -e .
python -m pip check
python -m last.upstream --directory /path/to/SIGMark-python --download
python -m last.baseline_probe --method sigmark \
  --upstream /path/to/SIGMark-python --output /private/new-sigmark-probe
```

Repeat the probe with `videoshield` and `videomark`, each in a new private output
directory. The recorded validation used public revision
`1d331462fff777cd825e23f630b8ce3aa18b23fa` with the later video dependency lock
(including the disclosed ftfy correction). The observed native lock includes
transitive baseline dependencies; it is not a wheel-hash lock. Real video
generation/inversion and timing in this environment remain unverified, and this
does not install or validate the official VBench quality stack.


## Quality environment candidate (not yet accepted)

`quality-linux-py310-cu124-candidate.txt` records 153 observed package versions
from the isolated quality environment. It excludes the editable LAST package
and the locally built MMCV wheel. This candidate is separate from the video
lock: VBench needs timm 0.4.12 and fsspec 2024.9.0. Do not install it into an
active video-generation environment. See `results/quality_environment_candidate.json`.

An exact candidate reconstruction uses `pip install --no-deps -r` on this
inventory, then builds MMCV 2.0.1 with the disclosed C++17-only build helper in
[QUALITY.md](../docs/QUALITY.md), installs that wheel with `--no-deps`, and
installs the pinned LAST checkout with `--no-deps -e .`. The `--no-deps` choice
is deliberate: the following upstream dependency declarations conflict with
this runtime and must remain visible, rather than being silently rewritten:

- MMEngine asks for the GUI `opencv-python` distribution; this runtime uses
  `opencv-python-headless` 4.10.0.84 because GUI OpenCV failed on missing libGL.
- RetinaFace 0.0.8 declares torch 1.9.0, torchvision 0.10.0 and albumentations
  1.0.0; the observed runtime uses 2.5.1, 0.20.1 and 1.4.19 respectively.

`pip check` therefore returns a nonzero result with four known messages.
Do not suppress new or different failures. All 18 official modules imported,
MMCV CPU/CUDA operator checks passed, and the unchanged RetinaFace detector ran
on one real frame; these checks do not validate the full identity scorer or all
model runtimes. A nonzero `pip check` is disclosed evidence, not a claim of a
fully dependency-compatible or accepted environment.

The candidate has now been replayed in a new Python virtual environment from
public checkout `723f62ad22f584ed481016a91b466f526ff007b2`, without inherited
Python dependency overlays. All 153 dependency installations succeeded, the
previously audited MMCV wheel was reused, and all 18 official scorer modules
imported. `pip check` reported exactly the four disclosed messages above.
See [the replay receipt](../results/quality_environment_fresh_replay.json) for
source/archive, lock and wheel hashes and individual step outcomes. This is
installation/import evidence, not a clean metadata check or a full V-score.
Complete real-video scoring remains an acceptance gate. Paired Camera Motion
runtime verification in this fresh environment has now completed on two LAST
and two corresponding reference videos. All official outputs match the prior
environment, with two applicable units and a mean of 0.0 for each state.
See [the paired runtime receipt](../results/quality_fresh_camera_pair.json).
This validates one scorer on four inputs, not all eighteen scorers or full V-score.

