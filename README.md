# LAST

Training-free, inversion-free video watermarking with endpoint latent-frequency margin coding (ELMC) and cross-group consistency temporal alignment (CCTA).

## Reproduction status

This repository is being constructed from a frozen manuscript protocol. Full-paper experiments have **not** been reproduced yet. Historical pilot results are not full-benchmark results, and manuscript values are not used as measured outputs.

The reproduction targets 512 information bits, two video backbones (HunyuanVideo and Wan-2.2 A14B), both T2V and I2V, matched baselines, spatial/temporal attacks, quality evaluation and ablations. Runs record model revisions, software versions, seed schedules, codec settings, raw counts, failures and hardware differences.

Generation is currently being prepared on an NVIDIA L40; the manuscript specifies A800 generation. This hardware difference will be recorded. Timing runs use an idle L40.

Secret keys, private messages, credentials and model weights are not committed.

Code, configuration, tests and exact reproduction commands will be added as they are validated. Do not interpret this initial repository as a completed or independently validated reproduction.
