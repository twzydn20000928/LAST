# Baseline contracts and implementation provenance

The primary comparison must keep512information bits and the frozen generation
configuration. Different native redundancy mechanisms are not described as an
equal-coded-length comparison. Baseline integration is still in progress.

One historical native VideoShield Hunyuan I2V integration video has completed all
seven actual MP4 conditions. `results/videoshield_seven_conditions_verified.json`
records independently checked videos, native-state/extraction receipts, public
reader source and decoded-bit counts:512/512 for clean, noise, compression, blur,
drop and clip;511/512 for insert. Its attack identifier is `integration-case-0`,
not a primary `paper-...` identifier. It therefore does not establish a matched
comparison with primary LAST/LFG cases, a400-video result, fresh-environment
generation, or exclusive timing. The historical overlay runtime and private
native state remain explicit in the evidence; decoded messages are not public.

## LFG paper-equation adaptation

`last.lfg` implements normalized3D Haar LLL spreading, per-channel population
standard deviation scaling and direct latent correlations. `last.lfg_schedulers`
injects into the predicted clean latent over the final10of50steps at strength.15.
Hunyuan keeps FlowMatchEuler; Wan keeps flow UniPC. Replacing Wan UniPC with Euler
for convenience is not allowed in this reproduction.

The first causal latent is reserved. Sixteen dynamic latent frames form eight
Haar time cells. Each cell carries two independently spread copies of the same
592bit BCH codeword; each sign has a Rademacher carrier of16384coordinates.
The1184superimposed signs are divided by sqrt(1184). SHA256 domain-separated keys
seed PCG64 per Haar cell. These packing/PRNG choices make the repeated-message
adaptation explicit; they are not claims about an unchanged author implementation.
The original LFG paper describes one code per bit over its chosen LLL geometry.
The LAST supplement requires a16group repeated592bit schedule, so this extension
must be disclosed in comparisons and supplemented by native/shared-carrier controls.

The unaligned reader tail-truncates or repeats the final received frame to65,
encodes the full video and averages16group correlations before BCH. It does not
use attack maps or source frames. This is an explicit frame-count alignment
choice; it does not recover temporal identity. `LFG-C` must remain a separate
matched-carrier control, not silently replace this baseline.

Run the public integration adapter with the same case, key and message as LAST:

```bash
python -m last.smoke --method lfg --family hunyuan --mode i2v \
  --model-dir /path/to/checkpoint --case /private/cases/paper-000.json \
  --key /private/primary-state/keys/00.key \
  --message /private/primary-state/messages/paper-000.bin \
  --output /private/runs/lfg-paper-000 --memory-gib 12 --offload sequential
python -m last.evaluate --family hunyuan --model-dir /path/to/checkpoint \
  --run /private/runs/lfg-paper-000 --video-id paper-000
```

The adapter generates an unmarked reference and a guided video with reset RNG
and identical initial noise. It is an integration/quality runner, not a timing
runner: its total duration includes both generations. Native LFG readout is
selected from the generation receipt. GPU integration remains under validation;
mathematical tests alone do not establish baseline fidelity or robustness.

## Other primary baselines (pending integration)

The shared comparison source is SIGMark-release commit
`3713243f2e002cb21bbc3da896094d39b2b528c9`. Its VideoShield/VideoMark classes
describe themselves as reimplementations; they are not the separate authors'
original packages. The pinned root has no LICENSE file. LAST does not vendor or
relicense this code: obtain it separately from its original repository, preserve
attribution and review upstream terms.

```bash
python -m last.upstream --directory /path/to/SIGMark-python --download
python -m last.upstream --directory /path/to/SIGMark-python
```

The manifest pins Python files by their Git blob hashes. This provides verified
source acquisition, not a completed baseline video runner or installation of all
its dependencies.

Install the pinned optional baseline dependencies and check an upstream noise
interface before attempting expensive video inversion:

```bash
pip install -e '.[video,baselines,test]'
python -m last.baseline_probe --method videoshield \
  --upstream /path/to/SIGMark-python --output /private/probes/videoshield
```

The probe saves/reloads native reference state, validates512information bits,
and reports a direct original-noise round trip. It is **not** video robustness.
`--method videomark` uses a fixed400candidate diagnostic registry and preserves
native lookup. The pinned VideoMark save/load names disagree; our wrapper adds
singular key aliases to private state without editing upstream source. Probe
outputs are private and existing directories are never overwritten.

The Hunyuan generation-only entry point uses the verified native noise writer,
50 Euler steps, CFG6, shift7, bf16 generator and float32 VAE, then exports and
reopens the65-frame512-square CRF18 MP4:

```bash
python -m last.baseline_generate --method videoshield --mode i2v \
  --upstream /path/to/SIGMark-python --model-dir /path/to/Hunyuan-I2V \
  --case /private/case.json --message /private/message.bin \
  --output /private/videoshield-generation
```

`case.json` contains `prompt`, `seed` and an I2V `image` path; `message.bin`
contains64bytes. VideoMark additionally requires `--registry` pointing to the
frozen directory of distinct64-byte messages, including the evaluated message.
The output status is deliberately `completed_generation_only`: inversion,
SGO where applicable, and real-video extraction must be verified separately.
This entry point currently supports Hunyuan only; Wan baseline ports remain open.

