# Rebuild measured robustness tables

For main Table 1, both commands below use the same paired extraction records
as the Table 2 example. Each includes the available official quality reports
for LAST and its unmarked reference. The Hunyuan command also includes the
available VideoShield and VideoMark measurements. Run from the repository root.

```bash
python -m last.clean_table --family hunyuan \
  --reports results/hunyuan_i2v_primary24.json results/hunyuan_t2v_primary14.json \
    results/hunyuan_i2v_videoshield_first2_complete.json results/hunyuan_t2v_videomark_first40.json \
    results/hunyuan_i2v_sigmark_first1_partial.json \
  --quality results/hunyuan_i2v_quality_six_dimensions_last.json \
    results/hunyuan_i2v_quality_five_dimensions_reference.json \
    results/camera_motion/hunyuan_t2v_last_camera_quality.json \
    results/camera_motion/hunyuan_t2v_reference_camera_quality.json \
    results/hunyuan_i2v_lfg_camera_quality.json results/hunyuan_t2v_videomark_quality.json \
  --output paired-table1/hunyuan.md

python -m last.clean_table --family wan22 \
  --reports results/wan22_i2v_primary14.json results/wan22_t2v_primary13.json results/wan22_i2v_videoshield_paper000_seven_conditions.json \
  --quality results/camera_motion/wan22_i2v_last_camera_quality.json \
    results/camera_motion/wan22_i2v_reference_camera_quality.json \
    results/camera_motion/wan22_t2v_last_camera_quality.json \
    results/camera_motion/wan22_t2v_reference_camera_quality.json \
  --output paired-table1/wan22.md
```

The `core-tests` workflow also renders both model families with the available native baseline rows. Its `audited-partial-clean-tables` artifact contains `hunyuan.md` and `wan22.md`.

The clean accuracy column pools 512 information bits per completed video;
the parenthesis gives completed videos out of 400. Each Table 1 report includes the integer bit counts and whole-message recovery counts beneath the rounded table. Table 2 also exports these counts in `counts.csv` for condition `clean`. Quality coverage uses a separate denominator of 18
dimensions. The formatter prints the number evaluated while the V-score is pending.

To rebuild a report from your own generated videos, use the frozen plan that
created the runs and the same artifact root used for generation. For the
paths in the [campaign example](CAMPAIGN.md), run

```bash
python -m last.report --plan /private/primary-plan.json \
  --root /private/primary-runs --verify-artifacts --output primary-report
```

This checks each completed attack receipt against the marked and received
MP4s. It writes `summary.json`, the per-condition counts and a Markdown
table. If you independently re-extracted historical videos, include their
audited [re-extraction index](REEXTRACTION.md). To render the published
partial results directly, use the public report files in the command below.

Table 2 starts with 65 frames. The primary temporal edits use map seed 0. Frame numbers in this example start at 1.

| Condition in the results | How the evaluation constructs the received video | Received frames |
|---|---|---:|
| `drop` | Remove 30 distinct frames sampled across the timeline. Keep the remaining frames in order. | 35 |
| `clip` | Remove one consecutive interval of 30 frames and join the surviving portions. For paper-000 the received video contains frames 1–8 followed by 39–65. | 35 |
| `insert` | Keep every source frame in order and fill 30 new positions with uniform random RGB8 noise frames. | 95 |

The evaluator writes each edit to an MP4 at CRF 18 and reads it back for extraction. To print the exact source indices for a given sample, run:

```bash
python -c "from last.temporal import attack_map; print(attack_map('paper-000', 'clip'))"
```

The function returns zero-based source indices. In an insertion map, `-1` marks a generated noise frame. These maps are available to the evaluator for scoring and auditing. The blind reader receives the edited video.

To rebuild the measured LAST, LFG and native baseline rows of Table 2 with attacks as columns, run:

```bash
python -m last.robustness_table --reports \
  results/hunyuan_i2v_primary24.json \
  results/hunyuan_t2v_primary14.json \
  results/wan22_i2v_primary14.json \
  results/wan22_t2v_primary13.json \
  results/wan22_i2v_videoshield_paper000_seven_conditions.json \
  results/hunyuan_i2v_videoshield_first2_complete.json \
  results/hunyuan_i2v_sigmark_first1_partial.json \
  results/hunyuan_t2v_videomark_first40.json \
  --output paired-table2
```

