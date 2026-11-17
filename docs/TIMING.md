# Timing protocol and current implementation

The paper excludes model loading, one-time key setup and export. Extraction
includes MP4 decoding and the complete reader. Main Table 3 averages two
synchronized repetitions after warmup. The supplement uses two warmups and
five repeats per clip, reporting each clip's median before aggregating 30 clips.
Use one otherwise idle L40; generation and extraction must not compete with
other experiments. Current concurrent integration runtimes are not table data.

For LAST or native-carrier LFG extraction on an already exported video:

```bash
python -m last.reader_timing --method last --family hunyuan --mode i2v \
  --video /path/to/marked.mp4 --key /path/to/secret.key \
  --model-dir /path/to/model --protocol main --output /path/to/new-timing.json
```

Run the same command on the shared 30-frame deletion condition. Use
`--protocol supplement` for five repetitions. Both modes use two warmups;
this makes the unspecified main-paper warmup count explicit. VAE is float32
on GPU with tiling in both methods. Model loading and codebook preparation
are outside timing, while MP4 decoding, alignment and BCH are inside it.
The LFG carrier matrices are prepared and resident on GPU before warmup;
this explicitly excludes one-time secret-carrier setup, without changing their
values or the scoring formula. The ordinary evaluator's default stays unchanged.
GPU synchronization encloses every measured read. Other compute processes
cause rejection; checks are not an operating-system resource reservation, so
reserve the GPU externally and keep other schedulers idle for the full run.

The above entry point covers only LAST/LFG extraction. Native extraction,
paired generation, direct CUDA-event embedding and a randomized 30-video schedule
have entry points described below, but real timing and parity validation remain
pending. Native Wan adapters and length-scaling experiments are also incomplete.
Do not present available commands as the complete five-method Table 3 or
supplementary Table 17 reproduction.

For native Hunyuan SIGMark, VideoShield or VideoMark:

```bash
python -m last.baseline_timing --method sigmark --mode i2v \
  --upstream /path/to/pinned-sigmark --model-dir /path/to/hunyuan-i2v \
  --video /private/received.mp4 --state /private/maintained_private.pkl \
  --protocol supplement --temporal --output /private/new-native-timing.json
```

Use only your own trusted native pickle state. Omit `--temporal` for the clean
65-frame input. With temporal recovery, SIGMark performs its native SGO inside
every timed read, including all its inversion calls; the other two methods use
their native received-length alignment. The final VAE encoding, 50-step
inversion and native decoder are included. Models/state load once, two warmups
precede two or five synchronized repeats. Sequential CPU offload transfers are
inside timing and explicitly reported. There are no per-step receipt writes.
Seed reset and lightweight repeat diagnostics are included; prediction
consistency across warmups/repeats is reported without exposing message bits.
This is Hunyuan-only and is not a validated Wan baseline timing adapter.
Real exclusive-GPU execution and parity with ordinary extraction remain pending.

Freeze the supplemental acquisition order before collecting any timings:

```bash
python -m last.timing_plan --output /private/timing-acquisition-plan.json
```

This uses the frozen thirty-video subset and all five methods: 300 reader jobs
(clean and deletion conditions) and 150 marked/unmarked generation-pair jobs for
one backbone/mode. Each method has fifteen reference-first and fifteen
marked-first pairs; pair members remain adjacent. NumPy PCG64 seed20261118 is
an explicit reconstruction choice, not a seed specified in the manuscript.
The plan contains no measured times and does not launch or reserve the GPU.
Keep failed attempts in their scheduled slots; do not reorder by observed
latency. The implemented timing runners and their generation/decode boundaries
still need real GPU validation before this plan can constitute a complete
efficiency experiment.

Each generation-pair job specifies two warmup pairs and five measured pairs;
each branch therefore gets two warmups and five measurements. It is not a
single sampling call per video/method. Compute each paired overhead from its
matched marked/unmarked measurement before aggregating videos. Schedule schema2
makes these generation repeat counts explicit; earlier schema1 plans did not
specify them and must not be treated as complete acquisition instructions.

