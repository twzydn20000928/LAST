# Official quality evaluation integration status

Paired PSNR/SSIM is implemented in `last.quality`; it is not the VBench2 V-score.
The full18dimension official scorer remains an open reproduction requirement.
Historical small-sample or proxy scores are not imported into the new benchmark.

The first new paired semantic diagnostic is stored in
`results/semantic_quality_integration.json`: one Hunyuan I2V Complex Landscape
case scores0.2for LAST and0.0for its unmarked reference, with one valid video
per state. It uses the official scoring function and auxiliary questions,
explicit local checkpoints, SDPA and SigLIP microbatch4 over all64sampled frames.
The previous full-batch attempt failed with GPU memory exhaustion and remains
in the audit history. This example does not establish an overall quality gain,
independent replication, or a completed V-score; the public summary keeps
`v_score` null and includes raw scores and receipt/video hashes.

The SIGMark comparison's augmented prompts and auxiliary question metadata are
pinned by37Git blob hashes in `configs/quality_metadata_manifest.json`:

```bash
python -m last.upstream --manifest configs/quality_metadata_manifest.json \
  --directory /path/to/SIGMark-quality-metadata --download
```

The script preserves the original files and verifies their bytes. Their source
is SIGMark-release commit3713243f2e002cb21bbc3da896094d39b2b528c9. Match each
augmented prompt to its exact row in the corresponding dimension prompt file,
then retain that row's official auxiliary questions. Do not invent replacement
questions or evaluate these structured dimensions as unrestricted custom input.

Prepare per-dimension metadata against the actual completed primary runs:

```bash
python -m last.quality_inputs --manifest configs/primary_manifest.json \
  --metadata-root /path/to/SIGMark-quality-metadata \
  --run-root /private/primary-runs --family hunyuan --mode i2v --method last \
  --output /private/quality-inputs/hunyuan-i2v-last
```

The command verifies all37upstream file hashes, generation identity and video
presence, preserves official auxiliary fields, and records video hashes. It
withholds scorer files if any of the400inputs are absent, while saving a complete
coverage report. `--allow-partial-diagnostic` explicitly permits diagnostic
metadata but does not permit a full-score claim. Reference uses the paired
unmarked videos from the LAST runs. Output directories must be new, preserving
previous coverage snapshots instead of silently overwriting them.

The primary manifest requires20videos per ordinary dimension (five prompts,
four seeds each), and60Diversity videos (three prompts,20seeds each). A complete
score must include the prescribed inputs, valid/applicable denominators and
all18dimension outputs. Missing or not-applicable results are not zeros.
## Official dimension runner

Before loading large scoring models, audit all eighteen dimension imports:

```bash
python -m last.quality_doctor --upstream /path/to/VBench/VBench-2.0 \
  --output /private/quality-import-audit.json
```

Each import runs in its own offline CPU subprocess with a timeout. The audit
retains import tracebacks, scorer source hashes and Python search paths.
For successful imports it also records the actually loaded package versions,
module paths and source hashes, plus loaded MMCV binary-extension hashes. These
can differ from package-manager metadata when compatibility overlays are used.
This inventory is evidence for constructing a standalone environment, not by
itself an installation lockfile or a validation of all compiled GPU operations.
Explicit dependency overlays can be supplied with repeated `--extra-pythonpath` options;
these are recorded, not treated as a clean installation. The output must be new.
Import success does not verify scoring weights, GPU operators or numerical scores.
The audit adds upstream's bundled dependency directories without changing their
files. If an overlay is required, its packages must still be pinned and validated
in the eventual standalone quality environment.

Audit reused package source against its installed wheel RECORD before claiming
an unmodified environment:

```bash
python -m last.package_audit --dist-info /env/site-packages/mmdet-3.0.0.dist-info \
  /env/site-packages/mmcv-2.2.0.dist-info --output /private/package-integrity.json
```

This checks Python-source hashes without importing the packages. RECORD itself
is local evidence, not proof of upstream authenticity. The reused diagnostic
environment has a disclosed MMDetection 3.0.0 modification: its MMCV upper-version
guard was increased to 2.3.0 to permit the locally built MMCV 2.2.0. The audit
found this one changed Python file among 1,158 MMDetection files and none among
128 MMCV files. This bypass is not an upstream-supported compatibility claim.
A small CUDA ROI Align check passed, but full anatomy evaluation and a standalone
validated environment remain pending. Do not reproduce this environment merely
by installing these two version numbers and assume the same behavior.

Acquire the exact upstream source (including its license files) without
executing its code during download:

```bash
python -m last.source_archive --manifest configs/vbench_source.json \
  --archive /path/to/cache/VBench-fd18b3d0.zip \
  --directory /path/to/VBench --download
```

An existing matching archive can be reused by omitting `--download`. The full
archive SHA256 is checked before extraction, unsafe paths are rejected, and
`LAST_SOURCE_RECEIPT.json` records every extracted file hash. Output must be a
new directory. The fixed upstream revision is preserved; this does not install
its dependencies or download scoring weights, and its own license applies.

`last.quality_score` calls the upstream `compute_<dimension>` function without
changing its questions, frames, model code or score formula. Use VBench source
revision `fd18b3d055cb0fc6f066ca90fe2c3c8cbb698490`, with `--upstream` pointing to
its `VBench-2.0` directory. Install that scorer's dependencies separately; the
LAST video environment alone does not include all official scoring models.

```bash
python -m last.quality_score --upstream /path/to/VBench/VBench-2.0 \
  --inputs /private/quality-inputs/hunyuan-i2v-last \
  --dimension Camera_Motion --submodules /private/camera-submodules.json \
  --device cuda --output /private/quality-scores/hunyuan-i2v-last/Camera_Motion
```

