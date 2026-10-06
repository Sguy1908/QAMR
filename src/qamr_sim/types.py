from dataclasses import dataclass, field
from typing import Any, Literal

Status = Literal["pending", "active", "completed", "rejected", "expired", "failed", "unfinished"]
TERMINAL = {"completed", "rejected", "expired", "failed", "unfinished"}


@dataclass
class Request:
    request_id: str
    session: int
    arrival: float
    status: Status = "pending"
    admitted: bool = False
    deferrals: int = 0
    end: float | None = None
    fidelity: float | None = None
    queue_wait: float = 0
    service_time: float = 0
    sojourn: float = 0
    purification_rounds: int = 0
    attempted_deliveries: int = 0
    duplicates: int = 0
    below_threshold: int = 0
    reason: str = ""
    path: list[int] = field(default_factory=list)


@dataclass
class Attempt:
    attempt_id: str
    parent_id: str
    path: tuple[int, ...]
    status: str = "created"
    start: float | None = None
    end: float | None = None
    queue_wait: float = 0
    service_time: float = 0
    fidelity: float | None = None
    purification_rounds: int = 0
    reason: str = ""


@dataclass
class Result:
    schema_version: int
    config: dict[str, Any]
    topology: dict[str, Any]
    requests: list[dict[str, Any]]
    attempts: list[dict[str, Any]]
    events: list[dict[str, Any]]
    node_metrics: list[dict[str, Any]]
    path_metrics: list[dict[str, Any]]
    summary: dict[str, Any]
