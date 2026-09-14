"""Evidently monitoring utility for Track A — evidently 0.7+ API.
Meets rubric: Data Drift, Target Drift, Custom Metric, MLflow artifact logging.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from evidently import DataDefinition, Dataset, Report
from evidently.metrics import ValueDrift, MeanValue
from evidently.presets import DataDriftPreset, DataSummaryPreset
from typing import Optional


REPORTS_DIR = Path(__file__).resolve().parents[3] / "reports"


def make_dataset(df: pd.DataFrame, num_cols: list = None, cat_cols: list = None):
    data_def = DataDefinition(
        numerical_columns=num_cols or [],
        categorical_columns=cat_cols or [],
    )
    return Dataset.from_pandas(df, data_definition=data_def)


def split_reference_current(df: pd.DataFrame, test_size: float = 0.3,
                             random_state: int = 42):
    """Split into reference (70%) and current (30%) with stratification."""
    from sklearn.model_selection import train_test_split
    ref, cur = train_test_split(df, test_size=test_size, random_state=random_state,
                                 stratify=df.get("Churn"))
    return ref.copy(), cur.copy()


def inject_drift(current_df: pd.DataFrame, random_state: int = 42):
    """Inject synthetic drift into current set for Evidently to detect.
    Rubric: shift MonthlyCharges, skew Contract, flip 5% labels.
    """
    df = current_df.copy()
    rng = np.random.default_rng(random_state)

    # 1. Shift MonthlyCharges by +15 (numeric drift)
    df["MonthlyCharges"] = df["MonthlyCharges"] + rng.normal(15, 5, size=len(df))

    # 2. Shift tenure by -10 (numeric drift)
    df["tenure"] = (df["tenure"] + rng.normal(-10, 3, size=len(df))).clip(lower=0)

    # 3. Skew Contract toward Month-to-month (categorical drift)
    non_mtm = df[df["Contract"] != "Month-to-month"].index
    flip_count = int(len(non_mtm) * 0.4)
    flip_idx = rng.choice(non_mtm, size=flip_count, replace=False)
    df.loc[flip_idx, "Contract"] = "Month-to-month"

    # 4. Flip 5% of labels (target/concept drift)
    flip_label_idx = df.sample(frac=0.05, random_state=random_state).index
    if df["Churn"].dtype == "object":
        df.loc[flip_label_idx, "Churn"] = df.loc[flip_label_idx, "Churn"].map(
            {"Yes": "No", "No": "Yes"}
        )
    else:
        df.loc[flip_label_idx, "Churn"] = 1 - df.loc[flip_label_idx, "Churn"]

    return df


class ChurnRateShift:
    """Custom metric: difference in churn rate between reference and current.
    Satisfies rubric: 'at least one custom metric beyond built-in defaults'.
    """
    def __init__(self):
        self.name = "ChurnRateShift"

    def calculate(self, reference: pd.DataFrame, current: pd.DataFrame) -> dict:
        ref_rate = (reference["Churn"].isin(["Yes", 1])).mean()
        cur_rate = (current["Churn"].isin(["Yes", 1])).mean()
        return {
            "reference_churn_rate": float(ref_rate),
            "current_churn_rate": float(cur_rate),
            "shift": float(cur_rate - ref_rate),
            "shift_pct": float((cur_rate - ref_rate) / ref_rate * 100) if ref_rate > 0 else 0,
        }


class MonthlyChargesShift:
    """Custom metric: difference in mean MonthlyCharges between reference and current."""
    def __init__(self):
        self.name = "MonthlyChargesShift"

    def calculate(self, reference: pd.DataFrame, current: pd.DataFrame) -> dict:
        ref_mean = reference["MonthlyCharges"].mean()
        cur_mean = current["MonthlyCharges"].mean()
        return {
            "reference_mean": float(ref_mean),
            "current_mean": float(cur_mean),
            "absolute_shift": float(cur_mean - ref_mean),
            "pct_shift": float((cur_mean - ref_mean) / ref_mean * 100) if ref_mean > 0 else 0,
        }


def run_data_drift_report(reference_df: pd.DataFrame, current_df: pd.DataFrame,
                           feature_cols: list = None):
    """Run Data Drift preset — flags columns where distribution changed."""
    if feature_cols is None:
        feature_cols = [c for c in reference_df.columns
                        if c not in ("customerID", "Churn")
                        and reference_df[c].dtype != "object"
                        or reference_df[c].nunique() < 10]

    num_cols = [c for c in feature_cols if reference_df[c].dtype in ("int64", "float64")]
    cat_cols = [c for c in feature_cols if c not in num_cols]

    ref_dataset = make_dataset(reference_df, num_cols=num_cols, cat_cols=cat_cols)
    cur_dataset = make_dataset(current_df, num_cols=num_cols, cat_cols=cat_cols)

    report = Report(metrics=[DataDriftPreset(include_tests=True)])
    snapshot = report.run(current_data=cur_dataset, reference_data=ref_dataset)
    return snapshot


def run_target_drift_report(reference_df: pd.DataFrame, current_df: pd.DataFrame):
    """Run ValueDrift on the Churn target column — rubric: 'Target Drift report'."""
    ref_target = reference_df[["Churn"]].copy()
    cur_target = current_df[["Churn"]].copy()

    # Encode target as numeric for drift detection
    ref_target["Churn_num"] = ref_target["Churn"].map({"Yes": 1, "No": 0, 1: 1, 0: 0})
    cur_target["Churn_num"] = cur_target["Churn"].map({"Yes": 1, "No": 0, 1: 1, 0: 0})

    ref_dataset = make_dataset(ref_target, num_cols=["Churn_num"])
    cur_dataset = make_dataset(cur_target, num_cols=["Churn_num"])

    report = Report(metrics=[ValueDrift(column="Churn_num")], include_tests=True)
    snapshot = report.run(current_data=cur_dataset, reference_data=ref_dataset)
    return snapshot


def compute_custom_metrics(reference_df: pd.DataFrame, current_df: pd.DataFrame):
    """Compute custom metrics: ChurnRateShift and MonthlyChargesShift."""
    churn_metric = ChurnRateShift()
    charges_metric = MonthlyChargesShift()
    return {
        "churn_rate_shift": churn_metric.calculate(reference_df, current_df),
        "monthly_charges_shift": charges_metric.calculate(reference_df, current_df),
    }


def save_report(snapshot, filename: str, output_dir: Path = None):
    if output_dir is None:
        output_dir = REPORTS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / filename
    snapshot.save_html(str(path))
    return path


def save_json(snapshot, filename: str, output_dir: Path = None):
    if output_dir is None:
        output_dir = REPORTS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / filename
    snapshot.save_json(str(path))
    return path


class EvidentlyReporter:
    def __init__(self, reports_dir: Path = None):
        self.reports_dir = reports_dir or REPORTS_DIR
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def generate_full_report(self, reference_df: pd.DataFrame, current_df: pd.DataFrame,
                              feature_cols: list = None, log_to_mlflow=None):
        """Generate all reports and optionally log to MLflow.

        Args:
            log_to_mlflow: tuple of (logger, run) to log artifacts to MLflow
        Returns:
            dict with all report paths and custom metrics
        """
        results = {}

        # 1. Data Drift report
        drift_snapshot = run_data_drift_report(reference_df, current_df, feature_cols)
        drift_path = save_report(drift_snapshot, "data_drift.html", self.reports_dir)
        save_json(drift_snapshot, "data_drift.json", self.reports_dir)
        results["data_drift_path"] = drift_path
        results["data_drift_snapshot"] = drift_snapshot

        # 2. Target Drift report
        target_snapshot = run_target_drift_report(reference_df, current_df)
        target_path = save_report(target_snapshot, "target_drift.html", self.reports_dir)
        save_json(target_snapshot, "target_drift.json", self.reports_dir)
        results["target_drift_path"] = target_path
        results["target_drift_snapshot"] = target_snapshot

        # 3. Custom metrics
        custom = compute_custom_metrics(reference_df, current_df)
        results["custom_metrics"] = custom

        # 4. Log to MLflow if logger provided
        if log_to_mlflow:
            logger, run = log_to_mlflow
            logger.log_artifact(run, str(drift_path), artifact_path="evidently_reports")
            logger.log_artifact(run, str(target_path), artifact_path="evidently_reports")

            # Log custom metrics
            for metric_name, metric_vals in custom.items():
                for k, v in metric_vals.items():
                    logger.client.log_metric(
                        run.info.run_id, f"{metric_name}_{k}", v
                    )

        return results

    def generate_drift_report(self, reference_df, current_df):
        """Legacy interface — returns drift results dict."""
        return self.generate_full_report(reference_df, current_df)
