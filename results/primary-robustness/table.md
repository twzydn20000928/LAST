# Measured robustness: bit accuracy and coverage

Percentages are recomputed from correct information bits. Each cell also shows completed/planned videos.
Coverage differs by method. Partial cells describe the available samples.

I2V uses an input image and prompt. T2V uses a text prompt. Drop removes 30 random frames, insert adds 30 noise frames, and clip removes 30 consecutive frames.

| Family | Mode | Method | clean | noise | compression | blur | drop | insert | clip |
|---|---|---|---|---|---|---|---|---|---|
| hunyuan | i2v | last | 100.00% [partial]; 48/400 | 99.09% [partial]; 48/400 | 97.80% [partial]; 48/400 | 99.78% [partial]; 48/400 | 77.79% [partial]; 48/400 | 85.75% [partial]; 48/400 | 98.62% [partial]; 48/400 |
| hunyuan | i2v | lfg | 97.31% [partial]; 48/400 | 92.20% [partial]; 48/400 | 94.43% [partial]; 48/400 | 94.47% [partial]; 48/400 | 65.56% [partial]; 48/400 | 59.36% [partial]; 48/400 | 77.96% [partial]; 48/400 |
| hunyuan | i2v | sigmark | 70.80% [partial]; 2/400 | 49.22% [partial]; 2/400 | 49.90% [partial]; 2/400 | 57.91% [partial]; 2/400 | 47.07% [partial]; 1/400 (1 failed) | unscored [partial]; 0/400 (2 failed) | 53.12% [partial]; 1/400 |
| hunyuan | i2v | videomark | 48.63% [partial]; 1/400 | 49.02% [partial]; 1/400 | 46.29% [partial]; 1/400 | 49.80% [partial]; 1/400 | 46.29% [partial]; 1/400 | pending [partial]; 0/400 | 46.29% [partial]; 1/400 |
| hunyuan | i2v | videoshield | 100.00% [partial]; 3/400 | 99.74% [partial]; 3/400 | 99.87% [partial]; 3/400 | 100.00% [partial]; 3/400 | 100.00% [partial]; 3/400 | 98.96% [partial]; 3/400 | 99.54% [partial]; 3/400 |
| hunyuan | t2v | last | 100.00% [partial]; 16/400 | 99.00% [partial]; 16/400 | 97.25% [partial]; 16/400 | 99.76% [partial]; 16/400 | 76.76% [partial]; 16/400 | 91.13% [partial]; 16/400 | 98.02% [partial]; 16/400 |
| hunyuan | t2v | lfg | 96.59% [partial]; 16/400 | 90.75% [partial]; 16/400 | 93.42% [partial]; 16/400 | 93.55% [partial]; 16/400 | 64.66% [partial]; 16/400 | 57.42% [partial]; 16/400 | 75.11% [partial]; 16/400 |
| hunyuan | t2v | videomark | 71.25% [partial]; 40/400 | 57.35% [partial]; 40/400 | 56.24% [partial]; 40/400 | 59.90% [partial]; 40/400 | 51.16% [partial]; 40/400 | 55.22% [partial]; 40/400 | 62.37% [partial]; 40/400 |
| wan22 | i2v | last | 100.00% [partial]; 15/400 | 98.15% [partial]; 15/400 | 95.61% [partial]; 15/400 | 98.88% [partial]; 15/400 | 66.09% [partial]; 15/400 | 84.41% [partial]; 15/400 | 95.16% [partial]; 15/400 |
| wan22 | i2v | lfg | 98.72% [partial]; 15/400 | 91.33% [partial]; 15/400 | 95.04% [partial]; 15/400 | 97.32% [partial]; 15/400 | 65.31% [partial]; 15/400 | 56.81% [partial]; 15/400 | 77.12% [partial]; 15/400 |
| wan22 | i2v | videoshield | 100.00% [partial]; 1/400 | 100.00% [partial]; 1/400 | 100.00% [partial]; 1/400 | 100.00% [partial]; 1/400 | 100.00% [partial]; 1/400 | 99.22% [partial]; 1/400 | 100.00% [partial]; 1/400 |
| wan22 | t2v | last | 100.00% [partial]; 15/400 | 98.40% [partial]; 15/400 | 96.21% [partial]; 15/400 | 98.96% [partial]; 15/400 | 72.19% [partial]; 15/400 | 84.69% [partial]; 15/400 | 96.09% [partial]; 15/400 |
| wan22 | t2v | lfg | 99.21% [partial]; 15/400 | 90.79% [partial]; 15/400 | 95.04% [partial]; 15/400 | 97.16% [partial]; 15/400 | 65.30% [partial]; 15/400 | 54.84% [partial]; 15/400 | 77.01% [partial]; 15/400 |

For the number of complete 512-bit messages recovered, see [counts.csv](counts.csv).
This formatter consumes audited reports; it does not rerun their artifact audit or prove protocol comparability.
