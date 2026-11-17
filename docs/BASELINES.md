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