LAST and LFG use the same sample IDs within each pipeline. The four inputs above cover 24 Hunyuan I2V pairs, 14 Hunyuan T2V pairs, 14 Wan I2V pairs and 13 Wan T2V pairs. VideoShield has two Hunyuan I2V observations per condition and one Wan I2V observation for each of the seven conditions. On Wan I2V paper-000, contiguous removal retained 35 frames. VideoShield recovered 512/512 bits, LAST 487/512 and LFG 353/512. On Wan I2V paper-000, insertion adds 30 frames to the 65-frame video. VideoShield recovered 508/512 bits, LAST 377/512 and LFG 255/512. After the [original blur extraction failed](../results/wan22_i2v_videoshield_paper000_blur_attempt.json), a retry on the saved MP4 recovered 512/512 bits. VideoMark has 40 Hunyuan T2V observations for each of the seven conditions. SIGMark has one Hunyuan I2V sample with measured clean, noise, compression, blur and contiguous-removal scores. On the same random-deletion MP4, a retry completed four 9-frame, 50-step window inversions. The upstream ordering stage returned only missing frames, and interpolation raised an error before decoding. The deletion observation therefore contributes zero scored bits. The rendered cell shows one failed video. In `counts.csv`, the `failed` column counts failed videos in the supplied snapshot; retries of the same video do not increase that count. A blank failure count means the source report did not provide it. The 95-frame insertion input was verified against the native extractor receipt. Extraction ran out of GPU memory and produced zero scored bits ([failure record](../results/sigmark_paper000_insert_failure.json)). On Hunyuan I2V paper-000, contiguous removal retained 35 frames. VideoShield recovered 512/512 bits, LAST 502/512, LFG 358/512 and SIGMark 272/512. This comparison covers one matched sample. See the [retry receipt summary](../results/sigmark_paper000_drop_retry_failure.json). Across all methods the command produces 12 rows and 84 condition cells, each with its own coverage out of 400. For example, random deletion on the fourteen Wan
I2V pairs gives 65.625% for LAST and 66.03% for LFG. The paired subsets can be
smaller than the single-method runs because both methods must finish all attacks.
Choose a fresh output directory on each invocation.

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
| Hunyuan text-to-video | [LAST](../results/hunyuan_t2v_last_first74.json) | 74 | 518 |
| Wan2.2 image-to-video | [LAST](../results/wan22_i2v_last_first44.json) | 44 | 308 |
| Wan2.2 text-to-video | [LAST](../results/wan22_t2v_last_first24.json) | 24 | 168 |
| Hunyuan text-to-video | [VideoMark](../results/hunyuan_t2v_videomark_first39.json) | 39 | 273 |
| Hunyuan image-to-video | [VideoShield](../results/hunyuan_i2v_videoshield_first_primary.json) | 1 | 7 |

The 40-video VideoMark report was also rebuilt with the primary-prefix audit's `--retry paper-038 noise` option and the verified retry directory. Its 280 observations include that case once. All seven cell totals agree with the earlier recount. The new receipt binds the old failed receipt and the saved prediction; the original extraction lacked a prediction digest.

The [39-video recount](../results/hunyuan_t2v_videomark_first39.json) includes all seven conditions per video. For `paper-038`, the failed noise extraction was rerun on the identical noisy MP4 and registered state. It recovered 253/512 bits. The original failed receipt fingerprint is `43fb8e28215754ce9297d883c903dfd47611bf06e681d22e484c1d11ac773e2d`; the completed receipt is recorded in the new report. The earlier [267 observations](../results/hunyuan_t2v_videomark_first39_partial.json) agree individually with the recount. Run `python tools/paired_videomark_table.py` for the 39-video paired comparison.

#### Replay the archived VideoMark retry

The original run directory for paper-038 retains the failed noise receipt.
The completed retry has SHA-256
`e4f7b3b2e3aaa081086e5db8e365177995087ef766a041f89f0a20837b366e56`
for `attacks/noise.json`. In both directories the generated MP4, noisy MP4,
generation receipt, clean receipt, payload and private registration state
were byte-identical. To reproduce the 39-video count with this two-directory
layout, run from the repository root after the first 39 jobs and retry have
finished. Use the temporary tree for reading only, because hard links share
their underlying data with the originals. Ordinary runs with all successful
outputs in the main tree can use that tree directly.

```bash
# Run on Linux. PRIMARY, RETRY, MANIFEST and PLAN point to your own files.
# PRIMARY contains the native and LAST run trees. RETRY is the separate
# verified paper-038 VideoMark run. AUDIT_PARENT is private local storage
# on the same filesystem as both runs (used for hard links).
set -eu
umask 077
view=$(mktemp -d "$AUDIT_PARENT/videomark-recount.XXXXXXXX")
mkdir -p "$view/hunyuan/t2v/videomark"
ln -s "$(realpath "$PRIMARY/.native-jobs")" "$view/.native-jobs"
ln -s "$(realpath "$PRIMARY/hunyuan/t2v/last")" "$view/hunyuan/t2v/last"
for index in $(seq 0 38); do
  id=$(printf 'paper-%03d' "$index")
  source_dir="$PRIMARY/hunyuan/t2v/videomark/$id"
  if [ "$index" -eq 38 ]; then
    for item in receipt.json message.bin marked.mp4 maintained_private.pkl attacks/noise.mp4 attacks/clean.json; do
      cmp "$source_dir/$item" "$RETRY/$item"
    done
    source_dir="$RETRY"
  fi
  cp -al "$source_dir" "$view/hunyuan/t2v/videomark/$id"
done
python tools/audit_videomark_prefix.py --family hunyuan --mode t2v --method videomark \
  --count 39 --manifest "$MANIFEST" --plan "$PLAN" --root "$view" --output "$view/recount.json"
```

