"""MLflow logging utility for Track A — wraps MlflowClient with convenience methods."""

import mlflow
from mlflow.tracking import MlflowClient
from mlflow.models.signature import ModelSignature
from pathlib import Path
from typing import Any, Optional
import numpy as np


class MLFlowLogger:
    def __init__(self, tracking_uri: str = None):
        if tracking_uri is None:
            tracking_uri = str(Path(__file__).resolve().parents[2] / "data" / "mlflow.db")
            tracking_uri = f"sqlite:///{tracking_uri}"
        self.tracking_uri = tracking_uri
        mlflow.set_tracking_uri(tracking_uri)
        self.client = MlflowClient(tracking_uri=tracking_uri)

    def get_or_create_experiment(self, name: str) -> str:
        exp = self.client.get_experiment_by_name(name)
        if exp is None:
            return self.client.create_experiment(name)
        return exp.experiment_id

    def get_run(self, run_name: str, experiment_id: str, create_new: bool = True):
        runs = self.client.search_runs(
            experiment_ids=[experiment_id],
            filter_string=f"tags.`mlflow.runName` = '{run_name}'",
        )
        if runs:
            return runs[0]
        if create_new:
            run = self.client.create_run(experiment_id, run_name=run_name)
            return run
        return None

    def log_run(self, run, metrics: dict, params: dict, tags: dict = None):
        for k, v in params.items():
            self.client.log_param(run.info.run_id, k, v)
        for k, v in metrics.items():
            self.client.log_metric(run.info.run_id, k, v)
        if tags:
            for k, v in tags.items():
                self.client.set_tag(run.info.run_id, k, v)

    def log_artifact(self, run, local_path: str, artifact_path: str = None):
        self.client.log_artifact(run.info.run_id, local_path, artifact_path=artifact_path)

    def log_model(self, run, model, artifact_path: str = "model", conda_env=None,
                  signature: ModelSignature = None, input_example=None):
        model_type = type(model).__name__
        with mlflow.start_run(run_id=run.info.run_id):
            if "XGB" in model_type:
                import mlflow.xgboost as xgb_mlflow
                xgb_mlflow.log_model(
                    xgb_model=model,
                    artifact_path=artifact_path,
                )
            else:
                import mlflow.sklearn as sklearn_mlflow
                sklearn_mlflow.log_model(
                    sk_model=model,
                    artifact_path=artifact_path,
                    conda_env=conda_env,
                    signature=signature,
                    input_example=input_example,
                )

    def register_model(self, model_name: str, model_uri: str, alias: str = None):
        model_version = mlflow.register_model(model_uri, model_name)
        if alias:
            self.client.set_registered_model_alias(
                model_name, alias=alias, version=model_version.version
            )
        return model_version

    def set_alias(self, model_name: str, alias: str, version: int):
        self.client.set_registered_model_alias(model_name, alias=alias, version=version)

    def load_model(self, model_name: str, alias: str = None, version: int = None):
        if alias:
            uri = f"models:/{model_name}@{alias}"
        elif version:
            uri = f"models:/{model_name}/{version}"
        else:
            uri = f"models:/{model_name}"
        return mlflow.pyfunc.load_model(uri)

    def search_runs(self, experiment_id: str, order_by: str = None):
        return self.client.search_runs(
            experiment_ids=[experiment_id],
            order_by=[order_by] if order_by else None,
        )
