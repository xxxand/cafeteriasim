from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SimulationConfig:
    window_count: int = 4
    table_count: int = 30
    duration_minutes: int = 120
    arrival_rate: float = 1.6
    service_min: int = 2
    service_max: int = 5
    dining_min: int = 10
    dining_max: int = 20
    snapshot_interval: int = 1
    random_seed: int = 42

    @classmethod
    def from_payload(cls, payload: dict) -> "SimulationConfig":
        return cls(
            window_count=max(1, int(payload.get("window_count", cls.window_count))),
            table_count=max(1, int(payload.get("table_count", cls.table_count))),
            duration_minutes=max(10, int(payload.get("duration_minutes", cls.duration_minutes))),
            arrival_rate=max(0.1, float(payload.get("arrival_rate", cls.arrival_rate))),
            service_min=max(1, int(payload.get("service_min", cls.service_min))),
            service_max=max(1, int(payload.get("service_max", cls.service_max))),
            dining_min=max(1, int(payload.get("dining_min", cls.dining_min))),
            dining_max=max(1, int(payload.get("dining_max", cls.dining_max))),
            snapshot_interval=max(1, int(payload.get("snapshot_interval", cls.snapshot_interval))),
            random_seed=int(payload.get("random_seed", cls.random_seed)),
        )
