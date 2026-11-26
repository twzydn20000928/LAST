# Main-paper ablations and margin sweep

## Supplement energy calibration: reconstruction boundary

Supplement Section G specifies 64 wrong-key responses per development candidate,
but does not state the calibration transform. `last.energy_calibration` explicitly
implements a reconstruction, not a verified original implementation: energy is
mean absolute correlation over592 coded bits; for each of16 group positions,
pool development candidate/key energies and fit the median and 1.4826 times MAD
(median absolute deviation), with a 1e-8 scale floor. A received energy is scored
as `(energy - development_median) / development_scale`. Candidates have equal
weight. The statistics remain frozen at test time; no messages or source-frame
maps enter this calculation.

The fitting function requires the complete 80-video disjoint development manifest
and 64 wrong keys per candidate, each evaluated at all 16 group positions. It
records groups with zero dispersion. Acquisition must verify 64 distinct wrong
keys, bind energies to actual candidate features and their video/source hashes,
and preserve private keys. These requirements are **not** proved by array shape
or the algebra tests. Real development acquisition, video-CLI integration,
shared normalization across all crossed readers and the calibrated energy rows
remain pending. The measured clean-chain consistency row of Table 13 is documented
below. Its AUROC compares correct and incorrect group assignments on marked clips.
A video-level false-acceptance rate requires a separate decision threshold and
counts of accepted and tested negative videos.

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

`last.controlled_fusion.readout` supplies a separate shared readout primitive for
those controlled comparisons: one592-coefficient vector per unique recovered
group, L2 normalization with floor1e-8, equal group mean, then the same BCH512.
It rejects duplicate group slots and reports empty evidence explicitly even if
the all-zero hard word has a valid BCH syndrome. This is not authentication.
Tests check invariance to positive group amplitudes and group ordering, exact
synthetic-message recovery, duplicate rejection and missing-evidence handling.
The primary CCTA chain-weighted fusion and received-order sum remain unchanged.
`last.controlled_reader.decode` now connects received-order, CCTA and calibrated
energy selection to this same readout. Received-order requires its own fixed
prefix/window cache; it cannot silently reuse the sliding-window candidate list.
CCTA keeps its per-segment consistency ranking, but repeated group slots across
segments use the highest-ranked chain (earlier segment on an exact tie) before
equal-group fusion. This is a disclosed controlled change from primary CCTA's
weighted segment fusion. If no consistency chain exists, raw-energy/spacing
selection supplies groups, followed by the same shared fusion.

`decode_oracle` accepts evidence already reconstructed using a true attack map
and explicitly labels its output nonblind. It does not reconstruct that evidence
itself. Synthetic tests recover the same known message through all four readout
paths with identical fusion outputs; they do not establish real-video alignment.
The CPU-only blind extraction command consumes an audited feature cache:

```bash
python -m last.controlled_extract --reader ccta --video /private/received.mp4 \
  --cache /private/candidate-cache --codes /private/codes.pt \
  --output /private/new-controlled-readout
```

Use a separately acquired `--reader received` feature cache for the received
control. `--reader calibrated_energy` additionally requires `--calibration`
pointing to the audited80-video fit; its VAE and feature implementation must match
the cache. The command has no truth-message or attack-map argument, checks inputs
and source before/after, and saves decoded bits privately. BCH success alone is
not watermark detection. The output must be evaluated separately against truth.

An actual existing LFG-C development cache (62 candidates) completed controlled
CCTA extraction, selecting groups7 and8. An independent CPU comparison using
public revision `41dfb73` found primary/controlled readouts both252/512, identical
decoded bits and maximum soft-response difference3.73e-9. This one local chain
does not establish equivalence across temporal edits or multiple segments.
Received-order, calibrated-energy and full video-level crossed experiments are
still pending. Neither primary results nor existing frozen workers use these controls.

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

To create the list from the two state directories used for generation, run the
following command on the experiment server. It checks both state receipts
against the manifests before collecting the eight key slots from each.

```bash
python - /private/development-state /private/primary-state /private/all-real-keys.json <<'PY'
import hashlib
import json
import os
import sys
from pathlib import Path

development, primary, output = map(Path, sys.argv[1:])
keys = []
for split, state in (("development", development), ("primary", primary)):
    manifest = Path("configs") / f"{split}_manifest.json"
    receipt = json.loads((state / "state.json").read_bytes())
    if receipt["manifest_sha256"] != hashlib.sha256(manifest.read_bytes()).hexdigest():
        raise ValueError(f"{split} state belongs to a different manifest")
    keys.extend((state / "keys" / f"{slot:02}.key").read_bytes() for slot in range(8))
if any(len(key) != 32 for key in keys) or len(set(keys)) != 16:
    raise ValueError("Expected 16 distinct 32-byte keys")
os.umask(0o077)
with output.open("x", encoding="utf-8") as stream:
    json.dump([key.hex() for key in keys], stream)
PY
```

```bash
python -m last.null_cache init-keys --real-keys /private/all-real-keys.json \
  --output /private/wrong64.json
OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 python -m last.null_cache acquire \
  --cache /private/new-candidate-cache --video /private/received.mp4 \
  --wrong-keys /private/wrong64.json --real-keys /private/all-real-keys.json \
  --output /private/new-null-responses
```

For the LAST operating point (Hunyuan I2V, margin 0.5), the first completed
development acquisition, `dev-000`, had 62 candidate windows and 63,488
energies. The saved array uses axes (candidate, wrong key, group). For each
of the 62 windows we independently recomputed the four combinations of key
indices 0 and 63 and group indices 0 and 15 from the saved feature and the
keyed codebook. All 248 energies agreed at relative tolerance 1e-6 and
absolute tolerance 1e-8. This checks a subset of projections for one video.
Fit the calibration after collecting all 80 development cases.

The [first ten LAST acquisition records](../results/last_development_null_first10.json)
cover dev-000 through dev-009. Across 605 candidate windows the private arrays
contain 619,520 energies. Replaying the four key/group combinations above for
every window reproduced all 2,420 sampled energies within the stated tolerances.
Each public record gives the video and response-receipt digests, candidate count,
total response count and replay count. The 80-video calibration fit is pending.

The [eleventh acquisition](../results/last_development_null_dev010.json)
adds 62 windows and 63,488 responses. To repeat the four sampled projections
for every window, run the following at the original acquisition paths (the
private receipt records absolute input paths and file digests).

```bash
python tools/replay_null_responses.py --video /private/received.mp4 \
  --cache /private/new-candidate-cache --responses /private/new-null-responses \
  --wrong-keys /private/wrong64.json --real-keys /private/all-real-keys.json
```

For dev-010 all 248 sampled projections matched. Across the eleven videos,
2,668 sampled projections have been checked out of 683,008 stored responses.

Reuse the saved wrong-key bank for replay. Existing outputs are not overwritten;
failures retain their receipt. Each acquisition performs 1024 actual QR carrier
projections and stores candidate-by-64-by-16 energies. It verifies input/source
hashes again before completion. It cannot detect omitted real keys or certify
development membership: the complete registry and 80-video manifest must still
be audited before fitting. Providing this CLI does not claim that the full
development calibration or AUROC experiment has been run.

An [actual acquisition integration](../results/null_cache_real_integration.json)
now verifies this command from public revision `bf67a4c`: one existing LFG-C
development video produced 62-by-64-by-16 responses using real QR carriers.
The audit checked actual artifacts, excluded all16 registered primary/development
keys, and recomputed the first key/group projection for all62 candidates.
The recorded57.11seconds is concurrent CPU elapsed time, not formal efficiency.
This single LFG-C input validates acquisition; it does not supply the LAST
development calibration or any detection/AUROC result.