The complete recount contains 273 observations. For the 40-sample snapshot,
the five completed observations from paper-039 were also audited; insertion
and contiguous removal had no scores at that checkpoint.


Run `python tools/paired_videomark_table.py --count 38` from the repository root to compare Hunyuan LAST and VideoMark on paper-000 through paper-037. The script reports the number of correctly decoded bits and the number of videos with an exact 512-bit message for each condition. All 266 VideoMark observations were recounted from the archived decoded bytes. The original extraction receipts lack prediction digests, so the recount verifies agreement with the recorded bit counts but cannot establish historical bit-for-bit identity.

To regenerate either Wan LAST report from your completed runs, use the primary pipeline audit command below. Set MODE to `i2v` or `t2v`. The audit checks the saved MP4 files and records missing samples separately in each condition.

```bash
MODE=t2v
python tools/primary_pipeline_report.py --plan /private/primary-wan-clean-plan.json \
  --root /private/primary --family wan22 --mode "$MODE" --method last \
  --output "wan22-${MODE}-last.json"
```

The [Wan T2V LAST fidelity report](../results/wan22_t2v_last_fidelity24.json)
covers the same 24 videos as the attack report above. Each marked MP4 is
compared with its own unmarked reference. Mean PSNR is 31.311 dB and mean
SSIM is 0.94135. Resampling the six prompts gives 95% intervals of
[30.184, 32.378] dB and [0.92868, 0.95139]. Recompute these statistics
with `python tools/fidelity_intervals.py results/wan22_t2v_last_fidelity24.json`.

## LAST across backbones on matched text-to-video samples

Both columns use paper-000 through paper-023 from the same manifest. Each backbone generated its own videos. Each condition has 12,288 information bits and 24 entire messages per backbone. Run `python tools/paired_backbone_table.py` to regenerate the comparison or add `--count 10` for the earlier prefix.

| Condition | Hunyuan correct bits | Wan2.2 correct bits | Hunyuan exact | Wan2.2 exact |
| --- | ---: | ---: | ---: | ---: |
| clean | 12288 | 12288 | 24 | 24 |
| noise | 12178 | 12154 | 18 | 18 |
| compression | 12005 | 11957 | 10 | 15 |
| blur | 12258 | 12208 | 21 | 19 |
| drop | 9665 | 8749 | 0 | 0 |
| insert | 10949 | 10281 | 2 | 1 |
| clip | 12067 | 11988 | 14 | 18 |

Run `python tools/paired_lfg_table.py --samples 7` to regenerate the seven-sample, two-prompt Hunyuan image-to-video comparison from the [matched LAST and LFG observations](../results/hunyuan_i2v_last_lfg_first_seven_paired.json).
For image-to-video, run `python tools/paired_backbone_table.py --mode i2v`. Each column uses the first 44 manifest entries, with 22,528 information bits per condition and 44 messages. Both backbones share the manifest entries and each generates its own MP4. Use `--count 43` or `--count 30` to reproduce earlier prefixes.
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

### Render the current Wan-2.2 tables

The two five-video reports cover the first two prompts of each generation mode. To render clean recovery (Table 1 layout) and attacked recovery (Table 2 layout), run:

```bash
python -m last.clean_table --family wan22 --reports results/wan22_t2v_paired_primary_first_five.json results/wan22_i2v_paired_primary_first_five.json --output tables/wan22-clean.md
python -m last.robustness_table --reports results/wan22_t2v_paired_primary_first_five.json results/wan22_i2v_paired_primary_first_five.json --output tables/wan22-attacks
```

The coverage label 5/400 counts completed videos in the supplied subset against the planned benchmark. Bit accuracy uses the 2,560 measured information bits per cell. The attack table also exports integer bit counts and exact-message counts to CSV. Missing official quality scores remain pending. The [five text-to-video fidelity pairs](../results/wan22_t2v_paired_fidelity_5.json) use byte-identical reference files across methods for all five cases.

### Hunyuan primary tables from the thirteen paired image-to-video cases

```bash
python -m last.clean_table --family hunyuan --reports results/hunyuan_i2v_paired_primary_first13.json results/hunyuan_t2v_paired_primary_first_five.json --output tables/hunyuan-clean.md
python -m last.robustness_table --reports results/hunyuan_i2v_paired_primary_first13.json results/hunyuan_t2v_paired_primary_first_five.json --output tables/hunyuan-attacks
```