The companion extraction command takes no true message or attack index map:

```bash
python -m last.baseline_extract --method videoshield --mode i2v \
  --upstream /path/to/SIGMark-python --model-dir /path/to/Hunyuan-I2V \
  --video /private/videoshield-generation/marked.mp4 \
  --state /private/videoshield-generation/maintained_private.pkl \
  --output /private/videoshield-clean-read
```

Use only your own trusted native pickle state. `decoded.bin` holds512decoded
information bits; compare it with the true message in a separate evaluator.
Add `--temporal` for temporal attacks: SIGMark invokes upstream SGO, while the
other two methods invoke upstream length alignment. The command uses the pinned
inverse Euler scheduler, empty prompt,50steps,CFG6 and shift7. T2V omits the
image argument supplied by upstream's I2V-oriented SGO helper. Failed recovery
or invalid decoder output is recorded as failure, never replaced by fabricated
bits. These are new adapters: CPU tests pass; real-video verification is pending.

### VideoMark registration audit

The pinned VideoMark reader first decodes PRC votes, then selects the nearest
registered message. A registry containing only the evaluated message can return
that answer regardless of corrupted votes. Therefore a one-entry registry is
not an eligible bit-accuracy benchmark. Preserve native registration access, but
freeze a multi-message registry before attacks and disclose its candidate count;
report raw pre-lookup votes separately when that diagnostic is implemented.
Old512bit experiments that removed this lookup are adaptations and cannot be
silently reused as native-reader results. Registration policy must be frozen
before completing this baseline integration.

- SIGMark: retain native PRC redundancy and inversion/SGO readout.
- VideoShield: retain native carrier repetition and non-blind reference access.
- VideoMark: retain native carrier repetition and non-blind reference access.

All ports require upstream revision/license records, numerical interface tests,
real MP4 extraction and per-condition receipts before benchmark eligibility.
Old private pilot runners are references for auditing, not public dependencies.

### End-to-end native integration

```bash
python -m last.baseline_run --method videomark --mode i2v \
  --upstream /path/to/pinned-SIGMark --model-dir /path/to/hunyuan-i2v \
  --case /private/case.json --message /private/messages/sample.bin \
  --registry /private/messages --output /private/videomark-integration \
  --memory-gib 8
```

Use `sigmark` or `videoshield` with the same arguments except `--registry` for
the other native adapters. This command uses the repository's pinned source
manifest and requires the baseline dependencies described above. The message
must contain 64 bytes; VideoMark's frozen registry must contain multiple distinct
64-byte messages including that message. Current integration uses all 400 primary
messages as candidates, not a singleton chosen for the tested video.

The command preserves separate generation and extraction receipts, actual MP4
and native private state. Extraction runs in a separate process with each
baseline's documented reference/registry access; only after it exits does the
evaluator compare decoded bits with truth. These native reference requirements
are not a claim of blind extraction. Failure stops the run and retains the
traceback. Output must be a new private directory; failed runs are not silently
overwritten. This is clean-video integration, not the full attack benchmark,
and concurrent wall time is not the paper's exclusive efficiency measurement.

### Same-map spatial and temporal attacks

```bash
python -m last.baseline_evaluate --run /private/videomark-integration/generation \
  --upstream /path/to/pinned-SIGMark --model-dir /path/to/hunyuan-i2v \
  --video-id paper-000 --clean-extraction /private/videomark-integration/extraction \
  --memory-gib 8
```

Use the same `--video-id` as LAST/LFG to obtain identical stochastic attacks.
The runner imports the same attack function, exports and rereads MP4, and invokes
the native reader in a separate process without the edit map or a separate truth
file. Native reference/registration access remains intact. SIGMark temporal
conditions enable upstream SGO; VideoShield/VideoMark use upstream frame-length
alignment. `--map-seed 0..4` supports the supplementary edit-map repetitions.
An optional clean extraction is reused only after checking method, mode, actual
video hash, native-state hash and successful extraction status. Completed
conditions may resume; a failed/unfinished condition stops with retained evidence
and must be inspected. There is no fake bit vector for a failed extraction.
Do not launch multiple evaluators for the same run/map simultaneously.

### Supplementary LFG development controls

The primary branch stays at strength 0.15 over the final ten steps. The appendix
also specifies a development-only 5-by-3 grid, frozen in
`configs/lfg_development_grid.json`. `last.smoke --method lfg` accepts
`--lfg-alpha` and `--lfg-final-steps`; it records them and refuses to reuse a
completed run with different settings. For example, after preparing a **development**
case and the separate development state:

```bash
python -m last.smoke --method lfg --family hunyuan --mode i2v \
  --model-dir /path/to/hunyuan-i2v --case /private/dev-000-case.json \
  --key /private/development-state/keys/00.key \
  --message /private/development-state/messages/dev-000.bin \
  --lfg-alpha 0.05 --lfg-final-steps 20 \
  --output /private/lfg-controls/a005-n20/dev-000 --memory-gib 8
```

