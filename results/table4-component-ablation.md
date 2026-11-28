# Component ablation on matched Hunyuan image-to-video samples

Values are information-bit accuracies. The w/o MM variant replaces the minimum-margin write with fixed targets. The three reader ablations remove cross-group consistency (CGC), sliding-window search (SWS), or the entire temporal alignment module (CCTA), respectively.

Matched 14/30 videos. Included: paper-003, paper-032, paper-033, paper-043, paper-063, paper-071, paper-098, paper-112, paper-146, paper-149, paper-160, paper-174, paper-270, paper-291
Reader observations available, writer pair missing: []
No writer pair or reader observations supplied: ["paper-351", "paper-254", "paper-232", "paper-308", "paper-377", "paper-391", "paper-337", "paper-182", "paper-201", "paper-282", "paper-269", "paper-340", "paper-258", "paper-235", "paper-306", "paper-364"]
Unmatched full baseline by condition: {}
| Variant | clean | noise | compression | blur | drop | insert | clip |
|---|---:|---:|---:|---:|---:|---:|---:|
| LAST | 1.000 | 0.968 | 0.942 | 0.993 | 0.724 | 0.794 | 0.951 |
| w/o MM | 1.000 | 0.966 | 0.932 | 0.989 | 0.701 | 0.795 | 0.948 |
| w/o CGC | 0.479 | 0.485 | 0.496 | 0.482 | 0.494 | 0.499 | 0.495 |
| w/o SWS | 0.964 | 0.873 | 0.824 | 0.893 | 0.655 | 0.720 | 0.854 |
| w/o CCTA | 1.000 | 0.968 | 0.940 | 0.993 | 0.527 | 0.540 | 0.673 |

Correct information bits out of 7,168 per cell.

| Variant | clean | noise | compression | blur | drop | insert | clip |
|---|---:|---:|---:|---:|---:|---:|---:|
| LAST | 7168 | 6939 | 6754 | 7118 | 5188 | 5693 | 6819 |
| w/o MM | 7168 | 6923 | 6683 | 7089 | 5024 | 5696 | 6793 |
| w/o CGC | 3437 | 3478 | 3556 | 3455 | 3540 | 3576 | 3548 |
| w/o SWS | 6909 | 6255 | 5906 | 6401 | 4696 | 5164 | 6122 |
| w/o CCTA | 7168 | 6942 | 6740 | 7117 | 3781 | 3872 | 4821 |

| Writer | Mean PSNR (dB) | Mean SSIM |
|---|---:|---:|
| minimum-margin | 33.796 | 0.95116 |
| fixed-target | 33.117 | 0.94864 |
