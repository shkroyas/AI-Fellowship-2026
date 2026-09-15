r"""Read-only application probes; writes temporary reports only under /tmp.

Run using the corresponding track's installed Python:
  python probe.py a /absolute/path/to/Task\ A /absolute/path/to/model/artifacts
  python probe.py b /absolute/path/to/Task\ B
No live LLM calls are made. Output intentionally demonstrates defects.
"""

import json
import sys
import tempfile
from pathlib import Path

mode, project = sys.argv[1], Path(sys.argv[2]).resolve()
sys.path.insert(0, str(project))
sys.path.insert(0, str(project / "src"))

if mode == "a":
    import mlflow
    from src.track_a import serve
    from src.track_a.data_prep import prepare_pipeline
    from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

    artifact = str(Path(sys.argv[3]).resolve())
    serve.model = mlflow.pyfunc.load_model(artifact)
    data = prepare_pipeline()
    print("Training feature count:", len(data["feature_cols"]))
    try:
        print("Prediction response:", serve.predict(serve.PredictRequest(
            tenure=12, MonthlyCharges=70.5, TotalCharges=846
        )))
    except Exception as exc:
        print("Prediction handler exception:", type(exc).__name__, str(exc))
    model = mlflow.sklearn.load_model(artifact)
    x, y = data["X_test"], data["y_test"]
    print("Saved model metrics:", json.dumps({
        "accuracy": accuracy_score(y, model.predict(x)),
        "f1": f1_score(y, model.predict(x)),
        "roc_auc": roc_auc_score(y, model.predict_proba(x)[:, 1]),
    }))
elif mode == "b":
    import pandas as pd
    import importlib.util
    import run_experiment as runner

    print("Environment example exists:", (project / ".env.example").exists())
    print("ddgs installed:", importlib.util.find_spec("ddgs") is not None)
    with tempfile.TemporaryDirectory(prefix="w17-regression-probe-") as directory:
        output = Path(directory)
        rows = [{"query": q, "response": "This is deliberately wrong. 15% of 340 is 999."}
                for q in runner.TEST_QUERIES]
        result = runner.run_evidently_regression("wrong_answers", rows, output)
        print("Deliberately wrong responses scored:", json.dumps(result))
        judge = runner.EvidentlyJudge(reports_dir=output)
        dataset = runner.build_dataset(pd.DataFrame([{
            "query": "q", "new_response": "wrong", "target_response": "right",
            "correct": "incorrect",
        }]), ["query", "new_response", "target_response"], ["correct"])
        print("Actual Evidently snapshot:", json.dumps(judge.run_text_eval_report(dataset).dict()))
else:
    raise SystemExit("Mode must be a or b")
