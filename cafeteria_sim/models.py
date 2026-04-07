from __future__ import annotations

# 数据模型模块：
# 用 dataclass 描述学生、窗口、餐桌以及最终结果结构，便于后端统一维护状态。

from dataclasses import dataclass, field


@dataclass(slots=True)
class Student:
    # 学生唯一编号。
    student_id: int
    # 到达食堂的时间点。
    arrival_time: float
    # 各阶段关键时间戳。
    queue_enter_time: float | None = None
    service_start_time: float | None = None
    service_end_time: float | None = None
    dining_start_time: float | None = None
    dining_end_time: float | None = None
    # 当前状态，例如 arrived、queued、serving、dining、completed。
    status: str = "created"
    # 学生对应的窗口编号和餐桌编号。
    window_id: int | None = None
    table_id: int | None = None


@dataclass(slots=True)
class Window:
    # 窗口编号。
    window_id: int
    # 当前排队长度和剩余服务时间。
    current_queue_length: int = 0
    remaining_service_time: float = 0.0


@dataclass(slots=True)
class Table:
    # 餐桌编号。
    table_id: int
    # 是否被占用、当前学生编号、剩余就餐时间。
    occupied: bool = False
    current_student: int | None = None
    remaining_dining_time: float = 0.0


@dataclass(slots=True)
class SimulationResult:
    # timeline 保存全过程快照。
    timeline: list[dict]
    # summary 保存统计汇总。
    summary: dict
    # students 保存学生明细。
    students: list[dict] = field(default_factory=list)
