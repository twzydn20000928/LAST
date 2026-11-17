# Prompt-cluster uncertainty

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