Once all80 **LAST** development clips have their own audited responses, fit
the disclosed reconstruction with a private JSON index. Each entry contains
`video_id`, `run` (generation directory), `features` (candidate cache directory),
and `responses` (null acquisition directory). Include each `dev-000` through
`dev-079` exactly once. A single LFG-C integration input is not accepted here.

On Linux, use this command to collect the responses and create the index.
The runs directory contains the 80 generated LAST development directories.
Use the same private key files on each invocation. A rerun verifies completed
artifacts and resumes at the next missing stage. If a stage failed, preserve
its output by moving that stage directory aside before retrying. The index
is written after all 80 entries pass the collection checks.

```bash
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 python tools/collect_development_calibration.py \
  --development configs/development_manifest.json --primary configs/primary_manifest.json \
  --runs /private/last-development/hunyuan/i2v --model-dir /models/hunyuan \
  --wrong-keys /private/wrong64.json --real-keys /private/all-real-keys.json \
  --output /private/development-calibration

python -m last.null_fit --index /private/development-calibration/index.json \
  --development configs/development_manifest.json --primary configs/primary_manifest.json \
  --development-state /private/development-state --primary-state /private/primary-state \
  --output /private/frozen-energy-calibration.json
```

The fitter checks all80 IDs before reading acquisition files, actual LAST keys
against their registered slots, unchanged margin/profile, generation cases,
video/cache/response hashes, and a common VAE, writer, feature implementation and
64-key null bank. All16 real keys must be excluded. Inputs are checked again after
fitting. The output is the frozen median/MAD reconstruction plus provenance;
keep it private because it includes key fingerprints and video identifiers.
Tests cover the completeness gate, underlying fit algebra, and an80-entry
synthetic file integration with a known expected center. Mutated video, key,
feature and energy files, changed margins and incomplete exclusion registries
are rejected. These fixtures are not generated videos or real QR acquisitions;
a full80-video real-data fit has not yet run. This command does not establish test performance,
chain discrimination or AUROC.

## Primary component protocol

### Generate LAST development inputs

The LAST development inputs have a separate runner from the LFG-C strength grid.
It uses all80 frozen development rows, their private development keys/messages,
and the registered first-frame conditioning images. The LAST margin remains0.5
with the main-paper nonuniform profile. It does not select videos by quality.

```bash
python -m last.development_run plan --family hunyuan \
  --development configs/development_manifest.json --primary configs/primary_manifest.json \
  --plan /private/last-development-plan.json
python -m last.development_run run \
  --development configs/development_manifest.json --primary configs/primary_manifest.json \
  --plan /private/last-development-plan.json --state /private/development-state \
  --conditioning /private/development-conditioning --model-dir /models/hunyuan \
  --output /private/last-development --max-jobs 1
```

Run from a frozen checkout using the video environment. A plan binds the complete
source; do not create it before modifying that checkout. Repeat the bounded run
command to continue. Each pass skips only completed jobs whose recorded inputs
and output hashes still match. Missing conditioning images remain pending;
unfinished or failed jobs require inspection and are not overwritten. A per-case
lock prevents duplicate launches. The memory gate is a local preflight, not a
global GPU reservation: coordinate concurrent launches externally.

The runner invokes the existing generation and paired-fidelity commands; it does
not fit energy statistics or measure AUROC. Source/plan and conditioning tests
have passed, but full80-video GPU execution is not yet complete.

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

For a batch stored as `formal-ablation-003/readers` for `paper-003` and
analogously for the other cases, build the index once from the frozen list.
Run the following from the repository root with `ABLATION_ROOT` set to the
directory containing those case directories:

```bash
python - "$ABLATION_ROOT" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
ids = json.loads(Path("configs/paper_subsets.json").read_bytes())["ablation_i2v_30"]
index = {video: f"formal-ablation-{video.removeprefix('paper-')}/readers" for video in ids}
with (root / "formal-reader-index.json").open("x") as stream:
    json.dump(index, stream, indent=2)
PY
python -m last.ablation_summary --index "$ABLATION_ROOT/formal-reader-index.json" \
  --output "$ABLATION_ROOT/summary-snapshot-01"
```

Reuse the index and choose a fresh output directory for each snapshot.
Each cell counts the completed videos for one attack and one reader variant
out of 30. JSON records the receipt hashes used for that snapshot.

The first actual member of the frozen30 subset is recorded in
`results/formal_reader_ablation_first_case.json` (`paper-003`, 28 completed
condition/reader rows). Its source video, attacked MP4s and codebook hashes were
checked before export. This is one of30 samples, distinct from the earlier
`paper-000` integration diagnostic. Do not combine the two as two formal subset
members or treat the first formal sample as the completed paper table.

### Paired measurements for paper-003

Each entry below counts correct information bits out of 512. Within each
condition the four readers received the same MP4. CGC denotes cross-group
consistency and SWS denotes sliding-window search.

| Reader | Clean | Noise | Compression | Blur | Drop | Insert | Clip |
|---|---:|---:|---:|---:|---:|---:|---:|
| Full | 512 | 512 | 502 | 512 | 327 | 499 | 506 |
| Without CGC | 230 | 240 | 275 | 261 | 273 | 260 | 237 |
| Without SWS | 504 | 475 | 456 | 473 | 274 | 494 | 452 |
| Without CCTA | 512 | 512 | 503 | 512 | 270 | 278 | 280 |

For this case, removing CCTA cost 221 correctly recovered bits after insertion
and 226 after clipping. After compression the same change gained one bit.
The [28 reader records](../results/formal_reader_ablation_first_case.json)
include the received-video fingerprints.

The writer replay used one shared diffusion endpoint and margin 0.5. Each
writer produced its own marked MP4. Its minimum-margin clean MP4 has a different
SHA256 from the clean MP4 in the reader experiment above, even though both
records use sample ID `paper-003`. Use the minimum-margin row below as the
reference for the fixed-target comparison.

| Writer | Clean | Noise | Compression | Blur | Drop | Insert | Clip | PSNR (dB) | SSIM |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Minimum margin | 512 | 512 | 499 | 512 | 332 | 501 | 504 | 30.16 | 0.9319 |
| Fixed target | 512 | 512 | 497 | 512 | 272 | 496 | 503 | 29.67 | 0.9284 |

Both comparisons cover one of the 30 planned samples. The
[writer replay record](../results/paired_writer_first_case.json) contains
the unrounded quality scores and the received-video hashes for both writers.

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

To acquire the entire grid in one Linux process, prepare development state and
conditioning with the same manifest used above. From the repository root run:

```bash
python tools/run_margin_sweep.py --state "$STATE" --conditioning "$CONDITIONING" \
  --model-dir "$MODEL" --family hunyuan --output "$SWEEP"
python tools/plot_margin_sweep.py --index "$SWEEP/index.json" --output figure4
```

The first command reads the three case IDs and five margins from the frozen
configs. It runs generation, MP4 attack/extraction and paired quality for each
cell. It reuses completed outputs in its sweep directory and writes the plot
index after verifying all fifteen cells. Give each backbone its own output
directory. The plotting command also writes Appendix Table 5.

If all three baseline development outputs already exist, add
`--reuse-development "$DEV"` to the acquisition command. Use the Python
package revision recorded in the development plan. The runner checks the
plan, case, key, message, writer configuration, artifact digests and paired
quality receipt, then copies the default-margin inputs into a private sweep
cell. It evaluates the attacks there. Other margins use the same case and
private state.

