# Prompt-cluster uncertainty

Before reporting primary tables, run `last.report` with `--verify-artifacts`.
This verifies both the original marked video and the exact received MP4 against
the extraction receipt. Missing received-video hashes or changed files fail the
audit; recomputing a new hash does not validate an old extraction result.
For the clean condition only, the source hash also identifies the received
video because both refer to the same `marked.mp4`.
Legacy receipts without this provenance require a separately documented audit
or re-extraction before inclusion in verified tables.

To independently check existing LAST attack videos without replacing any old
receipts or regenerating videos:

```bash
python -m last.reextract --run /path/to/completed-last-run \
  --model-dir /path/to/frozen-model --output /path/to/new-private-audit
```

The output directory must be new. Each MP4 is passed to the public blind CLI
in a separate process; truth is loaded by the evaluator only after it exits.
The audit hashes videos before and after extraction, prior receipts, reader
sources and private predictions. It records discrepancies rather than keeping
only matching scores. This is a new measurement: equal correct-bit counts do
not prove identical predicted bits, and it cannot retroactively prove which
file an older extractor read. Private decoded messages must not be published.
These audit rows are kept separate from the original primary table; they do
not silently replace its measurements or rewrite its frozen source version.

`results/primary_reextraction_integration.json` records the first completed
seven-condition check on primary `paper-000`: clean/noise/compression/blur/
drop/insert/clip recovered 512/512/486/512/371/424/502 correct bits out of512.
Every correct-bit count matches the original evaluator. Original MP4 and receipt
hashes were rechecked before export. This is one video's new measurement series,
not a 400-video result, a proof of historical bitwise parity, or full-message
recovery under all attacks. The original missing-hash receipts remain unchanged.

`last.cluster_intervals` computes bit accuracy and exact-message recovery, or
paired differences between two methods, using the supplement's prompt-cluster
resampling unit. It does not resample individual bits or treat repeated attack
maps as independent videos.

```bash
python -m last.cluster_intervals --manifest configs/primary_manifest.json \
  --rows /path/to/last-drop-rows.json --map-seeds 0 1 2 3 4 \
  --output /path/to/last-drop-intervals.json
```

Input rows are a JSON list for one method and one condition, with `status`,
`video_id`, `map_seed`, `correct_bits`, `total_bits` and optionally `exact_message`.
Exactly one completed row is required for each manifest video and requested map;
missing, failed, duplicate or extra rows prevent a final estimate. Add
`--paired-rows /path/to/lfg-drop-rows.json` for LAST minus LFG on the same cases.
Paired conditions, families and modes must agree whenever those fields are supplied.

For the primary map (seed 0), a newly generated artifact-verified
`last.report` summary includes the individual bit counts in
`audited_observations`. For example, extract the Hunyuan I2V LAST deletion
rows with the following command and pass the resulting file to
`last.cluster_intervals` with `--map-seeds 0`.

```bash
jq '[.audited_observations[] | select(.family == "hunyuan" and .mode == "i2v" and .method == "last" and .condition == "drop")]' summary.json > last-drop-rows.json
```

Clusters are SHA256 hashes of stripped prompt text, so the same prompt reused in
different dimensions still belongs to one cluster. Each bootstrap draw samples
the original number of prompt clusters with replacement, retaining every video
and map from each sampled cluster. Rates use total successes divided by the
corresponding total trial counts; paired comparisons use identical cluster draws.
The interval is the2.5th–97.5th percentile over10,000draws with PCG64seed0 by default.
Draw count, seed, input hashes and denominators are written to the output.

These numerical bootstrap choices are explicit reconstruction choices where the
manuscript specifies the resampling unit but not all implementation details.
One prompt returns no interval. Few prompts can produce unstable intervals; the
single-video integration measurements therefore do not establish a population
confidence interval. This module does not certify authentication or independence
across secret keys, and a degenerate interval on an all-correct sample does not
prove perfect population performance.

## Message outcomes and error distribution

```bash
python -m last.message_outcomes --manifest configs/primary_manifest.json \
  --root /path/to/primary --family hunyuan --mode i2v --method last \
  --output /path/to/message-outcomes.json --markdown /path/to/tables-10-11.md
```

This entry point reads the seven condition receipts without accessing secret
keys or message files. It records receipt hashes, integer bit-error totals,
pre-BCH errors where available, exact-message recovery and nearest-rank BER
median/p95/p99/maximum. Missing videos remain missing: final rates stay null
until every manifest case has completed. Observed partial rates are separate.

