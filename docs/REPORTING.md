# Rebuild measured robustness tables

For main Table 1, run `python -m last.clean_table --family hunyuan --reports
results/last_hunyuan_t2v_audited_partial.json results/last_hunyuan_i2v_audited_partial.json
--output table1.md` as a single command. Add `--quality` followed by the
corresponding `last.quality_report` JSON paths as scores become available.
The command displays both generation modes and coverage for clean recovery.
Use `--family wan22` with Wan reports for the separate backbone comparison.
Only official quality reports containing all applicable dimension means produce
a numeric V-score.

For the qualitative comparison, run `python -m last.qualitative_figure --index
/private/figure3-cases.json --output figure3` as a single command. The index is
a list of two animal-video cases. Each entry contains `video_id`, `family`,
`mode`, the private `case` JSON path and a `runs` mapping from the five method
names to their generation directories. Paths resolve relative to the index.
The no-watermark panels use the paired reference from the LAST run. The output
includes the lossless PNG and source fingerprints for all twelve video panels.
Frame indices 4 and 16 are zero-based. Record the chosen sample IDs; the
caption alone does not identify the original examples.

First run `last.report --verify-artifacts` against the frozen experiment plan and
actual run directory. If historical reader results were independently replayed,
supply the audited `--reextraction-index` described in `REEXTRACTION.md`.
That audit produces `summary.json`, raw-count CSV and a long-form Markdown table.

To format audited reports into a Table2-style layout with attacks as columns:

```bash
python -m last.robustness_table --reports \
  results/last_hunyuan_i2v_audited_partial.json \
  results/last_hunyuan_t2v_audited_partial.json \
  results/last_wan_i2v_audited_partial.json \
  --output /path/to/new-table-output
```

This example uses checked-in partial snapshots, not live server state. It has
rendered 25 Hunyuan I2V, 6 Hunyuan T2V and 4 Wan I2V cases from their existing
audits. It does not compare those different pipelines as paired methods. For the
final paper table, supply newly audited complete reports covering every required
method and pipeline; the present example does not satisfy that requirement.

`table.md` shows correct-information-bit percentages and completed/planned video
counts. `counts.csv` retains correct bits, total bits, exact-message counts and
separate observed/final accuracy columns. `receipt.json` binds the source reports
and formatter revision by SHA256. Partial cells keep null final scores; missing
data is not zero accuracy. Overlapping snapshots are rejected rather than added
together. Each pipeline must include all seven condition cells and one planned
denominator, even when none of its videos has completed.

The receipt field `supplied_cells_complete` covers only the reports passed to
the command. A completed single-pipeline report can set this field to true.
Whole-paper coverage requires checking the supplied pipelines against the paper protocol.

The formatter recomputes percentages from integer counts. It does not rerun GPU
extraction, replace the artifact audit, establish comparable protocols, compute
statistical uncertainty or select a winner. Three CPU tests cover count-derived
percentages, missing conditions, unaudited inputs, overlap, impossible recovery
counts and rejection of final scores on partial results. Quality, efficiency,
uncertainty and supplementary tables remain separate workflows.

The `core-tests` GitHub Actions workflow also executes the command above in its
core CPU job and uploads `audited-partial-robustness-tables`. Download that
artifact from a successful workflow run to obtain the Markdown table, CSV counts
and input/source receipt for that exact public revision. This checks that the
published snapshots can be rendered by the released formatter; it does not
repeat the private video audit or turn incomplete snapshots into final results.

### Three matched Hunyuan I2V cases

From the repository root, run `python tools/paired_lfg_table.py` to render
the LAST and LFG adaptation results for paper-000 through paper-002. The
command uses Python's standard library and reads the published per-case
observations. Each condition covers three messages of 512 information bits.
The exact-message column counts videos with all 512 bits correct.

The runs share case records, payloads and realized attack maps. Their unmarked
reference videos differ slightly after decoding (RGB PSNR 39.98–41.00 dB).
The three-case subset has limited coverage of the planned 400 cases.

### First 100 Hunyuan I2V LAST samples

The [per-sample observations](../results/hunyuan_i2v_last_first100_robustness.json) span the first 100 entries in frozen manifest order. Each condition has 51,200 information bits. The prefix contains 20 samples each from Camera Motion, Complex Landscape, Complex Plot, Composition and Diversity. The full branch calls for 400 samples.

| Condition | Correct bits / 51,200 | Bit accuracy | Entire 512-bit messages / 100 |
| --- | ---: | ---: | ---: |
| blur | 50952 | 99.52% | 80 |
| clean | 51200 | 100.00% | 100 |
| clip | 49941 | 97.54% | 51 |
| compression | 49236 | 96.16% | 28 |
| drop | 37704 | 73.64% | 1 |
| insert | 42247 | 82.51% | 7 |
| noise | 50013 | 97.68% | 47 |

## Additional primary evaluation records

Each link contains results for the indicated prefix of a 400-video branch. Each condition contributes 512 information bits per video.

| Generator and task | Method | Videos | Observations across seven conditions |
| --- | --- | ---: | ---: |
| Hunyuan text-to-video | [LAST](../results/hunyuan_t2v_last_first50.json) | 50 | 350 |
| Wan2.2 image-to-video | [LAST](../results/wan22_i2v_last_first30.json) | 30 | 210 |
| Wan2.2 text-to-video | [LAST](../results/wan22_t2v_last_first10.json) | 10 | 70 |
| Hunyuan text-to-video | [VideoMark](../results/hunyuan_t2v_videomark_first20.json) | 20 | 140 |
| Hunyuan image-to-video | [VideoShield](../results/hunyuan_i2v_videoshield_first_primary.json) | 1 | 7 |
Run `python tools/paired_videomark_table.py` from the repository root to compare the same twenty prompt IDs (paper-000 through paper-019) for Hunyuan text-to-video. The script reports the number of correctly decoded bits and the number of videos with an exact 512-bit message for each condition.

