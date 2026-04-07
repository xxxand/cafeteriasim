from __future__ import annotations

# 配置模块：
# 用于统一管理一轮仿真所需的所有输入参数，并提供从前端请求体到配置对象的转换逻辑。

from dataclasses import dataclass


@dataclass(slots=True)
class SimulationConfig:
    # 打饭窗口数量。
    window_count: int = 4
    # 餐桌数量。
    table_count: int = 30
    # 仿真总时长，单位为分钟。
    duration_minutes: int = 120
    # 学生到达速率，数值越大表示单位时间到达学生越多。
    arrival_rate: float = 1.6
    # 打饭服务时间上下界。
    service_min: int = 2
    service_max: int = 5
    # 就餐时间上下界。
    dining_min: int = 10
    dining_max: int = 20
    # 采样间隔，用于记录时间线快照。
    snapshot_interval: int = 1
    # 随机种子，便于复现实验结果。
    random_seed: int = 42

    @classmethod
    def from_payload(cls, payload: dict) -> "SimulationConfig":
        # 将前端传来的表单数据转成标准配置对象。
        # 同时使用 max(...) 做边界保护，避免出现非法参数。
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
