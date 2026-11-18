# Rebuild measured robustness tables

First run `last.report --verify-artifacts` against the frozen experiment plan and
actual run directory. If historical reader results were independently replayed,
supply the audited `--reextraction-index` described in `REEXTRACTION.md`.
That audit produces `summary.json`, raw-count CSV and a long-form Markdown table.

To format audited reports into a Table2-style layout with attacks as columns:

```bash
python -m last.robustness_table --reports \
  results/last_hunyuan_i2v_audited_partial.json \
  results/last_hunyuan_t2v_audited_partial.json \
  results/last_wan_i2v_audited_partial.json \
  --output /path/to/new-table-output
```

This example uses checked-in partial snapshots, not live server state. It has
actually rendered15 Hunyuan I2V,2 Hunyuan T2V and2 Wan I2V cases from their existing
audits. It does not compare those different pipelines as paired methods. For the
final paper table, supply newly audited complete reports covering every required
method and pipeline; the present example does not satisfy that requirement.

`table.md` shows correct-information-bit percentages and completed/planned video
counts. `counts.csv` retains correct bits, total bits, exact-message counts and
separate observed/final accuracy columns. `receipt.json` binds the source reports
and formatter revision by SHA256. Partial cells keep null final scores; missing
data is not zero accuracy. Overlapping snapshots are rejected rather than added
together. Each pipeline must include all seven condition cells and one planned
denominator, even when none of its videos has completed.

The formatter recomputes percentages from integer counts. It does not rerun GPU
extraction, replace the artifact audit, establish comparable protocols, compute
statistical uncertainty or select a winner. Three CPU tests cover count-derived
percentages, missing conditions, unaudited inputs, overlap, impossible recovery
counts and rejection of final scores on partial results. Quality, efficiency,
uncertainty and supplementary tables remain separate workflows.

The `core-tests` GitHub Actions workflow also executes the command above in its
core CPU job and uploads `audited-partial-robustness-tables`. Download that
artifact from a successful workflow run to obtain the Markdown table, CSV counts
and input/source receipt for that exact public revision. This checks that the
published snapshots can be rendered by the released formatter; it does not
repeat the private video audit or turn incomplete snapshots into final results.
