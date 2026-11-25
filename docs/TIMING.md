# Timing protocol and current implementation

The paper excludes model loading, one-time key setup and export. Extraction
includes MP4 decoding and the complete reader. Main Table 3 averages two
synchronized repetitions after warmup. The supplement uses two warmups and
five repeats per clip, reporting each clip's median before aggregating 30 clips.
Use one otherwise idle L40; generation and extraction must not compete with
other experiments. Current concurrent integration runtimes are not table data.

The main table builder checks that all ten extraction receipts report the
same PyTorch and CUDA build versions. New paired generation receipts record
both versions as well. For older generation receipts that omit both fields,
verify the generation environment from the run log before interpreting the
generation and extraction times together.

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

For the supplement's LAST length study, supply one clean MP4 of the
specified length to each invocation. Use `--protocol supplement` with
`--length-study-frames 65`, `129`, or `257` respectively. The runner checks the
decoded frame count and times five complete extractions after two warmups.
For LAST, the timing receipt also records `candidate_windows`, the number of
windows actually encoded by the final read. The reader scans each optical-flow
segment separately, so this count can vary between clips of the same duration.
Report the median of the five seconds values per clip. Divide
`peak_allocated_bytes` by 2³⁰ for GiB. PyTorch resets the allocation high-water
mark after warmup and before the first measured read, so resident model memory
is included. Keep the MP4 generation provenance with the timing receipt.
The manuscript leaves construction of the longer inputs unspecified; only
the 65-frame generation configuration is defined in the standard campaign.

Section I of the supplement reports 18.9, 38.4 and 78.2 seconds at 65,
129 and 257 frames, with peak allocated memory of 5.2, 5.3 and 5.4 GiB
under sequential window batching. These are manuscript reference values.
The supplied manuscript gives neither input file fingerprints nor a recipe
for producing the 129- and 257-frame inputs. When reporting a reconstruction,
identify the source and construction of each MP4 alongside its measured
window count so a timing difference can be interpreted against the actual
amount of extraction work.

For a controlled duration diagnostic, the following command uses a completed
65-frame LAST clip. It traverses its frames forward and backward without
duplicating the turnaround frame and encodes all three lengths at CRF18,
8 fps. The manifest records source indices and MP4 fingerprints. This
reconstruction measures the reader's work on repeated content. Native
long-video generation and temporal robustness require separate experiments.

```bash
python tools/prepare_length_inputs.py --run /private/primary/hunyuan/i2v/last/paper-000 \
  --output /private/length-study-inputs
```

After collecting all three receipts with the same model, GPU, runtime and source
revision, print the length table from the repository root:

```bash
python tools/length_timing_table.py timing/65.json timing/129.json timing/257.json
```

For the constructed inputs, append `--inputs /private/length-study-inputs/inputs.json`
to check that each timed read used the corresponding encoded MP4.
On the Hunyuan I2V `paper-000` reconstruction each input produced one optical-flow
segment. The reader proposed 62, 126 and 254 four-frame windows, respectively,
with no boundary padding. These are CPU-verified workload counts.

The above entry point covers only LAST/LFG extraction. Native extraction,
paired generation, direct CUDA-event embedding and a randomized 30-video schedule
have entry points described below, but real timing and parity validation remain
pending. For native Wan timing, pass `--family wan22` and the corresponding
I2V or T2V checkpoint to `last.baseline_timing`. Timing and extraction share
the same inversion pipeline loader, scheduler shift, Wan latent normalization
and image-input conversion. The Hunyuan default uses shift 7 and Wan uses
shift 5. Real exclusive-GPU Wan timing and length-scaling measurements remain pending.
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
Real exclusive-GPU execution and parity with ordinary extraction remain pending.

### Main Table 3

Run `python tools/main_timing_table.py --index /private/timing-index.json --output table3`
after acquiring all five methods on the same case and L40. The index has a
`video_id` and a `methods` object with keys `sigmark`, `videoshield`, `videomark`,
`lfg`, and `last`. Each method maps `case`, `generation`, `clean`, `drop`,
`clean_attack`, and `drop_attack` to JSON paths relative to the index. Supply the
case file, paired generation timing, two extraction timings, and corresponding
evaluation receipts, respectively. Use a private output directory when index
paths contain local identifiers. The Markdown table contains only method names
and measured seconds. Generation uses the mean marked duration. Overhead uses
the mean of the two within-pair differences and retains negative observations.
Clean and deletion columns each use the mean of two synchronized reads.

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
All five methods share the same decode and offload path within each backbone.
For a paired Wan run, choose `--family wan22` and its matching mode-specific
checkpoint. Both branches use the Wan UniPC flow scheduler and the same
per-channel VAE denormalization as native video generation. Native dependency setup and complete
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

For the native methods, index the clean-video run with temporal recovery off
and the 30-frame deletion run with temporal recovery on. The summary checks the
index condition against the recorded switch. Keep LAST length-study receipts
in the length experiment even when the input length happens to be 65 frames.

For the generation and overhead columns of supplement Table 17, pass
`--generation` to `last.timing_summary` with an index listing `video_id`, `case`,
and paired generation timing `receipt` for each measured clip. Paths resolve
relative to the index. Each clip contributes its median of five marked
durations and its median of five within-pair differences. Across 30 clips,
generation is summarized by median and quartiles. The overhead interval uses
10,000 video-level bootstrap samples with PCG64 seed 0. The summary checks
that 15 videos used each pair order. Missing cases retain null aggregate
values; pass completed receipts and retain any failed attempts separately.

For a paper measurement, include the corresponding `attack_receipt` path in
each index entry and run the summary with `--verify-attack-receipts`. The
summary checks the timed MP4 fingerprint against the completed evaluation
receipt for that sample, method, condition and default attack seed. It records
both receipt fingerprints. This catches a deletion timing accidentally indexed
as clean even when the timing JSON itself has no condition label. Older index
files remain usable for summaries with unverified sample and condition labels.

For SIGMark, VideoShield and VideoMark, the main-table formatter and verified
supplement summary also require the timing and attack receipts to identify
the same native state file by SHA256. This checks which registered state was
loaded when reading the clip. Both commands perform the comparison from the
two receipts; the state file stays in the private run directory.

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

### Interpreting the earlier single-clip pilot

The earlier five-method Hunyuan I2V pilot timed one generation per method after
a two-step warmup. The unmarked branch ran separately. Each clean and deletion
extraction had one warmup and two measured reads. The LAST/LFG pilot reader
loaded the VAE in bfloat16. Main Table 3 uses paired generation measurements,
and the current LAST/LFG reader uses float32. Keep pilot durations separate
when rebuilding the main table. The primary timing formatter checks that all
eight generation calls (reference and marked in four pairs) decoded 65 frames.
For supplementary Table 17 the verified extraction summary requires the L40 and checks the actual decoded length against the clean or deletion record. Native readers record the received length for each warmup and timed read. A paired generation receipt must record fourteen decoded lengths of 65 frames (two arms for each of seven pairs).
