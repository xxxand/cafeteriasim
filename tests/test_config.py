"""配置模块自动化测试。

本文件测试的重点是：
1. 前端传来的字符串参数能否被正确转换为数值类型。
2. 边界保护逻辑能否在非法输入时自动修正。
"""

import unittest

from cafeteria_sim.config import SimulationConfig


class SimulationConfigTests(unittest.TestCase):
    """测试 SimulationConfig.from_payload 的行为是否符合预期。"""

    def test_from_payload_converts_types_correctly(self):
        """测试前端字符串参数能否被正确转换为 int / float。"""

        payload = {
            "window_count": "5",
            "table_count": "40",
            "duration_minutes": "90",
            "arrival_rate": "2.0",
            "service_min": "2",
            "service_max": "6",
            "dining_min": "8",
            "dining_max": "18",
            "snapshot_interval": "2",
            "random_seed": "123",
        }

        config = SimulationConfig.from_payload(payload)

        self.assertEqual(config.window_count, 5)
        self.assertEqual(config.table_count, 40)
        self.assertEqual(config.duration_minutes, 90)
        self.assertEqual(config.arrival_rate, 2.0)
        self.assertEqual(config.service_min, 2)
        self.assertEqual(config.service_max, 6)
        self.assertEqual(config.dining_min, 8)
        self.assertEqual(config.dining_max, 18)
        self.assertEqual(config.snapshot_interval, 2)
        self.assertEqual(config.random_seed, 123)

    def test_from_payload_applies_minimum_bounds(self):
        """测试非法输入时，配置对象是否会回退到最小允许值。"""

        payload = {
            "window_count": "0",
            "table_count": "-1",
            "duration_minutes": "1",
            "arrival_rate": "-10",
            "service_min": "0",
            "service_max": "0",
            "dining_min": "0",
            "dining_max": "0",
            "snapshot_interval": "0",
            "random_seed": "42",
        }

        config = SimulationConfig.from_payload(payload)

        self.assertEqual(config.window_count, 1)
        self.assertEqual(config.table_count, 1)
        self.assertEqual(config.duration_minutes, 10)
        self.assertEqual(config.arrival_rate, 0.1)
        self.assertEqual(config.service_min, 1)
        self.assertEqual(config.service_max, 1)
        self.assertEqual(config.dining_min, 1)
        self.assertEqual(config.dining_max, 1)
        self.assertEqual(config.snapshot_interval, 1)


if __name__ == "__main__":
    unittest.main()
