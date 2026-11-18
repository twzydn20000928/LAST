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

Choices are `drop10`, `drop30`, `drop45`, `duplicate30`, `natural30`,
`interpolate30`, and `drop30_crf28`. Map seeds0–4 are fixed before extraction.
Drop30 uses exactly the primary deletion map. Combined editing uses this same
map then CRF28; other exports use CRF18,8fps,yuv420p. Every export is reopened.

Duplicate insertion samples30distinct source frames and copies each immediately
after its source. Natural insertion requires `--donor-reference` pointing to an
unwatermarked same-size clip, selects a contiguous30frame donor portion and
inserts it at a uniformly chosen boundary. Freeze donor assignments before
evaluation and keep them identical across methods; the complete donor assignment
manifest remains pending. Do not use marked donors or choose donors by accuracy.

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

Each immediate subdirectory of `--attacks` contains `attack.json` and
`received.mp4`. Source and received hashes are verified. The evaluator reads
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
