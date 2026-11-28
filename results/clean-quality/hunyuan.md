# Clean recovery and video quality — hunyuan

| Method | Inversion-free | Extraction | T2V bit accuracy | T2V V-score | I2V bit accuracy | I2V V-score |
|---|---|---|---:|---:|---:|---:|
| No-mark | — | — | — | pending (1/18 dimensions) | — | pending (6/18 dimensions) |
| VideoMark | No | Non-blind | 0.713 (40/400) | pending (2/18 dimensions) | pending | pending |
| VideoShield | No | Non-blind | pending | pending | 1.000 (3/400) | pending |
| SIGMark | No | Blind | pending | pending | 0.708 (2/400) | pending |
| LFG | Yes | Blind | 0.967 (15/400) | pending | 0.970 (41/400) | pending (1/18 dimensions) |
| LAST | Yes | Blind | 1.000 (15/400) | pending (1/18 dimensions) | 1.000 (41/400) | pending (6/18 dimensions) |

Bit accuracy is pooled over 512 information bits per completed video. Counts below 400 indicate interim observations. V-score requires the full quality report.

### Counts behind the clean bit accuracies

| Mode | Method | Correct information bits | Entire messages recovered |
|---|---|---:|---:|
| I2V | LAST | 20992/20992 | 41/41 |
| I2V | LFG | 20365/20992 | 21/41 |
| I2V | SIGMark | 725/1024 | 0/2 |
| I2V | VideoShield | 1536/1536 | 3/3 |
| T2V | LAST | 7680/7680 | 15/15 |
| T2V | LFG | 7425/7680 | 3/15 |
| T2V | VideoMark | 14592/20480 | 17/40 |

### Official dimension means

Diversity uses prompt groups as scoring units. Other dimensions use videos.

| Mode | Method | Dimension | Mean | Valid / planned units |
|---|---|---|---:|---:|
| I2V | LAST | Camera_Motion | 0.2500 | 20/20 |
| I2V | LAST | Complex_Landscape | 0.1300 | 20/20 |
| I2V | LAST | Complex_Plot | 0.0800 | 20/20 |
| I2V | LAST | Composition | 0.5500 | 20/20 |
| I2V | LAST | Diversity | 0.2455 | 3/3 |
| I2V | LAST | Dynamic_Spatial_Relationship | 0.2500 | 20/20 |
| I2V | LFG | Camera_Motion | 0.4000 | 20/20 |
| I2V | No-mark | Camera_Motion | 0.3500 | 20/20 |
| I2V | No-mark | Complex_Landscape | 0.1300 | 20/20 |
| I2V | No-mark | Complex_Plot | 0.0700 | 20/20 |
| I2V | No-mark | Composition | 0.5500 | 20/20 |
| I2V | No-mark | Diversity | 0.2549 | 3/3 |
| I2V | No-mark | Dynamic_Spatial_Relationship | 0.2500 | 20/20 |
| T2V | LAST | Camera_Motion | 0.2000 | 20/20 |
| T2V | No-mark | Camera_Motion | 0.1500 | 20/20 |
| T2V | VideoMark | Camera_Motion | 0.2000 | 20/20 |
| T2V | VideoMark | Complex_Landscape | 0.1700 | 20/20 |
