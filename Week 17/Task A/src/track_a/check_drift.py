"""Drift task entrypoint, isolated from Airflow dependencies."""
import argparse
import json
from pathlib import Path
import pandas as pd
from src.track_a.utils.evidently_reporter import EvidentlyReporter, split_reference_current, inject_drift


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--inject-drift', action='store_true')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    df = pd.read_csv(root / 'data/raw/Telco-Customer-Churn.csv')
    df['TotalCharges'] = pd.to_numeric(df.TotalCharges, errors='coerce').fillna(0)
    df['Churn'] = df.Churn.map({'Yes': 1, 'No': 0})
    df = df.drop(columns='customerID')
    reference, current = split_reference_current(df)
    if args.inject_drift:
        current = inject_drift(current)
    output = Path(args.output)
    results = EvidentlyReporter(output).generate_full_report(reference, current)
    shift = results['custom_metrics']['monthly_charges_shift']['pct_shift']
    verdict = dict(drift_detected=abs(shift) >= 10, pct_shift=shift,
                   injected_demo=args.inject_drift, threshold_pct=10)
    (output / 'drift_verdict.json').write_text(json.dumps(verdict, indent=2))
    print(json.dumps(verdict))

if __name__ == '__main__':
    main()
