# Main-paper ablations and margin sweep

## Supplement energy calibration: reconstruction boundary

Supplement Section G specifies64 wrong-key responses per development candidate,
but does not state the calibration transform. `last.energy_calibration` explicitly
implements a reconstruction, not a verified original implementation: energy is
mean absolute correlation over592 coded bits; for each of16 group positions,
pool development candidate/key energies and fit the median and1.4826 times MAD
(median absolute deviation), with a1e-8 scale floor. A received energy is scored
as `(energy - development_median) / development_scale`. Candidates have equal
weight. The statistics remain frozen at test time; no messages or source-frame
maps enter this calculation.

The fitting function requires the complete80-video disjoint development manifest
and64 responses per candidate. It records degenerate groups rather than concealing
zero dispersion. Acquisition still must verify that these are64 distinct wrong
keys, bind energies to actual candidate features and their video/source hashes,
and preserve private keys. These requirements are **not** proved by array shape
or the algebra tests. Real development acquisition, video-CLI integration,
shared normalization across all crossed readers and the supplement AUROC experiment remain
pending. The current primary CCTA/raw-energy fallback is unchanged. No calibrated
energy benchmark or Table13/14 reproduction is claimed by this implementation.

`last.null_energy.responses` supplies the response-computation primitive. It
requires64 distinct32-byte wrong keys and a nonempty real-key exclusion registry,
rejects overlap, and streams the existing public QR carrier construction one
group at a time. `new_wrong_keys` uses operating-system randomness; callers must
persist the returned keys only in private run state and reuse them for replay.
The output has candidate-by64-by16 energies, with key fingerprints and precision
recorded separately. The caller must supply **all** actual development/test keys;
this function cannot infer omitted keys. Its input must be the same normalized
1776-dimensional candidate features as the reader, with acquisition provenance
audited separately. Tests of streaming and key exclusion are not real-video
calibration results; the streaming test substitutes a simple known projection
to check all1024 key/group indexes without claiming a full QR experiment.

`last.calibrated_reader.align` now applies the frozen transform to candidate
correlations and reuses the energy fallback's search: choose the best group for
each window, then select nonoverlapping monotonically increasing groups with
start difference equal to four times the group-index difference within a segment.
Repeated group slots across segments retain the higher calibrated score. Its
message readout averages L2-normalized selected group vectors, and its metadata
records selected window/group identities for alignment auditing. This is still
an explicit reconstruction; it is not exhaustive joint search over every group
hypothesis, nor authentication. Primary CCTA and default raw-energy fusion keep
their existing behavior. Synthetic bias/spacing tests verify this API only;
real calibrated-reader results and shared-fusion crossed comparisons are pending.

Acquire candidate features once, using the same frozen VAE, segmentation, window
construction and feature normalization as `last.evaluate.extract`:

```bash
python -m last.feature_cache --video /private/received.mp4 --family hunyuan \
  --model-dir /models/hunyuan --output /private/new-candidate-cache
```

This command needs no key, message or attack map. Its private output contains
`features.npy`, `nodes.json` and a receipt binding them to the actual MP4, feature
source and local VAE files. All are checked again before completion. Consumers
must use `last.feature_cache.load(cache_directory, original_video)` to verify
the artifacts. Keep caches private; key-free acquisition does not make video
features anonymous. `--reader received` and `--no-scan` provide explicit control
variants, not the primary full sliding-window input. Successful acquisition is
not proof that a cache belongs to the development split: later calibration must
also bind it to the frozen development manifest and complete key registry.

The CPU-only response acquisition CLI binds the saved energies to the candidate
cache, actual MP4, key files and implementation hashes. Prepare a private JSON
list containing **every** real development/test key as a 64-character hexadecimal
string; do not put that list, the wrong-key bank, or the output in the repository.

```bash
python -m last.null_cache init-keys --real-keys /private/all-real-keys.json \
  --output /private/wrong64.json
OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 python -m last.null_cache acquire \
  --cache /private/new-candidate-cache --video /private/received.mp4 \
  --wrong-keys /private/wrong64.json --real-keys /private/all-real-keys.json \
  --output /private/new-null-responses
```

Reuse the saved wrong-key bank for replay. Existing outputs are not overwritten;
failures retain their receipt. Each acquisition performs 1024 actual QR carrier
projections and stores candidate-by-64-by-16 energies. It verifies input/source
hashes again before completion. It cannot detect omitted real keys or certify
development membership: the complete registry and 80-video manifest must still
be audited before fitting. Providing this CLI does not claim that the full
development calibration or AUROC experiment has been run.

## Primary component protocol