The first [measured development cell](../results/margin_sweep_dev000_mu05.json)
at μ=0.5 recovered 2,879 of 3,072 attacked bits across six edits on dev-000.
The separate clean condition recovered all 512 bits. Figure 4 requires all
three selected cases at each of the five margins.

For example, set `DEV` to the completed development-generation root, `STATE`
to its private development state, `MODEL` to the same checkpoint and `SWEEP`
to the private sweep root. For one case and one new strength, use:

```bash
id=dev-000
mu=0.25
base="$DEV/$id"
run="$SWEEP/$id/mu-$mu"
slot=$(python -c 'import json,sys; print("%02d" % json.load(open(sys.argv[1]))["key_slot"])' "$base/case.json")
family=$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["family"])' "$base/receipt.json")
mkdir -p "$run"
cp -n "$base/case.json" "$run/case.json"
cmp "$base/case.json" "$run/case.json" || exit 1
python -m last.smoke --case "$run/case.json" --family "$family" --mode i2v \
  --model-dir "$MODEL" --method last --mu "$mu" --output "$run" \
  --key "$STATE/keys/$slot.key" --message "$STATE/messages/$id.bin" \
  --memory-gib 8 --offload sequential &&
python -m last.evaluate --run "$run" --family "$family" --model-dir "$MODEL" --video-id "$id" &&
python -m last.quality --reference "$run/reference.mp4" --marked "$run/marked.mp4" --output "$run/quality.json"
```

Use the three frozen IDs from `margin_sweep_ids`. At μ=0.5, a matching
completed default development run already supplies generation and quality.
Index that directory directly after evaluating its seven conditions.

For a completed sweep, create a private JSON list with one entry per run, e.g.
`{"video_id":"dev-000","run":"dev-000/mu-0.1"}`. Directory paths are relative
to the index. Each run contains its development case, generation receipt, private
key and message, quality receipt, MP4s and all seven evaluation receipts. From the
repository root, in an environment with Matplotlib installed, run
`python tools/plot_margin_sweep.py --index /private/index.json --output figure4`.
The PDF shows one curve per metric. Each bit-accuracy point pools 9,216
information bits (three videos × six attacks × 512 bits). Each quality point
averages three video-level measurements. The accompanying CSV retains the
numerators and denominators. The same command writes Appendix Table 5 to
`table5.md`, including clean accuracy. Each condition uses 1,536 bits per margin.
The collector checks each deletion, insertion and clipping map against the
deterministic map for that development ID. For example, deleting 30 frames
from a 65-frame video leaves 35 received frames, but a different choice of
those 35 frames changes the experiment. The collector checks both the original
indices and the received frame count, even when all strengths used the same
edit. Quality receipts must cover all 65 frames and their PSNR must agree with
the recorded RGB mean squared error. Incomplete sweeps produce no figure or table.

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

## Post-hoc grouping diagnostics

```bash
python -m last.alignment_metrics --video /private/received.mp4 \
  --cache /private/candidate-cache --extraction /private/completed-controlled-read \
  --attack-receipt /private/run/attacks/drop.json --output /private/alignment.json
```

This evaluator reads the true edit map only **after** the blind reader has
completed; it cannot change selection or decoding. An intact window must contain
the four consecutive original identities of exactly one source group, in order.
Windows crossing a boundary, containing inserted pixels or padding/repetition
are not assigned a fictitious true group. They count as errors in
`selected_alignment_accuracy`. The output separately reports group accuracy
among intact selected windows and coverage of available intact groups, each with
explicit counts. An empty denominator is null, not100% or zero by convention.
These explicit denominator definitions are diagnostic choices, not a claim that
the supplement completely specified every aggregation detail.

Three CPU tests cover boundary crossing, foreign/padded/reordered windows,
incorrect group identity and empty/duplicate selections. A real post-hoc check
on the existing clean LFG-C `dev-000` cache found both selected windows intact
but wrongly identified: true groups14/15 were predicted as7/8 (zero-based).
This uses the full unedited generation MP4 verified by hash and identity map;
it is one low-strength development case, not LAST primary performance or the
30-video Table14 experiment. The feature acquisition and blind predictions were
not rerun or changed. Full attacked-video diagnostics remain pending.

## Shared-fusion per-case workflow

Freeze the shared-carrier block only after the full LFG-C development grid has
completed and selected a fidelity-matched point:

```bash
python -m last.controlled_plan --primary configs/primary_manifest.json \
  --development configs/development_manifest.json \
  --calibration-plan /private/lfg-c-development-plan.json \
  --calibration-root /private/lfg-c-development \
  --output /private/frozen-controlled-plan.json
```

This re-audits actual calibration videos/receipts, retains both writers' full400
I2V sample lists, keeps LAST's original margin profile, and freezes four readers
and three conditions (9,600 readouts). The CLI rejects incomplete grids, native
LFG calibration and unmatched fidelity. It creates a plan only; it does not
launch generation or batch extraction. Native LFG-N/CCTA rows are separate.
The current real development grid is incomplete, so no successful full controlled
plan is claimed. Planner tests use synthetic fidelity summaries to check coverage
and rejection logic, not measured calibration results.

With the frozen plan available, reuse the primary LAST writer cases and add
their LFG-C counterparts on the Linux evaluation host. Set `RUNS` to the
existing primary output root and `STATE` to its private key/message state:

```bash
set -e
for ((i=0; i<400; i++)); do
  printf -v id 'paper-%03d' "$i"
  python tools/controlled_writer_case.py --plan "$PLAN" --manifest configs/primary_manifest.json \
    --runs "$RUNS" --model "$MODEL" --state "$STATE" --video-id "$id"
done
```

Each LFG-C run uses the LAST case's exact prompt, conditioning image, seed,
key and 512-bit message. The command calls the generation and MP4 attack
evaluation entry points using the strength and step count selected by the
development grid. It writes to the separate `lfg-c` directory under `RUNS`.
For new cases the runner copies the original LAST carrier tensor inside the
private run directory before generation. For existing cases it checks each
archive against its own generation receipt and accepts a different archive
encoding only when the tensor values and dtype agree.

After generating the two writer blocks with the selected settings and
completing their clean, drop and compression evaluations, render the
800 per-case extraction commands on the execution host. Use the pipeline's
own VAE and its audited 80-video energy calibration:

```bash
python tools/controlled_batch_commands.py --plan /private/frozen-controlled-plan.json \
  --manifest configs/primary_manifest.json --runs "$RUNS" \
  --model /path/to/hunyuan-i2v --calibration /private/full80-frozen-calibration.json \
  --output /private/new-controlled-reads > controlled-reads.sh
bash controlled-reads.sh
```

Each command evaluates one writer and video on all three conditions using
all four readers. Before emitting commands the builder checks each generated
case, conditioning image, seed and recorded writer parameters against the
frozen block. The script runs sequentially and stops on the first failed
command. For a partial run, retain completed outputs and execute the
remaining commands individually with fresh destinations for retries.

```bash
python -m last.controlled_evaluate --run /private/completed-writer-case \
  --family hunyuan --model-dir /path/to/hunyuan-i2v \
  --calibration /private/full80-frozen-calibration.json \
  --output /private/new-controlled-comparison
```

This runs all four controlled readers on the identical clean, delete30 and
compression MP4s required by Table12. Generation and all three attack receipts
must already be complete and verifiable. The CCTA candidate cache is shared by
CCTA and calibrated energy; received-order and oracle acquire their own window
sets. The codebook, VAE, inputs and implementation are hash-checked, and truth is
read only after each extraction subprocess returns. Raw correct-bit counts,
exact-message flags and extraction/feature receipt hashes are recorded per row.
The oracle rows remain explicitly non-blind.

