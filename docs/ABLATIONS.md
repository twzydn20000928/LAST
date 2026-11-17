# Main-paper ablations and margin sweep

The main-paper protocol uses30I2V samples for ablations and three fixed
development samples for the margin sweep. Freeze these sample IDs, keys and
messages before inspecting results. A one-sample integration check is not the
reported30sample experiment. The full selection manifest is still pending.

For each completed LAST run with all seven attack MP4s:

```bash
python -m last.reader_ablation --run /private/last-run \
  --family hunyuan --model-dir /path/to/Hunyuan-I2V \
  --output /private/ablations/sample-id
```

The four rows are full CCTA, response-energy/spacing without CGC, segment-start
four-frame grid without SWS, and received-order grouping without CCTA. All use
identical attack files. Without CCTA, the first received frame is treated as the
causal prefix, at most64remaining frames are grouped in fours, and a short final
group repeats its last frame. Missing groups remain absent. This deterministic
choice is explicit because the main text does not specify short-tail handling.
There is no source-position oracle. Feature caching is per received video and
does not share features across attacks; these runs are not timing measurements.

For the writer ablation, rerun `last.smoke` with the same case, key and message
and append `--fixed-target`; use a new output directory. Then run `last.evaluate`
with the same video ID (identical deterministic attack maps) and `last.quality`.
This replaces only the minimum-margin projection with fixed signed targets.

For Figure4, independently generate the same three development cases at each
`--mu 0.1`, `0.25`, `0.5`, `0.75`, `1.0`, each in its own directory, followed by
the same evaluation and quality commands. Keep key/message/seed fixed across
strengths. Average bit accuracy over the six attacked conditions, excluding
clean; report paired PSNR and SSIM separately. The causal profile remains
`[0,mu,mu,2*mu,mu,...]`. Do not choose the three examples by the resulting score.

Default main-paper generation is unchanged (`--mu .5`, no `--fixed-target`).
Writer and reader adapters require real-video integration verification; no
manuscript ablation number is imported as a measured result.
