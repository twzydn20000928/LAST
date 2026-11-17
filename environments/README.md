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

