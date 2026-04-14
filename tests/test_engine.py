"""仿真引擎自动化测试。

本文件主要测试：
1. 仿真是否能够正常运行并返回非空结果。
2. 返回的统计字段是否完整、数值是否合理。
3. 资源分配逻辑是否保持在合法范围内。
"""

import unittest

from cafeteria_sim.config import SimulationConfig
from cafeteria_sim.engine import CafeteriaSimulation, run_simulation


class SimulationEngineTests(unittest.TestCase):
    """测试仿真引擎的核心行为。"""

    def setUp(self):
        """为每个测试准备一组较小规模的仿真参数。"""

        self.config = SimulationConfig(
            window_count=2,
            table_count=5,
            duration_minutes=20,
            arrival_rate=1.0,
            service_min=1,
            service_max=2,
            dining_min=3,
            dining_max=5,
            snapshot_interval=1,
            random_seed=42,
        )

    def test_run_simulation_returns_expected_structure(self):
        """测试仿真执行后，是否返回 timeline、summary 和 students。"""

        result = run_simulation(self.config)

        self.assertTrue(len(result.timeline) > 0)
        self.assertIsInstance(result.summary, dict)
        self.assertIsInstance(result.students, list)
        self.assertIn("total_students", result.summary)
        self.assertIn("completed_students", result.summary)
        self.assertIn("peak_queue", result.summary)
        self.assertIn("table_utilization", result.summary)

    def test_summary_values_stay_in_reasonable_range(self):
        """测试关键统计值是否处于合法区间。"""

        result = run_simulation(self.config)
        summary = result.summary

        self.assertGreaterEqual(summary["total_students"], 0)
        self.assertGreaterEqual(summary["completed_students"], 0)
        self.assertGreaterEqual(summary["peak_queue"], 0)
        self.assertGreaterEqual(summary["peak_system_total"], 0)
        self.assertGreaterEqual(summary["table_utilization"], 0)
        self.assertLessEqual(summary["table_utilization"], 100)

    def test_snapshot_table_counts_never_exceed_capacity(self):
        """测试任意时间点下，占用桌数都不会超过总桌数。"""

        result = run_simulation(self.config)

        for point in result.timeline:
            occupied_count = sum(1 for table in point["tables"] if table["occupied"])
            idle_count = point["idle_tables"]
            self.assertLessEqual(occupied_count, self.config.table_count)
            self.assertGreaterEqual(idle_count, 0)
            self.assertEqual(occupied_count + idle_count, self.config.table_count)

    def test_choose_window_prefers_shorter_queue(self):
        """测试 choose_window 会优先选择当前负载更小的窗口。"""

        simulation = CafeteriaSimulation(self.config)

        # 人工构造窗口负载：
        # 第 1 个窗口负载较大，第 2 个窗口负载较小，因此预期返回索引 1。
        simulation.window_resources[0].users.append(object())
        simulation.window_resources[0].queue.append(object())

        chosen_index = simulation.choose_window()

        self.assertEqual(chosen_index, 1)


if __name__ == "__main__":
    unittest.main()
