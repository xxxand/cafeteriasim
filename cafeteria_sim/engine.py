# 延迟注解求值，将类型注解以字符串形式存储，而不是在定义时立即求值。注解会被当作字符串存储，等到真正需要时才解析。
# 防止类 A 引用了类 B，而类 B 又引用了类 A（循环引用），报错。
from __future__ import annotations

# 仿真引擎模块：
# 负责完成学生到达、窗口排队、打饭服务、餐桌占用、就餐离开以及数据统计全过程。

import random
from dataclasses import asdict
from statistics import mean

import pandas as pd
import simpy
# 从同项目的 config 模块导入 SimulationConfig 配置类，它包含了仿真时长、窗口数量、餐桌数量、服务时间范围、随机种子等参数。
# 从 models 模块导入数据模型类。
from cafeteria_sim.config import SimulationConfig
from cafeteria_sim.models import SimulationResult, Student, Table, Window

# 定义：食堂仿真类CafeteriaSimulation。
class CafeteriaSimulation:
    # 构造方法，接收一个配置对象 config。
    def __init__(self, config: SimulationConfig):
        # 保存配置对象，供整个仿真过程读取。
        self.config = config
        # 独立随机数生成器，便于通过随机种子复现实验。
        self.random = random.Random(config.random_seed)
        # SimPy 环境对象，负责管理仿真时间推进。
        # 创建了一个 SimPy 仿真环境对象，并把它赋值给实例变量 self.env
        #基于 离散事件 的仿真库。在离散事件仿真中，系统的状态只在某些离散的时间点上发生变化（比如学生到达、开始打饭、离开餐桌）
        self.env = simpy.Environment()

        # 初始化所有窗口与对应的服务资源。
        # 初始化 self.windows 列表：根据配置的窗口数量 window_count，为每个窗口创建一个 Window 模型对象。
        self.windows = [Window(window_id=i + 1) for i in range(config.window_count)]
        # 初始化 self.window_resources 列表：为每个窗口创建一个 SimPy 的 Resource，capacity=1 表示每个窗口一次只能服务一名学生（即单服务台）。
        # Resource 内部维护一个队列，学生需要 request() 才能获得服务。
        self.window_resources = [simpy.Resource(self.env, capacity=1) for _ in range(config.window_count)]

        # 初始化所有餐桌，并使用 Container 管理剩余空桌数量。
        self.tables = [Table(table_id=i + 1) for i in range(config.table_count)]
        # 这是一个 SimPy 的 Container 容器，可以看作一个资源池。init 和 capacity 都设为餐桌总数，表示初始时所有餐桌空闲。
        # 每个学生就餐时要从这个容器中“取出”一个单位（get(1)），离开时“放回”一个单位（put(1)）。
        # 这实现了学生等待空桌的功能。
        self.table_resource = simpy.Container(self.env, init=config.table_count, capacity=config.table_count)

        # 运行期状态数据。
        # 列表，保存所有创建的学生对象（包括已完成和未完成的）。
        self.students: list[Student] = []
        # 已顺利完成就餐并离开的学生数量。
        self.completed_students = 0
        # 列表，每个元素是一个字典，记录某一时刻系统状态。
        self.timeline: list[dict] = []
        # 学生序号计数器，每个新到达的学生获得一个递增的 ID。
        self.student_seq = 0

    def choose_window(self) -> int:
        # 采用最短队列策略，为新到达学生选择负载最小的窗口。
        # resource.count：当前正在使用该资源的进程数量。因为每个窗口的 capacity=1（容量），所以 count 的值要么是 0（空闲），要么是 1（有人）。
        # len(resource.queue)：正在排队等待的。
        # 每个窗口资源 resource 的两者相加就是该窗口的总负载（正在服务+等待）。
        # min(range(len(lengths)), key=lambda idx: (lengths[idx], idx))：返回长度最小的窗口索引。如果长度相同，选择索引较小的（即窗口号靠前的），保证确定性。
        lengths = [resource.count + len(resource.queue) for resource in self.window_resources]
        return min(range(len(lengths)), key=lambda idx: (lengths[idx], idx))

    def occupy_table(self, student_id: int, dining_time: float) -> int:
        # 找到第一张空闲桌并标记占用，返回桌号。
        # 遍历所有餐桌，找到第一个 occupied == False 的桌子，将其标记为占用。
        # 记录就餐的学生 ID 和剩余就餐时间，返回该桌的 ID。
        for table in self.tables:
            if not table.occupied:
                table.occupied = True
                table.current_student = student_id
                table.remaining_dining_time = dining_time
                return table.table_id
        return -1

    def release_table(self, table_id: int) -> None:
        # 学生离开后释放餐桌状态。根据桌号找到对应的餐桌，将其占用状态重置为 False，清除学生 ID 和剩余就餐时间。
        for table in self.tables:
            if table.table_id == table_id:
                table.occupied = False
                table.current_student = None
                table.remaining_dining_time = 0.0
                # (0.0)
                return

    def sample_service_time(self) -> int:
        # 随机生成一次打饭服务时长，在 min 和 max 之间均匀随机整数。
        return self.random.randint(self.config.service_min, self.config.service_max)

    def sample_dining_time(self) -> int:
        # 随机生成一次就餐时长，在的 min 和 max 之间均匀随机整数。
        return self.random.randint(self.config.dining_min, self.config.dining_max)

    def student_process(self, student: Student):
        # 单个学生的用餐周期：排队 -> 打饭 -> 等桌 -> 就餐 -> 离开。
        # 话说会不会有人吃完了饭不够又去打了一份，或者一份没吃完，这样步骤就不是固定的了。不过那属于少数情况吧，暂不考虑。

        # 设置学生状态为 "queued"正在排队等待打饭，记录开始排队的时间。
        student.status = "queued"
        student.queue_enter_time = self.env.now

        # 调用 choose_window 选择最短队列窗口，得到窗口索引。
        # 然后根据索引获取窗口对象，记录学生分配到的窗口号，并将该窗口的当前排队长度计数器加 1。
        window_idx = self.choose_window()
        window = self.windows[window_idx]
        student.window_id = window.window_id
        window.current_queue_length += 1

        # 使用 with 语句申请该窗口的资源（Resource）。request() 返回一个事件，
        # yield req 将进程挂起，直到资源可用（即轮到该学生）。这就是 SimPy 实现排队等待的方式。
        with self.window_resources[window_idx].request() as req:
            # 等待该窗口服务资源可用。
            # 一旦获得资源，表示该学生开始被服务：更新窗口的排队长度计数器减一，状态改为 "serving"，记录服务开始时间。
            # 随机生成服务时长 service_time，并将窗口的剩余服务时间设为该值（用于前端实时显示进度）。
            # yield self.env.timeout(service_time) 暂停进程，模拟打饭耗时。
            # 时间到后，服务结束，将窗口剩余服务时间清零，记录服务结束时间。
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
        # 打饭完成后状态变为 "waiting_table"（等待空桌）。然后尝试从餐桌容器 table_resource 中获取 1 个单位资源。
        # 如果容器当前容量为 0（没有空闲桌子），get(1) 会阻塞进程，直到有学生离开放回资源。这就实现了等桌排队。
        student.status = "waiting_table"
        yield self.table_resource.get(1)

        # 成功获得桌子后，生成随机就餐时长，调用 occupy_table 将桌子标记为占用，记录桌号、状态改为 "dining"（就餐中）、记录开始就餐时间。
        dining_time = self.sample_dining_time()
        table_id = self.occupy_table(student.student_id, dining_time)
        student.table_id = table_id
        student.status = "dining"
        student.dining_start_time = self.env.now
        # yield self.env.timeout(dining_time) 模拟就餐过程。
        # 就餐结束，记录结束时间，状态改为 "completed"
        # 模拟就餐耗时。
        yield self.env.timeout(dining_time)
        student.dining_end_time = self.env.now
        student.status = "completed"

        # 释放餐桌（release_table），然后将一个单位资源放回餐桌容器 table_resource.put(1)，让其他等待的学生可以使用这张桌子。
        self.release_table(table_id)
        # 学生离开后将桌位配额放回资源池。
        #
        # 已完成学生计数器加 1。
        yield self.table_resource.put(1)
        self.completed_students += 1

    def arrival_process(self):
        # 不断生成新的学生，每次生成后休眠一段随机间隔（模拟相邻两个学生的到达时间间隔）。
        # 当仿真时间超过设定的总时长 (duration_minutes) 时，停止生成新生。
        # 每生成一个学生，就启动一个独立的 student_process 进程，该进程会处理该学生从排队到离开的全部行为。
        while self.env.now < self.config.duration_minutes:

            # 生成一个指数分布（泊松）的随机数。
            # 为什么使用泊松分布 QAQ ：泊松分布在任意两个不相交的时间区间内，到达数量是独立的。
            # 在足够小的时间区间 Δt 内，恰好有一次到达的概率 ≈ λ·Δt（λ 为到达率）
            # f(t)=λe^(−λt),均值为 1/λ，顾客随机、独立地到达。
            # 为什么不使用其它 QAQ ：如均匀分布，正态分布，已知已等待的时间会改变对剩余时间的预测。
            # 违背“到达过程与历史无关”。
            gap = max(0.1, self.random.expovariate(self.config.arrival_rate))

            # 表示“等待 gap 分钟”。当时间推进了 gap 分钟后，Timeout 事件触发，arrival_process 从 yield 处恢复，继续执行后面的代码。
            # 效果：模拟了现实世界中两个学生到达之间的空闲间隔。:)
            yield self.env.timeout(gap)

            # 恢复后，再次检查当前时间。有可能因为之前的等待导致时间超过了总时长（例如总时长 180 分钟，但等待 5 分钟后变为 182 分钟）。
            # 如果超时，立即跳出循环，不再创建新学生。
            if self.env.now > self.config.duration_minutes:
                break

            # 创建学生对象，自增后为ID。记录到达时间。状态设置 arrival 。
            self.student_seq += 1
            student = Student(student_id=self.student_seq, arrival_time=round(self.env.now, 2))
            student.status = "arrived"
            # 将学生对象添加到 self.students 列表中，以便后续统计和结果输出。
            self.students.append(student)
            # 生成器函数，它包含了该学生从排队、打饭、等桌、就餐到离开的周期。
            self.env.process(self.student_process(student))

    # 周期性采样进程，它的任务是在仿真运行的整个过程中，每隔固定时间间隔（snapshot_interval）记录一次系统当前的状态
    def snapshot_process(self):
        # 周期性记录系统运行状态，供仿真页播放和结果页绘图。
        while True:
            # 所有窗口的总排队人数。count + len(queue) 就是该窗口的总负载（正在服务 + 等待）
            queue_total = sum(resource.count + len(resource.queue) for resource in self.window_resources)
            # 正在就餐的人数
            dining_count = sum(1 for student in self.students if student.status == "dining")
            # 等待的人数
            waiting_table_count = sum(1 for student in self.students if student.status == "waiting_table")
            # 系统内总人数
            system_total = sum(1 for student in self.students if student.status != "completed")
            # 空闲餐桌数量
            idle_tables = sum(1 for table in self.tables if not table.occupied)

            # 构建快照字典并添加到 timeline
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
                    # zip(self.windows, self.window_resources) 将窗口模型对象列表和服务资源列表一一配对。
                    # 每次迭代取一个窗口的模型对象（存有 window_id）和对应的资源对象（用于获取实际负载），然后生成一条记录。
                    "window_queues": [
                        {
                            "window_id": window.window_id,
                            "queue_length": resource.count + len(resource.queue),
                        }
                        for window, resource in zip(self.windows, self.window_resources)
                    ],
                    # 每张餐桌的实时占用情况。遍历 self.tables，将每个 Table 对象的关键信息提取出来。
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
            # 为什么不直接用 while self.env.now <= self.config.duration_minutes？ QAQ
            # 因为学生在 duration_minutes 之后仍可能继续就餐，若只采样到 duration_minutes，就无法记录学生离开后的空闲桌子数量等信息，最终统计会不准确。
            if self.env.now >= self.config.duration_minutes and system_total == 0:
                break
            yield self.env.timeout(self.config.snapshot_interval)

    def build_summary(self) -> dict:
        # 将所有学生对象转换为字典，方便后续统计。
        student_rows = [asdict(student) for student in self.students]
        # 处理无学生的边界情况
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
        # 将字典列表转换为一个二维表格（DataFrame），行代表每个学生，列代表学生的属性
        df = pd.DataFrame(student_rows)
        # 筛选出状态为 "completed" 的学生
        completed = df[df["status"] == "completed"].copy()
        completed["waiting_time"] = completed["service_start_time"] - completed["queue_enter_time"]
        completed["dining_time"] = completed["dining_end_time"] - completed["dining_start_time"]
        completed["system_time"] = completed["dining_end_time"] - completed["arrival_time"]

        # 采样点数量。or 1 ：如果 timeline 为空，则 len(...) == 0，0 or 1 的结果是 1，避免后续可能的除零。
        total_timeline = len(self.timeline) or 1
        # 用平均空闲桌数反推平均餐桌利用率。
        avg_idle_tables = mean(item["idle_tables"] for item in self.timeline) if self.timeline else self.config.table_count
        # 餐桌利用率
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

    # 启动入口
    def run(self) -> SimulationResult:
        # 注册到达过程和采样过程，随后启动仿真主循环。
        # 按泊松过程生成学生。调用 arrival_process() 会返回一个生成器对象，env.process() 将其注册为独立进程。
        self.env.process(self.arrival_process())
        # 周期性记录系统状态。注册后，它会和到达进程并发运行。
        self.env.process(self.snapshot_process())
        # 执行。学生到达进程不断生成新学生。每个学生进程经历排队、打饭、等桌、就餐。快照进程定时记录状态。
        self.env.run()

        # 返回统一结果对象，便于 API 直接输出给前端。
        return SimulationResult(
            timeline=self.timeline,
            summary=self.build_summary(),
            students=[asdict(student) for student in self.students],
        )

# 接收一个配置对象。内部创建实例，调用该实例的 run() 方法执行仿真，直接返回仿真结果。
def run_simulation(config: SimulationConfig) -> SimulationResult:
    # 对外暴露的简化入口，隐藏内部实现细节。
    return CafeteriaSimulation(config).run()