Use the ordinary attack and paired-fidelity commands on each completed output.
All settings share the same development cases, messages and keys. Do not tune
on primary samples or overwrite primary results. The public scheduler tests
check guidance timing and zero-strength equivalence for both Euler and UniPC,
including the dynamic 16-frame I2V interface and full 17-frame interface.
Actual development grid results remain pending. These options retain LFG's
random CDMA/Haar writer; they are **not** the supplementary shared-codebook
LFG-C control described below.

### Shared-codebook LFG-C control

`last.smoke --method lfg-c` applies late predicted-clean guidance through the
same Euler/UniPC adapters, but replaces the native random Haar carriers with
LAST's per-group orthonormal DCT codebooks and the same repeated 592-bit codeword.
It does **not** invoke ELMC's minimum-margin projection. `last.evaluate` uses
the identical CCTA front end and BCH decoder as LAST for this explicit method.

The supplement does not give the complete carrier scaling equation. Our declared
reconstruction uses `s_g = sqrt(1776/592) C_g^T b`, which has mean coordinate
energy one for orthonormal rows. At each guided step, compute the population
standard deviation of the group's 1776 selected DCT coefficients and add
`alpha * std_g * s_g` in those coordinates. Inverse DCT maps the update back to
the dynamic latent frames; the causal first latent frame stays unchanged.
This changes the carrier parameterization and variance domain relative to Haar
LFG and is a controlled adaptation, not unchanged LFG author code.

Use a new output directory, the development cases/state, and explicit strength
and final-step arguments as above. Mathematical tests verify carrier signs,
unit-energy normalization, expected update norm, zero-strength behavior and
causal-frame preservation. Actual-video verification and development-only
PSNR/SSIM calibration remain pending. Do not call it matched distortion until
the measured development results meet the specified budget; no parameter is
selected to match a target paper accuracy.

Freeze the full supplemental grid before choosing an operating point:

```bash
python -m last.lfg_calibration --method lfg-c --family hunyuan \
  --output /private/new-lfg-c-development-plan.json
```

This enumerates all 80 disjoint development cases at each of the 15 declared
strength/step combinations (1200 runs). It only creates a plan; it does not
launch generation. Each item supplies the arguments for `last.smoke`, using
the development image, key and message, followed by paired `last.quality`.
The initial alpha=.05, ten-step integration is only one cell, not a selected
operating point. Select only after complete coverage, using development mean
per-video PSNR within33.1±0.1dB and mean SSIM≥.950. If several points qualify,
our explicit tie-break is PSNR distance, then fewer steps, then smaller strength;
this tie-break is a reconstruction detail rather than a rule stated in the paper.
If none qualify, report an unmatched control. Never choose by primary accuracy.
Keep an exact copy of the generation input `case.json` in each run directory.
After computing paired quality for the grid, run:

```bash
python -m last.lfg_calibration_report --plan /private/new-lfg-c-development-plan.json \
  --root /private/lfg-c-grid --output /private/new-calibration-report.json
```

The report verifies manifests, complete grid identity, generation case/parameters,
video hashes and fidelity definitions. Missing cells leave selection null;
unmatched fidelity leaves selection null even when the grid is complete. It
never reads bit-accuracy fields to choose a point. Mixed writer-source versions
require a separate audit rather than automatic pooling. Real-video completion
of the full calibration grid remains pending.

The first scheduled grid cell (`dev-000`, strength0.025, final5steps) has now
completed generation and paired fidelity evaluation. Running the public report
command against the full frozen grid verified both MP4 hashes, the development
case, parameters and manifests. `results/lfgc_first_grid_verified_report.json`
retains all1200 expected observations: only1 is complete and selection is null.
That one video's PSNR is42.5864dB and SSIM0.975846; these are not an80-video
candidate mean or a matched-fidelity operating point. The report selects by
fidelity only and does not use message accuracy to choose parameters.

### Native LFG writer with CCTA reading only

`last.lfg_native_reader` reuses already-exported native-LFG attack MP4s; it does
not regenerate or rewrite them. Native temporal Haar combines two dynamic latent
frames, so candidates contain eight received frames plus one duplicated prefix.
The VAE produces three latent frames; excluding its causal prefix leaves the
two frames needed for the original Haar transform. The reader uses the original
1184 random CDMA carriers per Haar pair, averages the two repeated 592-bit
responses, and forms eight candidate pair identities. CCTA uses eight-frame
spacing for this control; LAST's default four-frame grouping is unchanged.
The eight-pair frontend is an explicit adaptation to the native writer's support,
not a change to native embedded signals or an assertion of recovered alignment.

```bash
python -m last.lfg_native_reader --family hunyuan \
  --model-dir /path/to/hunyuan-i2v --run /private/original-lfg-run \
  --output /private/original-lfg-ccta-read
```

The original generation and all seven original attack receipts must be complete.
The runner verifies received-video hashes, supplies no truth or edit map to
alignment, then compares final decoded bits with truth. Predictions remain in
the private output directory. Test coverage includes eight-frame spacing and
short-window padding. One completed Hunyuan I2V diagnostic is recorded in
`results/lfg_native_ccta_integration.json`: clean/noise/compression/blur/drop/
insert/clip give 504/486/493/496/365/385/430 correct bits out of512, versus
504/485/492/496/357/305/399 for the original received-order reader on the same
MP4s. No condition recovers the entire message; every BCH status is failure.
This is one sample, not a population estimate or evidence of correct grouping.
This control is distinct from `--method lfg-c`, which changes the
writer's carrier parameterization.

