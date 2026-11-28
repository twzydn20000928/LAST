# Supplement temporal stress protocol

The primary seven-condition evaluator also supports the four supplementary map
seeds without overwriting map0:

```bash
python -m last.evaluate --run /private/last-run --family hunyuan \
  --model-dir /path/to/Hunyuan-I2V --video-id paper-000 --map-seed 1
```

Repeat for seeds2,3,4. Map0 remains in `attacks`; other seeds use
`attacks-map-N`. Only temporal randomization changes: spatial attacks retain
their primary pixel settings and randomness. Cached results must match the
source hash, video ID, method and map seed. The primary table reporter reads
map0 only; repeated-map aggregation remains a separate analysis.

```bash
python -m last.stress --video /private/run/marked.mp4 --video-id paper-000 \
  --attack drop45 --seed 0 --output /private/stress/paper-000/drop45/map0
```

To reproduce the public sailboat deletion on CPU, run from the repository root:

```bash
python -m last.stress --video examples/public_demo/sailboat.mp4 --video-id sailboat-demo-v1 \
  --attack drop30 --seed 0 --demo-codec-threads --output sailboat-drop30
sha256sum sailboat-drop30/received.mp4
```

The expected SHA-256 digest is `355e680d6a82ff9c8b10de34aac21ced4a3d2ed2baeff48a1f3ac85d58475b6d`.
This 35-frame MP4 is byte-identical to the [scored primary demo deletion](../results/public_sailboat_attacks.json)
(471/512 bits on CUDA). The demo flag fixes the encoder thread counts. It is
optional for reader-owned clips.

The [CPU and CUDA predictions](../results/public_sailboat_cpu_drop.json)
selected the same three windows. For example, received frames 28–31
correspond to original frames 54–57, exactly the predicted four-frame group
(one-based frame numbers here). The windows on either side each contained
only two frames from their predicted group. The two readers differed on
one information bit despite choosing the same temporal alignment. Both
returned the raw information-bit signs after BCH decoding failed. The saved
edit map is needed only to audit the alignment after extraction.

Table 15 uses eight edits. Choices are `drop10`, `drop20`, `drop30`, `drop45`, `duplicate30`, `natural30`,
`interpolate30`, and `drop30_crf28`. Map seeds0–4 are fixed before extraction.
Drop30 uses exactly the primary deletion map. Combined editing uses this same
map then CRF28; other exports use CRF18,8fps,yuv420p. Every export is reopened.

Duplicate insertion samples30distinct source frames and copies each immediately
after its source. Natural insertion requires `--donor-reference` pointing to an
unwatermarked same-size clip, selects a contiguous30frame donor portion and
inserts it at a uniformly chosen boundary. The supplement specifies an
unmarked donor clip and leaves donor identities unspecified. For new campaign
runs, use the [registered donor assignments](../configs/stress_donors.json).
Group the primary manifest IDs by normalized prompt in first-occurrence order,
preserve order within each prompt, then rotate this list by its largest group
size (20). Each of the 400 targets receives a different-prompt donor, and each
donor serves one target. The same donor serves all five map seeds. All methods
use the same directory of unmarked LAST reference videos for the backbone and
mode being compared. The exporter verifies the donor case and video receipts.

```bash
python -m last.stress_donors --manifest configs/primary_manifest.json --output /private/rebuilt-donors.json
python -m last.stress --video /private/run/marked.mp4 --video-id paper-000 \
  --attack natural30 --seed 0 --donor-plan configs/stress_donors.json \
  --reference-root /private/primary/hunyuan/i2v/last \
  --output /private/registered-stress/paper-000/natural30/map0
```

For your own 65-frame marked MP4, you can supply a second, unmarked clip
directly. It must have the same resolution and contain at least 30 frames.
Choose a fresh output directory and pass the resulting MP4 to the blind reader:

```bash
python -m last.stress --video marked.mp4 --video-id my-video --seed 0 \
  --attack natural30 --donor-reference unmarked.mp4 --output natural-test
python -m last.extract --family hunyuan --model-dir /path/to/checkpoint \
  --video natural-test/received.mp4 --key /private/secret.key --output prediction.json
```

For a Wan-2.2 video, select `--family wan22` and its matching VAE. The
attack command writes the chosen insertion boundary and donor start in
`natural-test/attack.json`. The extraction command receives only the edited
video, key and model. Use the registered donors above for paper comparisons.

