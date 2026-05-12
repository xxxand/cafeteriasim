"""联调测试文件。

本文件分为两部分：
1. 接口联调测试：验证配置模块、仿真引擎、接口层、页面层之间能否正常通信。
2. 系统联调测试：以具体业务场景为用例，验证系统整体流程是否正常。
"""

import unittest

import app as app_module


class InterfaceIntegrationTests(unittest.TestCase):
    """接口联调测试。

    目标：
    - 验证前端参数能够进入 Flask 接口。
    - 验证接口能够调用配置模块和仿真引擎。
    - 验证仿真结果能够被仿真页和结果页正常读取。
    """

    def setUp(self):
        """为每个测试创建一个干净的 Flask 测试环境。"""

        app_module.app.config["TESTING"] = True
        self.client = app_module.app.test_client()
        app_module.SIMULATIONS.clear()

    def create_simulation(self, payload: dict) -> str:
        """辅助方法：创建仿真并返回仿真编号。"""

        response = self.client.post("/api/simulations", json=payload)
        self.assertEqual(response.status_code, 200)
        simulation_id = response.get_json()["simulation_id"]
        self.assertTrue(simulation_id)
        return simulation_id

    def test_api_and_engine_can_coordinate(self):
        """测试创建仿真接口、配置模块和仿真引擎能否协同工作。"""

        simulation_id = self.create_simulation(
            {
                "window_count": 3,
                "table_count": 12,
                "duration_minutes": 30,
                "arrival_rate": 1.2,
                "service_min": 1,
                "service_max": 3,
                "dining_min": 4,
                "dining_max": 6,
                "snapshot_interval": 1,
                "random_seed": 42,
            }
        )

        stored_data = app_module.SIMULATIONS[simulation_id]

        # 联调验证点：
        # 1. 配置数据被正确保存。
        # 2. 仿真引擎产生了 timeline / summary / students。
        self.assertEqual(stored_data["config"]["window_count"], 3)
        self.assertEqual(stored_data["config"]["table_count"], 12)
        self.assertTrue(len(stored_data["timeline"]) > 0)
        self.assertIn("completed_students", stored_data["summary"])
        self.assertIsInstance(stored_data["students"], list)

    def test_pages_can_read_same_simulation_result(self):
        """测试仿真页和结果页能否共享同一份仿真数据。"""

        simulation_id = self.create_simulation(
            {
                "window_count": 2,
                "table_count": 8,
                "duration_minutes": 25,
                "arrival_rate": 1.0,
                "service_min": 1,
                "service_max": 2,
                "dining_min": 3,
                "dining_max": 5,
                "snapshot_interval": 1,
                "random_seed": 7,
            }
        )

        simulation_page = self.client.get(f"/simulation/{simulation_id}")
        results_page = self.client.get(f"/results/{simulation_id}")
        data_api = self.client.get(f"/api/simulations/{simulation_id}")

        self.assertEqual(simulation_page.status_code, 200)
        self.assertEqual(results_page.status_code, 200)
        self.assertEqual(data_api.status_code, 200)
        self.assertIn(simulation_id, simulation_page.get_data(as_text=True))
        self.assertIn(simulation_id, results_page.get_data(as_text=True))
        self.assertEqual(data_api.get_json()["id"], simulation_id)


class SystemIntegrationTests(unittest.TestCase):
    """系统联调测试。

    目标：
    - 以完整业务场景作为用例，验证系统整体能力。
    - 不只看单个模块，而是看“参数输入 -> 仿真执行 -> 结果输出”是否成链条工作。
    """

    def setUp(self):
        """初始化测试客户端并清空缓存。"""

        app_module.app.config["TESTING"] = True
        self.client = app_module.app.test_client()
        app_module.SIMULATIONS.clear()

    def run_case(self, payload: dict) -> dict:
        """辅助方法：运行一个完整用例并返回结果数据。"""

        create_response = self.client.post("/api/simulations", json=payload)
        self.assertEqual(create_response.status_code, 200)
        simulation_id = create_response.get_json()["simulation_id"]

        result_response = self.client.get(f"/api/simulations/{simulation_id}")
        self.assertEqual(result_response.status_code, 200)
        return result_response.get_json()

    def test_case_high_load_limited_tables(self):
        """用例一：高峰期高到达率、桌位较紧张。

        预期：
        - 系统能够正常完成仿真。
        - 会出现一定排队或候桌现象。
        - 结果页所需结构完整。
        """

        result = self.run_case(
            {
                "window_count": 2,
                "table_count": 4,
                "duration_minutes": 40,
                "arrival_rate": 2.5,
                "service_min": 1,
                "service_max": 2,
                "dining_min": 6,
                "dining_max": 8,
                "snapshot_interval": 1,
                "random_seed": 42,
            }
        )

        self.assertTrue(len(result["timeline"]) > 0)
        self.assertGreater(result["summary"]["total_students"], 0)
        self.assertGreaterEqual(result["summary"]["peak_queue"], 0)
        self.assertGreaterEqual(
            max(point["waiting_table_total"] for point in result["timeline"]),
            0,
        )

    def test_case_low_load_sufficient_resources(self):
        """用例二：平峰期低到达率、资源充足。

        预期：
        - 系统能够正常运行。
        - 餐桌空闲数整体较高。
        - 完成学生人数应大于 0。
        """

        result = self.run_case(
            {
                "window_count": 4,
                "table_count": 20,
                "duration_minutes": 30,
                "arrival_rate": 0.5,
                "service_min": 1,
                "service_max": 2,
                "dining_min": 3,
                "dining_max": 5,
                "snapshot_interval": 1,
                "random_seed": 24,
            }
        )

        idle_table_values = [point["idle_tables"] for point in result["timeline"]]

        self.assertTrue(len(result["timeline"]) > 0)
        self.assertGreater(result["summary"]["completed_students"], 0)
        self.assertGreaterEqual(min(idle_table_values), 0)
        self.assertLessEqual(max(idle_table_values), 20)

    def test_case_full_process_from_start_page_to_result_data(self):
        """用例三：模拟真实使用流程。

        流程：
        - 访问启动页
        - 提交仿真参数
        - 访问仿真页
        - 访问结果页
        - 读取最终结果数据
        """

        index_page = self.client.get("/")
        self.assertEqual(index_page.status_code, 200)

        create_response = self.client.post(
            "/api/simulations",
            json={
                "window_count": 3,
                "table_count": 10,
                "duration_minutes": 35,
                "arrival_rate": 1.4,
                "service_min": 1,
                "service_max": 3,
                "dining_min": 4,
                "dining_max": 6,
                "snapshot_interval": 1,
                "random_seed": 11,
            },
        )
        simulation_id = create_response.get_json()["simulation_id"]

        simulation_page = self.client.get(f"/simulation/{simulation_id}")
        results_page = self.client.get(f"/results/{simulation_id}")
        result_data = self.client.get(f"/api/simulations/{simulation_id}").get_json()

        self.assertEqual(simulation_page.status_code, 200)
        self.assertEqual(results_page.status_code, 200)
        self.assertEqual(result_data["id"], simulation_id)
        self.assertIn("summary", result_data)
        self.assertIn("timeline", result_data)
        self.assertIn("students", result_data)


if __name__ == "__main__":
    unittest.main()