To repeat the private artifact audit with resumed acquisitions, supply the
original LAST plan via `--plan`, its continuation via `--additional-last-plan`,
and the LFG plan via `--lfg-plan` to `tools/paired_primary_subset.py`.
The completed job receipt selects the exact plan for each video and arm. The audit checks the generation family, mode, method and seed, the 512-bit binary message, and for image-to-video the bytes of the conditioning image against its manifest digest. Keep the original conditioning images available at the case paths for this audit.
Pass the historical `--reextraction-index` when incorporating independently
repeated extractions; only entries for this slice are used. The thirteen-case
report includes the twelve previously published cases, with matching counts
and received-video digests on all 168 overlapping observations. Use this
report alone for this image-to-video subset.

### Four-pipeline paired snapshot

The latest audited primary prefixes contain 13 Hunyuan I2V pairs and eight
pairs in each other pipeline. Across the four pipelines this yields 518
method-by-video-by-condition records. The eight-case prefixes each cover two
prompts and four seeds per prompt. All three preserve the earlier five cases.

```bash
python -m last.robustness_table --reports results/hunyuan_i2v_paired_primary_first13.json results/hunyuan_t2v_primary8.json results/wan22_i2v_primary8.json results/wan22_t2v_primary8.json --output tables/four-pipeline-attacks
python -m last.clean_table --family hunyuan --reports results/hunyuan_i2v_paired_primary_first13.json results/hunyuan_t2v_primary8.json --output tables/hunyuan-prefix-clean.md
python -m last.clean_table --family wan22 --reports results/wan22_i2v_primary8.json results/wan22_t2v_primary8.json --output tables/wan22-prefix-clean.md
```

Both eight-case Wan pipelines use byte-identical reference videos across the
two methods on every pair. In Hunyuan T2V the two unmarked reference MP4s
differ on all eight pairs. Each fidelity measurement uses the reference from
that method's own paired generation.

### VideoMark and LAST on 35 matched Hunyuan text-to-video cases

Run `python tools/paired_videomark_table.py --count 35` to compare the
[first 35 VideoMark cases](../results/hunyuan_t2v_videomark_first35.json)
against the same IDs in the LAST 50-case report. Each condition contributes
17,920 bits per method. The 245 native predictions were recounted on the
evaluation host from retained decoded bytes against the message used for
the corresponding LAST case. The audit also matches prompt, seed and edit
map. The native historical receipts lack decoded-byte hashes on all 245
reads. Current byte recounts agree with the saved scores; the original
decoded byte sequence cannot be independently authenticated from those
receipts alone.

To rebuild the counts on the evaluation host, use
`python tools/audit_videomark_prefix.py --root /private/primary --manifest configs/primary_manifest.json --plan /private/native-plan.json --count 35 --output videomark35.json`.

### Rebuild the primary LAST row from the message-level measurements

Run these commands from the repository root. The same 170 measured videos contribute to each I2V attack cell. The aggregate carries the hash of the source measurements and the planned denominator of 400 videos.

```bash
python tools/primary_message_tables.py --report results/hunyuan_i2v_primary_message_170.json --aggregate primary-counts.json
python -m last.clean_table --family hunyuan --reports primary-counts.json --quality results/hunyuan_i2v_quality_six_dimensions_last.json results/hunyuan_i2v_quality_five_dimensions_reference.json --output table1-last.md
python -m last.robustness_table --reports primary-counts.json --output table2-last
```

The clean bit accuracy covers 170 videos. V-score uses its own 18-dimension protocol. The current five completed dimensions leave V-score pending. For a LAST/LFG comparison on identical samples, use the 16 paired cases linked from the README.
To check deterministic attack acquisition on an existing generated MP4, run `python tools/replay_primary_attacks.py --run /private/primary/hunyuan/i2v/last/paper-005`. It regenerates the six edits in a temporary directory, rereads their MP4s and matches hashes, frame counts and temporal maps against the original evaluation receipts. The [paper-005 replay](../results/replay_attacks_paper005.json) matched all six archived edits in the reproduction environment; the clean row checks the original marked file.

### Compare all four pipelines on the same eight primary IDs

From the repository root, run the following Bash loop to render all seven
conditions for each pipeline on paper-000 through paper-007. Each accuracy
uses 4,096 information bits. Each exact-message rate uses eight videos.
The same IDs specify matched prompts and seeds across pipelines. Each model
and generation mode produces its own videos.

```bash
for report in hunyuan_i2v_paired_primary_first16 hunyuan_t2v_primary9 wan22_i2v_primary8 wan22_t2v_primary8; do
  echo "$report"
  python tools/paired_lfg_table.py --report "results/$report.json" --first 8
done
```

