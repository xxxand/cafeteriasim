from __future__ import annotations

# 仿真引擎模块：
# 负责完成学生到达、窗口排队、打饭服务、餐桌占用、就餐离开以及数据统计全过程。

import random
from dataclasses import asdict
from statistics import mean

import pandas as pd
import simpy

from cafeteria_sim.config import SimulationConfig
from cafeteria_sim.models import SimulationResult, Student, Table, Window


class CafeteriaSimulation:
    def __init__(self, config: SimulationConfig):
        # 保存配置对象，供整个仿真过程读取。
        self.config = config
        # 独立随机数生成器，便于通过随机种子复现实验。
        self.random = random.Random(config.random_seed)
        # SimPy 环境对象，负责管理仿真时间推进。
        self.env = simpy.Environment()

        # 初始化所有窗口与对应的服务资源。
        self.windows = [Window(window_id=i + 1) for i in range(config.window_count)]
        self.window_resources = [simpy.Resource(self.env, capacity=1) for _ in range(config.window_count)]

        # 初始化所有餐桌，并使用 Container 管理剩余空桌数量。
        self.tables = [Table(table_id=i + 1) for i in range(config.table_count)]
        self.table_resource = simpy.Container(self.env, init=config.table_count, capacity=config.table_count)

        # 运行期状态数据。
        self.students: list[Student] = []
        self.completed_students = 0
        self.timeline: list[dict] = []
        self.student_seq = 0

    def choose_window(self) -> int:
        # 采用最短队列策略，为新到达学生选择负载最小的窗口。
        lengths = [resource.count + len(resource.queue) for resource in self.window_resources]
        return min(range(len(lengths)), key=lambda idx: (lengths[idx], idx))

    def occupy_table(self, student_id: int, dining_time: float) -> int:
        # 找到第一张空闲桌并标记占用，返回桌号。
        for table in self.tables:
            if not table.occupied:
                table.occupied = True
                table.current_student = student_id
                table.remaining_dining_time = dining_time
                return table.table_id
        return -1

    def release_table(self, table_id: int) -> None:
        # 学生离开后释放餐桌状态。
        for table in self.tables:
            if table.table_id == table_id:
                table.occupied = False
                table.current_student = None
                table.remaining_dining_time = 0.0
                return

    def sample_service_time(self) -> int:
        # 随机生成一次打饭服务时长。
        return self.random.randint(self.config.service_min, self.config.service_max)

    def sample_dining_time(self) -> int:
        # 随机生成一次就餐时长。
        return self.random.randint(self.config.dining_min, self.config.dining_max)

    def student_process(self, student: Student):
        # 单个学生的生命周期：排队 -> 打饭 -> 等桌 -> 就餐 -> 离开。
        student.status = "queued"
        student.queue_enter_time = self.env.now

        window_idx = self.choose_window()
        window = self.windows[window_idx]
        student.window_id = window.window_id
        window.current_queue_length += 1

        with self.window_resources[window_idx].request() as req:
            # 等待该窗口服务资源可用。
            yield req
            window.current_queue_length -= 1
            student.status = "serving"
            student.service_start_time = self.env.now
            service_time = self.sample_service_time()
            window.remaining_service_time = service_time

            # 模拟打饭耗时。
            yield self.env.timeout(service_time)
            window.remaining_service_time = 0
            student.service_end_time = self.env.now

        student.status = "waiting_table"
        # 若无空桌，则在这里阻塞等待。
        yield self.table_resource.get(1)

        dining_time = self.sample_dining_time()
        table_id = self.occupy_table(student.student_id, dining_time)
        student.table_id = table_id
        student.status = "dining"
        student.dining_start_time = self.env.now

        # 模拟就餐耗时。
        yield self.env.timeout(dining_time)
        student.dining_end_time = self.env.now
        student.status = "completed"

        self.release_table(table_id)
        # 学生离开后将桌位配额放回资源池。
        yield self.table_resource.put(1)
        self.completed_students += 1

    def arrival_process(self):
        # 按泊松到达过程生成学生。
        # expovariate(arrival_rate) 返回相邻到达间隔时间。
        while self.env.now < self.config.duration_minutes:
            gap = max(0.1, self.random.expovariate(self.config.arrival_rate))
            yield self.env.timeout(gap)
            if self.env.now > self.config.duration_minutes:
                break

            self.student_seq += 1
            student = Student(student_id=self.student_seq, arrival_time=round(self.env.now, 2))
            student.status = "arrived"
            self.students.append(student)
            self.env.process(self.student_process(student))

    def snapshot_process(self):
        # 周期性记录系统运行状态，供仿真页播放和结果页绘图。
        while True:
            queue_total = sum(resource.count + len(resource.queue) for resource in self.window_resources)
            dining_count = sum(1 for student in self.students if student.status == "dining")
            waiting_table_count = sum(1 for student in self.students if student.status == "waiting_table")
            system_total = sum(1 for student in self.students if student.status != "completed")
            idle_tables = sum(1 for table in self.tables if not table.occupied)

            self.timeline.append(
                {
                    # 当前仿真时间。
                    "time": round(self.env.now, 2),
                    # 系统内总人数。
                    "system_total": system_total,
                    # 总排队人数。
                    "queue_total": queue_total,
                    # 正在就餐人数。
                    "dining_total": dining_count,
                    # 等待餐桌人数。
                    "waiting_table_total": waiting_table_count,
                    # 空闲桌数。
                    "idle_tables": idle_tables,
                    # 已完成离开人数。
                    "completed_total": self.completed_students,
                    # 每个窗口的实时负载。
                    "window_queues": [
                        {
                            "window_id": window.window_id,
                            "queue_length": resource.count + len(resource.queue),
                        }
                        for window, resource in zip(self.windows, self.window_resources)
                    ],
                    # 每张餐桌的实时占用情况。
                    "tables": [
                        {
                            "table_id": table.table_id,
                            "occupied": table.occupied,
                            "student_id": table.current_student,
                        }
                        for table in self.tables
                    ],
                }
            )

            # 到达结束时间且系统内无人后，结束采样。
            if self.env.now >= self.config.duration_minutes and system_total == 0:
                break
            yield self.env.timeout(self.config.snapshot_interval)

    def build_summary(self) -> dict:
        # 将所有学生对象转换为字典，方便后续统计。
        student_rows = [asdict(student) for student in self.students]
        if not student_rows:
            return {
                "total_students": 0,
                "completed_students": 0,
                "average_waiting_time": 0,
                "average_dining_time": 0,
                "average_system_time": 0,
                "peak_queue": 0,
                "peak_system_total": 0,
                "table_utilization": 0,
            }

        # 只统计已完成学生，避免未结束样本影响平均值。
        df = pd.DataFrame(student_rows)
        completed = df[df["status"] == "completed"].copy()
        completed["waiting_time"] = completed["service_start_time"] - completed["queue_enter_time"]
        completed["dining_time"] = completed["dining_end_time"] - completed["dining_start_time"]
        completed["system_time"] = completed["dining_end_time"] - completed["arrival_time"]

        total_timeline = len(self.timeline) or 1
        # 用平均空闲桌数反推平均餐桌利用率。
        avg_idle_tables = mean(item["idle_tables"] for item in self.timeline) if self.timeline else self.config.table_count
        utilization = 1 - avg_idle_tables / self.config.table_count

        return {
            "total_students": int(len(df)),
            "completed_students": int(len(completed)),
            "average_waiting_time": round(float(completed["waiting_time"].mean() if not completed.empty else 0), 2),
            "average_dining_time": round(float(completed["dining_time"].mean() if not completed.empty else 0), 2),
            "average_system_time": round(float(completed["system_time"].mean() if not completed.empty else 0), 2),
            "peak_queue": int(max(item["queue_total"] for item in self.timeline) if self.timeline else 0),
            "peak_system_total": int(max(item["system_total"] for item in self.timeline) if self.timeline else 0),
            "table_utilization": round(utilization * 100, 2),
            "timeline_points": total_timeline,
        }

    def run(self) -> SimulationResult:
        # 注册到达过程和采样过程，随后启动仿真主循环。
        self.env.process(self.arrival_process())
        self.env.process(self.snapshot_process())
        self.env.run()

        # 返回统一结果对象，便于 API 直接输出给前端。
        return SimulationResult(
            timeline=self.timeline,
            summary=self.build_summary(),
            students=[asdict(student) for student in self.students],
        )


def run_simulation(config: SimulationConfig) -> SimulationResult:
    # 对外暴露的简化入口，隐藏内部实现细节。
    return CafeteriaSimulation(config).run()
