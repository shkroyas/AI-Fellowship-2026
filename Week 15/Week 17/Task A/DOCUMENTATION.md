# Track A implementation notes

The current commands and evidence are in [README.md](README.md). Fresh measurements are generated in [training_summary.json](reports/training_summary.json); older synthetic-data metrics are historical and must not be used to describe the IBM-data model.

## Reproducibility and selection

- Commit `pyproject.toml` and `uv.lock`; reproduce with `uv sync --locked`.
- Load `data/raw/Telco-Customer-Churn.csv`; `quarantine_synthetic.csv` is excluded from training.
- Split 80/20 with stratification and seed 42 before fitting preprocessing.
- Fit scaling and categorical encoding inside each five-fold training CV split.
- Compare balanced logistic regression, two balanced forests, and weighted XGBoost.
- Select highest training CV F1 among the current execution's four run IDs. Holdout metrics are reported after fitting.
- Register the full fitted pipeline in staging. Assign production only if training CV F1 ≥0.60 and holdout ROC-AUC ≥0.80; otherwise retain existing production. The local SQLite store is `data/mlflow.db`; portable run exports are committed, while model stores remain local.

## Serving contract

POST `/predict` accepts the 19 raw customer fields. Numeric tenure, monthly charges and total charges are required; the schema supplies categorical defaults. To represent a real customer accurately, send all fields. Unknown categories use the encoder's `handle_unknown=ignore` behavior. The same fitted pipeline supplies the API probability. `/health` reports the loaded model version.

## Monitoring and orchestration

Evidently generates data and target drift reports with explicit tests. `MonthlyChargesShiftCalculation` returns the absolute relative change in the reference/current mean monthly charge as a percentage. A value >=10 fails the custom test. Separate summary calculations retain signed changes for interpretation. Monitoring HTML is logged to the selected MLflow run.

Airflow invokes track-local Python in subprocesses. Both no-drift and injected-drift paths were manually triggered through the scheduler; exported task states and logs are the evidence. Retraining in this assignment uses the same original labeled IBM dataset and the declared CV policy. No claim is made about a real production distribution or newly labeled data.