For deletion, the LAST/LFG correct-bit counts are 3129/2795 (Hunyuan I2V),
3263/2786 (Hunyuan T2V), 2825/2791 (Wan2.2 I2V), and 3086/2738 (Wan2.2 T2V).
Neither method recovered a complete deleted-video message in these four slices.
For clipping, the LAST exact counts are 4, 4, 4 and 6 of eight respectively;
LFG recovered zero complete messages in each slice. These prefixes supply
partial reproduction results for the 400-case protocol.

The Wan2.2 I2V LAST snapshot covers the first 43 specified primary cases and
all seven conditions. Recreate its Table 2 row in a new output directory:

```bash
python -m last.robustness_table --reports results/wan22_i2v_last_first43.json --output wan43-table
```

All 210 observations in the earlier 30-case release matched the expanded
report on their shared fields. The 43-case snapshot includes 301 verified
observations. The 357 remaining cases have no score in each condition.

The [44-video Wan2.2 I2V LAST fidelity report](../results/wan22_i2v_last_fidelity44.json)
covers the same IDs as the [44-video attack report](../results/wan22_i2v_last_first44.json).
Mean PSNR is 30.616 dB (95% prompt-cluster interval 29.391 to 32.153) and
mean SSIM is 0.9263 (0.9118 to 0.9410). The intervals use 11 prompts,
10,000 resamples and seed 0. Run
`python tools/fidelity_intervals.py results/wan22_i2v_last_fidelity44.json`
to regenerate these values, or
`python tools/primary_message_fidelity.py --root /private/primary --report results/wan22_i2v_last_first44.json`
to verify them against the received video hashes and paired reference files.

Both main table commands read the benchmark denominator from current
(`planned_videos_per_method`) and earlier (`planned_videos`) audited reports.
For example, Hunyuan T2V LAST recovered every clean bit in its first 50 cases.
The manuscript protocol plans 400, so the corresponding clean cell is
`1.000 (50/400)`. To reproduce it:

```bash
python -m last.clean_table --family hunyuan --reports results/hunyuan_t2v_last_first50.json --output clean-first50.md
```

The Hunyuan T2V LAST snapshot contains 74/400 videos and 518 verified
condition receipts. All 511 overlapping observations agree with the earlier
73-case snapshot. Render the Table 2 row on CPU:

```bash
python -m last.robustness_table --reports results/hunyuan_t2v_last_first74.json --output hunyuan74-table
```

To generate the same report format from your own campaign, use the actual
generation plan for those runs. The method, model and mode select one of its
400-case pipelines. Existing MP4s and their original attack receipts are
verified and missing observations retain their planned denominator.

```bash
python tools/primary_pipeline_report.py --plan /private/primary-plan.json --root /private/primary --family hunyuan --mode t2v --method last --output hunyuan-t2v-last.json
```
For the same 74 Hunyuan T2V LAST cases, run `python tools/fidelity_intervals.py results/hunyuan_t2v_last_fidelity74.json`. The mean per-video PSNR is 32.607 dB and SSIM is 0.92754. The 95% prompt-cluster intervals across 19 prompts are [31.445, 33.959] and [0.91494, 0.93908].

To recount frame deletion directly from the released per-video records (CPU,
standard-library Python), run the following from the repository root:

```python
import json
from pathlib import Path

report = json.loads(Path("results/hunyuan_t2v_last_first74.json").read_bytes())
rows = [r for r in report["audited_observations"] if r["condition"] == "drop"]
assert len({r["video_id"] for r in rows}) == len(rows)
correct = sum(r["correct_bits"] for r in rows)
total = sum(r["total_bits"] for r in rows)
exact = sum(r["correct_bits"] == r["total_bits"] for r in rows)
print(f"Correct bits: {correct}/{total} ({correct/total:.2%})")
print(f"Entire messages recovered: {exact}/{len(rows)} ({exact/len(rows):.2%})")
```

This yields 29,132/37,888 correct bits (76.89%) and 1/74 entire messages
recovered (1.35%). Each video contributes 512 information bits. The 326
pending videos are excluded from both observed rates.
The 72-video Hunyuan T2V report was replayed against the archived acquisition plan (SHA-256 50c3116868fbec36447cac9ae7a03c4ef9d55c9eed001399d66251b564408447). After checking case IDs, prompts, seeds, key slots and the generation receipts against the case files, the output SHA-256 was 8600dfc7143a05d98bc41d016d6e0fbf06d370d019777d8d99db2250c80de876, identical to the released report.

### Matched temporal attacks by backbone and input mode

All entries are observed information-bit accuracy on the same frozen sample IDs for LAST and LFG. The pairs in each cell are LAST / LFG. Each sample contributes 512 bits per condition. The primary experiment plans 400 samples per pipeline. Hunyuan I2V includes paper-000 through paper-024 and paper-291.