To compare both readers on your own primary Hunyuan I2V generations, set
`PRIMARY_ROOT` to the directory containing `hunyuan/i2v/lfg/paper-000`,
`HUNYUAN_MODEL` to the model directory, and `READ_ROOT` to a private output
directory. Start with completed original-reader runs in manifest order. Set
`COUNT` to the number of completed cases (400 for the paper protocol).
Run from the repository root using Bash and the installed project environment.

```bash
set -e
mkdir -p -m 700 "$READ_ROOT"
for ((i=0; i<COUNT; i++)); do
  id=$(printf 'paper-%03d' "$i")
  python -m last.lfg_native_reader --family hunyuan --model-dir "$HUNYUAN_MODEL" \
    --run "$PRIMARY_ROOT/hunyuan/i2v/lfg/$id" --output "$READ_ROOT/$id"
done
python tools/lfg_reader_pairs.py --root "$PRIMARY_ROOT" --outputs "$READ_ROOT" \
  --count "$COUNT" > "$READ_ROOT/paired-counts.json"
python tools/lfg_reader_table.py "$READ_ROOT/paired-counts.json"
```

Each reader output needs a fresh per-case directory. The comparator checks
the manifest case, edit map, original and received MP4 hashes, and recounts
the CCTA predictions against the private 512-bit messages. The table can
also be acquired incrementally on Linux. Use the following instead of the
generation loop above while the primary experiment is still producing videos:

```bash
python tools/run_lfg_reader_campaign.py --root "$PRIMARY_ROOT" --outputs "$READ_ROOT" \
  --model-dir "$HUNYUAN_MODEL" --first 0 --stop 400 --follow
```

The worker waits for the next primary case in manifest order, runs the reader
on its seven received MP4s and audits the saved predictions. Restarting the
command verifies completed cases before advancing. A failed or incomplete
reader directory is preserved for inspection. Once the requested cases are
complete, export paired counts with `tools/lfg_reader_pairs.py` as above.
The table can
subsequently be rendered on CPU from the exported JSON alone. When auditing
the original archived videos, add `--report` with their earlier paired primary
report to also check its baseline counts and file fingerprints. Independent
generations can produce different MP4 fingerprints.

### Wan-2.2 native-carrier integration (real-video validation pending)

`last.baseline_generate` now accepts `--family wan22` for the three native
initial-noise carriers. It retains their original512-bit message/state handling,
including VideoMark's multi-message registry, and uses the A14B T2V/I2V pipeline
with50-step flow-UniPC, guidance5, shift5, bfloat16 generation and float32 VAE.
Wan's per-channel latent mean/std are restored before decoding; Hunyuan keeps
its scalar VAE scaling and Euler/CFG6/shift7 defaults.

Channel normalization roundtrip and registry tests pass, but real Wan
native-carrier GPU generation and extraction have not been validated.
Native efficiency adapters remain Hunyuan-only. The single-case integration
runner accepts an explicit family and forwards it to generation and extraction:

```bash
python -m last.baseline_run --family wan22 --method videomark --mode i2v \
  --upstream /path/to/pinned-SIGMark --model-dir /path/to/Wan-I2V-A14B \
  --case /private/cases/paper-000.json \
  --message /private/primary-state/messages/paper-000.bin \
  --registry /private/primary-state/messages \
  --output /private/new-wan-videomark-integration --memory-gib 8
```

Use a new output directory and retain failed attempts. VideoMark requires the
full frozen message registry; do not substitute a singleton correct answer.
The runner evaluates truth only after the separate extractor has exited.

The experimental `last.baseline_extract --family wan22` entry point now uses
Wan's per-channel mean/std, CFG5 for both A14B experts, and the appropriate
T2V/I2V pipeline. A VAE facade supplies normalized mode latents to upstream
SIGMark SGO, which otherwise assumes a Hunyuan scalar scale. The actual VAE
inside the pipeline is unchanged, including image-conditioning encoding.
Native PRC detection, group search and reference access remain upstream code.

Extraction retains the upstream inverse Euler scheduler with shift5 and50
steps. This is an explicitly reconstructed inversion adaptation: the supplied
manuscript specifies UniPC generation but not a Wan inverse-solver recipe.
Generation remains UniPC; no claim of exact inverse-UniPC or bitwise inversion
is made. On Diffusers0.35.2, both real Wan pipeline classes accept the required
call parameters and the inverse scheduler yields50 timesteps with51 ascending
sigmas from0 to1. Five normalization/adapter tests pass. These CPU checks do
not establish real-video extraction accuracy, temporal SGO correctness, or
complete Wan baseline reproduction. Use explicit `--family wan22`; the default
extractor family remains Hunyuan.

## Native VideoMark real-video integration

