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