| Backbone and mode | Paired videos | Deletion | Insertion | Clip |
|---|---:|---:|---:|---:|
| Hunyuan I2V ([first 24](../results/hunyuan_i2v_primary24.json), [024](../results/hunyuan_i2v_primary_slice024.json), [291](../results/hunyuan_i2v_primary_slice291.json)) | 26 | 76.56% / 65.99% | 87.26% / 59.37% | 98.37% / 77.42% |
| [hunyuan t2v](../results/hunyuan_t2v_primary14.json) | 14 | 75.63% / 64.75% | 90.69% / 57.53% | 97.74% / 73.62% |
| [wan22 i2v](../results/wan22_i2v_primary14.json) | 14 | 65.625% / 66.03% | 84.42% / 56.57% | 94.81% / 76.88% |
| [wan22 t2v](../results/wan22_t2v_primary13.json) | 13 | 73.39% / 65.88% | 83.41% / 54.70% | 95.49% / 75.71% |

The fidelity scores below use the same samples as the temporal-attack rows above. Each PSNR value averages per-video PSNR in dB. Reference matches count byte-identical unmarked MP4s between methods, verified by SHA-256.

| Backbone and mode | Paired videos | Matching references | PSNR LAST / LFG | SSIM LAST / LFG |
|---|---:|---:|---:|---:|
| Hunyuan I2V ([first 24](../results/hunyuan_i2v_fidelity24.json), [024](../results/hunyuan_i2v_paired_fidelity_slice024.json), [291](../results/hunyuan_i2v_paired_fidelity_slice291.json)) | 26 | 3/26 | 31.67 / 22.46 | 0.9338 / 0.7208 |
| [hunyuan_t2v](../results/hunyuan_t2v_fidelity14.json) | 14 | 0/14 | 31.80 / 22.53 | 0.9338 / 0.7286 |
| [wan22_i2v](../results/wan22_i2v_fidelity14.json) | 14 | 14/14 | 30.18 / 23.53 | 0.9382 / 0.8163 |
| [wan22_t2v](../results/wan22_t2v_fidelity13.json) | 13 | 13/13 | 31.37 / 25.24 | 0.9476 / 0.8446 |

Decoded Hunyuan reference comparisons use all 65 frames of both unmarked videos. Reproduce with `python tools/paired_reference_differences.py --report <paired-fidelity.json> --root <primary-runs>`. RMSE below measures channel differences on the 0–255 scale. It does not measure perceived quality.

- [Hunyuan I2V](../results/hunyuan_i2v_pixels24.json): 22/24 paired unmarked references differed after decoding. RMSE across the differing pairs ranged from 1.660 to 2.750 out of 255. On paper-022 the RMSE was 2.750 over 65 frames. The [generation settings](../results/hunyuan_i2v_settings24.json) cover the same 24 pairs. PSNR and SSIM in the table use each method's own reference.
- [Hunyuan t2v](../results/hunyuan_t2v_reference_pixels14.json): all 14 pairs had different decoded values. RMSE ranged from 1.612 to 2.824. The first nine pairs yielded the same pixel statistics in the earlier OpenCV 3.4.18 run and this OpenCV 4.10.0 run.

For the 24 Hunyuan I2V pairs, the generation receipt hashes the bytes of
`src/last/smoke.py`. The archived copies matching those hashes came from
LAST revision `c1f2f694cfb777053795e7bbf186b5776c9fecd0` and LFG revision
`b4f9eeadb912b2850eef7d381b14b341c669dd89`. The latter script exposes the
LAST margin and fixed-target options, validates them on resume, records them
and passes them to the LAST embedding call. Both scripts construct the
initial latent and run the unmarked diffusion pass with the same code. LFG
then runs a separate marked pass before decoding the reference. The reference
latent in both branches is the output of the unmarked pass.

| LAST process limit (GiB) | LFG process limit (GiB) | Pairs | Pixel-identical unmarked references |
|---:|---:|---:|---:|
| 8 | 12 | 18 | 0 |
| 12 | 8 | 4 | 0 |
| 12 | 12 | 2 | 2 |

The source fingerprint differs even in the two identical pairs. The memory
limit coincides with the pixel difference pattern on this prefix. These runs
did not vary the limit in isolation on each sample, so the pattern does not
establish causality. Join the linked settings and decoded-pixel reports on
`video_id` to reproduce the counts.

Add `--settings-only` to the reference comparison command to audit the
generation configuration for each pair. On the [fourteen T2V pairs](../results/hunyuan_t2v_reference_settings14.json),
the case file, seed, recorded generation source, sampler settings, model
directory name, hardware label and offload mode matched within each pair.
All fourteen pairs used process limits of 8 GiB for LAST and 12 GiB for LFG.
Each fidelity score uses its own recorded reference. These records establish
the configuration difference; they do not identify the cause of the pixel differences.

To rebuild the Hunyuan I2V quality columns of Table 1 from individual public scores, run these commands from the repository root in a Linux shell:

