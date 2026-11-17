# Resumable primary LAST/LFG comparison

Prepare the verified dataset and private state following DATA.md. Create a local
JSON model-path mapping with keys `hunyuan_i2v`, `hunyuan_t2v`, `wan22_i2v`,
`wan22_t2v`, each pointing to its pinned downloaded checkpoint directory.

```bash
python -m last.campaign plan --manifest configs/primary_manifest.json --output /private/primary-plan.json
python -m last.campaign run --plan /private/primary-plan.json \
  --manifest configs/primary_manifest.json --root /private/primary-runs \
  --state /private/primary-state --image-root /path/to/images \
  --models /private/model-paths.json --family hunyuan --mode i2v \
  --method last --max-jobs 1 --memory-gib 12 --offload sequential
```

The first command freezes3200marked-video jobs:400samples×2backbones×2modes×2methods,
with22400attack observations. This is the LAST/LFG portion only; it does not claim
that SIGMark, VideoShield, VideoMark, VBench or supplementary experiments are done.
Start with one job to validate your installation, then omit filters/job limit for
the full portion. Integrations are still being verified on the project server.

The worker runs the public generation adapter, MP4 attack evaluation and paired
fidelity command; its campaign receipt contextualizes each generation-adapter
receipt as a planned primary observation. Per-job Linux flock prevents duplicate
work. Use disjoint `--shards N --shard K` workers when resources allow. Memory
headroom checks are advisory, not atomic GPU reservations: use external resource
scheduling when multiple independent users share a GPU. A waiting-memory worker
returns and can be invoked again; it does not kill other jobs. A failed job stops
the worker with its receipt preserved. Inspect and fix it before resuming.

Completed jobs are skipped, and failed stages retain their logs. Do not modify
code/configuration midway through a formal campaign without a new campaign root
and an explicit reuse audit. Timing is a separate exclusive-GPU experiment;
these throughput workers generate both reference and marked outputs for fidelity.

```bash
python -m last.report --plan /private/primary-plan.json --root /private/primary-runs --output /path/to/tables
```

This reports all planned runs, including pending ones. It never turns a filtered
or partial execution into a full400sample result.
