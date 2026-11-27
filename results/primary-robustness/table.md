# Measured robustness: bit accuracy and coverage

Percentages are recomputed from correct information bits. Each cell also shows completed/planned videos.
Coverage differs by method. Partial cells describe the available samples.

I2V uses an input image and prompt. T2V uses a text prompt. Drop removes 30 random frames, insert adds 30 noise frames, and clip removes 30 consecutive frames.

| Family | Mode | Method | clean | noise | compression | blur | drop | insert | clip |
|---|---|---|---|---|---|---|---|---|---|
| hunyuan | i2v | last | 100.00% [partial]; 27/400 | 99.00% [partial]; 27/400 | 97.61% [partial]; 27/400 | 99.70% [partial]; 27/400 | 76.79% [partial]; 27/400 | 87.30% [partial]; 27/400 | 98.43% [partial]; 27/400 |
| hunyuan | i2v | lfg | 98.05% [partial]; 27/400 | 92.98% [partial]; 27/400 | 95.49% [partial]; 27/400 | 95.26% [partial]; 27/400 | 65.91% [partial]; 27/400 | 59.74% [partial]; 27/400 | 77.47% [partial]; 27/400 |
| hunyuan | i2v | sigmark | 70.80% [partial]; 2/400 | 49.22% [partial]; 2/400 | 50.20% [partial]; 1/400 | 67.38% [partial]; 1/400 | unscored [partial]; 0/400 (1 failed) | unscored [partial]; 0/400 (1 failed) | 53.12% [partial]; 1/400 |
| hunyuan | i2v | videoshield | 100.00% [partial]; 3/400 | 99.74% [partial]; 3/400 | 99.87% [partial]; 3/400 | 100.00% [partial]; 3/400 | 100.00% [partial]; 3/400 | 98.96% [partial]; 3/400 | 99.54% [partial]; 3/400 |
| hunyuan | t2v | last | 100.00% [partial]; 14/400 | 98.86% [partial]; 14/400 | 96.86% [partial]; 14/400 | 99.72% [partial]; 14/400 | 75.63% [partial]; 14/400 | 90.69% [partial]; 14/400 | 97.74% [partial]; 14/400 |
| hunyuan | t2v | lfg | 96.76% [partial]; 14/400 | 90.95% [partial]; 14/400 | 93.55% [partial]; 14/400 | 93.64% [partial]; 14/400 | 64.75% [partial]; 14/400 | 57.53% [partial]; 14/400 | 73.62% [partial]; 14/400 |
| hunyuan | t2v | videomark | 71.25% [partial]; 40/400 | 57.35% [partial]; 40/400 | 56.24% [partial]; 40/400 | 59.90% [partial]; 40/400 | 51.16% [partial]; 40/400 | 55.22% [partial]; 40/400 | 62.37% [partial]; 40/400 |
| wan22 | i2v | last | 100.00% [partial]; 14/400 | 98.02% [partial]; 14/400 | 95.30% [partial]; 14/400 | 98.80% [partial]; 14/400 | 65.62% [partial]; 14/400 | 84.42% [partial]; 14/400 | 94.81% [partial]; 14/400 |
| wan22 | i2v | lfg | 98.94% [partial]; 14/400 | 91.64% [partial]; 14/400 | 95.40% [partial]; 14/400 | 97.53% [partial]; 14/400 | 66.03% [partial]; 14/400 | 56.57% [partial]; 14/400 | 76.88% [partial]; 14/400 |
| wan22 | i2v | videoshield | 100.00% [partial]; 1/400 | 100.00% [partial]; 1/400 | 100.00% [partial]; 1/400 | 100.00% [partial]; 1/400 | 100.00% [partial]; 1/400 | 99.22% [partial]; 1/400 | 100.00% [partial]; 1/400 |
| wan22 | t2v | last | 100.00% [partial]; 14/400 | 98.28% [partial]; 14/400 | 95.94% [partial]; 14/400 | 98.88% [partial]; 14/400 | 71.28% [partial]; 14/400 | 84.28% [partial]; 14/400 | 95.81% [partial]; 14/400 |
| wan22 | t2v | lfg | 99.15% [partial]; 14/400 | 90.26% [partial]; 14/400 | 94.68% [partial]; 14/400 | 96.96% [partial]; 14/400 | 65.28% [partial]; 14/400 | 54.39% [partial]; 14/400 | 75.84% [partial]; 14/400 |

For the number of complete 512-bit messages recovered, see [counts.csv](counts.csv).
This formatter consumes audited reports; it does not rerun their artifact audit or prove protocol comparability.