`results/videomark_native_integration.json` records one completed Hunyuan I2V
65-frame exported-video test using pinned native VideoMark. Clean extraction
recovered 512/512 information bits and the full message. The MP4, private state,
generation/extraction receipts and independently recomputed bit count were
checked before export. An initial extraction failed under concurrent GPU memory
pressure; the successful retry reused the identical MP4, and the original
failure remains recorded. This is integration evidence only: no attack sweep,
multi-video ranking or formal efficiency value is established by this result.
Secrets and predicted messages are excluded from the public record.

### Isolated-environment real-video check

A single existing VideoMark Hunyuan I2V MP4 was re-extracted using public
commit `1d331462fff777cd825e23f630b8ce3aa18b23fa` in the reconstructed
`native_clean_v1` environment, without historical Python overlays. All 512
information bits were recovered and the decoded bytes exactly matched the
previous environment. Input video, private native state, and original receipts
were checked for changes; evaluation truth was read after extraction exited.
See `results/native_clean_videomark_video.json`. This verifies one clean-video
extraction, not all baselines, attacks, model families, or benchmark timing.

### Execute the development grid

```bash
python -m last.calibration_run --plan /private/lfg-c-plan.json \
  --development configs/development_manifest.json --primary configs/primary_manifest.json \
  --root /private/lfg-c-grid --state /private/development-state \
  --conditioning /private/development-conditioning --model-dir /models/hunyuan-i2v \
  --writer-root /path/to/pinned-LAST-checkout --writer-python /path/to/video-python \
  --max-jobs 1 --memory-gib 8 --min-free-mib 32000
```

Use the same frozen writer checkout and dependency environment throughout a grid.
The runner invokes public `last.smoke` and `last.quality`, keeps per-cell command
receipts, and uses file locks to avoid duplicate workers. A bounded pass skips
unavailable conditioning images; rerun after their generation completes. It
verifies the full grid, disjoint manifests, development state, conditioning
prompt/seed/image hash and completed videos before reuse. An unfinished cell
requires explicit inspection rather than automatic overwrite or retry. The
memory gate is an execution setting, not a scientific parameter; it does not
reserve memory against unrelated jobs. Coordinate concurrent launchers.

The runner never selects a candidate or evaluates message accuracy. Run
`last.lfg_calibration_report` after acquisition; incomplete grids still return
no selected parameter. Existing active cells started by other controllers must
finish before using this runner on their output root. All commands must use
reader-owned private keys and state, not the authors' experimental secrets.

### Wan attack sweep entry point

After a native Wan integration completes, its generation directory can be passed
to the same attack evaluator. The model family is read from the verified
generation receipt and forwarded explicitly to extraction. Reused extraction
receipts must match family, mode, method, video, private state and temporal flag.

```bash
python -m last.baseline_evaluate --run /private/new-wan-videomark-integration/generation \
  --upstream /path/to/pinned-SIGMark --model-dir /path/to/Wan-I2V-A14B \
  --video-id paper-000 --memory-gib 8 \
  --clean-extraction /private/new-wan-videomark-integration/extraction
```

This covers the same seven exported MP4 conditions and map seeds as LAST.
SIGMark temporal conditions invoke native SGO through the Wan adapter; the
other native baselines retain their original length alignment. This entry point
is implemented and its family/provenance checks are tested; real Wan baseline
attack results remain pending. Do not infer robustness from CPU interface tests.


### Frozen native primary campaign

```bash
python -m last.native_campaign plan --manifest configs/primary_manifest.json \
  --output /private/native-primary-plan.json
python -m last.native_campaign run --plan /private/native-primary-plan.json \
  --manifest configs/primary_manifest.json --root /private/native-primary \
  --state /private/primary-state --image-root /path/to/images \
  --models /private/model-paths.json --upstream /path/to/pinned-SIGMark \
  --family hunyuan --mode i2v --method videomark --max-jobs 1 \
  --memory-gib 8 --min-free-mib 32000
```

The plan covers 4,800 videos: three native methods, both model families and
both modes, with all 400 manifest samples in every cell. Model paths use the
same four keys as the LAST/LFG campaign. Run from the pinned repository root
in the native dependency environment. Any scientific source change requires an
explicitly audited new plan. Filters do not shrink the planned denominator.

To reproduce one named video, keep the full plan and all three pipeline filters. For example, run from the pinned checkout:

```bash
python -m last.native_campaign run --plan /private/native-primary-plan.json \
  --manifest configs/primary_manifest.json --root /private/native-primary \
  --state /private/primary-state --image-root /path/to/images \
  --models /private/model-paths.json --upstream /path/to/pinned-SIGMark \
  --family hunyuan --mode i2v --method sigmark --shards 400 --shard 0 \
  --max-jobs 1 --memory-gib 8 --min-free-mib 32000
```

These arguments select only `hunyuan/i2v/sigmark/paper-000` in the frozen plan. For `paper-037`, use `--shard 37`. Each pipeline contains the same 400 manifest entries in index order. In contrast, `--max-jobs 1` alone can advance to the next eligible video if an earlier one is locked or already complete. A `waiting_resources` message means the worker returned before generation. Verify completion through the sample's job receipt and all seven attack receipts.