The earlier seven-edit integration used the Hunyuan T2V smoke reference as
its donor. Its donor hash and score remain attached to that diagnostic. The
new assignment for paper-000 uses the reference from paper-020.

Interpolation samples30distinct adjacent pairs. It computes forward/backward
Farneback flow with scale.5,3levels,15window,3iterations,poly5,sigma1.2;
each image is remapped by minus half its flow using bilinear interpolation and
reflected boundaries, then the two warped images are averaged and rounded to
RGB8. These explicit numerical choices fill details absent from the supplement;
they are not claimed to be an unpublished author implementation.

`attack.json` records edit positions and source/received/donor hashes. Pass only
`received.mp4` and the key to `last.extract` (or native baseline video/state to
`last.baseline_extract --temporal`). Attack metadata must not enter the reader.
The exporter claims no bit accuracy. Aggregate repeated maps by original prompt
cluster; five maps of one video are not five independent test videos.

For LAST, the batch evaluator runs an isolated `last.extract` process per exported
condition, with no true message or edit map passed to it:

```bash
python -m last.stress_evaluate --run /private/last-run \
  --attacks /private/stress/paper-000 --family hunyuan \
  --model-dir /path/to/Hunyuan-I2V --output /private/stress-scores/paper-000
```

Use `<attack>/map<seed>/attack.json` and `received.mp4` under the sample
directory, as in the export example. The evaluator checks the nested directory
names against the recorded condition and seed and preserves that structure
in its outputs. It also accepts earlier flat exports with one subdirectory per
condition. Each video/attack/seed combination can occur once per evaluation.
Source and received hashes are verified. The evaluator reads
truth only after extraction exits, records failures explicitly, and retains
private decoded outputs. This command currently evaluates LAST only; other
baseline adapters still require separate stress integration.

New stress evaluation receipts bind the generation receipt, original/received
MP4, attack receipt, private key/message, VAE model files and Python source files
by SHA256. Inputs and source are checked again after the isolated reader exits;
the private prediction is hashed separately. Completed cached evaluations must
match those fingerprints before being reused. Older receipts without this
provenance are rejected: retain them and choose a new output directory for a
pinned-reader replay. No historical score is silently promoted to verified
status. The provenance tests use synthetic files; fresh real-video validation
of this updated evaluator remains pending. Keep evaluation receipts private
because they include private-file paths and fingerprints; publish only sanitized
aggregate records.

Reuse also recomputes correct-bit and exact-message counts from the saved private
prediction and bound truth file, and checks attack name, seed, video ID and model
family. A changed score in a receipt cannot pass merely because the decoded file
hash still matches. This check is post-extraction evaluation; truth never enters
the isolated blind reader. Six CPU tests cover provenance and count checks,
including a synthetic full evaluator run: no message/map argument reaches the
child, a completed case resumes without launching another child, edited counts
are rejected, and a truth-file change during the child marks the case failed.
These orchestration tests do not measure real-video robustness.

## Completed repeated-map diagnostic

`results/map_sensitivity_integration.json` records seeds0..4 for all seven
primary conditions on one existing Hunyuan I2V LAST video, including source,
received-video and receipt hashes. All35conditions completed. Correct-bit
counts below are ordered by map seed, with512informationbits per observation:

| Attack | Correct bits for maps0,1,2,3,4 | Exact messages |
| --- | --- | --- |
| Delete30frames | 371,372,415,404,357 | 0/5 |
| Insert30noise frames | 424,413,474,426,414 | 0/5 |
| Remove30contiguous frames (retain35) | 502,492,512,481,512 | 2/5 |

These are five edits of the same original video. They are not independent
samples, a population confidence interval, or a completed400-video stress test.
The primary seed0 results remain the primary results; none is replaced by the
best-performing map. Only temporal randomness changes between map seeds.

The clipping row removes a contiguous 30-frame interval from the 65-frame
source and concatenates the remaining frames in their original order. It does
not retain a 30-frame excerpt. An earlier label in this document said otherwise;
checking all five recorded edit maps and received-video hashes confirmed the
35 retained frames and consecutive 30 removed indices. The label is corrected;
the videos, maps and measured bit counts have not been changed.

