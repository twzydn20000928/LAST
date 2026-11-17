# Main-paper ablations and margin sweep

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
calibrated matched-PSNR control. Real-video replay validation remains pending.

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

