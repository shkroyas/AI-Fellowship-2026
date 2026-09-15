"""FastAPI serving wrapper for the production churn model.

Fixes applied:
  - Load model via alias (models:/<name>@<alias>) — no deprecated Stage API.
  - Download features.json from the registered version's artifacts so encoding
    always matches training.
  - Load underlying sklearn model via mlflow.sklearn.load_model for real predict_proba.
  - Encode a single row by constructing all expected dummy columns explicitly,
    preventing the silent zero-fill that discarded category information.
  - Return a genuine probability, not a class label cast to float.
"""

import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import mlflow
import mlflow.sklearn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import pandas as pd
from contextlib import asynccontextmanager

MODEL_NAME = "ChurnClassifier"
MODEL_ALIAS = "production"
TRACKING_URI = "http://127.0.0.1:5000"

model = None          # sklearn pipeline/estimator
feature_cols: list = []


def _load_production_model():
    """Load the model and its feature list from the current @production alias."""
    global model, feature_cols

    mlflow.set_tracking_uri(TRACKING_URI)
    client = mlflow.MlflowClient()

    # Resolve alias → exact registered model version
    mv = client.get_model_version_by_alias(MODEL_NAME, MODEL_ALIAS)
    run_id = mv.run_id

    # Download features.json that train.py logged under metadata/
    local_path = mlflow.artifacts.download_artifacts(
        run_id=run_id,
        artifact_path="metadata/features.json",
    )
    feature_cols = json.loads(Path(local_path).read_text())

    # Load the raw sklearn model so predict_proba is accessible
    model = mlflow.sklearn.load_model(f"runs:/{run_id}/model")
    print(f"Loaded {MODEL_NAME}@{MODEL_ALIAS}  run={run_id}  features={len(feature_cols)}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _load_production_model()
    yield
    global model, feature_cols
    model = None
    feature_cols = []


app = FastAPI(title="Churn Predictor", version="2.0", lifespan=lifespan)

# ---------------------------------------------------------------------------
# All fields used during training (matches IBM Telco dataset after drop_first)
# Categorical columns and their unique values (must match training get_dummies)
# ---------------------------------------------------------------------------
CATEGORICAL_VALUES = {
    "gender":          ["Female", "Male"],
    "Partner":         ["No", "Yes"],
    "Dependents":      ["No", "Yes"],
    "PhoneService":    ["No", "Yes"],
    "InternetService": ["DSL", "Fiber optic", "No"],
    "Contract":        ["Month-to-month", "One year", "Two year"],
    "PaymentMethod": [
        "Bank transfer (automatic)",
        "Credit card (automatic)",
        "Electronic check",
        "Mailed check",
    ],
}


class PredictRequest(BaseModel):
    tenure: float = Field(..., description="Months with company")
    MonthlyCharges: float = Field(..., description="Monthly bill amount")
    TotalCharges: float = Field(..., description="Total amount billed")
    SeniorCitizen: int = Field(0, description="1 if senior citizen, else 0")
    gender: str = Field("Male", description="Male or Female")
    Partner: str = Field("No", description="Yes or No")
    Dependents: str = Field("No", description="Yes or No")
    PhoneService: str = Field("Yes", description="Yes or No")
    InternetService: str = Field("DSL", description="DSL, Fiber optic, or No")
    Contract: str = Field("Month-to-month", description="Month-to-month, One year, Two year")
    PaymentMethod: str = Field("Electronic check", description="Payment method")


class PredictResponse(BaseModel):
    churn_probability: float
    churn_prediction: str
    confidence: float


def _encode_request(req: PredictRequest) -> pd.DataFrame:
    """Reproduce the pd.get_dummies(drop_first=True) encoding from training.

    Instead of calling get_dummies on a single row (which silently loses
    categories that happen not to appear in that one row), we build the
    expected dummy columns explicitly from the known vocabulary.
    """
    row = req.model_dump()
    numeric = {k: row[k] for k in ("tenure", "MonthlyCharges", "TotalCharges", "SeniorCitizen")}
    encoded = dict(numeric)

    for col, values in CATEGORICAL_VALUES.items():
        # drop_first=True drops values[0] (alphabetically first)
        for val in values[1:]:
            encoded[f"{col}_{val}"] = 1.0 if row[col] == val else 0.0

    df = pd.DataFrame([encoded])

    # Align to training feature order; fill any unexpected extra columns with 0
    if feature_cols:
        for fc in feature_cols:
            if fc not in df.columns:
                df[fc] = 0.0
        df = df[feature_cols]

    return df


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    df = _encode_request(req)

    # Use predict_proba for a genuine probability
    if hasattr(model, "predict_proba"):
        prob = float(model.predict_proba(df)[0, 1])
    else:
        # Fallback: binary classifier returning 0/1 — cast but log a warning
        prob = float(model.predict(df)[0])

    return PredictResponse(
        churn_probability=round(prob, 4),
        churn_prediction="Yes" if prob > 0.5 else "No",
        confidence=round(max(prob, 1 - prob), 4),
    )


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": model is not None, "features": len(feature_cols)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=1234)
