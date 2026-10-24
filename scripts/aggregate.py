#!/usr/bin/env python3
"""
Field Calibration Aggregator
Reads atomic field survey JSONs and builds canonical master deliverables
in both CSV and JSON formats, standardizing all timestamps to UTC.
"""

import glob
import json
import os
import sys
import pandas as pd


def main():
    survey_dir = os.path.join("data", "surveys")
    dist_dir = os.path.join("data", "dist")
    os.makedirs(dist_dir, exist_ok=True)

    json_files = glob.glob(os.path.join(survey_dir, "*.json"))
    print(f"Found {len(json_files)} survey records in {survey_dir}...")

    if not json_files:
        print("No survey records present to compile.")
        sys.exit(0)

    records = []
    for fp in json_files:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                records.append(json.load(f))
        except Exception as err:
            print(f"Warning: Skipping corrupted record {fp}: {err}")

    if not records:
        print("No valid survey records extracted.")
        sys.exit(0)

    df = pd.DataFrame(records)

    # Standardize all timestamps to UTC so naive and aware timestamps sort cleanly
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="mixed", errors="coerce", utc=True)
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp", ascending=True)

    # 1. Full Chronological Audit Logs (Both CSV and JSON)
    log_csv = os.path.join(dist_dir, "survey_audit_log.csv")
    log_json = os.path.join(dist_dir, "survey_audit_log.json")
    df.to_csv(log_csv, index=False)
    df.to_json(log_json, orient="records", indent=2, date_format="iso")

    # 2. Deduplicated Current Status (keeping latest test per pivot)
    latest_df = df.groupby("pivotId").last().reset_index()
    schedule_csv = os.path.join(dist_dir, "master_schedule.csv")
    schedule_json = os.path.join(dist_dir, "master_schedule.json")
    latest_df.to_csv(schedule_csv, index=False)
    latest_df.to_json(schedule_json, orient="records", indent=2, date_format="iso")

    print(f"Successfully generated master deliverables for {len(latest_df)} unique pivots.")


if __name__ == "__main__":
    main()
