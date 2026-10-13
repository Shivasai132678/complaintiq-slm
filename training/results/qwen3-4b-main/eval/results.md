# Results: Qwen3-4B-Instruct-2507+qwen3-4b-main

### Test set (newest months, Feb-Jul 2026, 10 classes): 3000 rows

| Metric | Value |
|---|---|
| 10-class accuracy | 64.50% |
| Macro F1 | 64.95% |
| Macro precision | 66.54% |
| Macro recall | 64.50% |
| Weighted F1 | 64.95% |
| Product accuracy | 90.27% |
| In-scope joint (product+issue) accuracy | 64.41% |
| Out-of-scope precision | 82.35% |
| Out-of-scope recall | 65.33% |
| Invalid replies | 0 |

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| Checking or savings account / Deposits and withdrawals | 62.84% | 62.00% | 62.42% | 300 |
| Checking or savings account / Managing an account | 47.58% | 65.67% | 55.18% | 300 |
| Checking or savings account / Problems caused by my funds being low | 83.19% | 64.33% | 72.56% | 300 |
| Credit card / Billing disputes | 76.66% | 81.00% | 78.77% | 300 |
| Credit card / Fees or interest | 87.84% | 86.67% | 87.25% | 300 |
| Credit card / Other | 76.78% | 68.33% | 72.31% | 300 |
| Credit reporting / Improper use of your report | 53.23% | 44.00% | 48.18% | 300 |
| Credit reporting / Incorrect information on your report | 43.34% | 59.67% | 50.21% | 300 |
| Credit reporting / Problem with a credit reporting company's investigation into an existing problem | 51.61% | 48.00% | 49.74% | 300 |
| Unknown / Needs review | 82.35% | 65.33% | 72.86% | 300 |

### Held-out check set: 1407 rows

| Metric | Value |
|---|---|
| 10-class accuracy | 74.48% |
| Macro F1 | 39.43% |
| Macro precision | 32.30% |
| Macro recall | 60.00% |
| Weighted F1 | 80.82% |
| Product accuracy | 77.90% |
| In-scope joint (product+issue) accuracy | 58.17% |
| Out-of-scope precision | 99.58% |
| Out-of-scope recall | 76.48% |
| Invalid replies | 0 |
| Accuracy on original_test_153 (n=153) | 58.17% |
| Accuracy on scope_other_products_test (n=1200) | 75.92% |
| Accuracy on scope_unrelated_authored_test (n=54) | 88.89% |

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| Checking or savings account / Deposits and withdrawals | 12.96% | 41.18% | 19.72% | 17 |
| Checking or savings account / Managing an account | 9.23% | 35.29% | 14.63% | 17 |
| Checking or savings account / Problems caused by my funds being low | 44.12% | 88.24% | 58.82% | 17 |
| Credit card / Billing disputes | 28.12% | 52.94% | 36.73% | 17 |
| Credit card / Fees or interest | 38.89% | 82.35% | 52.83% | 17 |
| Credit card / Other | 22.92% | 64.71% | 33.85% | 17 |
| Credit reporting / Improper use of your report | 45.16% | 82.35% | 58.33% | 17 |
| Credit reporting / Incorrect information on your report | 6.67% | 41.18% | 11.48% | 17 |
| Credit reporting / Problem with a credit reporting company's investigation into an existing problem | 15.38% | 35.29% | 21.43% | 17 |
| Unknown / Needs review | 99.58% | 76.48% | 86.51% | 1254 |