```bash
python tools/quality_units_table.py results/hunyuan_i2v_quality_units/*_last.json > quality-last.json
python tools/quality_units_table.py results/hunyuan_i2v_quality_units/*_reference.json > quality-reference.json
python -m last.clean_table --family hunyuan --quality quality-last.json quality-reference.json --output table1-quality.md
```

The LAST row covers six of 18 dimensions and the unmarked reference covers five. The additional LAST score is for dynamic spatial relationships. Each dimension retains the number of valid and inapplicable scoring units. Creativity is complete for this subset of dimensions; the overall V-score is pending.

### Include the native baseline results in the Hunyuan tables

To render Tables 1 and 2 with the available VideoShield I2V, SIGMark I2V and VideoMark T2V observations, run in Bash from the repository root:

```bash
reports=(results/hunyuan_i2v_primary24.json results/hunyuan_t2v_primary14.json
         results/hunyuan_i2v_videoshield_first2_complete.json results/hunyuan_t2v_videomark_first40.json
         results/hunyuan_i2v_sigmark_first1_partial.json)
python -m last.clean_table --family hunyuan --reports "${reports[@]}" \
  --quality results/hunyuan_i2v_quality_six_dimensions_last.json results/hunyuan_i2v_quality_five_dimensions_reference.json \
    results/camera_motion/hunyuan_t2v_{last,reference}_camera_quality.json \
    results/hunyuan_i2v_lfg_camera_quality.json results/hunyuan_t2v_videomark_quality.json --output native-tables/table1.md
python -m last.robustness_table --reports "${reports[@]}" --output native-tables/table2
```

On Hunyuan I2V `paper-000`, SIGMark recovered 483, 256, 257, 345 and 272
of 512 bits on clean, noise, compression, blur and contiguous removal.
Random deletion and insertion failed during extraction. All five scored
predictions were recounted. Four historical receipts lack prediction-file
digests. To repeat this partial audit on the original run tree:

```bash
python tools/audit_videomark_prefix.py --method sigmark --mode i2v --count 1 \
  --manifest configs/primary_manifest.json --plan /private/native-plan.json \
  --root /private/primary --allow-incomplete --output sigmark-partial.json
```

For a comparison on the same input, the following rows use only Hunyuan I2V
`paper-000` and primary map seed 0. Each entry counts correct information bits
out of 512. Every method generates its own marked video. LAST uses the verified
re-extraction from its archived MP4s for this historical sample.

| Method | Clean | Noise | Compression | Blur | Drop | Insert | Clip |
|---|---:|---:|---:|---:|---:|---:|---:|
| LAST | 512 | 512 | 486 | 512 | 371 | 424 | 502 |
| LFG | 500 | 483 | 488 | 488 | 349 | 276 | 358 |
| SIGMark | 483 | 256 | 257 | 345 | Failed | Failed | 272 |
| VideoShield | 512 | 512 | 512 | 512 | 512 | 509 | 512 |

Read the `audited_observations` arrays in the paired primary and two native
I2V reports listed above. Select `video_id == "paper-000"` and `map_seed == 0`,
then take `correct_bits` for each method and condition. SIGMark's two
failed extractions are recorded in `incomplete_observations`. The larger
tables above include different numbers of samples for each method.

To compare methods with different coverage, take the intersection of their
verified sample IDs separately for each condition. The command prints the IDs,
correct bits and, in parentheses, entire messages recovered. A dash means no
common scored sample. Failures and pending cases remain in the input reports.

```bash
python tools/matched_primary_methods.py --family hunyuan --mode i2v \
  --methods last lfg videoshield --reports results/hunyuan_i2v_primary24.json \
  results/hunyuan_i2v_videoshield_first2_complete.json
```

On the two shared Hunyuan I2V cases, random deletion gave LAST 739/1,024
correct bits, LFG 717/1,024 and VideoShield 1,024/1,024. Whole-message
recovery was 0/2, 0/2 and 2/2, respectively. With only two samples from
the same prompt this comparison is descriptive.

For a three-method Hunyuan T2V comparison on identical manifest IDs, run:

```bash
python tools/matched_primary_methods.py --family hunyuan --mode t2v \
  --methods last lfg videomark --reports results/hunyuan_t2v_primary14.json \
  results/hunyuan_t2v_videomark_first40.json
```

All seven conditions have 13 shared videos (6,656 information bits per
method and condition). On deletion, LAST, LFG and VideoMark recovered
5,014, 4,342 and 3,352 bits, respectively. Each recovered zero entire
messages. The CPU workflow exports the seven-condition table, including
the common video IDs, in `three-method-t2v.md`.

These commands preserve the sample count for each method. VideoShield recovered 1,024/1,024 clean bits across its two I2V samples. VideoMark recovered 14,317/19,968 clean bits on 39 T2V samples, with 17 entire messages recovered. Its quality row covers one of 18 dimensions. SIGMark's individual integration runs remain separate from the primary table.