For `paper-000`, the pinned reader also completed seven of the eight supplementary edits at seed 0.
The [measured results](../results/stress_seven_edits_verified.json) list decoded
frame counts, correct information bits, exact recovery and hashes for each MP4
and evaluation receipt. Deleting 30 frames yielded 371/512; adding CRF28
compression to the deletion yielded 331/512 on this case.
For this recorded natural insertion, the first seven source frames are followed by donor frames 21 through 50 (zero-based), then the remaining 58 source frames. The JSON includes the actual edit maps and CRF for all seven observations.

The [20-frame deletion record](../results/stress_drop20_verified.json) completes the eight Table 15 edits for paper-000 at seed 0. The pinned reader recovered 439/512 bits from the 45 retained frames; the message had 73 errors. The received MP4 and prediction were verified, and the count was recomputed from the private prediction and truth on the experiment server. Table 15's mean message recovery rate measures whole messages across videos and map seeds. This single condition contributes one failed exact recovery to that statistic.

### Recompute the Table 15 recovery columns

To generate a Markdown table from all archived forty-map reports, run
`python tools/stress_recovery_table.py --reports results/stress_paper*_forty_maps.json --format markdown`
in Bash. Each row gives the observed trial count over the planned count. Exact
messages count only trials with all 512 information bits correct. Full-cohort
recovery, intervals and map-seed ranges appear when the required data are available.

```bash
python tools/stress_recovery_table.py --manifest configs/primary_manifest.json \
  --index results/stress_recovery_index.json
```

The [source index](../results/stress_recovery_index.json) selects the five-map
series for Drop 20 and Drop 30, the registered donor for natural insertion,
and the original seed-0 records for the other five edits. Each source is
selected by attack protocol and seed coverage. Earlier predictions remain
accessible in their original reports. Use `--reports file1.json file2.json`
for a custom collection of nonoverlapping reports.

The JSON output gives per-edit coverage, bit counts, and exact-message counts.
For example, natural insertion recovered 512/512 bits on paper-000 at seed 0,
contributing one exact message. Duplicate insertion recovered 451/512 bits on
the same case, contributing zero. Drop 20 covers five of 2,000 planned
video–map pairs. Drop 30 covers ten, including [five maps of paper-004](../results/stress_drop30_paper004_five_maps.json).
The other six edits each cover one. Once all 400
videos at each of the five seeds are present,
the script computes mean message recovery, its 95% prompt-cluster bootstrap
interval, and the lowest and highest recovery rates among the five seeds.
Resampling a prompt retains its videos and every associated map. Chain length,
fallback and group accuracy require separate alignment observations.

### Intact groups after editing