Decoder success is not proof of message recovery. The report distinguishes
wrong messages with decoder failure, wrong messages despite decoder success,
and exact messages. It separately counts decoder failures that nonetheless
return correct systematic information bits. These are decoding outcomes, not
watermark authentication decisions. Descriptive 95% Wilson bounds on message
recovery do not replace the prompt-cluster intervals above.

When the primary Hunyuan I2V results include independently repeated extractions,
pass the corresponding `--reextraction-index` to the message-outcome command.
The evaluator checks each indexed MP4, prediction and source revision against
its replay receipt and uses that pass for both pre- and post-decoding counts.
Older predictions containing only the decoded message contribute to post-BCH
statistics. A pooled pre-BCH result requires raw decisions for every completed
observation in the cell. Keep private predictions on the experiment server.

### Paired method differences on a measured primary prefix

```bash
python tools/paired_primary_intervals.py --report results/wan22_i2v_primary8.json --output tables/wan-i2v-prefix8-differences.json
```

The command reads one paired report, checks its observations against its
aggregate counts, and uses the frozen manifest to group all seeds of a prompt
in the same bootstrap draw. It gives LAST minus LFG in proportion units for
bit accuracy and exact-message recovery, for each of the seven conditions.
The JSON reports measured videos, planned videos and distinct prompts. Use
the other primary prefix reports in the README to repeat the calculation.

For Wan I2V after deletion, LAST recovered 1,230 bits and LFG 1,454 on
paper-000 through paper-003. For paper-004 through paper-007 the counts were
1,595 and 1,337. Each group has 2,048 bits. The pooled difference is +0.83
percentage points. Across the two prompts the individual differences are
−10.94 and +12.60 points. With only two prompt clusters, the 95% bootstrap
interval reaches exactly these two endpoints; it describes the observed
prefix and gives little information about variability across new prompts.

### Supplement I: deletion recovery by key

Run `python tools/deletion_by_key.py results/hunyuan_i2v_paired_primary_first13.json` to group the audited primary LAST deletion trials by manifest key slot. All 512 information bits must match for one recovery. The thirteen available prefix cases cover eight slots with counts of 2, 2, 2, 2, 2, 1, 1 and 1 videos. None recovered the entire message. The published paper reports 368/400 on its full run. Use a full 400-video report to compute the minimum and maximum of the eight block recovery rates, each based on 50 videos.

### Source-group survival under random deletion

Run `python tools/deletion_group_survival.py --report results/hunyuan_i2v_paired_primary_first13.json`. The script inspects the 400 reconstructed primary deletion maps (65 frames, 30 distinct removals, seed 0) and optionally joins observed Hunyuan I2V LAST results. Source frame 0 is the initial frame; original groups are frames 1–4, 5–8 and so on. A pair survives intact only if all eight frames of two adjacent source groups survive. Of the 400 maps, 27 preserve such a pair and 83 preserve no complete group. None of the first thirteen maps preserve an intact adjacent pair. CCTA can still construct candidate chains from mixed or partially surviving groups, and the repeated payload can provide useful evidence there. These map counts measure source-group survival, not extraction success, route selection or an upper bound on message recovery.
For the supplementary PSNR and SSIM intervals, run `python tools/fidelity_intervals.py results/hunyuan_i2v_paired_fidelity_first13.json`. Use `--method lfg` for the LFG adaptation. Each video contributes one measurement against its own paired reference. The 10,000 draws sample entire prompt clusters with replacement and retain all videos for each drawn cluster. The current prefix spans only four prompts and cannot establish population-level precision. V-score requires separate dimension-level scoring.
Primary deletion snapshot: `python tools/primary_deletion_errors.py --root /private/primary` scans original Hunyuan I2V LAST attack receipts and verifies the manifest case, primary frame map, marked MP4 and received MP4. The [observations](../results/hunyuan_i2v_primary_deletion_errors.json) cover 170 videos; eight legacy receipts lacked a recorded received-file hash and were excluded. Of 170, one recovered the whole message, 169 returned a wrong message with BCH failure, and none returned a wrong message with BCH success. Median post-decoding error was 130/512. Results from replayed extractions are tracked separately.
On the same 170 primary deletion receipts, all 170 used the consistency-chain route. Among 643 selected windows, 154/87/166/172/64 had respectively 0/1/2/3/4 received frames from the predicted source group. Use `python tools/deletion_chain_audit.py --root /private/primary --report results/hunyuan_i2v_primary_deletion_errors.json` to recompute the [window counts](../results/hunyuan_i2v_primary_deletion_chains.json). Ground-truth frame indices are used only after blind extraction. A four-frame window with partial group support may still carry information; this histogram is separate from message recovery.
