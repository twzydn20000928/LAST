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

The earlier ten-video Wan I2V prefix contains three Camera Motion prompts with four, four and two seeds. Use `--report results/wan22_i2v_primary10.json` and a fresh output file to reproduce its estimates. On random deletion the LAST minus LFG difference was -1.19 percentage points (prompt-cluster interval -10.94 to +12.60). On insertion it was +29.20 (+18.55 to +36.62), and on contiguous removal +15.33 (+1.17 to +21.00). Ten thousand draws resample only these three distinct prompts. These intervals describe sensitivity to the prompts in this prefix and are unstable estimates for the planned cohort.

For Wan I2V after deletion, LAST recovered 1,230 bits and LFG 1,454 on
paper-000 through paper-003. For paper-004 through paper-007 the counts were
1,595 and 1,337. Each group has 2,048 bits. The pooled difference is +0.83
percentage points. Across the two prompts the individual differences are
−10.94 and +12.60 points. With only two prompt clusters, the 95% bootstrap
interval reaches exactly these two endpoints; it describes the observed
prefix and gives little information about variability across new prompts.

Using the four paired reports in the main Table 2 replay gives the following
random-deletion differences. Values are percentage points of bit accuracy
(LAST minus LFG). Intervals use 10,000 paired draws of whole prompts, seed 0.

| Report in `results/` | Videos | Distinct prompts | Correct bits, LAST / LFG | Bits per method | Difference | 95% interval |
|---|---:|---:|---:|---:|---:|---:|
| `hunyuan_i2v_primary18.json` | 18 | 5 | 6,842 / 6,082 | 9,216 | +8.25 | [+0.34, +14.43] |
| `hunyuan_t2v_primary12.json` | 12 | 3 | 4,610 / 4,049 | 6,144 | +9.13 | [+4.10, +12.94] |
| `wan22_i2v_primary12.json` | 12 | 3 | 4,086 / 4,180 | 6,144 | -1.53 | [-10.94, +12.60] |
| `wan22_t2v_primary11.json` | 11 | 3 | 4,079 / 3,731 | 5,632 | +6.18 | [0.00, +12.84] |

After random deletion, both methods recovered zero entire 512-bit messages in
each of these four paired prefixes. For example, on Hunyuan I2V the 760 extra
correct bits across 18 videos give a difference of 100 × 760 / 9,216 = 8.25
percentage points, while whole-message recovery is 0/18 for both methods.
To verify the counts, filter the Table 2 `counts.csv` to `condition=drop` and
methods `last` and `lfg`. Its `exact_messages` column counts videos for which
all 512 decoded bits match.

The ninth Wan I2V video introduces a third prompt and changes the sign of
the pooled difference. These intervals reflect the limited observed prompts.
To replay any row, pass its report to the command above and multiply
`bit_accuracy` and `bit_accuracy_ci95` for condition `drop` by 100.

### Supplement I: deletion recovery by key

Run `python tools/deletion_by_key.py results/hunyuan_i2v_paired_primary_first13.json` to group the audited primary LAST deletion trials by manifest key slot. All 512 information bits must match for one recovery. The thirteen available prefix cases cover eight slots with counts of 2, 2, 2, 2, 2, 1, 1 and 1 videos. None recovered the entire message. The published paper reports 368/400 on its full run. Use a full 400-video report to compute the minimum and maximum of the eight block recovery rates, each based on 50 videos.

### Source-group survival under random deletion

