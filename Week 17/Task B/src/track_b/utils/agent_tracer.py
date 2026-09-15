"""Agent tracing utility for Track B — wraps MLflow for LLM/agentic experiment tracking."""

import mlflow
from mlflow.tracking import MlflowClient
from mlflow.entities import Metric
import json
import time
from pathlib import Path
from typing import Optional


class AgentTracer:
    def __init__(self, tracking_uri: str = None):
        if tracking_uri is None:
            tracking_uri = str(Path(__file__).resolve().parents[3] / "data" / "mlflow.db")
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
        """Create a new run for every execution; never resume by display name."""
        from datetime import datetime, timezone
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
        return self.client.create_run(experiment_id, run_name=f"{run_name}_{stamp}")

    def log_run(self, run, metrics: dict, params: dict, tags: dict = None):
        for k, v in params.items():
            self.client.log_param(run.info.run_id, k, v)
        for k, v in metrics.items():
            if isinstance(v, (int, float)):
                self.client.log_metric(run.info.run_id, k, v)
        if tags:
            for k, v in tags.items():
                self.client.set_tag(run.info.run_id, k, v)

    def log_trace(self, run, trace_data: dict, trace_name: str = "trace"):
        trace_json = json.dumps(trace_data, indent=2, default=str)
        trace_path = Path(f"/tmp/{trace_name}.json")
        trace_path.write_text(trace_json)
        self.client.log_artifact(run.info.run_id, str(trace_path), artifact_path="traces")
        trace_path.unlink(missing_ok=True)

    def log_agent(self, run, agent_fn, artifact_path: str = "agent"):
        mlflow.pyfunc.log_model(
            artifact_path=artifact_path,
            python_model=agent_fn,
            run_id=run.info.run_id,
        )

    def register_agent(self, model_name: str, model_uri: str, alias: str = None):
        mv = mlflow.register_model(model_uri, model_name)
        if alias:
            self.client.set_registered_model_alias(model_name, alias=alias, version=mv.version)
        return mv

    def load_registered_agent(self, model_name: str, alias: str = "production"):
        return mlflow.pyfunc.load_model(f"models:/{model_name}@{alias}")

    def set_alias(self, model_name: str, alias: str, version: int):
        self.client.set_registered_model_alias(model_name, alias=alias, version=version)

    def search_runs(self, experiment_id: str, order_by: str = None):
        return self.client.search_runs(
            experiment_ids=[experiment_id],
            order_by=[order_by] if order_by else None,
        )

    def end_run(self, run_id: str, status: str = "FINISHED"):
        self.client.set_terminated(run_id, status=status)

    def register_prompt(self, name: str, template: str, description: str = "",
                        version: str = None, commit_message: str = ""):
        prompt = mlflow.genai.register_prompt(
            name=name,
            template=template,
            description=description,
            version=version,
            commit_message=commit_message,
        )
        return prompt

    def load_prompt(self, name: str, version: str = None):
        if version:
            return mlflow.genai.load_prompt(name=name, version=version)
        return mlflow.genai.load_prompt(name=name)

    def set_prompt_alias(self, name: str, alias: str, version: str):
        mlflow.genai.set_prompt_alias(name=name, alias=alias, version=version)
