# MLflow Run Comparison

| Rank | Run | Accuracy | Precision | Recall | F1 | ROC-AUC | CV-F1 | Model |
|------|-----|----------|-----------|--------|-----|---------|-------|-------|
| 1 | lr_balanced | 0.7353 | 0.8027 | 0.7257 | 0.7623 | 0.8132 | 0.7511 | LogisticRegression |
| 2 | rf_deep_balanced | 0.7246 | 0.7817 | 0.7342 | 0.7572 | 0.7976 | 0.7516 | RandomForestClassifier |
| 3 | xgb_weighted | 0.7189 | 0.7758 | 0.7306 | 0.7525 | 0.8006 | 0.751 | XGBClassifier |
| 4 | rf_balanced | 0.7211 | 0.7885 | 0.7148 | 0.7498 | 0.7987 | 0.7467 | RandomForestClassifier |
| 5 | xgb_tuned | 0.6969 | 0.2766 | 0.0675 | 0.1086 | 0.5067 | 0.0 | XGBClassifier |
| 6 | rf_deep | 0.7253 | 0.0 | 0.0 | 0.0 | 0.5319 | 0.0 | RandomForestClassifier |
| 7 | rf_depth8 | 0.7268 | 0.0 | 0.0 | 0.0 | 0.507 | 0.0 | RandomForestClassifier |
| 8 | lr_baseline | 0.7268 | 0.0 | 0.0 | 0.0 | 0.5071 | 0.0 | LogisticRegression |
