from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Student:
    student_id: int
    arrival_time: float
    queue_enter_time: float | None = None
    service_start_time: float | None = None
    service_end_time: float | None = None
    dining_start_time: float | None = None
    dining_end_time: float | None = None
    status: str = "created"
    window_id: int | None = None
    table_id: int | None = None


@dataclass(slots=True)
class Window:
    window_id: int
    current_queue_length: int = 0
    remaining_service_time: float = 0.0


@dataclass(slots=True)
class Table:
    table_id: int
    occupied: bool = False
    current_student: int | None = None
    remaining_dining_time: float = 0.0


@dataclass(slots=True)
class SimulationResult:
    timeline: list[dict]
    summary: dict
    students: list[dict] = field(default_factory=list)