The main-paper protocol uses30I2V samples for ablations and three fixed
development samples for the margin sweep. The30sample ablation/timing IDs are
frozen in `configs/paper_subsets.json`, covering all18primary dimensions using
a metadata-only deterministic rule. The file discloses that selection occurred
after the first primary sample was measured; no results are inputs to selection.
A one-sample integration check is not the reported30sample experiment. A
separate disjoint development manifest for the three-sample sweep and80video
supplement is frozen in `configs/development_manifest.json`; actual development
runs remain pending. Primary samples must not be used for tuning.

Aggregate reader outputs with `python -m last.ablation_summary --index index.json
--output /private/new-ablation-summary`. The index maps frozen sample IDs to
their reader-ablation directories. Missing sample IDs remain in the denominator;
only complete cells receive final scores. JSON and CSV retain observed partial
rates separately. Paired variants must reference identical video/codebook hashes,
and mixed writer methods or reader revisions are rejected. This verifies recorded
provenance, not a new audit of the MP4 bytes; retain raw files and receipts.
The fixed-target writer experiment remains a separate required control.

The first actual member of the frozen30 subset is recorded in
`results/formal_reader_ablation_first_case.json` (`paper-003`, 28 completed
condition/reader rows). Its source video, attacked MP4s and codebook hashes were
checked before export. This is one of30 samples, distinct from the earlier
`paper-000` integration diagnostic. Do not combine the two as two formal subset
members or treat the first formal sample as the completed paper table.

To regenerate the subset file at a new destination:

```bash
python -m last.subsets --manifest configs/primary_manifest.json --output /private/paper-subsets.json
```

For each completed LAST run with all seven attack MP4s:

```bash
python -m last.reader_ablation --run /private/last-run \
  --family hunyuan --model-dir /path/to/Hunyuan-I2V \
  --output /private/ablations/sample-id
```

The four rows are full CCTA, response-energy/spacing without CGC, segment-start
four-frame grid without SWS, and received-order grouping without CCTA. All use
identical attack files. Without CCTA, the first received frame is treated as the
causal prefix, at most64remaining frames are grouped in fours, and a short final
group repeats its last frame. Missing groups remain absent. This deterministic
choice is explicit because the main text does not specify short-tail handling.
There is no source-position oracle. Feature caching is per received video and
does not share features across attacks; these runs are not timing measurements.

For the supplement's crossed writer/reader control, use this same command with
`--run /private/lfg-c-run` and a separate output directory. The generation receipt
must identify the shared-codebook `lfg-c` writer; native Haar/CDMA `lfg` videos
are rejected because they require `last.lfg_native_reader` instead. No video is
rewritten when changing the reader. Each row records the writer, codebook hash
and relevant reader implementation hashes. Resuming older outputs that lack
this provenance is refused; retain those records and choose a new directory.
This adds an executable control, not evidence that LFG-C has met the required
matched-fidelity development criterion or completed its benchmark.

For the writer ablation, rerun `last.smoke` with the same case, key and message
and append `--fixed-target`; use a new output directory. Then run `last.evaluate`
with the same video ID (identical deterministic attack maps) and `last.quality`.
This replaces only the minimum-margin projection with fixed signed targets.

For Figure4, independently generate the same three development cases at each
`--mu 0.1`, `0.25`, `0.5`, `0.75`, `1.0`, each in its own directory, followed by
the same evaluation and quality commands. Keep key/message/seed fixed across
strengths. Average bit accuracy over the six attacked conditions, excluding
clean; report paired PSNR and SSIM separately. The causal profile remains
`[0,mu,mu,2*mu,mu,...]`. Do not choose the three examples by the resulting score.

Default main-paper generation is unchanged (`--mu .5`, no `--fixed-target`).
For supplement Table16's uniform writing control, add `--uniform-profile`
to `last.smoke --method last --mu .5` and use a new run directory. All sixteen
message groups then have margin0.5 instead of the default first-group0 and
fourth-group1 exceptions. The initial causal VAE latent remains untouched.
Keep case/key/message and subsequent attack IDs identical to the paired primary
run. The receipt records the switch and refuses reuse under a different profile.
This alternative does not replace any primary run; test-video quality must not
be used to tune its settings. The fixed-target matched-PSNR control separately
requires development calibration before test evaluation.
Writer and reader adapters require real-video integration verification; no
manuscript ablation number is imported as a measured result.

## Strictly paired endpoint writer control

Generate a LAST run with the additional `last.smoke --save-endpoint` option.
The private `endpoint.pt` is the actual normalized diffusion output before
embedding. It must not be committed or distributed with public results.
Then change only the writer rule on that exact endpoint:

