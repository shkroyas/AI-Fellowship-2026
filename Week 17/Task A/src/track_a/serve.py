"""Serve the exact registered raw-input sklearn pipeline and real probabilities."""
import os
from pathlib import Path
from contextlib import asynccontextmanager
import mlflow
import mlflow.sklearn
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

TRACKING_URI = os.getenv('MLFLOW_TRACKING_URI', f"sqlite:///{Path(__file__).resolve().parents[2] / 'data/mlflow.db'}")
model = None
model_version = None


def _load_production_model():
    global model, model_version
    mlflow.set_tracking_uri(TRACKING_URI)
    model_version = mlflow.MlflowClient().get_model_version_by_alias('ChurnClassifier', 'production')
    model = mlflow.sklearn.load_model(f'models:/ChurnClassifier/{model_version.version}')
    if not hasattr(model, 'predict_proba'):
        raise RuntimeError('Production model must expose predict_proba')


@asynccontextmanager
async def lifespan(app):
    global model
    _load_production_model()
    yield
    model = None


app = FastAPI(title='Churn Predictor', version='2.0', lifespan=lifespan)


class PredictRequest(BaseModel):
    tenure: float = Field(ge=0)
    MonthlyCharges: float = Field(ge=0)
    TotalCharges: float = Field(ge=0)
    SeniorCitizen: int = Field(default=0, ge=0, le=1)
    gender: str = 'Male'
    Partner: str = 'No'
    Dependents: str = 'No'
    PhoneService: str = 'Yes'
    MultipleLines: str = 'No'
    InternetService: str = 'DSL'
    OnlineSecurity: str = 'No'
    OnlineBackup: str = 'No'
    DeviceProtection: str = 'No'
    TechSupport: str = 'No'
    StreamingTV: str = 'No'
    StreamingMovies: str = 'No'
    Contract: str = 'Month-to-month'
    PaperlessBilling: str = 'Yes'
    PaymentMethod: str = 'Electronic check'


@app.post('/predict')
def predict(req: PredictRequest):
    if model is None:
        raise HTTPException(503, 'Model not loaded')
    probability = float(model.predict_proba(pd.DataFrame([req.model_dump()]))[0, 1])
    return {'churn_probability': probability, 'churn_prediction': 'Yes' if probability >= .5 else 'No',
            'confidence': max(probability, 1-probability)}


@app.get('/health')
def health():
    return {'status': 'ok', 'model_loaded': model is not None,
            'model_version': model_version.version if model_version else None}
