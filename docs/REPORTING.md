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
Run `python tools/paired_videomark_table.py` from the repository root to compare the same twenty sample IDs across five prompts (paper-000 through paper-019) for Hunyuan text-to-video. The script reports the number of correctly decoded bits and the number of videos with an exact 512-bit message for each condition.

## Text-to-video comparison on ten shared samples across three prompts

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
Run `python tools/paired_lfg_table.py --samples 7` to regenerate the seven-sample, two-prompt Hunyuan image-to-video comparison from the [matched LAST and LFG observations](../results/hunyuan_i2v_last_lfg_first_seven_paired.json).
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
one of the planned 400 video samples. The completion field applies to the requested
prefix. The command compares the actual case, private key and message locally,
reconstructs editing positions, and verifies the received MP4s before exporting
counts. Choose the sample count before comparing outcomes.
For Wan-2.2 image-to-video, use the same command with `--family wan22 --mode i2v --count 1`. The [first Wan I2V pair](../results/wan22_i2v_paired_primary_first_case.json) reports seven conditions on paper-000 for both methods.
The [first Wan T2V pair](../results/wan22_t2v_paired_primary_first_case.json) uses the same primary prefix and seven conditions. To audit it, change the arguments to `--family wan22 --mode t2v --count 1`.
Camera Motion scores are available for [Wan I2V](../results/wan22_i2v_camera_motion_20_pairs.json) and [Hunyuan T2V](../results/hunyuan_t2v_camera_motion_20_pairs.json). Each arm contains all 20 planned videos. These exports reproduce official per-video scores and verify frozen sample identities; they cover one dimension of the quality metric.
The [Hunyuan I2V Complex Plot records](../results/hunyuan_i2v_complex_plot_20_pairs.json) cover all five prompts and four seeds per prompt. Per-video scores, MP4 digests and scorer receipt fingerprints are included. LAST averaged 0.08 and its unmarked reference averaged 0.07 on this dimension.
Use `--count 2` to reproduce the first two sample IDs in the [Hunyuan T2V](../results/hunyuan_t2v_paired_primary_first_two.json), [Wan I2V](../results/wan22_i2v_paired_primary_first_two.json) and [Wan T2V](../results/wan22_t2v_paired_primary_first_two.json) snapshots. Each cell has 1,024 information bits. The two samples are different seeds of the same prompt.
For Hunyuan T2V, the [three-seed results](../results/hunyuan_t2v_paired_primary_first_three.json) include the rerun of paper-002 after a shared-GPU memory failure. Use the same command with `--count 3`. Each condition pools 1,536 information bits from three seeds of the same prompt.
The [three-seed Wan I2V results](../results/wan22_i2v_paired_primary_first_three.json) use the same conditioning image and prompt with three seeds. Run the Wan I2V command with `--count 3`.
The [LAST Hunyuan I2V Diversity result](../results/hunyuan_i2v_diversity_last_60.json) gives three prompt-level scores and the verified hashes of all 60 videos. Use the frozen 20 seeds per prompt and compute the arithmetic mean of the three scores.
The current matched T2V prefixes include [four Hunyuan seeds](../results/hunyuan_t2v_paired_primary_first_four.json) and [three Wan seeds](../results/wan22_t2v_paired_primary_first_three.json), all from the first prompt.
The [paired unmarked Diversity record](../results/hunyuan_i2v_diversity_reference_60.json) uses the same three prompt groups and twenty seeds per group as LAST. The mean was 0.254863 for the reference and 0.245475 for LAST. All 120 input MP4 fingerprints were checked against the official scoring receipts.
All [20 Hunyuan I2V Composition pairs](../results/hunyuan_i2v_composition_20_pairs.json) received identical within-pair scores from the official scorer. The mean was 0.55 in both arms. Each input MP4 was rehashed against its scoring receipt.

For Hunyuan I2V, the Creativity category gives Composition and Diversity equal weight. Average the 20 individual Composition scores for each arm and the three prompt-level Diversity scores for the same arm, then average the two dimension means. Each Diversity prompt covers 20 distinct seeds. This gives (0.55 + 0.2454754263) / 2 = 0.397738 for LAST and (0.55 + 0.2548630685) / 2 = 0.402432 for the paired reference. The observed difference of -0.004694 comes entirely from Diversity. See the [LAST Diversity scores](../results/hunyuan_i2v_diversity_last_60.json) and [reference Diversity scores](../results/hunyuan_i2v_diversity_reference_60.json). A full V-score additionally requires the other four categories.
For the [four-seed Wan I2V comparison](../results/wan22_i2v_paired_primary_first_four.json), pass --count 4 to the Wan I2V prefix audit. Both methods cover the first prompt and conditioning image at four different seeds, with 2,048 information bits per condition.
For the [four-seed Wan T2V comparison](../results/wan22_t2v_paired_primary_first_four.json), use the Wan prefix audit with --mode t2v --count 4. The two methods share the first prompt and four seeds. On deletion LAST and LFG recovered 1,486 and 1,401 of 2,048 bits, respectively, with zero exact messages in either arm.
The [five-video Hunyuan T2V prefix](../results/hunyuan_t2v_paired_primary_first_five.json) adds the first seed of the second prompt after four seeds of the first. Reproduce it with --family hunyuan --mode t2v --count 5. The new sample recovered 416/360 bits on deletion, 445/313 on insertion and 485/467 on clipping (LAST/LFG; 512 bits per video). Aggregates weight videos equally.

