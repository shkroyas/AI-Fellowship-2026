"""Evidently LLM judge for regression testing in Track B — evidently 0.7+ API."""

import pandas as pd
import numpy as np
from evidently import DataDefinition, Dataset, Report
from evidently.presets import TextEvals
from evidently.tests import eq
from pathlib import Path
from typing import Optional


REPORTS_DIR = Path(__file__).resolve().parents[2] / "reports"


def build_dataset(df: pd.DataFrame, text_columns: list, categorical_columns: list = None):
    data_def = DataDefinition(
        text_columns=text_columns,
        categorical_columns=categorical_columns or [],
    )
    return Dataset.from_pandas(df, data_definition=data_def)


class EvidentlyJudge:
    def __init__(self, reports_dir: Path = None):
        self.reports_dir = reports_dir or REPORTS_DIR
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def run_text_eval_report(self, eval_dataset: Dataset):
        """Run TextEvals preset — the only supported approach in evidently 0.7+."""
        report = Report(metrics=[TextEvals()])
        snapshot = report.run(current_data=eval_dataset)
        return snapshot

    def run_correctness_report(self, eval_df: pd.DataFrame,
                                response_col: str = "new_response",
                                target_col: str = "target_response"):
        """Run a correctness check: substring matching against target keywords.

        This provides a deterministic, reproducible correctness metric that
        doesn't rely on LLM calls (which are unavailable in this environment).
        """
        correct_count = 0
        details = []
        for _, row in eval_df.iterrows():
            resp = str(row[response_col]).lower()
            target = str(row[target_col]).lower()
            # Check if key content from target appears in response
            target_words = [w for w in target.split() if len(w) > 2]
            matches = sum(1 for w in target_words if w in resp)
            is_correct = matches >= min(3, len(target_words))
            if is_correct:
                correct_count += 1
            details.append({
                "query": row.get("query", ""),
                "is_correct": is_correct,
                "matches": matches,
                "total_target_words": len(target_words),
            })

        pct = correct_count / max(len(eval_df), 1)
        return {
            "correctness_pct": round(pct, 3),
            "correct": correct_count,
            "total": len(eval_df),
            "details": details,
        }


def create_golden_set() -> pd.DataFrame:
    return pd.DataFrame({
        "query": [
            "What is RAG?",
            "What is the current date?",
            "Calculate 15% of 340.",
            "What are Python best practices?",
            "Compare RAG vs fine-tuning.",
        ],
        "target_response": [
            "RAG (Retrieval-Augmented Generation) is a method that combines retrieval from an external knowledge base with LLM generation to produce more accurate, grounded responses.",
            "The current date can be determined using the get_current_datetime tool.",
            "15% of 340 is 51.",
            "Python best practices include: use virtual environments, follow PEP 8, write docstrings, use type hints, and test your code.",
            "RAG is better for up-to-date knowledge without retraining; fine-tuning is better for domain-specific behavior and style.",
        ],
    })
