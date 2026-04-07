// 仿真页脚本：
// 负责按时间顺序播放后端返回的 timeline 数据，并动态刷新统计卡片、窗口列表、餐桌网格和折线图。
let simulationData = null;
let currentIndex = 0;
let timer = null;
let chart = null;

function renderStats(point) {
  // 将当前时间点的关键指标整理成卡片列表。
  const stats = [
    ["当前时间", `${point.time} 分钟`],
    ["系统总人数", point.system_total],
    ["排队总人数", point.queue_total],
    ["就餐人数", point.dining_total],
    ["候桌人数", point.waiting_table_total],
    ["空闲桌数", point.idle_tables],
    ["已完成人数", point.completed_total],
  ];

  document.getElementById("stats-grid").innerHTML = stats
    .map(([label, value]) => `<div class="stat-card"><span>${label}</span><strong>${value}</strong></div>`)
    .join("");
}

function renderWindows(point) {
  // 渲染每个窗口当前的排队长度。
  document.getElementById("window-list").innerHTML = point.window_queues
    .map((item) => `<div class="window-item">窗口 ${item.window_id}<br>排队人数: <strong>${item.queue_length}</strong></div>`)
    .join("");
}

function renderTables(point) {
  // 渲染餐桌占用网格，busy 类会触发不同颜色。
  document.getElementById("table-grid").innerHTML = point.tables
    .map((table) => `
      <div class="table-seat ${table.occupied ? "busy" : ""}">
        ${table.occupied ? `桌${table.table_id}<br>学生${table.student_id}` : `桌${table.table_id}<br>空闲`}
      </div>
    `)
    .join("");
}

function buildChart() {
  // 创建折线图实例，播放过程中会持续往图中追加新数据点。
  const ctx = document.getElementById("timeline-chart");
  chart = new Chart(ctx, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        { label: "系统总人数", data: [], borderColor: "#0f766e", tension: 0.3 },
        { label: "排队总人数", data: [], borderColor: "#f59e0b", tension: 0.3 },
        { label: "已完成人数", data: [], borderColor: "#1e2430", tension: 0.3 },
      ],
    },
    options: {
      responsive: true,
      animation: false,
      maintainAspectRatio: false,
      scales: { y: { beginAtZero: true } },
    },
  });
}

function step() {
  // 每执行一次，就向前播放一个时间点。
  if (!simulationData || currentIndex >= simulationData.timeline.length) {
    clearInterval(timer);
    timer = null;
    return;
  }

  const point = simulationData.timeline[currentIndex];
  renderStats(point);
  renderWindows(point);
  renderTables(point);

  chart.data.labels.push(point.time);
  chart.data.datasets[0].data.push(point.system_total);
  chart.data.datasets[1].data.push(point.queue_total);
  chart.data.datasets[2].data.push(point.completed_total);
  chart.update();

  currentIndex += 1;
}

function startPlayback() {
  // 防止重复点击开始后创建多个计时器。
  if (!timer) {
    timer = setInterval(step, 400);
  }
}

async function init() {
  // 读取当前仿真编号对应的完整数据。
  const response = await fetch(`/api/simulations/${window.SIMULATION_ID}`);
  simulationData = await response.json();
  buildChart();

  if (simulationData.timeline?.length) {
    // 初始化时先展示第一个时间点，等待用户开始播放。
    renderStats(simulationData.timeline[0]);
    renderWindows(simulationData.timeline[0]);
    renderTables(simulationData.timeline[0]);
  }

  // 绑定播放器控制按钮。
  document.getElementById("start-btn").addEventListener("click", startPlayback);
  document.getElementById("pause-btn").addEventListener("click", () => {
    clearInterval(timer);
    timer = null;
  });
  document.getElementById("resume-btn").addEventListener("click", startPlayback);
  document.getElementById("reset-btn").addEventListener("click", () => {
    // 重置时需要停止计时器、清空图表并回到初始时间点。
    clearInterval(timer);
    timer = null;
    currentIndex = 0;
    chart.destroy();
    buildChart();
    if (simulationData.timeline?.length) {
      renderStats(simulationData.timeline[0]);
      renderWindows(simulationData.timeline[0]);
      renderTables(simulationData.timeline[0]);
    }
  });
  document.getElementById("end-btn").addEventListener("click", () => {
    // 结束播放后跳转到结果页。
    window.location.href = `/results/${window.SIMULATION_ID}`;
  });
}

// 页面加载后立即执行初始化。
init();
