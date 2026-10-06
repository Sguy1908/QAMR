import json
import math
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import yaml

from .schemas import SCHEMAS


def clean(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    return value


def write_json(path, value):
    Path(path).write_text(json.dumps(clean(value), indent=2, allow_nan=False) + "\n")


def export(result, directory, manifest):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "resolved_config.yaml").write_text(yaml.safe_dump(result.config, sort_keys=True))
    write_json(directory / "topology.json", result.topology)
    write_json(directory / "manifest.json", manifest)
    for name in ("requests", "attempts", "events", "node_metrics", "path_metrics"):
        rows = getattr(result, name)
        table = pa.Table.from_pylist(rows, schema=SCHEMAS.get(name))
        pq.write_table(table, directory / f"{name}.parquet")
    write_json(directory / "summary.json", result.summary)
    return directory


def load_run(directory):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text())
    if manifest["schema_version"] != 1:
        raise ValueError("Unsupported run schema")
    return dict(
        directory=directory,
        manifest=manifest,
        config=yaml.safe_load((directory / "resolved_config.yaml").read_text()),
        topology=json.loads((directory / "topology.json").read_text()),
        summary=json.loads((directory / "summary.json").read_text()),
        **{
            name: pq.read_table(directory / f"{name}.parquet").to_pandas()
            for name in ("requests", "attempts", "events", "node_metrics", "path_metrics")
        },
    )
