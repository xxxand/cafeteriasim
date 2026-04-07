// 结果页脚本：
// 负责渲染统计摘要、结果图表和部分学生明细。
function renderSummary(summary) {
  // 将后端字段名映射为中文显示名称。
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
      // 时间类指标追加“分钟”，利用率追加百分号。
      const suffix = key.includes("time") ? " 分钟" : key === "table_utilization" ? "%" : "";
      return `<div class="stat-card"><span>${label}</span><strong>${summary[key]}${suffix}</strong></div>`;
    })
    .join("");
}

function buildCharts(timeline) {
  // 所有图表共用时间线作为横轴。
  const labels = timeline.map((item) => item.time);

  // 折线图展示系统人数、排队人数和空闲桌数的变化趋势。
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

  // 柱状图读取最后一个时间点的窗口队列情况，便于横向比较各窗口压力。
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
  // 仅展示前 20 条学生记录，避免结果页表格过长。
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
  // 根据页面注入的 simulation_id 从后端读取结果。
  const response = await fetch(`/api/simulations/${window.SIMULATION_ID}`);
  const data = await response.json();
  renderSummary(data.summary);
  buildCharts(data.timeline);
  renderStudents(data.students);
}

// 页面加载完成后立即初始化。
init();
