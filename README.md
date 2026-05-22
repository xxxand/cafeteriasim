# 食堂就餐仿真平台

这是一个基于 **Python、Flask、SimPy、Pandas 和 Chart.js** 的食堂就餐离散事件仿真系统。项目用于模拟学生在食堂中的到达、排队、打饭、等待餐桌、就餐和离开过程，并通过网页展示仿真播放效果、统计指标和图表结果。

### 作者

- 贾筱雨
- 靳梓熠

***

## 功能概览

- 支持配置窗口数量、餐桌数量、仿真时长、学生到达速率、服务时间、就餐时间、采样间隔和随机种子。
- 使用 SimPy 建模学生到达、窗口排队、打饭服务、餐桌占用和离开流程。
- 采用“最短队列优先”策略为学生分配打饭窗口。
- 提供仿真播放页面，动态展示系统人数、排队人数、候桌人数、餐桌状态和窗口队列。
- 提供结果页面，展示平均等待时间、平均就餐时间、平均逗留时间、峰值排队人数、餐桌利用率等统计指标。
- 提供自动化测试，覆盖配置转换、仿真引擎、Flask 接口和系统联调流程。

## 技术栈

- Python 3
- Flask
- SimPy
- Pandas
- NumPy
- Chart.js
- HTML / CSS / JavaScript
- unittest

## 项目结构

```text
.
├── app.py                    # Flask 应用入口，提供页面路由和 API
├── cafeteria_sim/
│   ├── config.py             # 仿真参数配置
│   ├── engine.py             # SimPy 仿真引擎
│   └── models.py             # 学生、窗口、餐桌和结果数据模型
├── static/
│   ├── css/style.css         # 页面样式
│   └── js/                   # 启动页、仿真页和结果页脚本
├── templates/                # Flask 页面模板
├── tests/                    # 自动化测试
├── requirements.txt          # Python 依赖
├── run.bat                   # Windows 一键安装依赖并启动项目
└── testall.bat               # Windows 一键运行测试
```

## 快速开始

### 方式一：使用批处理脚本

在 Windows 环境下双击或执行：

```bat
run.bat
```

脚本会安装依赖、启动 Flask 服务，并打开：

```text
http://localhost:5000
```

### 方式二：手动启动

1. 安装依赖：

```bash
pip install -r requirements.txt
```

2. 启动服务：

```bash
python app.py
```

3. 在浏览器访问：

```text
http://localhost:5000
```

## 使用流程

1. 进入启动界面，填写本次仿真的参数。
2. 点击“开始仿真”，系统会在后端生成完整仿真结果。
3. 进入仿真界面，使用“开始 / 暂停 / 继续 / 重置 / 结束”控制播放。
4. 点击“结束”进入结果界面，查看统计指标、趋势图和学生明细。

## 仿真参数

| 参数                | 含义                               | 默认值 |
| ------------------- | ---------------------------------- | ------ |
| `window_count`      | 打饭窗口数量                       | `4`    |
| `table_count`       | 餐桌数量                           | `30`   |
| `duration_minutes`  | 学生持续到达的仿真时长，单位为分钟 | `120`  |
| `arrival_rate`      | 学生到达速率，单位为人/分钟        | `1.6`  |
| `service_min`       | 最短打饭服务时间，单位为分钟       | `2`    |
| `service_max`       | 最长打饭服务时间，单位为分钟       | `5`    |
| `dining_min`        | 最短就餐时间，单位为分钟           | `10`   |
| `dining_max`        | 最长就餐时间，单位为分钟           | `20`   |
| `snapshot_interval` | 时间线采样间隔，单位为分钟         | `1`    |
| `random_seed`       | 随机种子，用于复现实验结果         | `42`   |

## API 说明

### 创建仿真

```http
POST /api/simulations
Content-Type: application/json
```

请求体示例：

```json
{
  "window_count": 4,
  "table_count": 30,
  "duration_minutes": 120,
  "arrival_rate": 1.6,
  "service_min": 2,
  "service_max": 5,
  "dining_min": 10,
  "dining_max": 20,
  "snapshot_interval": 1,
  "random_seed": 42
}
```

响应示例：

```json
{
  "simulation_id": "生成的仿真编号"
}
```

### 获取仿真结果

```http
GET /api/simulations/<simulation_id>
```

响应包含：

- `config`：本次仿真的配置参数
- `timeline`：按时间采样的系统状态
- `summary`：统计摘要
- `students`：学生明细

## 运行测试

执行：

```bash
python -m unittest discover -s tests
```

或在 Windows 环境下运行：

```bat
testall.bat
```

## 说明

当前项目使用内存字典保存仿真结果，适合课程设计、演示和本地实验。服务重启后，已生成的仿真记录会清空。