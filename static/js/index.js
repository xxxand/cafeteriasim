// 启动页脚本：
// 负责读取表单参数，提交给后端创建一次仿真，并跳转到仿真界面。
const form = document.getElementById("config-form");

form?.addEventListener("submit", async (event) => {
  // 阻止浏览器默认提交，改为 fetch 异步提交。
  event.preventDefault();
  // 将表单数据转为普通对象，键名与后端配置字段保持一致。
  const payload = Object.fromEntries(new FormData(form).entries());

  // 请求后端创建仿真任务。
  const response = await fetch("/api/simulations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const data = await response.json();
  if (data.simulation_id) {
    // 创建成功后跳转到仿真界面。
    window.location.href = `/simulation/${data.simulation_id}`;
  }
});