`last.paired_timing.measure_pairs` implements the shared acquisition core:
adjacent AB/BA branches, synchronization and exclusive-process checks around
each operation, two excluded warmup pairs and five measured pairs by default.
Overheads are computed within each pair, including negative observed differences;
they are not differences of separately selected medians. Optional receipt writes
occur after the pair, outside the intervals. A branch failure propagates without
automatic retries or a successful partial-pair record. This core is CPU-tested,
and the adapters below still need exclusive-GPU validation for each method.
The core alone is not a generation CLI or measured efficiency result.

The LAST/LFG adapter is now available for both backbone/mode combinations:

```bash
python -m last.generation_timing --family hunyuan --mode i2v --method last \
  --model-dir /path/to/model --case /private/case.json \
  --key /private/secret.key --message /private/message.bin \
  --order AB --protocol supplement --output /private/new-generation-timing
```

Take `--order` from the frozen acquisition plan, not observed speeds. Each
branch independently samples from the same seed; neither branch reuses the
other's endpoint. Models remain loaded and sequential CPU offload is used for
both branches. Scheduler construction/reset, noise preparation, prompt encoding,
sampling, write operation, VAE decoding and PIL frame conversion are inside
timing. Model/carrier setup, conditioning-image file reads and MP4 encoding/export
are outside. ELMC remains after the returned normalized endpoint, not inside a
last-step callback (some pipelines change the latent after that callback).
The LFG marked branch uses its late predicted-clean scheduler guidance.

This adapter's occupied-GPU rejection has been exercised on the active server;
it refused before loading models and retained a failed receipt. Actual exclusive
GPU measurements and numerical parity with ordinary generation are still pending.
Do not pool adapter timings with a different offload/decode policy.

The same generation command also accepts `--method sigmark`, `videoshield` or
`videomark` with `--family hunyuan --upstream /path/to/pinned-sigmark`; omit
`--key` for these methods. Their native constructor prepares PRC keys outside
timing; each marked call performs the native message-to-noise encoding inside
timing. VideoShield's per-video ephemeral key/nonce draws are part of that native
operation and remain included, explicitly distinguished from one-time setup.
The post-constructor NumPy/Torch states are restored for repeated native encoding,
and per-video registration accumulators are cleared to avoid growth across repeats.
Sampling resets its seed after initial-noise construction as in ordinary generation.
All five Hunyuan methods share the same decode/offload path in this entry point.
Native Wan generation timing is rejected. Native dependency setup and complete
GPU output parity still require validation; CLI availability is not a measured
five-method efficiency comparison. VideoMark registration-based extraction is
not exercised by generation timing.

For one method/backbone/condition, aggregate the frozen 30-video subset with:

```bash
python -m last.timing_summary --index /path/to/timing-index.json \
  --output /path/to/new-summary.json
```

The index is a list of objects containing `video_id`, `condition` and `receipt`
(path relative to the index or absolute). Use the saved `reader_timing` receipts.
Missing or failed videos prevent final aggregate scores. Every completed video
must declare its I2V or T2V mode; mixed or unspecified modes are rejected rather
than merged into a misleading efficiency row. Every completed video
must have two warmups and five repeats. The summary takes each video's median,
then reports the across-video median, quartiles and a percentile interval from
10,000 PCG64 seed0 bootstrap draws of videos. These numerical bootstrap choices
are disclosed reconstruction choices. Repeats are never treated as independent
videos. The caller must use the frozen randomized acquisition schedule; this
aggregator cannot establish exclusivity or random ordering from elapsed times.

## Direct embedding operation

Add `--save-endpoint` to a new `last.smoke --method last` run to retain the
normalized pre-embedding latent privately. This changes artifact retention,
not the embedding formula. Existing runs without it cannot reconstruct that
endpoint from an MP4; they must not substitute a VAE re-encoding or random tensor.

On an otherwise idle GPU, run:

```bash
python -m last.embedding_timing --run /private/completed-run-with-endpoint \
  --output /private/new-embedding-timing.json
```

The entry point hashes the saved endpoint, runs two warmups and five CUDA-event
measurements of the actual ELMC call with resident GPU inputs, and reports their
median and quartiles. It includes transforms, allocations and margin operations;
disk reads, input transfers, model generation and decoding are outside the event
interval. The measurement is distinct from paired end-to-end generation overhead.
Keep endpoints, keys and messages private. This entry point still requires an
actual idle-GPU measurement; CPU tests are not timing results.
