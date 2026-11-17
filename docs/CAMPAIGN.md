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

## Frozen release used for the LFG branch

Hunyuan I2V LFG entered the primary queue only after a fresh generated MP4,
all seven attacks and paired fidelity completed. Its source is frozen at public
commit `b4f9eeadb912b2850eef7d381b14b341c669dd89`; the downloaded archive passed
42 tests and strict runtime-version checks. The earlier LAST branch remains on
its original frozen release. This is versioned integration, not a claim that
the whole primary comparison has completed.

For an additional method on an updated release, create a **new plan** and use
only that method filter. Existing results from another release must not be
overwritten or resumed against the new plan. The project uses disjoint method
subdirectories under a shared artifact root; every job records its own immutable
plan hash. Both branches retain the same primary manifest and private state.
The source change fixes LFG's final-step latent interface and adds runners; it
does not select LFG parameters using primary outcomes. Do not pool jobs without
checking their recorded protocol and plan provenance.

```bash
python -m last.report --plan /private/primary-plan.json --root /private/primary-runs --output /path/to/tables --verify-artifacts
```

This reports all planned runs, including pending ones. It never turns a filtered
or partial execution into a full400sample result.
Artifact verification checks completed generation identity, the marked-video hash
bound to each attack receipt, and presence of each attack MP4. The report records
current receipt/video hashes and the plan hash. This is provenance checking, not
a rerun of the decoder or proof of equivalence to manuscript results.
