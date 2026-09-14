"""FastAPI serving wrapper for the production churn model."""

import sys
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    mlflow.set_tracking_uri(TRACKING_URI)
    model = mlflow.pyfunc.load_model(f"models:/{MODEL_NAME}@{MODEL_ALIAS}")
    print(f"Loaded model {MODEL_NAME}@{MODEL_ALIAS}")
    yield
    model = None


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

    # Align with training features — fill missing cols with 0
    prediction = model.predict(df)
    proba = model.predict(df, params={"return_proba": True}) if hasattr(model, "predict") else None

    churn_prob = float(prediction[0]) if not hasattr(model, "predict_proba") else float(prediction[0])
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
