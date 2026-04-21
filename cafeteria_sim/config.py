# 延迟注解求值，将类型注解以字符串形式存储，而不是在定义时立即求值。注解会被当作字符串存储，等到真正需要时才解析。
# 防止类 A 引用了类 B，而类 B 又引用了类 A（循环引用），报错。
from __future__ import annotations

# 配置模块：
# 用于统一管理一轮仿真所需的所有输入参数，并提供从前端请求体到配置对象的转换逻辑。
# 初始化，用于基础配置。以下全部配置可以调节。

# 导入dataclass。
from dataclasses import dataclass

# 不再拥有 __dict__，而是有一个固定大小的 __slots__ 元组，属性直接存储在预分配的内存槽位中。禁止动态添加未声明的属性，比如a=10不行。
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

    @classmethod # 声明这是一个类方法，而不是实例方法。
    def from_payload(cls, payload: dict) -> "SimulationConfig": # 提供一个从字典构造 SimulationConfig 对象的便捷接口
        # 用字符串是因为类还没定义完（配合前面的 from __future__ import annotations）

        # 将前端传来的表单数据转成标准配置对象。
        # 同时使用 max(...) 做边界保护，避免出现非法参数。
        #由于 @classmethod ，cls 自动传入，指向 SimulationConfig 类本身，相当于 SimulationConfig(...)

        # 安全：用 max() 防止非法参数破坏仿真
        # 容错：用 .get() 提供默认值，字段缺失不崩溃
        # 类型安全：强制转换 int/float，确保后续计算正确
        return cls(
            # 从 payload 字典中取键 "window_count" 的值；若不存在，则使用类属性 cls.window_count 作为默认值。
            # int() 将取出的值强制转换为整数。
            # max() 确保最终值不小于 1。若转换后数值小于 1，则自动替换为 1。
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
