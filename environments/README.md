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
their additional environments are not covered. Do not add historical server
overlay directories to `PYTHONPATH` to conceal missing dependencies. Keep
failed installation logs and report differences rather than silently relaxing
versions. Model weights, secret state and input datasets are not dependencies
bundled in this lock.
