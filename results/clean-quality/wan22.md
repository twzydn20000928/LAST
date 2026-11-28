# Clean recovery and video quality — wan22

| Method | Inversion-free | Extraction | T2V bit accuracy | T2V V-score | I2V bit accuracy | I2V V-score |
|---|---|---|---:|---:|---:|---:|
| No-mark | — | — | — | pending (1/18 dimensions) | — | pending (1/18 dimensions) |
| VideoMark | No | Non-blind | pending | pending | pending | pending |
| VideoShield | No | Non-blind | pending | pending | 1.000 (1/400) | pending |
| SIGMark | No | Blind | pending | pending | pending | pending |
| LFG | Yes | Blind | 0.992 (15/400) | pending | 0.987 (15/400) | pending |
| LAST | Yes | Blind | 1.000 (15/400) | pending (1/18 dimensions) | 1.000 (15/400) | pending (1/18 dimensions) |

Bit accuracy is pooled over 512 information bits per completed video. Counts below 400 indicate interim observations. V-score requires the full quality report.

### Counts behind the clean bit accuracies

| Mode | Method | Correct information bits | Entire messages recovered |
|---|---|---:|---:|
| I2V | LAST | 7680/7680 | 15/15 |
| I2V | LFG | 7582/7680 | 12/15 |
| I2V | VideoShield | 512/512 | 1/1 |
| T2V | LAST | 7680/7680 | 15/15 |
| T2V | LFG | 7619/7680 | 10/15 |

### Official dimension means

Diversity uses prompt groups as scoring units. Other dimensions use videos.

| Mode | Method | Dimension | Mean | Valid / planned units |
|---|---|---|---:|---:|
| I2V | LAST | Camera_Motion | 0.8000 | 20/20 |
| I2V | No-mark | Camera_Motion | 0.7500 | 20/20 |
| T2V | LAST | Camera_Motion | 0.6000 | 20/20 |
| T2V | No-mark | Camera_Motion | 0.5500 | 20/20 |