For [Hunyuan I2V paper-000](../results/hunyuan_i2v_last_controlled_paper000.json),
the clean, compressed and deletion MP4 hashes match the corresponding LAST
rows in the [primary evaluation](../results/hunyuan_i2v_primary17.json).
With 30 frames deleted, reading in received order recovered 289/512 bits,
blind CCTA recovered 371/512, and the reader given the true frame map recovered
512/512. The controlled CCTA and independently replayed primary reader agreed on all 512 bit decisions for each of the three MP4s. On deletion both missed the same 141 positions.
All three controlled readers recovered the clean message. On compression they
recovered 484, 486 and 484 bits respectively.

To compare the actual decisions on deletion, run the following on the
experiment host. The command checks the received MP4 and controlled read
receipt, then prints only the number of matching bits and public metadata.

```bash
python tools/compare_blind_predictions.py --video /private/original-case/attacks/drop.mp4 \
  --first /private/completed-independent-reextraction/drop-private.json \
  --controlled-read /private/new-controlled-comparison/drop-ccta-read
```

For legacy runs whose attack receipts predate received-MP4 fingerprints, use the
independent [re-extraction audit](REEXTRACTION.md) and its frozen source checkout.
Prepare an input directory from those verified files on the experiment host:

```bash
python tools/prepare_controlled_replay.py --run /private/original-case \
  --replay /private/completed-independent-reextraction \
  --source /private/source-used-for-reextraction --output /private/new-controlled-input
```

Pass the new directory as `--run` to both evaluation and export. Its three
attack receipts retain the original measurements and identify the original
receipt, verified replay receipt and received MP4 by SHA-256. Video, message
and codebook links resolve to the original private files, which must remain
available at their recorded locations. Standard runs with fingerprinted attack
receipts can use the original case directory directly.

On the evaluation host, recount the 512 predicted information bits for each
completed row and export the public counts and evidence hashes:

```bash
python tools/export_controlled_case.py --run /private/completed-writer-case \
  --evaluation /private/new-controlled-comparison --output controlled-case.json
```

The export preserves the reader set used and checks its coverage of clean,
drop and compression. For the calibrated-energy reader the export records the SHA-256 of the frozen development calibration. The table requires the same calibration across conditions, videos and writers. Keep the source directory layout intact during this
step because the evaluation receipt records absolute paths for its inputs.

Render the shared-fusion measurements from the public counts on CPU:

```bash
python tools/controlled_reader_table.py results/hunyuan_i2v_last_controlled_paper*.json \
  --primary results/hunyuan_i2v_last_first100_robustness.json \
  --primary results/hunyuan_i2v_last_primary100_179.json
```

The two primary reports let the command check each clean, deletion and compressed
MP4 against the main experiment for the same sample and writer. Reader variants
may return different bit counts on those identical inputs.
The GitHub Actions artifact `audited-partial-temporal-diagnostics` includes
this output as `table12-shared-fusion.md`. Its companion `table12-oracle.md`
compares the primary blind reader with the direct true-map reader on a larger
cohort. The two files use different fusion rules and sample counts.

On the same 30-frame deletions for `paper-005` and `paper-006`, received-order
grouping recovered 559/1,024 bits, CCTA recovered 826/1,024, and the reader
given the true edit map recovered 1,024/1,024. Only the assisted reader
recovered either message exactly. All three readers recovered both clean
messages. These 18 measurements use the same frozen source and LAST writer;
the calibrated-energy and matched LFG-C comparisons still require calibration.

For a larger run, pass all per-case exports as positional arguments. Use the
same sample IDs for both writers when comparing them, and keep each model,
reader set and source revision in a separate table. The heading reports the
number of distinct measured videos per supplied writer out of 400.

The default requires the audited full80 development calibration. For a clearly
partial interface check, `--readers received ccta oracle` omits calibrated energy
and records `complete_reader_set: false`; this is not a completed crossed table.
Use a new output directory: failed and interrupted outputs are retained for
inspection rather than silently reused. This per-case wrapper does not generate
the matched LFG-C videos, certify their fidelity match, schedule all400 cases,
or supply the native LFG-N+CCTA rows. Those remain separate unfinished tasks.
Command-contract tests cover map/secret separation, common extraction dispatch
and missing-calibration rejection. A real Hunyuan I2V LAST case completed the
three-reader path using the original attacked MP4s. Each cell below counts
correct information bits out of 512 after the shared fusion and BCH decoder.

| Input for `paper-005` | Received order (blind) | CCTA (blind) | True edit map (assisted) |
|---|---:|---:|---:|
| Clean | 512 | 512 | 512 |
| Delete 30 frames | 268 | 420 | 512 |
| Compression | 501 | 502 | 501 |

On this deletion, CCTA recovered 152 additional bits over received order.
The assisted reader used true group identities and filled missing within-group
frames before fusion. All nine predictions were recounted against the same
message and matched to the received MP4s. The calibrated-energy reader
awaits the full development fit. [Per-case measurements](../results/hunyuan_i2v_last_controlled_paper005.json)

Across Hunyuan I2V cases `paper-000` through `paper-022`, all three readers
recovered every clean message. After deleting 30 frames, the received-order
reader recovered 6,237 of 11,776 bits (52.96%), CCTA recovered 8,945 (75.96%),
and the reader given the true edit map recovered 11,768 (99.93%). Whole-message
recovery was 0/23, 0/23 and 22/23, respectively. Under compression the three
readers each recovered 10/23 complete messages. These samples cover the first
23 manifest entries of the planned 400. To pool the counts over all currently
published cases, run from the repository root:

```bash
python tools/controlled_reader_table.py results/hunyuan_i2v_last_controlled_paper*.json
```

The controlled comparison can acquire true-map-assisted features separately
and pass them through the **same** `controlled_fusion.readout` used by the other
controlled readers:

```bash
python -m last.oracle_feature_cache --family hunyuan --model-dir /path/to/hunyuan-i2v \
  --video /private/run/attacks/drop.mp4 \
  --attack-receipt /private/run/attacks/drop.json --output /private/oracle-drop-features
python -m last.controlled_extract --reader oracle \
  --video /private/run/attacks/drop.mp4 --cache /private/oracle-drop-features \
  --codes /private/run/codes.pt --output /private/controlled-oracle-drop
```

Acquisition verifies the receipt against the received MP4 and records the VAE,
source and output hashes. The cache contains no message or codebook. The readout
normalizes each selected group's correlation vector, averages unique groups and
uses the shared BCH decoder. Both stages explicitly report `blind: false`:
the evaluator's edit map is privileged information, even though the second
command does not reload it. No deleted pixels are retrieved from an original
video. The nearest surviving same-group fill rule below still differs from blind
candidate construction, so shared fusion alone does not isolate every source of
the performance gap.

CPU tests verify received-frame selection, exclusion of foreign/duplicate
identities, missing-group handling and both families' latent scaling with mocked
VAE outputs. The public cache CLI and shared readout have now completed one real
Wan I2V deletion case at revision `cc93c8e`, recorded in
`results/controlled_oracle_real_verified.json`: 501/512 correct bits, without
complete-message recovery. All16 groups retain some frames, but none retains
all four; 30 missing slots use the documented same-group fill. Actual video,
attack map, VAE, source, cache and private decoded output hashes were independently
checked. The correct-bit count matches the older diagnostic, which does not prove
bitwise prediction parity. This is non-blind single-case integration evidence;
the complete controlled comparison remains pending. The earlier
`last.oracle_reader` results below used its original direct acquisition path.

`last.oracle_reader` is deliberately **not blind**: it reads the evaluator's
true temporal edit map. It supports existing LAST and shared-codebook LFG-C
videos, without changing their writer or attacked MP4s.

