"""Flask 接口自动化测试。

本文件主要测试：
1. 创建仿真接口是否能成功接收参数并返回 simulation_id。
2. 查询仿真接口是否能返回完整结果结构。
3. 不存在的仿真编号是否会返回 404。
"""

import unittest

import app as app_module


class FlaskApiTests(unittest.TestCase):
    """测试 Flask 提供的仿真接口。"""

    def setUp(self):
        """为每个测试创建独立的测试客户端，并清空内存缓存。"""

        app_module.app.config["TESTING"] = True
        self.client = app_module.app.test_client()
        app_module.SIMULATIONS.clear()

    def test_create_simulation_returns_simulation_id(self):
        """测试创建仿真接口是否能返回一个可用编号。"""

        payload = {
            "window_count": 2,
            "table_count": 6,
            "duration_minutes": 20,
            "arrival_rate": 1.0,
            "service_min": 1,
            "service_max": 2,
            "dining_min": 3,
            "dining_max": 5,
            "snapshot_interval": 1,
            "random_seed": 42,
        }

        response = self.client.post("/api/simulations", json=payload)
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertIn("simulation_id", data)
        self.assertTrue(data["simulation_id"])

    def test_get_simulation_returns_complete_payload(self):
        """测试根据编号查询时，是否能返回前端所需的完整字段。"""

        create_response = self.client.post(
            "/api/simulations",
            json={
                "window_count": 2,
                "table_count": 6,
                "duration_minutes": 20,
                "arrival_rate": 1.0,
                "service_min": 1,
                "service_max": 2,
                "dining_min": 3,
                "dining_max": 5,
                "snapshot_interval": 1,
                "random_seed": 42,
            },
        )
        simulation_id = create_response.get_json()["simulation_id"]

        response = self.client.get(f"/api/simulations/{simulation_id}")
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["id"], simulation_id)
        self.assertIn("config", data)
        self.assertIn("timeline", data)
        self.assertIn("summary", data)
        self.assertIn("students", data)
        self.assertTrue(len(data["timeline"]) > 0)

    def test_get_missing_simulation_returns_404(self):
        """测试查询不存在的仿真编号时，接口是否返回 404。"""

        response = self.client.get("/api/simulations/not-found")
        data = response.get_json()

        self.assertEqual(response.status_code, 404)
        self.assertEqual(data["error"], "simulation not found")


if __name__ == "__main__":
    unittest.main()
