"""Arrow schemas retained even for empty tables. Schema version 1."""

import pyarrow as pa

SCHEMAS = {
    "requests": pa.schema(
        [
            (k, t)
            for k, t in [
                ("request_id", pa.string()),
                ("session", pa.int64()),
                ("arrival", pa.float64()),
                ("status", pa.string()),
                ("admitted", pa.bool_()),
                ("deferrals", pa.int64()),
                ("end", pa.float64()),
                ("fidelity", pa.float64()),
                ("queue_wait", pa.float64()),
                ("service_time", pa.float64()),
                ("sojourn", pa.float64()),
                ("purification_rounds", pa.int64()),
                ("attempted_deliveries", pa.int64()),
                ("duplicates", pa.int64()),
                ("below_threshold", pa.int64()),
                ("reason", pa.string()),
                ("path", pa.list_(pa.int64())),
            ]
        ]
    ),
    "attempts": pa.schema(
        [
            (k, t)
            for k, t in [
                ("attempt_id", pa.string()),
                ("parent_id", pa.string()),
                ("path", pa.list_(pa.int64())),
                ("status", pa.string()),
                ("start", pa.float64()),
                ("end", pa.float64()),
                ("queue_wait", pa.float64()),
                ("service_time", pa.float64()),
                ("fidelity", pa.float64()),
                ("purification_rounds", pa.int64()),
                ("reason", pa.string()),
            ]
        ]
    ),
    "events": pa.schema(
        [
            (k, t)
            for k, t in [
                ("schema_version", pa.int64()),
                ("time", pa.float64()),
                ("kind", pa.string()),
                ("request_id", pa.string()),
                ("attempt_id", pa.string()),
                ("node", pa.int64()),
                ("value", pa.float64()),
                ("detail", pa.string()),
            ]
        ]
    ),
    "path_metrics": pa.schema(
        [
            (k, t)
            for k, t in [
                ("schema_version", pa.int64()),
                ("time", pa.float64()),
                ("request_id", pa.string()),
                ("retry", pa.int64()),
                ("path", pa.list_(pa.int64())),
                ("paper_fidelity", pa.float64()),
                ("fidelity", pa.float64()),
                ("rounds", pa.int64()),
                ("delay", pa.float64()),
                ("mu_path", pa.float64()),
                ("rho_path", pa.float64()),
                ("aggregate_ok", pa.bool_()),
                ("node_ok", pa.bool_()),
                ("memory_mean_ok", pa.bool_()),
                ("fidelity_ok", pa.bool_()),
                ("eligible", pa.bool_()),
                ("score", pa.float64()),
                ("probability", pa.float64()),
            ]
        ]
    ),
}
