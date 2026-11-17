# Prompt-cluster uncertainty

Before reporting primary tables, run `last.report` with `--verify-artifacts`.
This verifies both the original marked video and the exact received MP4 against
the extraction receipt. Missing received-video hashes or changed files fail the
audit; recomputing a new hash does not validate an old extraction result.
For the clean condition only, the source hash also identifies the received
video because both refer to the same `marked.mp4`.
Legacy receipts without this provenance require a separately documented audit
or re-extraction before inclusion in verified tables.

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

## Message outcomes and error distribution

```bash
python -m last.message_outcomes --manifest configs/primary_manifest.json \
  --root /path/to/primary --family hunyuan --mode i2v --method last \
  --output /path/to/message-outcomes.json
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
