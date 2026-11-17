# Timing protocol and current implementation

The paper excludes model loading, one-time key setup and export. Extraction
includes MP4 decoding and the complete reader. Main Table 3 averages two
synchronized repetitions after warmup. The supplement uses two warmups and
five repeats per clip, reporting each clip's median before aggregating 30 clips.
Use one otherwise idle L40; generation and extraction must not compete with
other experiments. Current concurrent integration runtimes are not table data.

For LAST or native-carrier LFG extraction on an already exported video:

```bash
python -m last.reader_timing --method last --family hunyuan \
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

This entry point covers only LAST/LFG extraction. Native baseline extraction,
paired generation in randomized AB/BA order, direct CUDA-event embedding
timing, the randomized 30-video/method schedule and length-scaling experiments
remain to be implemented/validated. Do not present this partial entry point
as the complete five-method Table 3 or supplementary Table 17 reproduction.