For a comparison of LAST and VideoMark on **the same 38 T2V videos**, use `python tools/paired_videomark_table.py --count 38`. On random deletion, LAST recovered 15,463 bits and VideoMark 9,959 out of 19,456, with zero and one entire message recovered, respectively. All 266 native predictions in the [38-video report](../results/hunyuan_t2v_videomark_first38.json) were recounted from stored files. The original extraction receipts lack prediction-file digests, which limits verification of those files' history.

For the full 40-video Hunyuan T2V prefix, run
`python tools/paired_videomark_table.py --count 40 --videomark-report hunyuan_t2v_videomark_first40.json`.
All 278 earlier records agree with this [280-observation recount](../results/hunyuan_t2v_videomark_first40.json).
On paper-039, insertion yielded 251/512 bits and contiguous removal yielded
254/512. All 280 VideoMark predictions were recounted against the matched
messages. Their historical receipts lack extraction-time prediction digests.

To check that every VideoMark camera-motion score used the same marked MP4 as the primary clean reader, run `python tools/quality_units_table.py results/hunyuan_t2v_videomark_camera_units.json --primary results/hunyuan_t2v_videomark_first40.json`. All 20 video fingerprints match. The official mean is 0.20 over 20 applicable units. Add results/hunyuan_t2v_videomark_landscape_units.json to the command to reproduce both completed dimensions. The landscape mean is 0.17 over 20 additional videos.

For LAST and the unmarked reference, pass the matching single-method fidelity
report to `tools/quality_units_table.py --fidelity`. The method selects
`marked_sha256` for LAST and `reference_sha256` for the unmarked video.
The Table 1 workflow checks 220 MP4 entries in nine LAST dimension reports and 200 in eight unmarked-reference reports. It also checks 40 entries in two VideoMark reports and 20 in one LFG report. Across the 20 reports, 480 MP4 entries contribute to 366 scoring units. Each of the two Diversity reports groups 60 files into three prompt-level scores.
These are counts of matched input files across methods and dimensions.
Diversity scores are computed per prompt, with several input videos per score.


### Three matched methods on the fixed timing sample

The ordinary Hunyuan I2V evaluations on paper-291 cover seven conditions per method. From the repository root:

```bash
python tools/matched_primary_methods.py --family hunyuan --mode i2v --methods last lfg videoshield --reports results/hunyuan_i2v_primary_slice291.json results/hunyuan_i2v_videoshield_slice291.json
```

Rebuild the [VideoShield counts](../results/hunyuan_i2v_videoshield_slice291.json) from the original acquisition:

```bash
python tools/audit_videomark_prefix.py --root "$PRIMARY_RUNS" --manifest configs/primary_manifest.json --plan "$NATIVE_PLAN" --start-index 291 --count 1 --family hunyuan --mode i2v --method videoshield --output videoshield-paper291.json
```

The audit checks the conditioning image, prompt, seed, 512-bit message, received MP4s and edit positions. It recounts each stored prediction. The seven historical extraction receipts lack prediction hashes recorded at extraction time. These scores cover one matched video. Formal efficiency measurements on the same sample require an exclusive GPU run.


For the complete intersection of Hunyuan I2V samples currently scored by all three methods (paper-000, paper-001 and paper-291), run:

```bash
python tools/matched_primary_methods.py --family hunyuan --mode i2v --methods last lfg videoshield --reports results/hunyuan_i2v_primary24.json results/hunyuan_i2v_primary_slice291.json results/hunyuan_i2v_videoshield_first2_complete.json results/hunyuan_i2v_videoshield_slice291.json
```

On random deletion, LAST, LFG and VideoShield recovered 989, 1,037 and 1,536 of 1,536 bits respectively. VideoShield recovered all three messages. On insertion, VideoShield recovered 1,520 bits and ranked first on each video. On contiguous removal, LAST and VideoShield tied at 512 bits on paper-001; VideoShield recovered more bits on the other two. The separate Wan I2V comparison covers only paper-000. These matched intersections include the preselected timing case and have limited coverage of the 400 planned samples per pipeline.


The [partial SIGMark recount for paper-291](../results/hunyuan_i2v_sigmark_slice291_partial.json) adds clean and noise reads to the four-method intersection. Use the native audit command above with `--method sigmark --allow-incomplete` and a fresh output path. On paper-000 SIGMark recovered 483/512 clean bits, and on paper-291 it recovered 242/512. Each clean read used one completed 50-step inversion of the full 65-frame MP4, with matching generation settings, inversion settings and adapter source hashes across the two runs. Under noise the same two samples yielded 256/512 and 248/512, respectively. The two clean scores describe the observed variation; its cause remains open. The report records the absence of an extraction-time prediction hash. The CI artifact `four-method-i2v.md` lists the common sample IDs for each condition.