Run `python tools/deletion_group_survival.py --report results/hunyuan_i2v_paired_primary_first13.json`. The script inspects the 400 reconstructed primary deletion maps (65 frames, 30 distinct removals, seed 0) and optionally joins observed Hunyuan I2V LAST results. Source frame 0 is the initial frame; original groups are frames 1–4, 5–8 and so on. A pair survives intact only if all eight frames of two adjacent source groups survive. Of the 400 maps, 27 preserve such a pair and 83 preserve no complete group. None of the first thirteen maps preserve an intact adjacent pair. CCTA can still construct candidate chains from mixed or partially surviving groups, and the repeated payload can provide useful evidence there. These map counts measure source-group survival, not extraction success, route selection or an upper bound on message recovery.
For the supplementary PSNR and SSIM intervals, run `python tools/fidelity_intervals.py results/hunyuan_i2v_paired_fidelity_first13.json`. Use `--method lfg` for the LFG adaptation. Each video contributes one measurement against its own paired reference. The 10,000 draws sample entire prompt clusters with replacement and retain all videos for each drawn cluster. The current prefix spans only four prompts and cannot establish population-level precision. V-score requires separate dimension-level scoring.
Primary deletion snapshot: `python tools/primary_deletion_errors.py --root /private/primary` scans original Hunyuan I2V LAST attack receipts and verifies the manifest case, primary frame map, marked MP4 and received MP4. The [observations](../results/hunyuan_i2v_primary_deletion_errors.json) cover 170 videos; eight legacy receipts lacked a recorded received-file hash and were excluded. Of 170, one recovered the whole message, 169 returned a wrong message with BCH failure, and none returned a wrong message with BCH success. Median post-decoding error was 130/512. Results from replayed extractions are tracked separately.
On the same 170 primary deletion receipts, all 170 used the consistency-chain route. Among 643 selected windows, 154/87/166/172/64 had respectively 0/1/2/3/4 received frames from the predicted source group. Use `python tools/deletion_chain_audit.py --root /private/primary --report results/hunyuan_i2v_primary_deletion_errors.json` to recompute the [window counts](../results/hunyuan_i2v_primary_deletion_chains.json). Ground-truth frame indices are used only after blind extraction. A four-frame window with partial group support may still carry information; this histogram is separate from message recovery.
For Tables 10–11 on the 170-case deletion cohort, run `python tools/primary_message_tables.py --report results/hunyuan_i2v_primary_message_170.json`. This uses exactly the same sample identifiers for all seven conditions. To acquire the measurements from the original generated files use `--root /private/primary --cohort results/hunyuan_i2v_primary_deletion_errors.json --export new-counts.json`. Every row requires both MP4 hashes, its primary attack map and its original correction status. All 1,190 public observations contain pre- and post-decoding counts.

To include all of the first 179 videos in Tables 10 and 11, run:

```bash
python tools/hunyuan_prefix_recovery.py --additional-original results/hunyuan_i2v_message_178_179.json \
  --verify-original-slice results/hunyuan_i2v_last_primary100_178.json \
  --message-tables results/replayed_message_counts_eight.json
```

Of these videos, 171 contribute original extraction records. Eight contribute
independent extractions from their archived MP4s. Each of the seven conditions
covers the same 91,648 information bits. After deletion the BCH decoder reduced
the total errors from 25,163 to 25,162; after blur, from 831 to 453.
The second table gives the per-video error distribution. To rebuild the eight
re-extraction records from the archived replay directory, run
`python tools/export_replayed_message_counts.py --root /private/bch-replays --output replay-counts.json`.
The exporter checks each source receipt hash, received video fingerprint and
post-decoding count against the archived measurements.

Across those same 179 videos, mean per-video PSNR was 32.946 dB
(95% interval 32.370–33.542) and mean SSIM was 0.94293 (0.93756–0.94817).
Both compare the marked video with its own unmarked reference. The interval
calculation resamples the 33 prompt clusters with 10,000 draws and seed 0.
Rebuild the interval from the published observations with the first command.
The second command verifies both MP4 files per video against the original runs.

```bash
python tools/fidelity_intervals.py results/hunyuan_i2v_primary_fidelity_179.json
python tools/primary_message_fidelity.py --root /private/primary \
  --report results/hunyuan_i2v_last_first100_robustness.json \
  --additional-report results/hunyuan_i2v_last_primary100_178.json > fidelity179.json
```
For fidelity on exactly the 170 Hunyuan I2V Table 10–11 videos, run `python tools/fidelity_intervals.py results/hunyuan_i2v_primary_fidelity_170.json`. These 32 prompt clusters yield mean per-video PSNR 33.025 dB and mean SSIM 0.94333. The report records the digest of its parent message table. To rebuild it, run `python tools/primary_message_fidelity.py --root /private/primary --report results/hunyuan_i2v_primary_message_170.json` against the original marked and reference MP4s.