The runner uses the original native carrier/key setup and the full frozen
400-message VideoMark registry. It invokes public generation and attack CLIs;
it does not add BCH or replace native reference access. The shared manifest key
slot is retained as metadata, not a claim that native keys equal LAST keys.
Private job records and locks live under `.native-jobs`; generated videos keep
the standard family/mode/method/sample directory layout for `last.report` and
`last.quality_inputs`. Completed jobs must pass actual artifact checks before
reuse. Interrupted/failed or unowned directories require inspection; automatic
overwrite and unrecorded retries are refused. The memory check is a launch gate,
not a resource reservation against unrelated processes.

This orchestrates generation and seven attacks only. Official V-score scoring,
paired fidelity where required and exclusive efficiency acquisition remain
separate workflows. The full native campaign has not run; real Wan integration
must be validated before launching its full matrix. CPU plan/command tests do
not establish robustness or complete reproduction.


### Isolated SIGMark clean-video integration

`results/native_clean_sigmark_video.json` records successful extraction of one
65-frame Hunyuan I2V MP4 using public reader revision
`1d331462fff777cd825e23f630b8ce3aa18b23fa` in the isolated native environment,
without historical Python overlays. All 512 information bits and the complete
message were recovered. The actual decoded bytes were independently compared
with truth after extraction exited, and video, native state, reader source and
receipt hashes were checked. An earlier shared-GPU out-of-memory attempt remains
preserved; the successful attempt reused the identical video without changing
scientific settings. This is one clean-video integration, not a temporal SGO
attack result, a 400-video aggregate or exclusive-GPU timing evidence.

### SIGMark noise-retry integration

`results/sigmark_noise_recovery_verified.json` records one actual Hunyuan I2V
noise-attack extraction: **398/512 information bits (77.734375%)**, without
complete-message recovery. The noise MP4 is unchanged from the original attempt
that failed because of shared-GPU memory contention. The original failure and
failed extraction remain preserved privately; the successful retry uses public
reader revision `f72378689d8f62bd5a580d5dc4d5469daad50507` in the isolated native
environment. Its 50-step inversion completed successfully. An independent audit
recomputed the bit count from decoded bytes and checked the actual video,
private state, message, source, extraction receipt and original-failure hashes.

Only hashes and aggregate counts are published; decoded messages and native
state remain private. This verifies one recovered acquisition path, not the full
seven-condition campaign, a method ranking or an exclusive timing measurement.
The standard `last.baseline_evaluate` command above runs the attacks on a new
user-generated case; the private recovery paths are not required to run it.

### SIGMark compression integration

`results/sigmark_compression_verified.json` records the subsequent CRF28
compression extraction on the same 65-frame Hunyuan I2V integration case:
**483/512 information bits (94.3359375%)**, without complete-message recovery.
The independent audit recomputed the count from decoded bytes and checked the
actual marked and compressed video hashes, native state, attack and extraction
receipts, public reader revision `f72378689d8f62bd5a580d5dc4d5469daad50507`,
and successful 50-step inversion. It also verified the recorded CRF28 export
command. The remaining attacks are not implied complete by this result.
This is a single-case integration check, not a method ranking or an exclusive
efficiency measurement; private messages and native state are not published.

### SIGMark single-video attack results

All seven rows refer to the same 65-frame Hunyuan image-to-video integration case. The JSON records in `results/` include the bit counts and provenance for each extraction.

| Attack | Correct information bits | Bit accuracy | Exact message |
|---|---:|---:|---|
| Clean | 512/512 | 100.00% | Yes |
| Noise | 398/512 | 77.73% | No |
| Compression (CRF28) | 483/512 | 94.34% | No |
| Blur | 512/512 | 100.00% | Yes |
| Deletion (35 received frames) | 295/512 | 57.62% | No |
| Insertion (95 received frames) | 289/512 | 56.45% | No |
| Remove 30 consecutive frames (35 received frames) | 398/512 | 77.73% | No |

The [temporal recount](../results/sigmark_temporal_verified.json) checks the original edit maps, native temporal extraction receipts, received videos and current prediction bytes. The archived receipts have no prediction-file digest. This case is reported separately from the 400-video primary acquisition.

The [input pairing audit](../results/sigmark_integration_pairing.json) identifies this case as paper-000. The generation receipt matches the exact LAST case file. The prompt, generation seed, conditioning image, 512 message bits and all seven edit maps match. Both methods used their own generated video. On this one matched case the temporal bit counts were:

| Condition | LAST correct bits | SIGMark correct bits |
|---|---:|---:|
| drop | 371/512 | 295/512 |
| insert | 424/512 | 289/512 |
| clip | 502/512 | 398/512 |

LAST counts come from paper-000 in the [Hunyuan I2V sample records](../results/hunyuan_i2v_last_first100_robustness.json). The integration run predates the frozen native acquisition worker and has no corresponding completed worker receipt. Its results are kept as a matched historical comparison.

### Wan 2.2 VideoMark clean extraction

On one 65-frame I2V video, the native reader used a registry of 400 messages and
recovered 254 of 512 bits (49.61%). The full message was incorrect. The initial
extraction encountered a conditioning-image interface error. The retry used the
same CRF18 MP4 and saved native state. An independent byte comparison verified
the count. Model settings and receipt hashes are in
[the single-video record](../results/wan22_videomark_clean_verified.json).
The decoded 512-bit value matched a different registered message exactly. Both the intended and selected messages were present in the original, fingerprint-verified registry.
## Recounting a native baseline score on CPU

