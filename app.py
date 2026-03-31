from __future__ import annotations

import uuid
from dataclasses import asdict
from typing import Any

from flask import Flask, jsonify, render_template, request

from cafeteria_sim.config import SimulationConfig
from cafeteria_sim.engine import run_simulation


app = Flask(__name__)
SIMULATIONS: dict[str, dict[str, Any]] = {}


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/simulation/<simulation_id>")
def simulation_view(simulation_id: str):
    if simulation_id not in SIMULATIONS:
        return render_template("404.html"), 404
    return render_template("simulation.html", simulation_id=simulation_id)


@app.get("/results/<simulation_id>")
def results_view(simulation_id: str):
    if simulation_id not in SIMULATIONS:
        return render_template("404.html"), 404
    return render_template("results.html", simulation_id=simulation_id)


@app.post("/api/simulations")
def create_simulation():
    payload = request.get_json(force=True, silent=True) or {}
    config = SimulationConfig.from_payload(payload)
    result = run_simulation(config)
    simulation_id = uuid.uuid4().hex
    SIMULATIONS[simulation_id] = {
        "id": simulation_id,
        "config": asdict(config),
        "timeline": result.timeline,
        "summary": result.summary,
        "students": result.students,
    }
    return jsonify({"simulation_id": simulation_id})


@app.get("/api/simulations/<simulation_id>")
def get_simulation(simulation_id: str):
    data = SIMULATIONS.get(simulation_id)
    if not data:
        return jsonify({"error": "simulation not found"}), 404
    return jsonify(data)


if __name__ == "__main__":
    app.run(debug=True)
