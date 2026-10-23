#!/usr/bin/env python3
"""
Field Calibration Aggregator
Reads atomic field survey JSONs and builds canonical master deliverables.
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
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp", ascending=True)

    # 1. Write full chronological audit log
    log_path = os.path.join(dist_dir, "survey_audit_log.csv")
    df.to_csv(log_path, index=False)

    # 2. Write deduplicated current status (keeping latest test per pivot)
    latest_df = df.groupby("pivotId").last().reset_index()
    schedule_path = os.path.join(dist_dir, "master_schedule.csv")
    latest_df.to_csv(schedule_path, index=False)

    print(f"Successfully generated master schedule for {len(latest_df)} unique pivots.")


if __name__ == "__main__":
    main()