For post-extraction scoring, `last.alignment_metrics` accepts the exporter's
`attack.json` as well as primary attack receipts. Pass the received MP4, its
feature cache and the completed blind controlled extraction as described in
[the alignment diagnostic](ABLATIONS.md#post-hoc-grouping-diagnostics).
Both the extraction and the receipt must identify the same received video.
A duplicate retains its original frame ID. A donor frame or a synthesized
midpoint has no original ID. A valid group contains four consecutive original
frames starting at frame 1, 5, 9, … (zero-based).

For paper-000, seed 0, the eight recorded edit maps leave the following
numbers of distinct intact original groups in any four-frame received window,
before segmentation or reader selection:

| Drop 10 | Drop 20 | Drop 30 | Drop 45 | Duplicate 30 | Natural insert 30 | Interpolate 30 | Drop 30 + CRF28 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 8 | 4 | 0 | 0 | 4 | 15 | 2 | 0 |

The unedited source has 16 groups. After Drop 30 in this example there are
zero intact groups, so an intact-only accuracy has no denominator. A blind
reader may still recover bits from mixed windows. The counts above describe
the available source groups; measuring actual alignment requires the
reader's saved selections.

### Score the windows selected during blind extraction

The published [chain selections](../results/stress_seed0_chain_selections.json)
contain start indices, first group IDs and lengths recovered from the saved
blind predictions. Each selection is joined to its edit by evaluation receipt
digest. Run:

```bash
python tools/stress_chain_table.py --selections results/stress_seed0_chain_selections.json \
  --reports results/stress_seven_edits_verified.json results/stress_drop20_verified.json
```

| Edit | Selected chain lengths | Selected windows | Intact selected | Correct group ID on intact |
|---|---|---:|---:|---:|
| Drop 10 | 11 | 11 | 2 | 2 |
| Drop 20 | 3 | 3 | 1 | 1 |
| Drop 30 | 2 | 2 | 0 | 0 |
| Drop 45 | 2 | 2 | 0 | 0 |
| Duplicate 30 | 5 | 5 | 1 | 1 |
| Natural insert 30 | 4, 2, 14 | 20 | 14 | 14 |
| Interpolate 30 | 6 | 6 | 0 | 0 |
| Drop 30 + CRF28 | 2 | 2 | 0 | 0 |

Each row covers paper-000 and map seed 0. With natural insertion the blind
reader chose three chains from separate segments. Group numbers may recur
across segments. Fourteen of the twenty selected windows contained four intact
original frames in the correct group; the other six crossed or lay outside an
intact group. With interpolation, the map retained two intact groups somewhere
in the video, but neither was among the six selected windows. An intact-only
accuracy is undefined whenever the intact-selected count is zero.

The [first registered-donor run](../results/stress_natural30_registered_first_case.json)
for paper-000/map0 used the unmarked Hunyuan I2V reference from paper-020.
The 95-frame received clip yielded 512/512 correct bits under the same
pinned reader as the earlier diagnostic. These two measurements share their
source and map seed. Use the registered-donor observation for the new donor
protocol; retain the earlier observation for its original comparison.
The verified execution copy of the donor manifest used CRLF line endings;
the result records both that file digest and the canonical LF digest.

### Run all five edit maps for a video

Replace `--seed 0` with `--all-seeds` and set the output to the attack
directory. The exporter reads the source once, reuses the same donor for
natural insertions, and creates map0 through map4. For example:

```bash
python -m last.stress --video /private/run/marked.mp4 --video-id paper-000 \
  --attack drop20 --all-seeds --output /private/edits/paper-000/drop20
python -m last.stress_evaluate --run /private/run --family hunyuan \
  --model-dir /path/to/Hunyuan-I2V --attacks /private/edits/paper-000 \
  --output /private/scores/paper-000
```

A single-map export and map0 of this batch produced byte-identical received
MP4s for paper-000/drop20. Both use the same 45 retained frames. Each remaining
seed contributes one additional trial for that video. When aggregating natural
insertions, use one donor assignment protocol throughout and the same donor
reference for every map of a given target.

The [five measured deletion maps](../results/stress_drop20_first_case_five_maps.json)
for paper-000 yielded 439, 411, 400, 417 and 451 correct bits out of 512,
respectively. This is 2,118/2,560 correct bits and 0/5 exact messages. Map0
reuses the earlier checked prediction. The source index above selects this
five-map series as the Drop 20 input to the combined eight-edit table.
For [five drop30 maps of paper-000](../results/stress_drop30_first_case_five_maps.json), the primary and stress exporters produced identical MP4s for every seed. Pinned blind-reader counts were 371, 372, 415, 404 and 357 of 512, matching the primary counts on all five. Map0 used its earlier verified pinned prediction. Count it once across protocols.

### Export recovery counts from a private experiment

Run this on the evaluation host using the original run and edit paths. The
reader checkout must point to the Git revision used for extraction. Use
matching roots for the attack and evaluation directories so that each map
has the same relative path in both. The run directory name is its manifest ID.

```bash
python tools/export_stress_counts.py --run /private/runs/paper-000 \
  --attacks /private/edits/paper-000 --evaluation /private/scores/paper-000 \
  --reader-repo /path/to/pinned/LAST --output paper-000-counts.json
python tools/stress_recovery_table.py --reports paper-000-counts.json
```

The exporter checks the committed reader source digest, attack and generation
receipts, received video, saved prediction and private payload before counting
matching bits. The public JSON contains counts and provenance fields. The
secret key, payload, decoded bits and host file paths stay on the evaluation
host. Choose a new output filename for each export.

For a reader distributed as a Git source archive, pass its original tarball
to `--reader-repo`. The exporter reads its embedded commit ID and hashes its
Python sources using the evaluator's ordering. This path was checked against
the registered natural-insertion recording for paper-000/map0. Inserting
30 frames from paper-020 yielded 95 received frames and 512/512 correct bits.
This recount refers to the existing trial.

### Run the primary manifest as a Linux batch

After primary generation and paired quality evaluation, point `--runs` to one
family/mode/LAST directory containing the 400 sample directories. Install the
reader from the same Git revision passed via `--reader-repo`. Keep the output
on private storage with space for 40 received MP4s per sample.

```bash
python tools/run_stress_campaign.py --family hunyuan --mode i2v \
  --runs /private/primary/hunyuan/i2v/last --model-dir /models/Hunyuan-I2V \
  --reader-repo . --output /private/stress/hunyuan/i2v
python tools/stress_recovery_table.py --reports /private/stress/hunyuan/i2v/paper-*/counts.json
```

The worker generates eight edits at five seeds per sample. It verifies the
registered unmarked donor for natural insertion, extracts from each received
MP4 and writes per-video public counts. Rerun the same command after an
interruption. Completed attack directories are reused and evaluation receipts
are checked before cached counts are accepted. For parallel workers, pass a
common `--shards N` and a different `--shard` from 0 to N−1 on each worker.
The manifest order determines shard membership. Use separate output roots for
different pipelines and revisions.

The batch also records the route taken by the blind reader. For CCTA, the
exporter compares its selected windows with the actual frame map after
extraction and records chain lengths, intact selected windows, and correct
group identities. For other routes, the JSON records the route and group
count with null chain diagnostics. To add these fields to an existing run,
use `tools/export_stress_counts.py --alignment` with the same inputs and a new
output file. For example, on paper-008/drop10/map0 the reader recovered
481/512 bits; the selected chain contained nine windows, of which two
contained an intact original group and both had the correct group ID.

The [paper-008 per-map results](../results/stress_paper008_forty_maps.json)
cover one Hunyuan I2V video, all eight edits and seeds 0–4 on reader
`1df83c5`. Recompute its eight rows separately from the earlier reader:

```bash
python tools/stress_recovery_table.py --reports results/stress_paper008_forty_maps.json
```

All five natural-insertion trials recovered the entire message. Across the
other seven edits, none of the 35 trials recovered all 512 bits. These
observations share a single generated video.

### Recount the eight edits on primary videos

The 20-video snapshot (IDs 000–019) covers the five Camera Motion prompts,
each with four generation seeds. The five edit maps on each video give 100
trials per attack. Natural insertion recovered the complete message in 100/100
trials; deleting 10 frames recovered it in 7/100, and deleting 30 frames in
0/100. These observations describe one content dimension of the manifest.
To reproduce this snapshot in Bash, run
`python tools/stress_recovery_table.py --reports results/stress_paper0[01][0-9]_forty_maps.json --format markdown`.

For these same 20 videos, compare each Drop 30 trial against its CRF28
re-encode using the same sample ID and edit seed. Correct bits fell from
39,075/51,200 to 33,119/51,200. The re-encode gave fewer correct bits in
99 of the 100 pairs and more in one. Both conditions recovered zero entire
messages. The 100 pairs come from 20 generated videos, with five edits each.

| Condition | Source groups surviving intact | Selected windows | Intact windows selected | Correct group IDs among intact selections |
|---|---:|---:|---:|---:|
| Drop 30 | 128/1,600 | 376 | 40 | 39/40 |
| Drop 30 then CRF28 | 128/1,600 | 412 | 32 | 23/32 |

To rebuild the window counts, pass the same 20 report files to
`tools/stress_deletion_alignment.py --reports`. The true edit map is used
here to score the blind reader’s window choices. The two rows share all 100
deletion maps, so the differences arise after the deletion step.

The first nine Hunyuan I2V LAST videos (primary IDs 000 through 008) each have 40 observations on reader revision `1df83c5`. They cover three prompts. Each attack uses five edit maps per video, giving 45 observations per attack and 360 across the eight attacks. To reproduce this nine-video snapshot in Bash:

```bash
python tools/stress_recovery_table.py --reports results/stress_paper00[0-8]_forty_maps.json --primary results/hunyuan_i2v_primary17.json --alignment
```

For Drop 30, seed zero repeats the primary deletion experiment. Both evaluations used identical received MP4s for all nine IDs and recovered 371, 368, 382, 327, 411, 420, 406, 444 and 330 bits per clip, respectively. The comparison checks the number of correct bits per clip. Identifying the error positions would require the individual predictions.

Random deletion of 10, 20, 30 and 45 frames recovered 21,589, 19,617, 17,456 and 14,071 of 23,040 information bits, respectively. Drop 30 followed by CRF28 compression recovered 14,784 bits. Natural insertion recovered 45/45 entire messages, Drop 10 recovered 2/45 and the other six attacks recovered 0/45 each. The full design has 400 videos and five map seeds, giving 2,000 planned observations per attack.

For later stress samples through primary ID 099, use `--primary results/hunyuan_i2v_last_first100_robustness.json`. This report contains all seven blind reads per video. The comparison selects Drop 30 at map seed zero and verifies the received MP4 fingerprint for each available stress sample.

The median counts selected candidate groups per trial, summed across segments, so repeated identities in separate segments can increase the count. The supplement encodes fallback as length one. The export identifies fallback by the reader route. Trials with no evidence are counted separately and leave the overall median undefined. Group accuracy divides correctly identified intact windows by all selected intact windows. The aggregate is unavailable when a fallback lacks saved window assignments or the denominator is zero.

| Attack | Median selected groups | Fallback trials | Correct ID / selected intact windows |
|---|---:|---:|---:|
| Drop 10 | 10 | 0/45 | 110/123 |
| Drop 20 | 5 | 0/45 | 47/51 |
| Drop 30 | 3 | 0/45 | 14/15 |
| Drop 45 | 2 | 0/45 | 1/1 |
| Duplicate 30 | 4 | 0/45 | 33/34 |
| Natural insert 30 | 17 | 0/45 | 651/651 |
| Interpolate 30 | 5 | 0/45 | 26/26 |
| Drop 30 + CRF28 | 3 | 0/45 | 9/11 |

To distinguish missing frames from missed groups, run `python tools/stress_deletion_alignment.py --reports results/stress_paper00[0-8]_forty_maps.json` for this nine-video snapshot. The diagnostic reconstructs each deletion map after extraction and counts how many original four-frame groups survived. It compares this count with the windows in the saved CCTA chains. Across 45 drop30 trials on nine videos, 53 of 720 original four-frame groups survived intact. Nine trials had no intact group and two retained an adjacent pair. Of 156 selected windows, 15 were intact and 14 had the correct group ID. The same deletion maps followed by CRF28 compression left the same 53 intact groups; 11 of 169 selected windows were intact and nine had the correct ID. With 45 frames deleted, 40 of 45 trials retained no intact group. Survival totals include every trial; selection counts describe only the CCTA route. Feature selection and message decoding can also be affected by partial groups.
When primary generation is still in progress, add `--ready-only` to the stress campaign command. It handles cases whose primary target and assigned unmarked donor both have completed campaign receipts. Missing or running dependencies are listed by sample ID; failed primary jobs raise an error. Rerun the same command as more inputs arrive. This option requires primary campaign receipts and retains the 400-video denominator. The default invocation expects finished inputs.

### Effect of compression after deletion on the first ten videos

Each of the ten videos (IDs 000–009) uses the same five deletion maps for both comparisons. Across the 50 trials, 62 of 800 original four-frame groups survived deletion intact. With deletion alone, 18 of the 180 windows selected by CCTA were intact and 17 of these had the correct group ID. After CRF28 compression of the same edits, 13 of 191 selected windows were intact and 11 had the correct ID. The number of correct information bits fell from 19,326 to 16,424 out of 25,600. Both conditions recovered zero complete messages. Compression changes the reader's evidence even when exactly the same original frames survive. These totals do not isolate its effects on window selection and bit decoding.

```bash
files=(results/stress_paper00[0-9]_forty_maps.json)
python tools/stress_recovery_table.py --reports "${files[@]}" --alignment
python tools/stress_deletion_alignment.py --reports "${files[@]}"
```

The first 28 Hunyuan I2V videos cover 140 trials per edit (five maps per video). Random deletion of 10, 20, 30 and 45 frames yielded 95.13%, 87.62%, 78.86% and 63.64% bit accuracy, with 30, 8, 2 and 0 complete messages out of 140. Deletion of 30 frames followed by CRF 28 yielded 67.52% and 0/140 complete messages. The five maps share one generated video within each sample.

For the 28 seed-zero deletion trials shared with the main benchmark, all received MP4 hashes and individual correct-bit counts matched. Both reads recovered 11,243/14,336 bits. These trials are already included in the primary results. Across all 140 deletion maps, 167 of 2,240 original groups remained intact, with 29 trials retaining none. Before CRF 28 the blind reader selected 559 windows, including 52 intact windows and 51 correct group identities among them. On the same maps after compression, it selected 599 windows, including 45 intact windows and 35 correct identities. These counts are rebuilt in the Table 15 CI artifacts from the per-map records.

### Compression after the same 30-frame deletion

For paper-000 through paper-027, each of the five deletion maps was encoded at
both CRF18 and CRF28. A comparison of the 140 paired attack receipts verified
the same source fingerprint, retained frame indices, 35-frame output length
and encoder arguments apart from CRF and destination path. Each received MP4
also matched its audited extraction fingerprint. The reader recovered
56,530/71,680 bits at CRF18 and 48,395/71,680 at CRF28. Recovery decreased in
139 pairs and increased in one. These are repeated edits of 28 videos.
To verify the pairing on regenerated inputs, compare the matching
`edits/drop30/mapN/attack.json` and `edits/drop30_crf28/mapN/attack.json`
for each source video before comparing the extraction counts.

For paper-028, all five natural-insertion MP4s were regenerated from the marked source and the assigned paper-048 unmarked reference using the recorded H.264 encoder. Each contained 95 frames and matched the file fingerprint in the corresponding recovery observation. For seed 0 the first seven marked frames are followed by donor frames 32 through 61 (one-based), then the remaining 58 marked frames. The [five rebuilt input fingerprints](../results/stress_natural028_rebuilt5.json) can be matched by seed to the [forty recovery observations](../results/stress_paper028_forty_maps.json).

For the 33-video prefix through paper-032, all 165 deletion-map pairs shared the source digest and the same 35 retained frame indices. All 330 received MP4s matched their acquisition digests. At CRF28 the reader recovered fewer bits on 163 maps, the same number on one and more on one. Averaging the five map differences within each video, all 33 videos lost correct bits. The median per-video loss was 50.2 of 512 bits, with a range of 28.8 to 115.4 bits. Use the video as the independent unit.

For the first 30 videos, 31 of 150 random 30-frame deletion trials left no intact source group. These trials recovered 12,110/15,872 bits and zero full messages. The 119 trials with at least one intact source group recovered 48,608/60,928 bits and three full messages. The subsets are defined by the frozen edit maps before considering decoder predictions. The same video can occur in both subsets. The Table 15 deletion diagnostic reports the underlying counts under recovery_by_intact_group_availability.

### First 60 videos across eight temporal edits

For Hunyuan I2V LAST, the frozen prefix from paper-000 through paper-059 covers
60 source videos, five edit maps per video and eight attacks. Rebuild these
2,400 observations with the command below (Bash, from the repository root):

```bash
python tools/stress_recovery_table.py --reports results/stress_paper0[0-5][0-9]_forty_maps.json --format markdown
```

<!-- stress-first60-start -->
| Attack | Trials (observed/planned) | Observed bit accuracy | Exact messages (observed) | Full-cohort message recovery | 95% interval | Map-seed range |
|---|---:|---:|---:|---:|---:|---:|
| drop10 | 300/2000 | 95.20% | 79/300 | — | — | — |
| drop20 | 300/2000 | 87.16% | 9/300 | — | — | — |
| drop30 | 300/2000 | 78.73% | 3/300 | — | — | — |
| drop45 | 300/2000 | 63.40% | 0/300 | — | — | — |
| duplicate30 | 300/2000 | 89.95% | 14/300 | — | — | — |
| natural30 | 300/2000 | 100.00% | 300/300 | — | — | — |
| interpolate30 | 300/2000 | 89.11% | 13/300 | — | — | — |
| drop30_crf28 | 300/2000 | 66.70% | 0/300 | — | — | — |
<!-- stress-first60-end -->

Each row scores 153,600 payload bits. All 300 natural-insertion trials
recovered the complete message under this donor-block protocol. Deleting
30 source frames and adding compression reduced accuracy by 12.03 percentage
points relative to the same deletion condition alone. Five maps share each
source video. The full protocol targets 400 source videos.

The 300 drop30 trials include 64 edits also measured by the primary reader.
For seed zero, each of the 60 received MP4s matched the primary file by
SHA-256, and every per-video correct-bit count agreed (24,090/30,720 bits).
For seeds 1–4 the primary archive also had the four paper-000 edits; those
hashes and counts matched as well. Across the 64 shared trials the reader
recovered 25,638/32,768 bits and one complete message. The other 236 trials
contributed 95,298/120,832 bits and two complete messages. Count each shared
edit once when combining these sources. The hash check establishes identical
received videos; the primary summaries record correct-bit counts only.

To inspect the 60 seed-zero comparisons on CPU, add
`--primary results/hunyuan_i2v_last_first100_robustness.json` to the
60-video command above and omit `--format markdown`. The JSON field
`primary_seed_zero_comparison` contains both counts for each received MP4.