After extraction, you can independently recount a VideoMark, VideoShield or
SIGMark score from the private 64-byte message and the 64-byte prediction.
Run this command with Python 3.10 or newer:

```bash
python tools/recount_native_predictions.py --run /private/sample
```

For an independently extracted clean video, add `--clean-extraction /private/clean-reader-output`.
For a single completed condition use `--condition clean` (or its attack name).
For another attack-map seed, select its directory with `--attacks`. The command
checks the received MP4 against both receipts, verifies available prediction
digests and outputs only counts and provenance. The JSON field
`prediction_digest_present` shows whether a historical digest was available.

### Hunyuan text-to-video VideoMark, first primary sample

For [paper-000](../results/hunyuan_t2v_videomark_paper000.json), six of the
seven MP4 conditions returned the same incorrect registered message (264/512
correct bits). Insertion returned a different incorrect registered message
(278/512). Each prediction matched exactly one of the 400 registry entries.
A diagnostic CPU float32 read of the saved original initial latent recovered
512/512 bits with the same registry. The clean-video benchmark value is
264/512. This comparison leaves the source of the end-to-end loss unresolved.

### Hunyuan T2V paired LAST and VideoMark results

The [first four paired videos](../results/hunyuan_t2v_last_videomark_first_four.json)
use matching prompts, generation seeds, 512-bit messages and temporal edit maps.
Clean extraction recovered the entire message on four of four LAST outputs
and two of four native VideoMark outputs. The corresponding bit accuracies
were 2048/2048 and 1555/2048. The file covers seven conditions and contains
the counts for each sample. All 28 VideoMark scores were recounted from the
retained decoded bytes against their registered messages. These historical
extraction receipts omit the decoded-byte digest. This subset covers four of
the 400 planned samples per method.

### Hunyuan I2V VideoShield memory during generation

On the shared L40, the first formal VideoShield run exhausted device memory
during VAE decoding. The allocation request was 1.06 GiB, global free memory
was 22.38 MiB and PyTorch had allocated 4.72 GiB under an 8 GiB process limit.
The run had already written private initialization and template state but had
yet to export the marked MP4. A free-memory check before model loading did
not predict the available memory during decoding. For this configuration,
reserve capacity through VAE decoding. Keep failed receipts and private state
together when retrying with the original sample, seed, checkpoint and payload.
Only a completed generation with an exported MP4 is eligible for attack scoring.

On a shared GPU the native worker can exit successfully after printing
`waiting_resources`, before starting a sample. For a single worker that
rechecks admission after 60 seconds, substitute
`python tools/wait_native_campaign.py` for `python -m last.native_campaign run`
in the command above. Use the native environment and the same arguments.
A nonzero child exit is propagated for inspection; completed or bounded
worker invocations return normally.
The Hunyuan I2V VideoShield first primary case can be exported for Tables 1 and 2 with `python tools/audit_videomark_prefix.py --method videoshield --mode i2v --count 1 --manifest configs/primary_manifest.json --plan /private/native-plan.json --root /private/primary --output videoshield-audit.json`. The [recount](../results/hunyuan_i2v_videoshield_first1.json) matches all seven earlier counts and verifies both methods used the frozen conditioning image and message. The seven archived predictions have no extraction-time prediction digest; the audit recounts their current bytes and compares with the archived scores.

To include the supplementary PSNR column for the archived LFG prefix, pass
`--fidelity results/hunyuan_i2v_paired_fidelity_first16.json` to
`tools/lfg_reader_table.py`. For new generations use the fidelity report
measured on those generations. The command selects the completed reader IDs
and matches each clean MP4 fingerprint. It averages per-video PSNR in dB.
Both reader rows share the same writer and the same videos, hence also the
same PSNR. The archived LFG value is 22.40 dB for paper-000 alone and 22.77 dB
for the 16-video prefix. Reader accuracy requires its own extraction receipts.

The first formal Hunyuan I2V case can be recounted on CPU:

```bash
python tools/lfg_reader_table.py results/hunyuan_i2v_lfg_ccta_first1.json \
  --fidelity results/hunyuan_i2v_paired_fidelity_first16.json
```

On paper-000, original/CCTA correct bits out of 512 were 349/365 after
deletion, 276/403 after insertion and 358/465 after clipping. Neither reader
recovered the entire message in any of the seven conditions. These results
describe one paired video from the primary 400-case protocol.

The first two formal cases are in `results/hunyuan_i2v_lfg_ccta_first2.json`.
Supply that file to the same command. The second deletion yielded 368/512
original versus 319/512 with CCTA; across both cases the totals were
717/1024 versus 684/1024. For insertion the totals were 557/1024 versus
853/1024 and for clipping 818/1024 versus 932/1024. No temporal condition
recovered an entire message in either arm. All seven first-case records
match the earlier one-case snapshot.
The three-case snapshot is `results/hunyuan_i2v_lfg_ccta_first3.json`. Across three Hunyuan I2V videos the original/CCTA correct bit counts were 1077/1061 after random deletion, 889/1246 after insertion and 1168/1394 after contiguous removal, out of 1536 per condition. Both readers recovered one of three clean messages.