The submodules JSON is the exact dictionary expected by the upstream dimension
function (for Camera Motion: `{"repo":"facebookresearch/co-tracker","model":"cotracker2"}`).
Upstream model acquisition may require network access. For the tracker-based
dimensions, an explicit `--cotracker-checkpoint /path/to/cotracker2.pth` avoids
unversioned `torch.hub` code acquisition: it uses the selected VBench checkout's
bundled CoTracker2 predictor with `window_len=8` and strict checkpoint loading.
The receipt identifies this model-loading adaptation and hashes both the weight
file and all bundled tracker Python files. The official scoring function remains
unchanged. Other hub requests fail instead of silently downloading a substitute.
Without that option the official model loader is used as-is. This entry point
does not silently redirect checkpoints, patch official code or substitute scores.
For LLaVA-based dimensions, `--llava-siglip /path/to/local/siglip` explicitly
selects a local vision tower through the bundled LLaVA implementation. Combine
it with `--llava-attention sdpa` (default for this adapter) or
`--llava-attention flash_attention_2`. The adapter records the attention backend,
SigLIP file hashes and bundled LLaVA Python hashes. SDPA is a disclosed backend
adaptation, not a claim of bit-identical Flash Attention outputs. The dimension's
official questions, 64-frame sampling where prescribed, generation parameters
and score function remain unchanged. Set `HF_HUB_OFFLINE=1` and
`TRANSFORMERS_OFFLINE=1` when testing cached models so an upstream fallback cannot
silently acquire a different model. The submodules JSON must still supply the
local LLaVA checkpoint under `llava`. Runtime validation of these large models
is separate from the CPU import audit.
If full-batch SigLIP encoding exhausts GPU memory, the explicit option
`--llava-vision-batch 4` processes the same sampled images in groups of four,
concatenating features in original frame order. This does not remove frames or
change questions, pooling or downstream scoring. The receipt records the
microbatch size; the default0 retains the original full batch. SigLIP encodes
each image independently, but a changed batch shape may change floating-point
roundoff. Tests verify frame count/order using an independent-image fixture;
they do not prove bit-identical scores from the pretrained model. Keep runtime
failures and compare actual scoring results before declaring this adapter valid.
The receipt records source, question-input and submodule-configuration hashes,
runtime, seed and applicability counts. `official_result.json` retains raw
outputs. Missing/duplicate video results or unexpected score ranges fail the
run. `-1` remains not applicable; all-not-applicable gives a null mean.
Diversity uses prompt-level units and requires 20 videos per prompt, even in
explicit diagnostic mode. Other dimensions use video-level units.

This runner has unit coverage for missing outputs, applicability and Diversity
denominators; full GPU scorer integration is still pending. Official model
acquisition, isolated scorer dependencies and aggregate validation still need
completion in this release. Do not interpret availability of this command as
evidence of a completed V-score.

## Aggregate verified dimension outputs

Store each dimension's output under `scores/<Dimension>/` as in the command
above, then run:

```bash
python -m last.quality_report --inputs /private/quality-inputs/hunyuan-i2v-last \
  --scores /private/quality-scores/hunyuan-i2v-last \
  --output /private/quality-scores/hunyuan-i2v-last/summary.json
```

The report checks question-input hashes, recomputes dimension means from raw
official outputs, and checks the prescribed five prompts times four videos per
ordinary dimension and three prompts times twenty videos for Diversity. It
averages dimensions within each of the five official categories, then averages
the five categories equally. This is not an unweighted mean of eighteen scores.
Missing, failed or entirely not-applicable dimensions yield a null V-score;
partial input coverage also yields null. Valid/applicable counts remain visible
for every dimension; not-applicable samples are never converted to zeros.
Receipts and raw outputs are hashed into the report for traceability.
# Paired fidelity table aggregation

Run `python -m last.fidelity_summary --plan /private/primary-plan.json --root
/private/primary --output /private/new-fidelity-summary.json` to aggregate the
planned PSNR/SSIM pairs. The command rechecks each reference/marked MP4 hash and
generation identity. Missing samples prevent final scores. The main aggregate
is the arithmetic mean of per-video PSNR; PSNR computed from average MSE is
reported separately and must not be silently substituted. Identical pairs have
infinite PSNR, represented by null plus an explicit infinity flag, not zero.
This table does not supply the official V-score or perceptual/dynamic quality.

## MMCV build compatibility work (not yet an accepted scorer environment)

The upstream anatomy stack uses MMDetection 3.0, whose version check requires
MMCV below 2.1. MMCV 2.0.1 forces C++14, whereas the selected PyTorch 2.5 build
requires C++17. `tools/build_mmcv201.py` provides the explicit build-only fix:
it verifies the pinned source archive, records the patch and hashes, changes
only compiler-standard flags, and builds a wheel without installing it. It
does not bypass MMDetection's version guard or change scoring formulas.

With the intended quality-environment Python and PyTorch already installed:

```bash
python tools/build_mmcv201.py --output /private/new-mmcv-build \
  --cuda-home /usr/local/cuda-12.1 --cuda-arch 8.9 --jobs 4
```

Use an unused output directory. An existing downloaded archive can be supplied
with `--source-archive`; the same SHA-256 check applies. Architecture 8.9 is the
L40 used here, not a universal GPU setting. Compilation hides CUDA devices and
does not launch GPU kernels. `receipt.json`, `cpp17.patch`, and `build.log`
retain provenance and failures. The CUDA toolkit and host compiler must be
available in addition to PyTorch; this command does not install system tools.

At publication of this helper, the server build is still running. The helper's
checksum, extraction-safety and patch tests pass, but no successful wheel,
CUDA-operator validation, complete dependency lock, or numerical anatomy-score
validation is claimed. Do not treat this as a completed V-score installation.

