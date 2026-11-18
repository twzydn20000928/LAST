# Auditing historical readouts

Some early attack receipts lack a fingerprint of the received MP4. They cannot
pass `last.report --verify-artifacts` unchanged. Do not insert a current hash
into an old receipt and describe it as contemporaneous evidence. Keep the old
files and independently extract each actual video with the public reader:

```bash
python -m last.reextract --run /private/run --model-dir /models/hunyuan \
  --output /private/new-independent-readout
```

Use an unused output directory. The reader subprocess receives the video, key
and model, not the true message or attack map. The evaluator loads truth only
after that subprocess exits. Keep its private decoded outputs on the server;
they contain messages and are required for a later audit, not for publication.

To incorporate completed independent evidence into a report, explicitly list
each planned run in a private JSON array:

```json
[
  {
    "run": "hunyuan/i2v/last/paper-001",
    "output": "/private/new-independent-readout",
    "source": "/checkouts/exact-reader-revision"
  }
]
```

Then use the original full experiment plan:

```bash
python -m last.report --plan /private/primary-plan.json --root /private/primary \
  --verify-artifacts --reextraction-index /private/reextractions.json \
  --output /private/new-verified-summary
```

The `source` directory must contain the exact `src/last/*.py` files fingerprinted
by the independent readout. The report verifies those files, generation receipt,
original attack receipt, current MP4 and private prediction; it then recomputes
correct-bit counts against the private truth. New counts are used even when they
differ from old counts, with the old counts and comparison retained in the audit.
Original receipts are never modified. Duplicate or unplanned index entries,
incomplete readouts, and changed artifacts are rejected. Other planned runs still
require their normal evidence; this option does not waive verification or remove
missing samples from the denominator.

Four historical Hunyuan I2V LAST videos have passed this path:28 actual conditions
were audited, with all correct-bit counts matching the earlier records. See
`results/legacy_reextract_four_verified.json`. This is integration evidence, not
the complete400-video benchmark, a timing comparison, or a claim that separately
generated videos are pixel-identical.

The [audited partial primary snapshot](../results/last_hunyuan_i2v_audited_partial.json)
now covers15 Hunyuan I2V LAST videos and105 conditions. It includes56 independent
re-extractions across eight historical videos. The first used public reader
`cb3a908471bc1f1a8b21767ef21972fcdd7a5cf8`; the next seven used
`1d331462fff777cd825e23f630b8ce3aa18b23fa`. Each was checked against its actual
source archive, not attributed to a single revision. An initially incorrect
source mapping was rejected by the auditor and corrected without modifying
original measurements.

All seven cells retain400 planned videos,15 observed and385 missing; final
scores remain null. Observed bit accuracies are clean100%, noise98.22%,
compression96.58%, blur99.58%, deletion73.11%, insertion85.74%, and clipping98.39%.
These are partial observations, not manuscript reproduction or evidence of
superiority over another method. The snapshot records exact-message counts
separately; high bit accuracy does not imply successful full-message recovery.