```bash
python -m last.oracle_reader --family hunyuan --model-dir /path/to/hunyuan-i2v \
  --run /private/completed-marked-run --output /private/oracle-read
```

To rebuild the paired diagnostic from the included records on CPU, run the
following commands in Bash at the repository root. Each bit accuracy uses
512 information bits per video. For whole-message recovery, add the
method's exclusive exact count to the `Both exact` column.

```bash
receipts=(results/hunyuan_i2v_oracle_paper*.json)
python tools/paired_oracle_table.py --report results/hunyuan_i2v_last_first100_robustness.json \
  --report results/hunyuan_i2v_last_primary100_178.json --manifest configs/primary_manifest.json \
  --oracle-dir results --count "${#receipts[@]}"
```

The second blind report covers IDs 100 through 178 (79 videos, 553
observations). These videos were generated under a 392-case continuation
plan. Eight earlier IDs already had outputs when that plan was frozen:
000, 001, 002, 003, 004, 020, 040 and 060. The original plan bytes are
included in `configs/historical_hunyuan_i2v_last_remaining_plan.json`.
To recount the second report from the archived primary run tree, set
`RUNS` to the directory containing `hunyuan/i2v/last` and run:

```bash
python tools/primary_pipeline_report.py \
  --plan configs/historical_hunyuan_i2v_last_remaining_plan.json \
  --manifest configs/primary_manifest.json --root "$RUNS" \
  --family hunyuan --mode i2v --method last --sample-range 100 179 \
  --output blind-100-178.json
```

For independently generated videos, use the plan that generated them.
The report checks the recorded plan and manifest digests, conditioning
images, case files and received MP4s. The exclusive stop index 179 keeps
`paper-178` as the last included video.

Among the first 80 videos, the map-assisted reader recovered 40,943 of
40,960 information bits after insertion. The 17 bit errors occurred in two
videos. For `paper-076`, blind extraction recovered 474/512 bits and the
assisted reader recovered 504/512. For `paper-078`, the counts were 369/512
and 503/512. In both assisted reads, all 16 four-frame groups were complete,
zero slots required filling, and BCH decoding reported failure. The recovered
information-bit counts equaled the corresponding pre-correction counts.
These records establish that correct frame grouping alone was insufficient
on these two videos. They do not isolate the source of the remaining bit errors.
To reproduce the per-video comparisons, run:

```bash
for id in 076 078; do
  python tools/paired_oracle_table.py --report results/hunyuan_i2v_last_first100_robustness.json \
    --oracle "results/hunyuan_i2v_oracle_paper${id}.json" --video-id "paper-${id}"
done
```

For a new Hunyuan I2V LAST reproduction, set `PLAN` to the plan used to
generate the videos, `RUNS` to its primary output root, `MODEL` to the
Hunyuan I2V model directory and `OUT` to a new results directory. The
following Bash commands score the first `N` manifest entries in order. Set
`N=400` for the full experiment once the seven primary reads exist per video.

