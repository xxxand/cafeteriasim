function renderSummary(summary) {
  const labels = {
    total_students: "学生总数",
    completed_students: "完成人数",
    average_waiting_time: "平均等待时间",
    average_dining_time: "平均就餐时间",
    average_system_time: "平均逗留时间",
    peak_queue: "峰值排队人数",
    peak_system_total: "峰值系统人数",
    table_utilization: "餐桌利用率",
  };

  document.getElementById("summary-grid").innerHTML = Object.entries(labels)
    .map(([key, label]) => {
      const suffix = key.includes("time") ? " 分钟" : key === "table_utilization" ? "%" : "";
      return `<div class="stat-card"><span>${label}</span><strong>${summary[key]}${suffix}</strong></div>`;
    })
    .join("");
}

function buildCharts(timeline) {
  const labels = timeline.map((item) => item.time);

  new Chart(document.getElementById("result-chart"), {
    type: "line",
    data: {
      labels,
      datasets: [
        { label: "系统总人数", data: timeline.map((item) => item.system_total), borderColor: "#0f766e", tension: 0.3 },
        { label: "排队总人数", data: timeline.map((item) => item.queue_total), borderColor: "#f59e0b", tension: 0.3 },
        { label: "空闲桌数", data: timeline.map((item) => item.idle_tables), borderColor: "#1e2430", tension: 0.3 },
      ],
    },
    options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true } } },
  });

  const latest = timeline[timeline.length - 1];
  new Chart(document.getElementById("window-chart"), {
    type: "bar",
    data: {
      labels: latest.window_queues.map((item) => `窗口 ${item.window_id}`),
      datasets: [
        {
          label: "最终排队人数",
          data: latest.window_queues.map((item) => item.queue_length),
          backgroundColor: ["#0f766e", "#1d4ed8", "#f59e0b", "#b45309", "#334155", "#8b5cf6"],
        },
      ],
    },
    options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true } } },
  });
}

function renderStudents(students) {
  document.querySelector("#student-table tbody").innerHTML = students
    .slice(0, 20)
    .map((student) => `
      <tr>
        <td>${student.student_id}</td>
        <td>${student.arrival_time}</td>
        <td>${student.window_id ?? "-"}</td>
        <td>${student.table_id ?? "-"}</td>
        <td>${student.status}</td>
      </tr>
    `)
    .join("");
}

async function init() {
  const response = await fetch(`/api/simulations/${window.SIMULATION_ID}`);
  const data = await response.json();
  renderSummary(data.summary);
  buildCharts(data.timeline);
  renderStudents(data.students);
}

init();