For five paired samples, pass [the five-case reader report](../results/hunyuan_i2v_lfg_ccta_first5.json) to the same command. Both readers recovered 2/5 clean messages and 0/5 after random deletion. Original and CCTA deletion recovery was 1,783/2,560 and 1,753/2,560 bits, respectively, on identical received MP4s. Both writer fidelity rows are 22.26 dB. All 21 overlapping observations agree with the earlier prefix.
For native primary campaigns the recount accepts `--family hunyuan` or `--family wan22` along with the generation mode and method. It checks the family recorded by the extraction process and the plan assignment for each sample. The explicit Hunyuan command reproduced the 36-case VideoMark report byte for byte. The Wan branch requires native primary generation and seven completed attack receipts on each requested sample.

The [seven-case paired report](../results/hunyuan_i2v_lfg_ccta_first7.json) contains 49 observations, including all 35 observations from the five-case report. With identical received MP4s, original LFG and LFG + CCTA recovered 2,174 and 3,070 bits after insertion, 2,737 and 3,247 after contiguous removal, and 2,470 and 2,477 after random deletion (3,584 bits per condition). Both recovered 3/7 whole messages clean and 0/7 after random deletion. The direction of the small random-deletion difference changed between the five- and seven-case prefixes.

### Wan VideoMark single-condition recount

On the archived Wan I2V VideoMark sample paper-000, the original clean read
recovered 254/512 bits. The [noise read](../results/wan22_i2v_videomark_noise_paper000.json)
on the same marked source recovered 264/512. The [CRF28 compression read](../results/wan22_i2v_videomark_compression_paper000.json) recovered 240/512. All three conditions have zero entire messages
recovered. For attack receipts that store message and prediction hashes,
recompute an individual observation with
`python tools/recount_native_attack.py --run /private/native-generation --video-id paper-000 --condition noise`.
The command verifies the generated and received MP4s, native registration and
extraction receipt before recounting the private message. When the generation receipt records message and registration hashes, both must also match the scored inputs. This one-clip
integration has separate provenance from the full primary campaign.

### Replay the seven-condition reader comparison

Run from the repository root after installing the package. The first table reproduces the available supplement Table 12 columns. The second gives the correct and total information bits for each condition, pooled across the same videos.

```bash
python tools/lfg_reader_table.py results/hunyuan_i2v_lfg_ccta_first17.json \
  --fidelity results/hunyuan_i2v_fidelity17.json --all-conditions
```

The eight paired clips cover two prompts. Under insertion, the original and
CCTA readers recovered 2,465 and 3,494 of 4,096 information bits, respectively.
Under random deletion they recovered 2,795 and 2,814 bits, with zero complete
messages for both readers. All 49 observations shared with the seven-case
snapshot match, including the received-video and extraction-receipt hashes.

The [11-case report](../results/hunyuan_i2v_lfg_ccta_first11.json) adds three
seeds of a third prompt. Original LFG and LFG+CCTA read 3,341 and 4,691 correct
bits after insertion, 4,237 and 5,008 after contiguous removal, and 3,741 and
3,839 after random deletion. Each condition has 5,632 information bits. Both
readers recovered 3/11 entire messages clean and 0/11 after random deletion.

The [12-case report](../results/hunyuan_i2v_lfg_ccta_first12.json) covers three prompts with four seeds each. On identical insertion-edited MP4s, CCTA recovered 5,046 of 6,144 information bits versus 3,623 for the original LFG reader. Under random deletion the counts were 4,153 versus 4,053, with zero complete messages for either reader. Clean counts matched at 6,022 bits and three complete messages each. All 77 paired observations shared with the 11-case report matched exactly.

The [13-case report](../results/hunyuan_i2v_lfg_ccta_first13.json) adds the first seed of the fourth prompt. On this clip the original and CCTA readers recovered 278 and 416 bits after insertion, 313 and 468 after contiguous removal, and 320 and 329 after random deletion (512 bits per condition). Across all 13 paired clips both readers recovered three entire clean messages and zero after random deletion. The 84 observations shared with the 12-case report match exactly.

The [16-case report](../results/hunyuan_i2v_lfg_ccta_first16.json) covers four prompts with four seeds each. All 91 paired observations from the 13-case report agree. On identical edited videos, CCTA increased insertion bit accuracy from 58.22% to 80.57%, clipping from 75.16% to 87.41%, and random deletion from 65.26% to 67.46%. Neither reader recovered a complete message after deletion. Clean, noise, compression and blur each lost 1 to 11 correct bits out of 8,192. The sample covers 16 of the planned 400 videos.

The [17-case report](../results/hunyuan_i2v_lfg_ccta_first17.json) adds paper-016 and verifies all 112 observations shared with the 16-case report. Random deletion yielded 5,722 versus 5,916 correct bits (original LFG versus CCTA), with zero complete messages for either reader. After compression, the original reader had more correct bits overall (8,186 versus 8,181 of 8,704), while CCTA recovered one entire message versus zero.
