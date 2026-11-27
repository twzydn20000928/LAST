# Component ablation on matched Hunyuan image-to-video samples

Values are information-bit accuracies. The w/o MM variant replaces the minimum-margin write with fixed targets. The three reader ablations remove cross-group consistency (CGC), sliding-window search (SWS), or the entire temporal alignment module (CCTA), respectively.

Matched 13/30 videos. Included: paper-003, paper-032, paper-033, paper-043, paper-063, paper-071, paper-098, paper-112, paper-146, paper-149, paper-160, paper-174, paper-291
Reader observations available, writer pair missing: []
No writer pair or reader observations supplied: ["paper-351", "paper-254", "paper-232", "paper-308", "paper-377", "paper-391", "paper-337", "paper-182", "paper-201", "paper-282", "paper-269", "paper-340", "paper-258", "paper-235", "paper-306", "paper-364"]
Unmatched full baseline by condition: {"paper-270": ["clean", "noise", "compression", "blur", "drop", "insert", "clip"]}
| Variant | clean | noise | compression | blur | drop | insert | clip |
|---|---:|---:|---:|---:|---:|---:|---:|
| LAST | 1.000 | 0.969 | 0.947 | 0.995 | 0.720 | 0.797 | 0.958 |
| w/o MM | 1.000 | 0.967 | 0.936 | 0.991 | 0.695 | 0.798 | 0.952 |
| w/o CGC | 0.480 | 0.485 | 0.495 | 0.480 | 0.494 | 0.498 | 0.492 |
| w/o SWS | 0.964 | 0.876 | 0.830 | 0.894 | 0.648 | 0.721 | 0.858 |
| w/o CCTA | 1.000 | 0.970 | 0.945 | 0.995 | 0.526 | 0.540 | 0.660 |

Correct information bits out of 6,656 per cell.

| Variant | clean | noise | compression | blur | drop | insert | clip |
|---|---:|---:|---:|---:|---:|---:|---:|
| LAST | 6656 | 6452 | 6300 | 6621 | 4794 | 5302 | 6375 |
| w/o MM | 6656 | 6437 | 6232 | 6593 | 4624 | 5309 | 6337 |
| w/o CGC | 3192 | 3227 | 3297 | 3196 | 3291 | 3318 | 3278 |
| w/o SWS | 6414 | 5828 | 5525 | 5949 | 4316 | 4799 | 5714 |
| w/o CCTA | 6656 | 6457 | 6293 | 6620 | 3499 | 3594 | 4392 |

| Writer | Mean PSNR (dB) | Mean SSIM |
|---|---:|---:|
| minimum-margin | 33.568 | 0.94965 |
| fixed-target | 32.886 | 0.94703 |
