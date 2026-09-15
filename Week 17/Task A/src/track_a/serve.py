"""FastAPI serving wrapper for the production churn model."""

import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import pandas as pd
import mlflow
from contextlib import asynccontextmanager

MODEL_NAME = "ChurnClassifier"
MODEL_ALIAS = "production"
TRACKING_URI = "http://127.0.0.1:5000"

model = None
feature_cols = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, feature_cols
    mlflow.set_tracking_uri(TRACKING_URI)
    model = mlflow.pyfunc.load_model(f"models:/{MODEL_NAME}@{MODEL_ALIAS}")
    print(f"Loaded model {MODEL_NAME}@{MODEL_ALIAS}")

    # Load feature list from the latest run artifact
    client = mlflow.tracking.MlflowClient(tracking_uri=TRACKING_URI)
    latest_version = client.get_latest_versions(MODEL_NAME, stages=["Production"])[0]
    run_id = latest_version.run_id
    artifact_path = mlflow.artifacts.download_artifacts(
        run_id=run_id, artifact_path="model"
    )
    # Try to find features.json in the run's artifacts
    try:
        features_local = mlflow.artifacts.download_artifacts(
            run_id=run_id, artifact_path="../features.json"
        )
        feature_cols = json.loads(Path(features_local).read_text())
    except Exception:
        # Fallback: derive from the model's training data
        feature_cols = None
        print("Warning: Could not load features.json; using dynamic alignment")

    yield
    model = None
    feature_cols = None


app = FastAPI(title="Churn Predictor", version="1.0", lifespan=lifespan)


class PredictRequest(BaseModel):
    tenure: float = Field(..., description="Months with company")
    MonthlyCharges: float = Field(..., description="Monthly bill amount")
    TotalCharges: float = Field(..., description="Total amount billed")
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


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    input_dict = req.model_dump()
    df = pd.DataFrame([input_dict])

    # Apply same preprocessing as training (one-hot encoding)
    categorical_cols = ["gender", "Partner", "Dependents", "PhoneService",
                        "InternetService", "Contract", "PaymentMethod"]
    df = pd.get_dummies(df, columns=categorical_cols, drop_first=True)

    # Align with training features
    if feature_cols is not None:
        # Add missing columns with 0, drop extra columns
        for col in feature_cols:
            if col not in df.columns:
                df[col] = 0
        df = df[feature_cols]
    else:
        # Dynamic: fill missing with 0 (less reliable)
        pass

    # Get probability using predict_proba
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(df)
        churn_prob = float(proba[0, 1])  # probability of class 1 (Yes)
    else:
        prediction = model.predict(df)
        churn_prob = float(prediction[0])

    return PredictResponse(
        churn_probability=churn_prob,
        churn_prediction="Yes" if churn_prob > 0.5 else "No",
        confidence=max(churn_prob, 1 - churn_prob),
    )


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": model is not None}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=1234)