```bash
set -e
N=400
mkdir -p "$OUT/receipts"
python tools/primary_pipeline_report.py --plan "$PLAN" --manifest configs/primary_manifest.json \
  --root "$RUNS" --family hunyuan --mode i2v --method last --output "$OUT/blind.json"
for ((i=0; i<N; i++)); do
  printf -v id 'paper-%03d' "$i"
  python -m last.oracle_reader --family hunyuan --model-dir "$MODEL" \
    --run "$RUNS/hunyuan/i2v/last/$id" --output "$OUT/$id"
  cp "$OUT/$id/receipt.json" "$OUT/receipts/hunyuan_i2v_oracle_${id/-/}.json"
done
python tools/paired_oracle_table.py --report "$OUT/blind.json" --manifest configs/primary_manifest.json \
  --oracle-dir "$OUT/receipts" --count "$N"
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


### Fixed-length hypothesis statistics (Table 13 support)

`last.hypothesis_statistics.four_group_consistency` computes the mean of the
six pairwise cosine similarities in a four-group chain. It is separate from
CCTA's length-scaled search score. It rejects zero/negligible projections,
whose cosine direction is undefined. `matched_summary` takes equally sized
correct/wrong arrays and identical, unique candidate IDs, and returns linear
P05/median/P95 quantiles and pooled ROC AUC (half credit for equal scores).
ROC AUC is not the fraction of matched pairs where the correct score wins.
The module has no access to messages and does not alter primary extraction.

Three CPU tests cover known cosine configurations, tied/reversed AUC and
mismatched candidate rejection. These are statistical unit tests, not measured
Table 13 results. Actual matched candidate acquisition, the complete frozen
80-video calibration, provenance-bound score export and the full empirical
Table 13 remain pending. ID equality alone does not prove correct pairing;
the eventual acquisition audit must establish the common video/window and
correct/wrong group labels. The supplement does not fully specify candidate
sampling or zero-projection handling, so these choices must be recorded before
collecting scores and must not be selected according to resulting AUC.

The [second audited equal-margin pair](../results/paired_writer_paper071.json)
covers frozen Hunyuan I2V case paper-071. The paired intervention uses the
same diffusion endpoint, reference MP4, key, message and seven seed-0 attack
conditions. Minimum-margin and fixed-target achieved 32.695 and 31.966 dB PSNR
respectively. On deletion they recovered 423 and 425 of 512 information bits;
on insertion they recovered 489 and 487. These are single-video counts.
Run `python tools/writer_ablation_table.py` to pool all published matched pairs. Supply explicit writer_pair_report JSON paths to summarize your own pairs. The difference column subtracts fixed-target accuracy from minimum-margin accuracy in percentage points; quality columns average the per-video PSNR and SSIM values.

Across the published 11-video subset, the two baseline columns agree in 73 of 77 video/condition bit counts. All four differences occur on paper-003, whose writer replay and reader experiment used different marked MP4s as documented above. In compression, deletion, insertion and clipping order, the writer replay gives 499, 332, 501 and 504 correct bits, while the reader experiment gives 502, 327, 499 and 506. Use the baseline measured within each experiment when calculating its ablation effect. Matching counts on the other conditions establish numerical agreement only.

For the reconstructed Table 13 clean consistency comparison, use `clean_consistency_pairs` on the 16 intact groups in source order. Each row of the input contains that window's 592 signed coefficients under each of the 16 group codebooks. For each of 13 possible four-group window starts, keep the four windows fixed and compare the correct assignment with all 12 other consecutive assignments. This yields 156 matched comparisons per video. Overlapping chains share frames and a correct score repeats once per alternative. Use the video as the sampling unit for uncertainty. This exhaustive candidate rule is a disclosed reconstruction of the unspecified sampling policy. It applies only to the consistency row. The function assumes its caller has verified the clean input and window identities; synthetic fixtures exercise pairing but supply no empirical Table 13 scores.

A [single clean LAST video](../results/hunyuan_i2v_clean_consistency_paper005.json) illustrates the consistency row on Hunyuan I2V. For paper-005 the correct and wrong medians were 0.544225 and 0.000472 across 156 matched comparisons (13 distinct correct chains). AUROC was 1.0 within this video. It gives no estimate of between-video variation. To reproduce the measurement, first run `last.oracle_feature_cache` with the original marked MP4 and its clean attack receipt as described above. Then run `python tools/clean_consistency_table.py --run /private/primary/hunyuan/i2v/last/paper-005 --cache /private/clean-cache` in the generation environment. The tool validates the cache against the actual video, checks the 16 clean groups and rebuilds the local codebook before computing the scores. The first attempted example, paper-003, lacked the original received-file fingerprint in its legacy clean receipt. Paper-005 was selected as the first available sample with that fingerprint before computing any scores.

Table 13 specifies clean videos but gives no separate sample count in its caption. We use the frozen 30-video component subset as a reconstruction choice for the consistency row. The earlier paper-005 diagnostic falls outside this subset. To pool the first two verified component cases, run:

```bash
python tools/pool_clean_consistency.py results/hunyuan_i2v_clean_consistency_paper032.json results/hunyuan_i2v_clean_consistency_paper033.json
```

These two seeds share a prompt. The 312 matched comparisons give pooled correct and wrong medians of 0.469923 and -0.002952, with AUROC 1.0. The program pools the raw scores across the supplied component videos, lists missing IDs and checks that every video contributes the same 156 comparisons. This partial result covers only the consistency statistic.

The next snapshot covers ten available component videos across nine distinct prompts and six VBench2 dimensions. Recompute it in Bash with:

```bash
python tools/pool_clean_consistency.py results/hunyuan_i2v_clean_consistency_paper{032,033,043,063,071,098,112,146,149,160}.json
```

Across 1,560 dependent comparisons, correct-group P05, median and P95 were 0.299087, 0.421767 and 0.598638. Wrong-group values were -0.027389, 0.000482 and 0.029469. The pooled AUROC was 1.0. Windows were fixed at intact group boundaries in clean videos; end-to-end blind localization under edits is a separate measurement. Twenty planned videos remain outside this snapshot.

The 12-case snapshot adds paper-003 and paper-174. For paper-003 the original
clean receipt records the source MP4 digest; the generation receipt independently
identifies the same marked MP4. The new score report records this binding.
Across 1,872 matched comparisons the correct and incorrect median scores are
0.432466 and 0.000560. The pooled AUROC is 1.0. To replay the 12/30 result:

```bash
python tools/pool_clean_consistency.py results/hunyuan_i2v_clean_consistency_paper{003,032,033,043,063,071,098,112,146,149,160,174}.json
```

To include both Table 13 energy rows, pass `--calibration /private/calibration.json` to `tools/clean_consistency_table.py`. Generate this file with `last.null_fit` from all 80 development videos. For the reconstructed raw scale, pool the development wrong-key responses over candidates, 64 keys and 16 groups and take one median. Earlier saved fits with only per-group medians require rerunning the fit on the original responses. The calibrated statistic uses each hypothesized group's frozen median and MAD scale. Average the four assigned group energies per chain; all three rows compare the same windows and assignments. Measured energy rows require the audited calibration file.
Run the same pooling command on the calibrated per-video reports to obtain energy_summary for the raw and calibrated rows alongside summary for consistency. The program matches each energy score by video, window start and candidate group start, and requires one shared development calibration digest across all videos. It pools candidate scores before computing quantiles and AUROC.
The [interim dev-000 sweep](../results/margin_sweep_dev000_interim.json) contains four paired margins, 0.1 through 0.75. Reference MP4 bytes matched across all four. Per-margin attacked-bit counts are pooled over six edits (3,072 bits per case). Complete figure generation still requires all fifteen cells.

### Completed development margin sweep

[Figure 4](../results/margin_sweep_figure4.pdf), [Supplement Table 5](../results/margin_sweep_table5.md), and the [pooled counts](../results/margin_sweep_aggregate.csv) cover three frozen Hunyuan image-to-video development samples at five embedding margins. Each condition contributes 1,536 bits per margin. The figure pools the six edited conditions (9,216 bits per margin). The table also reports clean recovery. PSNR and SSIM are averaged over the three paired videos.

To regenerate the figure and table from the [15 audited per-video measurements](../results/margin_sweep_cells.json), run the following from the repository root:

```bash
python -m pip install -e '.[figures]'
python tools/plot_margin_sweep.py --cells results/margin_sweep_cells.json --output figure4-from-cells
```

For acquisition on a GPU host without Matplotlib, pass `--tables-only` to the
private-index command. It verifies the private run records and exports
`cells.json`, the aggregate CSV and Table 5. The cells include all seven
per-condition bit counts, PSNR and SSIM for each video and margin.

The acquisition audit checks Hunyuan I2V, 50 steps, guidance 6, shift 7,
65 frames at 512×512 and 8 fps, clean CRF18, bfloat16 generation and float32
VAE against the frozen configuration. All 105 condition counts and 30 quality
measurements in the released 15 cells matched the archived counts and quality
receipts. At the default margin of 0.5, the L40 run gave 0.729 drop bit
accuracy versus 0.971 in supplement Table 5. SSIM rounded to 0.942 in both;
paired PSNR was 34.95 dB in the rerun versus 31.84 dB in the manuscript.
The sample-level rerun and the manuscript both use three development videos;
the original images, messages and keys are unavailable for an exact paired
comparison to the manuscript values.

### Equal base margin: matched writer results

The public writer reports cover 12 of the 30 planned component videos,
including [paper-174](../results/paired_writer_paper174.json). At the same
base margin of 0.5, minimum-margin writing gave 73.99% after deletion,
compared with 70.93% for fixed-target writing; neither recovered a complete
message on these 12 deletions. After insertion the rates were 80.24% and
80.53%. Mean per-video PSNR was 33.408 and 32.753 dB respectively.
Run `python tools/writer_ablation_table.py` for all seven conditions,
exact-message counts, and SSIM.

### Paired temporal profile on a saved endpoint

To change the temporal margin profile while retaining the minimum-margin
writer, reuse the same saved endpoint, codebook, message and reference video:

```bash
python -m last.writer_replay --run /private/minimum-margin --model-dir /models/hunyuan-i2v \
  --uniform-profile --output /private/uniform-profile
