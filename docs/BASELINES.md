# Baseline contracts and implementation provenance

The primary comparison must keep512information bits and the frozen generation
configuration. Different native redundancy mechanisms are not described as an
equal-coded-length comparison. Baseline integration is still in progress.

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
