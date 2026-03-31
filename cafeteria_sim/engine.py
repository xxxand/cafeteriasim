from __future__ import annotations

import random
from dataclasses import asdict
from statistics import mean

import pandas as pd
import simpy

from cafeteria_sim.config import SimulationConfig
from cafeteria_sim.models import SimulationResult, Student, Table, Window


class CafeteriaSimulation:
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.random = random.Random(config.random_seed)
        self.env = simpy.Environment()
        self.windows = [Window(window_id=i + 1) for i in range(config.window_count)]
        self.window_resources = [simpy.Resource(self.env, capacity=1) for _ in range(config.window_count)]
        self.tables = [Table(table_id=i + 1) for i in range(config.table_count)]
        self.table_resource = simpy.Container(self.env, init=config.table_count, capacity=config.table_count)
        self.students: list[Student] = []
        self.completed_students = 0
        self.timeline: list[dict] = []
        self.student_seq = 0

    def choose_window(self) -> int:
        lengths = [resource.count + len(resource.queue) for resource in self.window_resources]
        return min(range(len(lengths)), key=lambda idx: (lengths[idx], idx))

    def occupy_table(self, student_id: int, dining_time: float) -> int:
        for table in self.tables:
            if not table.occupied:
                table.occupied = True
                table.current_student = student_id
                table.remaining_dining_time = dining_time
                return table.table_id
        return -1

    def release_table(self, table_id: int) -> None:
        for table in self.tables:
            if table.table_id == table_id:
                table.occupied = False
                table.current_student = None
                table.remaining_dining_time = 0.0
                return

    def sample_service_time(self) -> int:
        return self.random.randint(self.config.service_min, self.config.service_max)

    def sample_dining_time(self) -> int:
        return self.random.randint(self.config.dining_min, self.config.dining_max)

    def student_process(self, student: Student):
        student.status = "queued"
        student.queue_enter_time = self.env.now
        window_idx = self.choose_window()
        window = self.windows[window_idx]
        student.window_id = window.window_id
        window.current_queue_length += 1

        with self.window_resources[window_idx].request() as req:
            yield req
            window.current_queue_length -= 1
            student.status = "serving"
            student.service_start_time = self.env.now
            service_time = self.sample_service_time()
            window.remaining_service_time = service_time
            yield self.env.timeout(service_time)
            window.remaining_service_time = 0
            student.service_end_time = self.env.now

        student.status = "waiting_table"
        yield self.table_resource.get(1)
        dining_time = self.sample_dining_time()
        table_id = self.occupy_table(student.student_id, dining_time)
        student.table_id = table_id
        student.status = "dining"
        student.dining_start_time = self.env.now
        yield self.env.timeout(dining_time)
        student.dining_end_time = self.env.now
        student.status = "completed"
        self.release_table(table_id)
        yield self.table_resource.put(1)
        self.completed_students += 1

    def arrival_process(self):
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
        while True:
            queue_total = sum(resource.count + len(resource.queue) for resource in self.window_resources)
            dining_count = sum(1 for student in self.students if student.status == "dining")
            waiting_table_count = sum(1 for student in self.students if student.status == "waiting_table")
            system_total = sum(1 for student in self.students if student.status != "completed")
            idle_tables = sum(1 for table in self.tables if not table.occupied)

            self.timeline.append(
                {
                    "time": round(self.env.now, 2),
                    "system_total": system_total,
                    "queue_total": queue_total,
                    "dining_total": dining_count,
                    "waiting_table_total": waiting_table_count,
                    "idle_tables": idle_tables,
                    "completed_total": self.completed_students,
                    "window_queues": [
                        {
                            "window_id": window.window_id,
                            "queue_length": resource.count + len(resource.queue),
                        }
                        for window, resource in zip(self.windows, self.window_resources)
                    ],
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

            if self.env.now >= self.config.duration_minutes and system_total == 0:
                break
            yield self.env.timeout(self.config.snapshot_interval)

    def build_summary(self) -> dict:
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

        df = pd.DataFrame(student_rows)
        completed = df[df["status"] == "completed"].copy()
        completed["waiting_time"] = completed["service_start_time"] - completed["queue_enter_time"]
        completed["dining_time"] = completed["dining_end_time"] - completed["dining_start_time"]
        completed["system_time"] = completed["dining_end_time"] - completed["arrival_time"]

        total_timeline = len(self.timeline) or 1
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
        self.env.process(self.arrival_process())
        self.env.process(self.snapshot_process())
        self.env.run()
        return SimulationResult(
            timeline=self.timeline,
            summary=self.build_summary(),
            students=[asdict(student) for student in self.students],
        )


def run_simulation(config: SimulationConfig) -> SimulationResult:
    return CafeteriaSimulation(config).run()