### Complete 178-video prefix using two measurement sources

Run `python tools/hunyuan_prefix_recovery.py` to recount Hunyuan I2V LAST
paper-000 through paper-177. The original-receipt column uses 170 videos.
For the eight IDs missing historical received-file hashes, the replay column
uses later blind extractions identified in the 100-video robustness report.
The eight-video pre/post-BCH report has a different set of replay receipt
hashes and agrees on the seven aggregate bit and exact-message counts. The
script checks these totals separately. It also checks all 644 overlapping
original records across the two larger reports against their MP4 and receipt
hashes and bit counts. Each video contributes once per condition. Deletion
gives 66,132/91,136 correct bits (72.56%) and one exact message out of 178.
The original-only 170-video snapshot remains separately reproducible above.

### Same final length, different temporal edits

Run `python tools/deletion_group_survival.py --matched-edits results/hunyuan_i2v_primary_message_170.json`
to join the primary attack maps to both measured outputs for each Hunyuan I2V
LAST video. Both edits remove 30 frames and preserve the order of the other 35.
An intact source group retains all four of its frames. Random deletion retained
215 of 2,720 source groups, and ten videos retained an intact adjacent pair.
Contiguous removal retained 1,325 groups, and all 170 videos retained an intact
adjacent pair. Contiguous removal yielded more correct bits on 169 paired videos
and the same count on one. Exact recovery was 76/170 versus 1/170 for random
deletion. The one exact random-deletion recovery came from the 160 cases without
an intact adjacent pair. These counts describe which frames survived the edit;
they do not establish which windows the blind reader actually selected.

### Which windows the blind reader actually selected

For the same 170 Hunyuan I2V LAST videos, recount the stored CCTA selections
against each edit map **after** extraction:

```bash
for edit in drop clip insert; do
  python tools/deletion_chain_audit.py --root /private/primary \
    --report results/hunyuan_i2v_primary_message_170.json --condition "$edit"
done
```

The exported files are `results/primary170_{drop,clip,insert}_windows.json`.
A support count of four means that all four received frames in a selected
window belong to its predicted original group. For random deletion 64/643
selected windows met this criterion. For contiguous removal it was 1097/1169.
For insertion it was 237/1227, covering 169 CCTA outputs. The remaining
insertion case used the energy-spacing fallback and has no recorded CCTA
chain. Denominators count selected windows; multiple windows can come from
one video. This audit measures alignment on existing bits and videos without
changing the blind decoder.

The same files also distinguish crossing a group boundary from assigning a
wrong identity to an intact group. Under random deletion, 570/643 selected
windows spanned source groups, 64 were intact and correctly identified, three
were intact with the wrong identity, and six contained the initial frame.
For contiguous removal the counts were 68, 1097, zero and four. Under
insertion, 781/1227 windows contained at least one inserted frame. Categories
are exclusive: inserted frames take precedence, then the initial frame, then
group boundaries and identity. These are window counts pooled across videos.

For random deletion, group the same 170 videos by the number of selected
windows with all four frames from the correctly identified original group:

| Intact, correctly identified windows per video | Videos | Correct bits / evaluated bits | Entire messages recovered |
|---|---:|---:|---:|
| 0 | 116 | 41,393 / 59,392 (69.69%) | 1 |
| 1 | 45 | 18,013 / 23,040 (78.18%) | 0 |
| 2 or more | 9 | 3,772 / 4,608 (81.86%) | 0 |

The sole exact message came from `paper-023`. Each of its five selected
windows crossed a boundary: three retained three frames of the predicted
group and two retained two. This case demonstrates that partial groups can
supply enough evidence to decode a full message. The accuracy differences
between rows describe an association on the observed videos.

