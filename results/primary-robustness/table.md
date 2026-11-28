# Measured robustness: bit accuracy and coverage

Percentages are recomputed from correct information bits. Each cell also shows completed/planned videos.
Coverage differs by method. Partial cells describe the available samples.

I2V uses an input image and prompt. T2V uses a text prompt. Drop removes 30 random frames, insert adds 30 noise frames, and clip removes 30 consecutive frames.

| Family | Mode | Method | clean | noise | compression | blur | drop | insert | clip |
|---|---|---|---|---|---|---|---|---|---|
| hunyuan | i2v | last | 100.00% [partial]; 45/400 | 99.03% [partial]; 45/400 | 97.78% [partial]; 45/400 | 99.77% [partial]; 45/400 | 77.65% [partial]; 45/400 | 86.19% [partial]; 45/400 | 98.53% [partial]; 45/400 |
| hunyuan | i2v | lfg | 97.13% [partial]; 45/400 | 91.94% [partial]; 45/400 | 94.15% [partial]; 45/400 | 94.24% [partial]; 45/400 | 65.10% [partial]; 45/400 | 59.03% [partial]; 45/400 | 77.41% [partial]; 45/400 |
| hunyuan | i2v | sigmark | 70.80% [partial]; 2/400 | 49.22% [partial]; 2/400 | 49.90% [partial]; 2/400 | 57.91% [partial]; 2/400 | 47.07% [partial]; 1/400 (1 failed) | unscored [partial]; 0/400 (2 failed) | 53.12% [partial]; 1/400 |
| hunyuan | i2v | videomark | 48.63% [partial]; 1/400 | 49.02% [partial]; 1/400 | 46.29% [partial]; 1/400 | 49.80% [partial]; 1/400 | pending [partial]; 0/400 | pending [partial]; 0/400 | pending [partial]; 0/400 |
| hunyuan | i2v | videoshield | 100.00% [partial]; 3/400 | 99.74% [partial]; 3/400 | 99.87% [partial]; 3/400 | 100.00% [partial]; 3/400 | 100.00% [partial]; 3/400 | 98.96% [partial]; 3/400 | 99.54% [partial]; 3/400 |
| hunyuan | t2v | last | 100.00% [partial]; 15/400 | 98.93% [partial]; 15/400 | 97.07% [partial]; 15/400 | 99.74% [partial]; 15/400 | 75.82% [partial]; 15/400 | 90.90% [partial]; 15/400 | 97.89% [partial]; 15/400 |
| hunyuan | t2v | lfg | 96.68% [partial]; 15/400 | 90.90% [partial]; 15/400 | 93.53% [partial]; 15/400 | 93.58% [partial]; 15/400 | 64.87% [partial]; 15/400 | 57.62% [partial]; 15/400 | 74.51% [partial]; 15/400 |
| hunyuan | t2v | videomark | 71.25% [partial]; 40/400 | 57.35% [partial]; 40/400 | 56.24% [partial]; 40/400 | 59.90% [partial]; 40/400 | 51.16% [partial]; 40/400 | 55.22% [partial]; 40/400 | 62.37% [partial]; 40/400 |
| wan22 | i2v | last | 100.00% [partial]; 14/400 | 98.02% [partial]; 14/400 | 95.30% [partial]; 14/400 | 98.80% [partial]; 14/400 | 65.62% [partial]; 14/400 | 84.42% [partial]; 14/400 | 94.81% [partial]; 14/400 |
| wan22 | i2v | lfg | 98.94% [partial]; 14/400 | 91.64% [partial]; 14/400 | 95.40% [partial]; 14/400 | 97.53% [partial]; 14/400 | 66.03% [partial]; 14/400 | 56.57% [partial]; 14/400 | 76.88% [partial]; 14/400 |
| wan22 | i2v | videoshield | 100.00% [partial]; 1/400 | 100.00% [partial]; 1/400 | 100.00% [partial]; 1/400 | 100.00% [partial]; 1/400 | 100.00% [partial]; 1/400 | 99.22% [partial]; 1/400 | 100.00% [partial]; 1/400 |
| wan22 | t2v | last | 100.00% [partial]; 14/400 | 98.28% [partial]; 14/400 | 95.94% [partial]; 14/400 | 98.88% [partial]; 14/400 | 71.28% [partial]; 14/400 | 84.28% [partial]; 14/400 | 95.81% [partial]; 14/400 |
| wan22 | t2v | lfg | 99.15% [partial]; 14/400 | 90.26% [partial]; 14/400 | 94.68% [partial]; 14/400 | 96.96% [partial]; 14/400 | 65.28% [partial]; 14/400 | 54.39% [partial]; 14/400 | 75.84% [partial]; 14/400 |

For the number of complete 512-bit messages recovered, see [counts.csv](counts.csv).
This formatter consumes audited reports; it does not rerun their artifact audit or prove protocol comparability.