To render the public paired counts without access to the private run directory, pass the exported JSON directly:

```bash
python tools/paired_lfg_table.py --report results/hunyuan_t2v_paired_primary_first_five.json
python tools/paired_lfg_table.py --report results/wan22_t2v_paired_primary_first_four.json
```

Each row includes the integer numerator and denominator, its percentage rounded to two decimals, and the number of exactly recovered messages. Each video contributes 512 information bits per condition.

For the same T2V samples, compare [five Hunyuan fidelity pairs](../results/hunyuan_t2v_paired_fidelity_5.json) and [four Wan fidelity pairs](../results/wan22_t2v_paired_fidelity_4.json). Recompute with `python tools/paired_prefix_fidelity.py --report results/hunyuan_t2v_paired_primary_first_five.json --root /private/primary-runs`, substituting the Wan report for Wan. Each method uses its own unmarked reference. Across methods, zero of five Hunyuan reference MP4s and all four Wan reference MP4s were byte-identical. These counts concern encoded files; decoded pixel identity was not assessed here.
The [decoded comparison of five Hunyuan T2V reference pairs](../results/hunyuan_t2v_reference_differences_first_five.json) found differences in all five 65-frame clips. Per-video root mean squared channel differences ranged from 1.837 to 2.824 on the 0–255 scale. Run python tools/compare_references.py with the two reference.mp4 paths, LAST first. The separate fidelity metrics compare each marked video to its own reference.
The [generation settings of these five Hunyuan T2V reference pairs](../results/hunyuan_t2v_reference_settings_first_five.json) match within each pair on sample-file digest, seed, sampling settings, recorded source digest, model directory name, hardware label and sequential offload. The process memory limit was 8 GiB for LAST and 12 GiB for LFG on all five cases. This comparison does not isolate the effect of that limit or identify the cause of the pixel differences.
The [five-video Wan I2V prefix](../results/wan22_i2v_paired_primary_first_five.json) adds a seed of the second prompt and conditioning image. Use --family wan22 --mode i2v --count 5 for the artifact audit. On the new sample LAST and LFG read 397/343 bits after deletion, 490/310 after insertion and 512/474 after clipping. Across the five videos, LFG led on deletion (1797 vs 1627 correct bits) while LAST led on insertion (2184 vs 1449). Each cell contains 2560 information bits.
For the [same five Wan I2V cases](../results/wan22_i2v_paired_fidelity_5.json), paired fidelity averaged 28.689 dB / 0.92846 SSIM for LAST and 22.250 dB / 0.78944 for LFG. All five reference MP4s matched byte for byte across methods. Recompute with tools/paired_prefix_fidelity.py using the five-video Wan I2V attack report and the primary run root.

### Hunyuan image-to-video, first twelve matched cases

Run the following from the repository root. The first file retains the earlier eight-case audit, including the independent clean re-extraction evidence. The second covers paper-008 through paper-011 under the remaining LAST campaign and the primary LFG campaign. For LAST, cases 000–004 used the initial plan and 005–011 used the remaining plan. The plan field in the first file names the initial LAST plan for the batch. Use each case's campaign receipt for its execution plan.

```bash
python tools/paired_lfg_table.py --report results/hunyuan_i2v_last_lfg_first_eight_paired.json results/hunyuan_i2v_paired_primary_008_011.json
```

This is an interim manifest prefix. Each attack column pools 6,144 information bits per method from twelve paired cases. Each exact-message count uses twelve messages as its denominator.

The [paired fidelity records for these twelve cases](../results/hunyuan_i2v_first12_paired_fidelity.json) match all 24 clean extraction inputs by marked MP4 digest. Mean per-video PSNR and SSIM are 30.892 dB and 0.93611 for LAST, and 22.357 dB and 0.74177 for LFG. Each marked video is compared with its method's own unmarked reference. Only two of the twelve pairs have identical encoded references across methods. Average the twelve per-video values within each method to recover the reported means.