## Text-to-video comparison on ten shared prompt IDs

Both columns use paper-000 through paper-009 and 512 information bits per video. Each backbone generated its own videos. Entries show correct bits out of 5,120 and exact messages out of ten.

| Condition | Hunyuan correct bits | Wan2.2 correct bits | Hunyuan exact | Wan2.2 exact |
| --- | ---: | ---: | ---: | ---: |
| clean | 5120 | 5120 | 10 | 10 |
| noise | 5058 | 5044 | 7 | 7 |
| compression | 4946 | 4954 | 3 | 6 |
| blur | 5100 | 5074 | 8 | 7 |
| drop | 3862 | 3736 | 0 | 0 |
| insert | 4702 | 4323 | 1 | 1 |
| clip | 4973 | 4943 | 4 | 6 |
`python tools/paired_backbone_table.py` regenerates this table from the two published observation files.
Run `python tools/paired_lfg_table.py --samples 7` to regenerate the seven-prompt Hunyuan image-to-video comparison from the [matched LAST and LFG observations](../results/hunyuan_i2v_last_lfg_first_seven_paired.json).
For image-to-video, run `python tools/paired_backbone_table.py --mode i2v`. Each column uses the first 30 manifest entries, with 15,360 information bits per condition and 30 opportunities to recover an entire message.
The [paired fidelity records](../results/hunyuan_i2v_last_first100_fidelity.json) cover the first 100 Hunyuan image-to-video LAST cases. Each row compares the 65-frame marked MP4 with its reference MP4. Summary fields give the arithmetic mean of the per-video PSNR (dB) and SSIM values.

### Comparing unmarked controls across methods

Use the same primary sample ID, backbone and generation mode on both sides. Run
the command below from the repository root with OpenCV and NumPy installed.
It compares all 65 decoded frames, counts changed color-channel values and
reports their root mean squared difference on the 0–255 scale.

```bash
python tools/compare_references.py \
  "$PRIMARY/hunyuan/i2v/last/paper-000/reference.mp4" \
  "$PRIMARY/hunyuan/i2v/lfg/paper-000/reference.mp4"
```

Set `PRIMARY` to the directory containing the backbone/mode/method run trees.
For the [first eight cases](../results/hunyuan_i2v_reference_differences.jsonl),
two pairs match exactly. The six other reference pairs have RMS differences of
2.03–2.56 intensity levels. Each method's [fidelity scores](../results/hunyuan_i2v_first8_paired_fidelity.json)
use its own unmarked reference. These eight samples do not establish a causal
effect of the memory limit on generation.

### Reader ablation on matched received videos

Run `python tools/reader_ablation_table.py` to reconstruct the seven-condition
table from the checked-in [paired observations](../results/hunyuan_i2v_reader_ablation_interim.json).
All four readers decode the same marked inputs. The energy reader replaces
cross-group consistency in `without_cgc`; `without_sws` disables the frame-by-frame
window scan; `without_ccta` uses received order. The script checks sample
membership and agreement between the observation sums and the stored cell
counts. The snapshot covers 11 of the 30 frozen cases.
The [clean-condition route records](../results/hunyuan_i2v_ablation_clean_routes.json) identify the selected route, group count and BCH decode status for each of the 44 reads. All 11 energy-only reads selected two to five distinct groups. The full reader used chains covering 15 or 16 group entries on these videos. Group counts alone do not establish correct group identity.

### Hunyuan text-to-video paired primary results

Use the shared LAST/LFG campaign plan, manifest and private run root to audit
the first sample. Run from the repository root in the installed LAST environment:

```bash
python tools/paired_primary_subset.py --plan "$PLAN" --manifest "$MANIFEST" \
  --root "$PRIMARY" --family hunyuan --mode t2v --count 1 > matched.json
```

The [first pair](../results/hunyuan_t2v_paired_primary_first_case.json) covers
one of the planned 400 prompts. The completion field applies to the requested
prefix. The command compares the actual case, private key and message locally,
reconstructs editing positions, and verifies the received MP4s before exporting
counts. Choose the sample count before comparing outcomes.
For Wan-2.2 image-to-video, use the same command with `--family wan22 --mode i2v --count 1`. The [first Wan I2V pair](../results/wan22_i2v_paired_primary_first_case.json) reports seven conditions on paper-000 for both methods.
The [first Wan T2V pair](../results/wan22_t2v_paired_primary_first_case.json) uses the same primary prefix and seven conditions. To audit it, change the arguments to `--family wan22 --mode t2v --count 1`.
Camera Motion scores are available for [Wan I2V](../results/wan22_i2v_camera_motion_20_pairs.json) and [Hunyuan T2V](../results/hunyuan_t2v_camera_motion_20_pairs.json). Each arm contains all 20 planned videos. These exports reproduce official per-video scores and verify frozen sample identities; they cover one dimension of the quality metric.
The [Hunyuan I2V Complex Plot records](../results/hunyuan_i2v_complex_plot_20_pairs.json) cover all five prompts and four seeds per prompt. Per-video scores, MP4 digests and scorer receipt fingerprints are included. LAST averaged 0.08 and its unmarked reference averaged 0.07 on this dimension.
