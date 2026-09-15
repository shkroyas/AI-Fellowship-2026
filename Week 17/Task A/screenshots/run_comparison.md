# Fresh IBM training and acceptance gates

| Model run | F1 | ROC-AUC | Training CV F1 |
|---|---:|---:|---:|
| xgb_weighted_20260915T090905_339855Z | 0.6367 | 0.8443 | 0.6341 |
| rf_balanced_20260915T090828_313113Z | 0.6285 | 0.8430 | 0.6326 |
| rf_deep_balanced_20260915T090908_874843Z | 0.6369 | 0.8413 | 0.6293 |
| lr_balanced_20260915T090822_537767Z | 0.6136 | 0.8416 | 0.6283 |

Production run: `765d91dead484c3e8eebde038848bb32`.

Acceptance floors: CV F1 >=0.60 and holdout ROC-AUC >=0.80. See [threshold policy](../../THRESHOLD_POLICY.md).
