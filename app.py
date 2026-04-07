from __future__ import annotations

# Flask 应用入口文件：
# 1. 创建 Web 服务。
# 2. 提供页面路由，分别对应启动页、仿真页和结果页。
# 3. 提供 API 路由，供前端提交参数、读取仿真结果。
# 4. 使用内存字典缓存仿真结果，便于课程设计阶段快速演示。

import uuid
from dataclasses import asdict
from typing import Any

from flask import Flask, jsonify, render_template, request

from cafeteria_sim.config import SimulationConfig
from cafeteria_sim.engine import run_simulation


app = Flask(__name__)
# 用于暂存每次仿真的完整结果。
# 键为 simulation_id，值为配置、时间线、统计摘要和学生明细。
SIMULATIONS: dict[str, dict[str, Any]] = {}


@app.get("/")
def index():
    # 返回启动页面，供用户填写本次仿真的参数。
    return render_template("index.html")


@app.get("/simulation/<simulation_id>")
def simulation_view(simulation_id: str):
    # 仿真界面需要依赖 simulation_id 找到结果数据。
    # 若编号不存在，则直接返回 404 页面。
    if simulation_id not in SIMULATIONS:
        return render_template("404.html"), 404
    return render_template("simulation.html", simulation_id=simulation_id)


@app.get("/results/<simulation_id>")
def results_view(simulation_id: str):
    # 结果界面同样依赖 simulation_id 定位仿真结果。
    if simulation_id not in SIMULATIONS:
        return render_template("404.html"), 404
    return render_template("results.html", simulation_id=simulation_id)


@app.post("/api/simulations")
def create_simulation():
    # 从前端读取 JSON 参数；若为空，则回退到默认配置。
    payload = request.get_json(force=True, silent=True) or {}
    # 将原始参数整理为结构化配置对象。
    config = SimulationConfig.from_payload(payload)
    # 执行一次完整仿真，得到时间线、摘要和学生明细。
    result = run_simulation(config)

    # 为当前仿真生成唯一编号，方便前端后续按编号读取。
    simulation_id = uuid.uuid4().hex
    SIMULATIONS[simulation_id] = {
        "id": simulation_id,
        "config": asdict(config),
        "timeline": result.timeline,
        "summary": result.summary,
        "students": result.students,
    }

    # 前端收到编号后，会跳转到仿真播放页面。
    return jsonify({"simulation_id": simulation_id})


@app.get("/api/simulations/<simulation_id>")
def get_simulation(simulation_id: str):
    # 仿真页和结果页都通过这个接口读取完整数据。
    data = SIMULATIONS.get(simulation_id)
    if not data:
        return jsonify({"error": "simulation not found"}), 404
    return jsonify(data)


if __name__ == "__main__":
    # 直接运行本文件时，启动 Flask 开发服务器。
    app.run(debug=True)
