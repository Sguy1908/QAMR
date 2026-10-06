"""Audit exported scientific invariants independently of engine object state."""

import argparse
import json
from pathlib import Path

import pandas as pd


def audit(root):
    failures = []
    count = 0
    for summary_file in Path(root).rglob("summary.json"):
        directory = summary_file.parent
        s = json.loads(summary_file.read_text())
        requests = pd.read_parquet(directory / "requests.parquet")
        attempts = pd.read_parquet(directory / "attempts.parquet")
        nodes = pd.read_parquet(directory / "node_metrics.parquet")
        import yaml

        c = yaml.safe_load((directory / "resolved_config.yaml").read_text())
        try:
            assert len(requests) == s["offered"]
            assert requests.request_id.is_unique
            assert requests.status.value_counts().to_dict() == s["terminal_counts"]
            assert requests.status.isin(
                ["completed", "rejected", "failed", "expired", "unfinished"]
            ).all()
            assert s["resources_after_cleanup"] == 0
            assert (nodes.peak_qubits <= c["memory_capacity"]).all()
            delivered = requests[
                (requests.status == "completed") & (requests.end >= c["warmup_seconds"])
            ]
            assert len(delivered) == s["delivered_measurement"]
            assert (delivered.fidelity >= c["fidelity_threshold"]).all()
            if s["measurement_seconds"]:
                assert abs(s["throughput"] - len(delivered) / s["measurement_seconds"]) < 1e-12
            assert attempts.attempt_id.is_unique
            assert set(attempts.parent_id) <= set(requests.request_id)
            assert not attempts.status.isin(["created", "active"]).any()
        except AssertionError:
            failures.append(str(directory))
        count += 1
    return count, failures


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", nargs="?", default="results")
    args = parser.parse_args()
    count, failures = audit(args.directory)
    print(json.dumps(dict(runs_audited=count, failures=failures), indent=2))
    raise SystemExit(bool(failures))