```bash
python -m last.writer_replay --run /private/minimum-margin \
  --model-dir /path/to/same-model --output /private/fixed-target --fixed-target
python -m last.evaluate --run /private/fixed-target --family hunyuan \
  --model-dir /path/to/same-model --video-id paper-003
python -m last.quality --reference /private/fixed-target/reference.mp4 \
  --marked /private/fixed-target/marked.mp4 --output /private/fixed-target/quality.json
```

Evaluate the minimum-margin run with the same video ID and map seed. Replay
retains the original margin/profile, codebook, message and reference video;
it loads only the frozen VAE and changes `fixed_target`. Without that flag it
can check the original writer path. Both families are supported; use the
matching family for evaluation. The same model directory is required to avoid
accidentally switching decoders. Inputs are hash-checked before and after replay.
The output directory must be new. Replay completion means video export only;
extraction and fidelity remain separate measured steps. Its runtime is not full
generation time. This equal-margin control is not the separate development-
calibrated matched-PSNR control. The first paired real-video replay has completed all seven conditions; the full 30-case ablation remains pending.

# Oracle grouping diagnostic

`last.oracle_reader` is deliberately **not blind**: it reads the evaluator's
true temporal edit map. It supports existing LAST and shared-codebook LFG-C
videos, without changing their writer or attacked MP4s.

```bash
python -m last.oracle_reader --family hunyuan --model-dir /path/to/hunyuan-i2v \
  --run /private/completed-marked-run --output /private/oracle-read
```

Original frame zero is the causal prefix; frames 1--4 belong to group zero,
5--8 to group one, and so on. Inserted foreign frames are excluded and duplicate
original identities count once. A missing slot uses the nearest surviving frame
within its true group, choosing the earlier original frame on a tie. Completely
absent groups contribute no evidence. The reader never retrieves deleted pixels
from the unmarked or pre-attack video. This fill rule is an explicit
reconstruction choice because the supplement does not specify it.

Each recovered group uses the same five-frame VAE encoding, normalized DCT
feature, codebook and BCH as LAST; group correlations are L2-normalized and
averaged. The receipt reports complete groups, filled slots and missing groups,
pre/post-BCH counts, exact-message recovery, and attack/video hashes. Truth bits
are compared only after readout. Do not include these map-assisted results in
deployable extraction claims or treat them as a guaranteed upper bound: missing
content, padding and local VAE re-encoding remain sources of error.


## Audit a completed writer pair

```bash
python -m last.writer_pair_report --minimum /private/minimum-margin \
  --fixed /private/fixed-target --output /private/new-writer-pair-report.json
```

This command verifies the replay's source artifacts, identical private inputs
and reference MP4, paired generation settings, all seven received-video hashes,
temporal edit maps, bit-count ranges and quality references. Private state and
messages are excluded from its output. Missing evidence causes an error rather
than a partial aggregate. The counts remain measured extraction receipts; this
CPU audit does not rerun extraction.

`results/paired_writer_first_case.json` records frozen case `paper-003` at margin
0.5. Minimum-margin versus fixed-target recovered respectively
512/512, 512/512, 499/497, 512/512, 332/272, 501/496 and 504/503 information bits
(out of 512) for clean, noise, compression, blur, drop, insert and clip.
Paired fidelity was 30.1615 versus 29.6723 dB PSNR and 0.93191 versus 0.92837 SSIM.
These are one equal-margin endpoint pair, not the full ablation table,
a matched-quality experiment, or evidence of statistical superiority.

The first formal Wan I2V case now has a completed seven-condition oracle
comparison in `results/wan_first_oracle_diagnostic.json`. The blind/oracle
correct-bit counts (out of 512) are:

| Condition | Blind | True-map-assisted diagnostic |
|---|---:|---:|
| Clean | 512 | 512 |
| Noise | 512 | 512 |
| Compression | 493 | 493 |
| Blur | 512 | 512 |
| Delete 30 | 255 | 501 |
| Insert 30 | 377 | 512 |
| Clip 30 | 487 | 494 |

The received MP4 hashes and original attack receipts were verified for every
pair. The deletion gap shows that substantial information remains readable
with true-group assistance in this sample. It does not isolate alignment alone:
the oracle also changes missing-slot filling and fusion. Deletion still does
not recover the complete message. This is one diagnostic case, not primary
blind performance, an aggregate ablation or a guaranteed upper bound.

### Verify identical exported inputs

The reader-ablation runner verifies the marked-video hash and every completed
attack receipt against the actual received MP4 before loading the VAE. It also
rechecks the received file and secret codebook after extraction. Replaced
files, mismatched conditions and legacy receipts without received-video hashes
are rejected; audit historical artifacts rather than filling in missing hashes
as if they had been recorded originally. These checks leave the scientific
reader variants unchanged and do not retroactively validate earlier runs.

