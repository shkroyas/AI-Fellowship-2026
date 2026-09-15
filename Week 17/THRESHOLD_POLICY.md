# Acceptance and monitoring thresholds

These are project-defined operating choices, not numerical requirements from the assignment. Passing a workflow means it executed correctly; passing a quality gate is a separate decision. Thresholds should be reviewed with a larger validation set and business costs before real deployment.

| Decision | Chosen threshold | Why it is useful here | Action when crossed |
|---|---|---|---|
| Track A candidate ranking | Highest training five-fold CV F1 within one execution | F1 balances precision and recall for the minority churn class; training-only CV avoids choosing the winner by holdout ranking. | Select that candidate for acceptance checks. |
| Track A production acceptance | Training CV F1 ≥0.60 **and** holdout ROC-AUC ≥0.80 | F1 prevents majority-class accuracy from masking poor churn detection; AUC checks useful discrimination across classification cutoffs. These are illustrative minimum floors for this dataset, not proof of business readiness. | A candidate below either floor stays in staging. Keep the existing production alias; if none exists, do not create one. Investigate features, data quality and validation design. |
| Track B regression acceptance | Combined case pass rate ≥80% | On this five-case demonstration suite, at least four cases must satisfy termination, deterministic checks and both live judges. The threshold tolerates one failure while exposing larger regressions. It is coarse and needs a broader, risk-weighted suite for real deployment. | Below 80%, log a regression alert and block promotion. At or above 80%, the version is eligible for review; the current DAG does not automatically assign any production prompt alias. |
| Charge-distribution monitoring | Absolute relative shift in mean MonthlyCharges ≥10% | A 10% shift is interpretable as a material change in customer billing mix; it is more actionable here than reacting to every statistically detectable difference. The Evidently custom test requires `<10%`. | Investigate the changed batch and trigger the demonstration retraining branch. Retraining still must pass Track A's acceptance gates before replacing production. |

The general Evidently dataset-drift preset uses its own default fraction-of-columns threshold (50%). This is distinct from the explicit 10% business-feature gate: three drifting columns may leave the dataset-wide flag false while the charge-shift gate still triggers action.

## Observed outcomes

- The IBM model's training CV F1 (~0.6341) and holdout ROC-AUC (~0.8443) satisfy the stated Track A floors.
- The final prompt comparison scored v1=100%, v2=80%, v3=40%. v3 is not eligible under this policy.
- The independent Airflow v3 run scored 60% and executed the regression-alert branch. No prompt was promoted.
- Injected charge drift was about 21.7%, which exceeded the 10% monitoring threshold and triggered retraining. The undrifted split stayed below the gate.

The numerical floors were formalized during this repair after initial results were visible. They are an explicit operational demonstration, not a preregistered research claim. Future comparisons should freeze thresholds before execution and document any policy change separately; do not lower them merely to pass a weak candidate.
