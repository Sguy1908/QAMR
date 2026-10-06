"""Versioned SI-unit configuration. Defaults not in Table II are assumptions A01-A24."""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Failure(BaseModel):
    model_config = ConfigDict(extra="forbid")
    time: float = Field(ge=0)
    duration: float = Field(gt=0)
    node: int | None = Field(default=None, ge=0)
    edge: tuple[int, int] | None = None

    @model_validator(mode="after")
    def target(self):
        if (self.node is None) == (self.edge is None):
            raise ValueError("Specify exactly one failure target")
        return self


class Config(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True, allow_inf_nan=False)
    schema_version: Literal[1] = 1
    profile: str = "paper_reconstruction"
    seed: int = Field(default=2026, ge=0)
    topology_seed: int = Field(default=17, ge=0)
    nodes: int = Field(default=60, ge=2)
    target_mean_degree: float = Field(default=4, gt=0)
    radius: float | None = Field(default=None, gt=0)
    memory_capacity: int = Field(default=8, ge=1)
    coherence_central_seconds: float = Field(default=50, gt=0)
    coherence_spread_seconds: float = Field(default=10, ge=0)
    coherence_distribution: Literal["bounded_uniform", "positive_truncated_normal", "fixed"] = (
        "bounded_uniform"
    )
    swap_time_seconds: float = Field(default=0.05, gt=0)
    purification_time_seconds: float = Field(default=0.02, gt=0)
    swap_success_probability: float = Field(default=0.95, gt=0, le=1)
    hardware_efficiency: float = Field(default=1, gt=0, le=1)
    link_success_probability: float = Field(default=1, ge=0, le=1)
    initial_fidelity: float = Field(default=0.98, gt=0.5, le=1)
    purification_efficiency: float = Field(default=0.6, gt=0)
    fidelity_threshold: float = Field(default=0.85, gt=0.5, lt=1)
    routing_fidelity_model: Literal["paper_exponential", "paper_half_floor"] = "paper_exponential"
    event_fidelity_model: Literal["paper_exponential", "paper_half_floor"] = "paper_exponential"
    proxy_swap_factor: bool = True
    arrival_rate: float = Field(default=0.5, ge=0)
    traffic_convention: Literal["total", "per_session"] = "total"
    session_count: int = Field(default=2, ge=1)
    sessions: list[tuple[int, int]] | None = None
    simulation_duration_seconds: float = Field(default=2000, gt=0)
    warmup_seconds: float = Field(default=0, ge=0)
    max_paths: int = Field(default=2, ge=1, le=8)
    path_kind: Literal["vertex_disjoint", "shortest_overlapping"] = "vertex_disjoint"
    candidate_cap: int = Field(default=8, ge=1, le=64)
    policy: Literal[
        "qamr",
        "single_path",
        "queue_aware_single",
        "no_queue",
        "no_purification",
        "congestion_penalty",
    ] = "qamr"
    dispatch: Literal["split", "replicate", "round_robin"] = "split"
    path_service: Literal["bottleneck", "serial"] = "bottleneck"
    load_estimator: Literal["steady_split", "rolling", "literal_full"] = "steady_split"
    rolling_window_seconds: float = Field(default=10, gt=0)
    score_weights: tuple[float, float, float] = (0.4, 0.4, 0.2)
    theta: float = Field(default=0.9, gt=0, lt=1)
    admission: Literal["aggregate_and_node", "aggregate_only"] = "aggregate_and_node"
    purification_round_cap: int = Field(default=4, ge=0, le=20)
    pending_capacity: int = Field(default=1000, ge=1)
    max_deferrals: int = Field(default=3, ge=0)
    retry_seconds: float = Field(default=0.1, gt=0)
    request_deadline_seconds: float = Field(default=60, gt=0)
    telemetry_interval_seconds: float = Field(default=1, gt=0)
    control_latency_seconds: float = Field(default=0, ge=0)
    failures: list[Failure] = []
    trace: bool = True

    @model_validator(mode="after")
    def consistent(self):
        if self.warmup_seconds >= self.simulation_duration_seconds:
            raise ValueError("Warm-up must be shorter than total duration")
        if any(w < 0 for w in self.score_weights) or abs(sum(self.score_weights) - 1) > 1e-9:
            raise ValueError("Score weights must be nonnegative and sum to 1")
        if (
            self.coherence_distribution == "bounded_uniform"
            and self.coherence_spread_seconds >= self.coherence_central_seconds
        ):
            raise ValueError("Uniform lifetime must be strictly positive")
        if self.sessions and any(
            s == d or min(s, d) < 0 or max(s, d) >= self.nodes for s, d in self.sessions
        ):
            raise ValueError("Session endpoints must be distinct valid nodes")
        if self.sessions == []:
            raise ValueError("Use arrival_rate=0 for no traffic")
        for f in self.failures:
            ids = [f.node] if f.node is not None else list(f.edge)
            if min(ids) < 0 or max(ids) >= self.nodes:
                raise ValueError("Invalid failure target")
        return self

    @property
    def mu(self):
        return (
            self.swap_success_probability
            * self.hardware_efficiency
            / (self.swap_time_seconds + self.purification_time_seconds)
        )

    @property
    def measurement_seconds(self):
        return self.simulation_duration_seconds - self.warmup_seconds


def load_config(path: str | Path) -> Config:
    return Config.model_validate(yaml.safe_load(Path(path).read_text()) or {})