python -m last.quality --marked /private/uniform-profile/marked.mp4 --reference /private/uniform-profile/reference.mp4 --output /private/uniform-profile/quality.json
python -m last.evaluate --run /private/uniform-profile --family hunyuan --video-id paper-071 --model-dir /models/hunyuan-i2v
python -m last.writer_pair_report --minimum /private/minimum-margin --uniform /private/uniform-profile --output profile-pair.json
```

Use the source video's manifest ID in the evaluation command. In this
comparison the decoder and base margin stay fixed. The uniform variant sets
all 16 message groups to 0.5. The default profile uses 0 for the first group,
1 for the fourth and 0.5 for the other fourteen groups.

In the twelve equal-margin pairs, minimum-margin writing yielded higher
PSNR and SSIM on every video. The per-video PSNR gains ranged from
0.201 to 1.119 dB. Deletion recovery varied by sample: minimum-margin
writing recovered more bits on seven videos and fewer on five. These
equal-margin comparisons address the writer rule at a common strength.

For Table 16, run `python tools/uniform_profile_table.py profile-pair.json`
with one or more distinct paired profile reports. Its denominator is the
400 primary test videos. It reports deletion bit accuracy, exact-message
recovery, mean per-video PSNR and SSIM. With the full population the paired
interval uses the difference in message recovery (uniform minus primary)
and resamples whole prompt clusters. The fixed-target row at matched PSNR
requires its separate development calibration.

The [first verified profile pair](../results/temporal_profile_pair_paper071.json)
uses paper-071. Under deletion the default profile recovered 423/512 bits
and the uniform profile recovered 424/512, with zero exact messages in
both arms. PSNR was 32.695 and 32.837 dB, respectively. One video leaves
the full-test paired interval pending.

### Supplementary development-set margin sensitivity

The extended sweep uses all 80 manifest entries and their eight key slots. Run the same generation command as Figure 4 with the additional flag `--all-development`. Reuse the same private state, conditioning directory and output root. The driver validates the earlier 15 cells before reuse and writes a separate `development80-index.json` after validating all 400 video/margin pairs.

During acquisition, run `python tools/development_margin_recovery.py --completed-root "$SWEEP" --export-cells partial-cells.json` to recount all videos whose five margins have finished. This reads the existing videos and receipts without changing the acquisition directory. Use the same frozen configuration directory as the acquisition via `--configs`. The result reports both observed and planned video counts. An invalid receipt in a selected case fails the audit.

The [interim development export](../results/development_margin_seven_videos.json)
covers dev-000 through dev-005 and dev-008 at all five margins.
Run `python tools/development_margin_recovery.py --cells results/development_margin_seven_videos.json`.
At margins 0.1, 0.25, 0.5, 0.75 and 1.0, complete messages were recovered
in 0, 0, 11, 23 and 26 of 42 video–attack pairs, respectively. Mean PSNR
was 39.46, 38.46, 36.70, 35.04 and 33.48 dB. Each margin uses the same
seven videos and six edits. Figure 4 and Table 5 use dev-000,
dev-004 and dev-008. Their 15 cells agree exactly with the corresponding
observations in this export. The full Section I experiment requires 80 videos.

```bash
python tools/development_margin_recovery.py --index "$SWEEP/development80-index.json"
python tools/development_margin_recovery.py --cells results/margin_sweep_cells.json
```

The second command illustrates the calculation on the three included Figure 4 videos. Each strength has six edited conditions per video. Exact recovery counts one success only when all 512 decoded information bits match. The full denominator is 480 video/attack trials per strength. The clean condition is excluded. Mean PSNR averages one paired measurement per video per strength. The three shared videos are part of the reconstructed 80-entry manifest.

To release the 80-video measurements after acquisition, run:

```bash
python tools/development_margin_recovery.py --index "$SWEEP/development80-index.json" --export-cells development80-cells.json
python tools/development_margin_recovery.py --cells development80-cells.json
```

The export contains video identifiers, margins, correct-bit counts, PSNR and SSIM. Each included video must have all five margins. The supplementary paper reports six-attack exact recovery of 0.550, 0.750, 0.913, 0.938 and 0.946 and mean PSNR of 35.02, 34.11, 33.08, 31.69 and 30.32 dB, respectively. These are reference values. Compare them with the rerun once its output reports `complete: true`. The 80 cases also serve as the matched-writer tuning population; the primary test split uses separate videos.

### Matched Hunyuan deletion example

On primary Hunyuan I2V `paper-000`, blind LAST recovered 371/512 information bits. With the original identities of the surviving frames supplied to `last.oracle_reader`, 504/512 information bits were correct before BCH and all 512 after BCH. The MP4 SHA-256 was `8562a0f6e475a3a671a5747f77dad6b3ddb358245911ec240a5df58d363bbcf1` in both reads; the deletion receipt SHA-256 was `522d3e7d2bf39ce8518b5951d99cc751910cd9fce1a941b4d2c92e0275d5fe5d`. All 16 source groups retained at least one frame, none retained all four. The diagnostic filled 30 missing slots with surviving frames from the corresponding groups. Its advantage on this case combines correct group identities, within-group filling and fusion across all surviving groups. It cannot be assigned to the boundary detector alone. Reproduce by running the oracle command on the same generation folder as the blind reader and comparing the drop row in both receipts.
Run `python tools/paired_oracle_table.py --report results/hunyuan_i2v_paired_primary_first13.json --oracle results/hunyuan_i2v_oracle_paper000.json --video-id paper-000` to compare all seven conditions with matching attack receipt and MP4 fingerprints. The oracle changes group construction and evidence fusion and can score below blind extraction, as the blur, compression and clip rows demonstrate on this example.
The second frozen prefix case is available in `results/hunyuan_i2v_oracle_paper001.json`. Run the same command with that file and `--video-id paper-001`. Deletion improved from 368/512 to 512/512 (511 before BCH), insertion from 436/512 to 512/512; the other five conditions had equal correct-bit counts. For deletion, one entire source group was missing, two were intact and the oracle filled 25 slots across the fifteen retained groups.
The next two matched inputs are `results/hunyuan_i2v_oracle_paper002.json` and `results/hunyuan_i2v_oracle_paper003.json`. Across the first four samples, blind/oracle exact recovery was 0/4 versus 4/4 for both random deletion and insertion, and 2/4 versus 2/4 for clipping. These are four matched cases of each edit.
The fifth matching receipt is `results/hunyuan_i2v_oracle_paper004.json`: blind/oracle correct information bits were 411/512 versus 512/512 for deletion, 503/512 versus 512/512 for insertion, and 512/512 for both on clipping.
For the first 20 matched diagnostic cases, run `python tools/paired_oracle_table.py --report results/hunyuan_i2v_last_first100_robustness.json --oracle-dir results --count 20`. This uses the frozen LAST observations directly and verifies 140 attack receipt and received MP4 fingerprint pairs. Each condition covers 10,240 information bits. The prefix contains the five Camera Motion prompts at four seeds each. Blind and assisted whole-message counts were 20 and 20 on clean input, 14 and 14 on noise, 7 and 7 on compression, and 16 and 15 on blur. Random deletion gave 0 and 19 exact messages, insertion 2 and 20, and contiguous removal 10 and 17. The assisted reader still lost eight information bits on paper-011 after random deletion. The planned Table 12 cohort spans 400 clips.

The default `python tools/reader_ablation_table.py` now recounts 12/30 frozen
Hunyuan I2V samples, 6,144 information bits per cell, from
`results/hunyuan_i2v_reader_ablation_first12.json`. All four readers used
the same seven input MP4s per case. The 308 observations from the earlier
11-case report agree on every shared field. Random deletion gave 73.91%
for the full reader, 49.56% using energy and spacing in place of cross-group
consistency, 65.89% with fixed-stride windows, and 52.60% with received-order
grouping. These paired scores describe this subset and the implemented variants.

To compare both sides of the component ablation on identical full-LAST
baseline inputs, run `python tools/matched_component_table.py`. It matches
all seven received MP4 hashes and full-reader bit counts before including
a video. Ten of twelve currently measured IDs meet this condition.
For paper-003 and paper-174 the baseline MP4 fingerprints differ between
the separate writer and reader runs for every condition. Each remains in
its original within-experiment table. The combined table names all excluded
IDs and conditions and covers 10 of the 30 planned samples.
The same command computes fidelity on those exact matched IDs: mean PSNR/SSIM 33.999 dB/0.95207 for minimum margin and 33.297 dB/0.94969 for fixed target.

### Intact groups and assisted recovery in the Table 12 deletion control

In the first 37 controlled Hunyuan I2V videos, six deletion maps left zero
intact four-frame groups. The assisted reader still recovered all six messages.
It uses the known frame mapping to fill missing positions with the nearest
surviving frame from the same original group and omits groups with no frames.
CCTA recovered zero whole messages on these 37 inputs. The assisted reader
missed eight bits on paper-011, whose map preserved two intact groups.
These outcomes measure the combined effect of knowing the mapping and using
partially surviving groups. They do not isolate the effect of a single alignment rule.

Holding the true group assignments and cached features fixed, repeat fusion
with all groups, intact groups alone, and partially surviving groups alone:

```bash
python tools/assisted_group_subsets.py --run /private/primary/hunyuan/i2v/last/paper-011 \
  --evaluation /private/controlled-paper011 --case results/hunyuan_i2v_last_controlled_paper011.json
