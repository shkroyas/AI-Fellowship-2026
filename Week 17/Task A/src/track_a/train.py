"""Training script for Track A — trains 3+ models with MLflow tracking."""

import sys
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import mlflow
import mlflow.sklearn
import mlflow.xgboost
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, ConfusionMatrixDisplay, RocCurveDisplay,
    classification_report,
)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from xgboost import XGBClassifier

from src.track_a.data_prep import prepare_pipeline, make_model_pipeline
from src.track_a.utils.mlflow_utils import MLFlowLogger


EXPERIMENT_NAME = "TelcoChurn"
ARTIFACT_DIR = Path(__file__).resolve().parents[2] / "reports"


MIN_CV_F1 = 0.60
MIN_HOLDOUT_ROC_AUC = 0.80


def promotion_allowed(metrics):
    """Project acceptance floors; ranking remains based on training CV F1."""
    return (metrics.get("cv_f1_mean", float("-inf")) >= MIN_CV_F1
            and metrics.get("roc_auc", float("-inf")) >= MIN_HOLDOUT_ROC_AUC)


def compute_metrics(y_true, y_pred, y_prob) -> dict:
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "roc_auc": roc_auc_score(y_true, y_prob) if y_prob is not None else 0.0,
    }


def cross_validate_model(model, X, y, cv=5):
    skf = StratifiedKFold(n_splits=cv, shuffle=True, random_state=42)
    scores = cross_val_score(model, X, y, cv=skf, scoring="f1", n_jobs=-1)
    return {
        "cv_f1_mean": float(scores.mean()),
        "cv_f1_std": float(scores.std()),
        "cv_f1_min": float(scores.min()),
        "cv_f1_max": float(scores.max()),
    }


def plot_confusion_matrix(y_true, y_pred, model_name: str, run_dir: Path):
    fig, ax = plt.subplots(figsize=(6, 5))
    ConfusionMatrixDisplay.from_predictions(y_true, y_pred, ax=ax, cmap="Blues")
    ax.set_title(f"Confusion Matrix — {model_name}")
    path = run_dir / f"{model_name}_confusion.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_roc_curve(y_true, y_prob, model_name: str, run_dir: Path):
    fig, ax = plt.subplots(figsize=(6, 5))
    RocCurveDisplay.from_predictions(y_true, y_prob, ax=ax)
    ax.set_title(f"ROC Curve — {model_name}")
    path = run_dir / f"{model_name}_roc.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_feature_importance(model, feature_cols, model_name: str, run_dir: Path):
    if not hasattr(model, "feature_importances_"):
        return None
    importances = model.feature_importances_
    indices = np.argsort(importances)[-15:]  # top 15
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(range(len(indices)), importances[indices], align="center")
    ax.set_yticks(range(len(indices)))
    ax.set_yticklabels([feature_cols[i] for i in indices])
    ax.set_title(f"Feature Importance — {model_name}")
    ax.set_xlabel("Importance")
    path = run_dir / f"{model_name}_features.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def train_and_log(logger: MLFlowLogger, experiment_id: str, run_name: str,
                  model, params: dict, data: dict, tags: dict = None):
    X_train, X_test = data["X_train"], data["X_test"]
    y_train, y_test = data["y_train"], data["y_test"]
    feature_cols = data["feature_cols"]

    model = make_model_pipeline(model)

    # Cross-validate on training set
    cv_results = cross_validate_model(model, X_train, y_train)

    # Fit
    model.fit(X_train, y_train)

    # Predict
    y_pred = model.predict(X_test)
    if hasattr(model, "predict_proba"):
        y_prob = model.predict_proba(X_test)[:, 1]
    else:
        y_prob = y_pred.astype(float)

    # Metrics
    metrics = compute_metrics(y_test, y_pred, y_prob)
    metrics.update(cv_results)

    # Create run
    run = logger.get_run(run_name, experiment_id)
    all_tags = {"model_type": type(model).__name__, "execution_id": logger.execution_id, "dataset_sha256": logger.dataset_sha256}
    if tags:
        all_tags.update(tags)
    logger.log_run(run, metrics=metrics, params=params, tags=all_tags)

    # Artifacts
    run_dir = ARTIFACT_DIR / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    cm_path = plot_confusion_matrix(y_test, y_pred, run_name, run_dir)
    logger.log_artifact(run, str(cm_path), artifact_path="plots")

    roc_path = plot_roc_curve(y_test, y_prob, run_name, run_dir)
    logger.log_artifact(run, str(roc_path), artifact_path="plots")

    feat_path = plot_feature_importance(model.named_steps["classifier"], list(model.named_steps["preprocessing"].get_feature_names_out()), run_name, run_dir)
    if feat_path:
        logger.log_artifact(run, str(feat_path), artifact_path="plots")

    # Log classification report as text
    clf_report = classification_report(y_test, y_pred, output_dict=True)
    for cls in ["0", "1"]:
        for metric in ["precision", "recall", "f1-score"]:
            key = f"class_{cls}_{metric}"
            metrics[key] = clf_report.get(cls, {}).get(metric, 0.0)

    # Log model
    logger.log_model(run, model, artifact_path="model")

    # Save and log feature list so the serving layer can align columns
    import json
    features_path = run_dir / "features.json"
    features_path.write_text(json.dumps(feature_cols))
    logger.log_artifact(run, str(features_path), artifact_path="metadata")

    print(f"  [{run_name}] Acc={metrics['accuracy']:.4f}  F1={metrics['f1']:.4f}  "
          f"AUC={metrics['roc_auc']:.4f}  CV-F1={metrics['cv_f1_mean']:.4f}±{metrics['cv_f1_std']:.4f}")
    return run, metrics


