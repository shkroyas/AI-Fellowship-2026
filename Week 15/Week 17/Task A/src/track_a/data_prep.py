"""Data preparation for Telco Customer Churn prediction."""

import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler


RAW_PATH = Path(__file__).resolve().parents[2] / "data" / "raw"
PROCESSED_PATH = Path(__file__).resolve().parents[2] / "data"


CATEGORICAL_COLS = [
    "gender", "Partner", "Dependents", "PhoneService", "MultipleLines",
    "InternetService", "OnlineSecurity", "OnlineBackup", "DeviceProtection",
    "TechSupport", "StreamingTV", "StreamingMovies", "Contract",
    "PaperlessBilling", "PaymentMethod",
]


def load_raw(filename: str = "WA_Fn-UseC_-Telco-Customer-Churn.csv") -> pd.DataFrame:
    df = pd.read_csv(RAW_PATH / filename)
    return df


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # TotalCharges has blank strings for tenure=0 customers
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce").fillna(0)

    # Binary target
    df["Churn"] = df["Churn"].map({"Yes": 1, "No": 0})

    # Drop customerID
    df = df.drop(columns=["customerID"])

    # One-hot encode categoricals
    df = pd.get_dummies(df, columns=CATEGORICAL_COLS, drop_first=True)

    return df


def split_data(df: pd.DataFrame, target: str = "Churn", test_size: float = 0.2,
               random_state: int = 42):
    X = df.drop(columns=[target])
    y = df[target]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )
    return X_train, X_test, y_train, y_test


def get_feature_cols(X_train: pd.DataFrame) -> list:
    return list(X_train.columns)


def scale_features(X_train: pd.DataFrame, X_test: pd.DataFrame):
    scaler = StandardScaler()
    X_train_scaled = pd.DataFrame(
        scaler.fit_transform(X_train), columns=X_train.columns, index=X_train.index
    )
    X_test_scaled = pd.DataFrame(
        scaler.transform(X_test), columns=X_test.columns, index=X_test.index
    )
    return X_train_scaled, X_test_scaled, scaler


def prepare_pipeline():
    df = load_raw()
    df = preprocess(df)
    X_train, X_test, y_train, y_test = split_data(df)
    feature_cols = get_feature_cols(X_train)
    X_train_scaled, X_test_scaled, scaler = scale_features(X_train, X_test)
    return {
        "df": df,
        "X_train": X_train, "X_test": X_test,
        "X_train_scaled": X_train_scaled, "X_test_scaled": X_test_scaled,
        "y_train": y_train, "y_test": y_test,
        "feature_cols": feature_cols,
        "scaler": scaler,
    }


if __name__ == "__main__":
    data = prepare_pipeline()
    print(f"Train shape: {data['X_train'].shape}")
    print(f"Test shape: {data['X_test'].shape}")
    print(f"Features: {len(data['feature_cols'])}")
    print(f"Churn rate (train): {data['y_train'].mean():.3f}")