```

The [37-case CPU replay](../results/assisted_group_subsets_first37.json)
matched every original all-group prediction bit for bit. Intact groups alone
gave one exact message among 31 videos with evidence; six had no intact group.
Partial groups alone gave 32/37 exact messages. All groups gave 36/37.
Group counts differ between these reads. This diagnostic measures the available
evidence from each subset under true-map assistance, without equalizing group counts.

Add `--equal-count` to enumerate every subset of partial groups with exactly
as many groups as the intact read on that video. The [per-video counts](../results/assisted_group_equal_counts_first37.json)
cover 31 videos with at least one intact group and 1,657 eligible subsets.
Average the subset bit accuracies within each video, then weight each of the
31 videos equally. Intact groups yielded 87.13% and equally many partial groups
yielded 80.69%. The intact read exceeded the video's partial-subset mean on
26/31 clips. The remaining six clips had zero intact groups and supply no paired
comparison. Original group positions and the number of encoded frames per
group still differ. Subsets from one video share evidence.

The table below compares reads of the same random-deletion MP4, stratified by
how many original four-frame groups survived intact. Each cell gives correct
information bits followed by entire messages recovered in parentheses. Every
video carries 512 information bits. The two assisted columns use the true
source groups; the blind CCTA column receives only the edited video and key.

| Intact groups | Videos | Bits per reader | Blind CCTA | Assisted, partial groups only | Assisted, all surviving groups |
|---:|---:|---:|---:|---:|---:|
| 0 | 6 | 3,072 | 2,377 (0/6) | 3,072 (6/6) | 3,072 (6/6) |
| 1 | 16 | 8,192 | 6,405 (0/16) | 8,175 (14/16) | 8,192 (16/16) |
| 2 | 12 | 6,144 | 4,819 (0/12) | 6,114 (9/12) | 6,136 (11/12) |
| 3 | 3 | 1,536 | 1,224 (0/3) | 1,536 (3/3) | 1,536 (3/3) |

In all six videos with zero intact groups, partial groups retained enough
evidence for exact recovery when their source assignments were supplied.
This establishes recoverability under assistance for those six inputs. The
gap to blind extraction includes both group identification and the assisted
reader's treatment of partially surviving groups.

To rebuild these counts from the two public records per video, run from the
repository root. The comparison checks their case fingerprints, received-video
identity and all-group bit counts.

```bash
python - <<'PY'
from collections import defaultdict
from hashlib import sha256
from pathlib import Path
import json

rows = json.loads(Path("results/assisted_group_subsets_first37.json").read_bytes())
assert [r["video_id"] for r in rows] == [f"paper-{i:03}" for i in range(37)]
groups = defaultdict(list)
for r in rows:
    video = r["video_id"]
    case_file = Path(f"results/hunyuan_i2v_last_controlled_paper{video[-3:]}.json")
    raw = case_file.read_bytes()
    assert sha256(raw).hexdigest() == r["case_sha256"]
    drop = [x for x in json.loads(raw)["rows"] if x["condition"] == "drop"]
    assert len({x["received_sha256"] for x in drop}) == 1
    bits = {x["reader"]: x["correct_bits"] for x in drop}
    subsets = r["subsets"]
    assert bits["oracle"] == subsets["all"]["correct_bits"]
    groups[subsets["intact"]["groups"]].append(
        [bits["ccta"], subsets["partial"]["correct_bits"], bits["oracle"]])
for intact, values in sorted(groups.items()):
    print(intact, len(values), [sum(col) for col in zip(*values)],
          [col.count(512) for col in zip(*values)])
PY
```

The [43-video extension](../results/assisted_group_equal_counts_first43.json)
adds the next six manifest IDs, paper-037 through paper-042. On the same
random-deletion MP4s, received-order grouping scored 11,541/22,016 bits,
blind CCTA scored 17,178/22,016 and true-map assistance scored 21,983/22,016.
Exact recovery was 0/43, 0/43 and 40/43. Eight videos contained zero intact
groups. Assistance recovered seven of these messages exactly and 495/512 bits
on paper-041. Among 35 videos eligible for the equal-count comparison,
intact groups averaged 87.43% and equally many partial groups averaged
80.45% over 1,869 subsets, weighting each video equally. The intact read
exceeded the partial-subset mean in 30/35 videos.

### Render main Table 4

```bash
python tools/matched_component_table.py --table4 \
  --archived-reread results/hunyuan_i2v_archived_reader_pair.json
```

The GitHub Actions artifact `audited-partial-robustness-tables` includes the generated `table4-component-ablation.md`. Its first two lines identify the matched samples and any excluded baselines.

This prints the manuscript's five variants and seven columns on the 0–1
bit-accuracy scale. All 35 cells currently cover the same 12 Hunyuan I2V
videos, or 6,144 information bits each. Under random deletion the measured
values in row order are 0.740 (full LAST), 0.709 (fixed targets), 0.493
(raw energy with spacing), 0.660 (fixed-stride windows) and 0.525
(received order). MM denotes the minimum-margin write, CGC denotes
cross-group consistency, and SWS denotes sliding-window search. The calibrated
energy-and-spacing reader belongs to the separate supplement experiment.

To include the completed archived-input reruns for paper-003 and paper-174, run `python tools/matched_component_table.py --archived-reread results/hunyuan_i2v_archived_reader_pair.json`. This yields 12/30 matched videos and 6,144 information bits per condition. The 56 rerun receipts cover both cases, seven conditions and four readers. The original reader data are retained separately. On these 12 videos the full reader scored 73.99%, 80.24% and 96.14% on drop, insert and clip. With received-order grouping the scores were 52.52%, 53.94% and 65.98%.
The raw reader-receipt aggregation command (`python -m last.ablation_summary`) uses only the Python standard library. With a source checkout, set PYTHONPATH to src. On the archived pair it reproduced all 28 aggregate cells and all 56 receipt fingerprints with third-party site packages disabled.

For your own runs, create an index JSON mapping each sample ID to its generation and reader output directories. Paths may be absolute or relative to the index. For example:

```json
{"paper-003": {"run": "paper-003/minimum-margin", "readers": "paper-003/reader-outputs"}}
```

Use the same frozen subset for the writer and reader runs. Export per-video counts and compare them with the paired writer report for each sample:

```bash
python tools/export_archived_readers.py --index /private/index.json --output reader-counts.json
python tools/matched_component_table.py --reader reader-counts.json --writers /private/paper-003-writer.json
```

Use `--archived-reread` only to replace a complete reader case whose original baseline used different MP4s. The exporter checks all four readers against the seven received videos and the generation codebook before emitting counts.
### Residual errors with the true frame map

The `clip` condition removes 30 consecutive frames from a 65-frame source and joins the surviving frames in order. For example, `attack_map('paper-000', 'clip', seed=0)` removes frames 9–38 (numbered from 1). The extractor receives frames 1–8 followed by 39–65, for 35 frames in total. The `drop` condition also leaves 35 frames but samples the 30 deleted positions without replacement across the full video.

Across the first 92 Hunyuan I2V videos, deletion left 26 messages with errors even after the diagnostic reader received the true frame map. These 26 accounted for all 390 incorrect information bits, with 6–28 errors per affected message (median 15). Insertion left three affected messages with 8, 8 and 9 errors. Contiguous removal left 32 with 7–29 errors (median 15.5). In these three conditions, every affected receipt records `bch_success: false`; every exact recovery records `bch_success: true`. This describes the decoder outcome on these files. It does not identify which earlier operation introduced each error.

To recount, use receipts `results/hunyuan_i2v_oracle_paper000.json` through `paper091.json`. For each of `drop`, `insert` and `clip`, take `512 - correct_bits` from each matching row and restrict the error distribution to strictly positive values. All 92 messages contribute to the bit accuracy reported in Table 12.