def main():
    print("Loading and preprocessing data...")
    data = prepare_pipeline()
    print(f"  Train: {data['X_train'].shape}, Test: {data['X_test'].shape}")
    print(f"  Churn rate (train): {data['y_train'].mean():.3f}")

    logger = MLFlowLogger()
    logger.execution_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    logger.dataset_sha256 = hashlib.sha256((Path(__file__).resolve().parents[2] / "data/raw/Telco-Customer-Churn.csv").read_bytes()).hexdigest()
    experiment_id = logger.get_or_create_experiment(EXPERIMENT_NAME)

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    print("\nTraining models...")

    # Run 1: Logistic Regression baseline (with class weight)
    lr = LogisticRegression(C=1.0, max_iter=1000, class_weight="balanced", random_state=42)
    train_and_log(logger, experiment_id, "lr_balanced",
                  lr,
                  params={"C": 1.0, "max_iter": 1000, "class_weight": "balanced"},
                  data=data,
                  tags={"model_family": "linear", "class_weight": "balanced"})

    # Run 2: Random Forest with class weight
    rf1 = RandomForestClassifier(
        n_estimators=300, max_depth=10, min_samples_leaf=10,
        class_weight="balanced", random_state=42, n_jobs=-1
    )
    train_and_log(logger, experiment_id, "rf_balanced",
                  rf1,
                  params={"n_estimators": 300, "max_depth": 10, "min_samples_leaf": 10,
                          "class_weight": "balanced"},
                  data=data,
                  tags={"model_family": "ensemble", "class_weight": "balanced"})

    # Run 3: Gradient Boosting (no class weight, uses sample weights via scale_pos_weight)
    pos_count = data["y_train"].sum()
    neg_count = len(data["y_train"]) - pos_count
    scale_pos_weight = neg_count / pos_count

    xgb = XGBClassifier(
        n_estimators=200, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        random_state=42, eval_metric="logloss",
    )
    train_and_log(logger, experiment_id, "xgb_weighted",
                  xgb,
                  params={"n_estimators": 200, "max_depth": 4, "learning_rate": 0.05,
                          "subsample": 0.8, "colsample_bytree": 0.8,
                          "scale_pos_weight": round(scale_pos_weight, 2)},
                  data=data,
                  tags={"model_family": "gradient_boosting", "class_weight": "scale_pos_weight"})

    # Run 4: Deeper RF for comparison
    rf2 = RandomForestClassifier(
        n_estimators=500, max_depth=None, min_samples_leaf=5,
        class_weight="balanced", random_state=42, n_jobs=-1
    )
    train_and_log(logger, experiment_id, "rf_deep_balanced",
                  rf2,
                  params={"n_estimators": 500, "max_depth": "None", "min_samples_leaf": 5,
                          "class_weight": "balanced"},
                  data=data,
                  tags={"model_family": "ensemble", "class_weight": "balanced"})

    # Compare runs
    runs = [r for r in logger.search_runs(experiment_id, order_by="metrics.cv_f1_mean DESC") if r.data.tags.get("execution_id") == logger.execution_id]
    print("\n=== Run Comparison (sorted by training CV F1) ===")
    print(f"{'Run':<22} {'Accuracy':>10} {'F1':>10} {'AUC':>10} {'CV-F1':>12}")
    print("-" * 66)
    best_run = None
    for r in runs:
        name = r.data.tags.get("mlflow.runName", r.info.run_id[:8])
        acc = r.data.metrics.get("accuracy", 0)
        f1 = r.data.metrics.get("f1", 0)
        auc = r.data.metrics.get("roc_auc", 0)
        cv_f1 = r.data.metrics.get("cv_f1_mean", 0)
        cv_std = r.data.metrics.get("cv_f1_std", 0)
        print(f"{name:<22} {acc:>10.4f} {f1:>10.4f} {auc:>10.4f} {cv_f1:>5.4f}±{cv_std:.4f}")
        if best_run is None:
            best_run = (name, r)

    # Register the CV-selected candidate; promote only when acceptance floors pass.
    promoted = False
    if best_run:
        name, run = best_run
        print(f"\nBest model: {name}")
        model_uri = f"runs:/{run.info.run_id}/model"
        mv = logger.register_model("ChurnClassifier", model_uri, alias="staging")
        print(f"Registered model version {mv.version} with alias 'staging'")

        promoted = promotion_allowed(run.data.metrics)
        logger.log_run(run, metrics={"promotion_gate_passed": int(promoted)},
                       params={"min_cv_f1": MIN_CV_F1, "min_holdout_roc_auc": MIN_HOLDOUT_ROC_AUC})
        if promoted:
            logger.set_alias("ChurnClassifier", "production", int(mv.version))
            print(f"Promoted version {mv.version}: acceptance floors passed")
        else:
            print("Promotion blocked: candidate below acceptance floor; existing production alias retained")

    # === EVIDENTLY MONITORING ===
    print("\n--- Evidently Monitoring ---")
    from src.track_a.utils.evidently_reporter import (
        EvidentlyReporter, split_reference_current, inject_drift
    )

    # Load raw data (before one-hot encoding) for monitoring
    raw_df = pd.read_csv(Path(__file__).resolve().parents[2] / "data" / "raw" / "Telco-Customer-Churn.csv")
    raw_df["TotalCharges"] = pd.to_numeric(raw_df["TotalCharges"], errors="coerce").fillna(0)
    raw_df["Churn"] = raw_df["Churn"].map({"Yes": 1, "No": 0})
    raw_df = raw_df.drop(columns=["customerID"])

    # Split into reference (70%) and current (30%)
    reference_df, current_df = split_reference_current(raw_df)
    print(f"  Reference: {len(reference_df)} rows, Current: {len(current_df)} rows")

    # Inject synthetic drift into current set
    current_drifted = inject_drift(current_df)
    print(f"  Injected drift: MonthlyCharges +15, tenure -10, Contract skew, 5% label flip")

    # Generate reports and log to MLflow
    reporter = EvidentlyReporter()
    best_run_obj = best_run[1] if best_run else list(logger.search_runs(experiment_id))[0]
    mlflow_tuple = (logger, best_run_obj)

    results = reporter.generate_full_report(
        reference_df, current_drifted,
        log_to_mlflow=mlflow_tuple
    )

    # Print interpretation
    custom = results["custom_metrics"]
    print(f"\n  Custom Metrics:")
    print(f"    Churn rate shift: {custom['churn_rate_shift']['reference_churn_rate']:.3f} -> "
          f"{custom['churn_rate_shift']['current_churn_rate']:.3f} "
          f"({custom['churn_rate_shift']['shift_pct']:+.1f}%)")
    print(f"    MonthlyCharges shift: {custom['monthly_charges_shift']['reference_mean']:.2f} -> "
          f"{custom['monthly_charges_shift']['current_mean']:.2f} "
          f"({custom['monthly_charges_shift']['absolute_shift']:+.2f})")

    print(f"\n  Reports saved:")
    print(f"    Data Drift: {results['data_drift_path']}")
    print(f"    Target Drift: {results['target_drift_path']}")
    print(f"    All reports logged to MLflow as artifacts")

    export = {"execution_id": logger.execution_id, "dataset_sha256": logger.dataset_sha256,
              "selection_policy": "highest training cross-validation F1 within this execution",
              "candidate_run_id": best_run[1].info.run_id,
              "production_run_id": (logger.client.get_model_version_by_alias("ChurnClassifier", "production").run_id
                                    if promoted else None),
              "promoted": promoted,
              "promotion_policy": {"min_cv_f1": MIN_CV_F1, "min_holdout_roc_auc": MIN_HOLDOUT_ROC_AUC},
              "runs": [{"run_id": r.info.run_id, "name": r.data.tags.get("mlflow.runName"),
                        "metrics": r.data.metrics, "params": r.data.params} for r in runs],
              "custom_metrics": custom}
    (ARTIFACT_DIR / "training_summary.json").write_text(json.dumps(export, indent=2))
    print("\nDone! Start MLflow UI: uv run mlflow ui --backend-store-uri sqlite:///data/mlflow.db")


if __name__ == "__main__":
    main()
