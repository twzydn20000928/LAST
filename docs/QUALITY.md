# Official quality evaluation integration status

Paired PSNR/SSIM is implemented in `last.quality`; it is not the VBench2 V-score.
The full18dimension official scorer remains an open reproduction requirement.
Historical small-sample or proxy scores are not imported into the new benchmark.

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
Upstream model acquisition may require network access. This entry point does
not silently redirect checkpoints, patch official code or substitute scores.
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