Of the 116 deletion cases in the first row, 33 had no intact group left in
the received video. In the other 83, at least one intact group survived but
the reader selected none with the correct identity. This includes
`paper-023`, where one intact group was available. For contiguous removal
on the same videos, all 170 had at least one correctly identified intact
group in the selected chain. These counts can be reproduced by joining each
video's window classifications to its frozen edit map:

```python
import json
from collections import Counter, defaultdict
from pathlib import Path
from last.temporal import attack_map

rows = json.loads(Path("results/primary170_drop_windows.json").read_bytes())["videos"]
by_count = defaultdict(list)
for row in rows:
    intact = row["window_types"].get("intact_correct_identity", 0)
    by_count[min(intact, 2)].append(row["correct_bits"])
for count, bits in sorted(by_count.items()):
    print(count, len(bits), sum(bits), 512 * len(bits), bits.count(512))

for edit in ("drop", "clip"):
    report = json.loads(Path(f"results/primary170_{edit}_windows.json").read_bytes())
    cases = Counter()
    for row in report["videos"]:
        received = set(attack_map(row["video_id"], edit))
        intact = sum(received.issuperset(range(i, i + 4)) for i in range(1, 65, 4))
        hits = row["window_types"].get("intact_correct_identity", 0)
        assert 0 <= hits <= intact
        if hits:
            cases["selected at least one"] += 1
        elif intact:
            cases["survived but none selected correctly"] += 1
        else:
            cases["none survived"] += 1
    print(edit, cases)
```

### Where intact deletion windows leave the reader

To acquire an additional contiguous slice for the primary message tables,
run `python tools/primary_message_tables.py --root /private/primary --range 178 179 --export new-original.json`.
The indices are zero-based with an exclusive upper bound. The command verifies
all seven original attack receipts and both MP4 fingerprints per observation.
Use `python tools/hunyuan_prefix_recovery.py --additional-original new-original.json`
to add the slice to the original 178-video prefix. The recount rejects overlap
with either original or independently replayed cases and rejects gaps in the
combined prefix. The [paper-178 observations](../results/hunyuan_i2v_message_178_179.json)
give 354/512 bits for random deletion and 380/512 for insertion.

Replay optical-flow segmentation and the four-frame sliding windows on the
170 archived received MP4s. The script verifies the MP4 and evaluation receipt
hashes and checks that every window in the saved CCTA chains occurs in the
replayed candidate set.

```bash
python tools/deletion_candidate_audit.py --root /private/primary \
  --report results/hunyuan_i2v_primary_message_170.json > drop-candidates.json
```

| Stage | Intact groups | Videos with at least one |
|---|---:|---:|
| Survived the edit | 215 | 137 |
| Appeared among sliding-window candidates | 213 | 135 |
| Selected with the correct group identity | 64 | 54 |

Of the 83 videos with a surviving group but no correctly selected intact
window, two lost every intact candidate at segmentation. The other 81 still
had an intact candidate entering the reader. The [per-video counts](../results/primary170_drop_candidates.json)
locate that loss after window generation; they do not distinguish identity
scoring from subsequent chain selection.

To join these stages to the measured decoded messages using only public files:

```bash
python tools/deletion_candidate_audit.py --saved-candidates results/primary170_drop_candidates.json \
  --report results/hunyuan_i2v_primary_message_170.json
```

| Outcome on each 35-frame received clip | Videos | Correct information bits | Exact messages |
|---|---:|---:|---:|
| No intact original group survived | 33 | 11,828/16,896 | 0/33 |
| An intact group survived, but none entered the candidate set | 2 | 885/1,024 | 0/2 |
| An intact candidate existed, but none was selected with its correct group ID | 81 | 28,680/41,472 | 1/81 |
| At least one intact candidate was selected with its correct group ID | 54 | 21,785/27,648 | 0/54 |

These are disjoint outcomes of the same reader on different clips. The single exact recovery occurred without a correctly identified intact window. Selecting one such window was insufficient for whole-message recovery in all 54 observed cases. The comparison binds the candidate replay to its source report digest, accepting the LF or CRLF serialization produced by Git on different platforms.
