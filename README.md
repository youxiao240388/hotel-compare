# 🏨 酒店多平台比价工具

> 一键搜索 10 大 OTA 平台，自动比价，找出最低价。

## ✨ 功能

- **10 平台覆盖** — 携程、美团、飞猪、去哪儿、Agoda、Booking.com、Expedia、抖音、京东、路客
- **全自动采集** — DrissionPage 接管 Chrome，绕过反爬，登录一次长期有效
- **LLM 智能解析** — DeepSeek 官方 API 提取房型名称与价格，无需手写正则
- **房型智能匹配** — N-gram 中文相似度算法，跨平台匹配同款房型
- **Web 可视化** — Flask 仪表盘，登录状态面板 + 比价结果表格，点击价格跳转实时页面
- **飞书通知** — 降价推送、定时监控
- **Docker 部署** — 一键启动，Linux/macOS/Windows 全支持

## 📦 支持的平台

| 分类 | 平台 | 采集方式 | 登录要求 |
|------|------|----------|----------|
| 🔵 国内 | 携程 | CSS 选择器 + LLM | ✅ 需登录 |
| 🟡 国内 | 美团 | CSS 选择器 + LLM | ✅ 需登录 |
| 🟠 国内 | 飞猪 | CSS 选择器 + LLM | ✅ 需登录 |
| 🟢 国内 | 去哪儿 | CSS 选择器 + LLM | ✅ 需登录 |
| 🔴 国际 | Agoda | CSS 选择器 + LLM | 较宽松 |
| 🔷 国际 | Booking.com | CSS 选择器 + LLM | 较宽松 |
| 🟣 国际 | Expedia | CSS 选择器 + LLM | 较宽松 |
| ⚫ 社交电商 | 抖音 | LLM 解析 | ✅ 需登录 |
| 🔴 电商 | 京东 | CSS 选择器 + LLM | ✅ 需登录 |
| 🟤 民宿 | 路客 | CSS 选择器 + LLM | ✅ 需登录 |

## 🚀 快速开始

### 安装

```bash
git clone https://github.com/youxiao240388/hotel-compare.git
cd hotel-compare
pip install -r requirements.txt
```

> **Windows 用户**：双击 `install.bat` 一键安装。

### 配置

```bash
# 设置 DeepSeek API Key（用于房型智能解析）
export DEEPSEEK_API_KEY="sk-xxxxxxxxxxxxxxxx"

# （可选）自定义 Chrome 路径
export CHROME_PATH="/path/to/chrome"
```

### 运行

**Web 可视化界面（推荐）：**

```bash
python main.py --web
# 浏览器访问 http://127.0.0.1:18888
```

首次使用：点击左侧平台登录按钮，在 Chrome 中完成各平台登录（仅需一次）。

**命令行模式：**

```bash
# 单次比价
python main.py --hotel "凯里亚德酒店苏州观前街店" --checkin 2026-05-04 --checkout 2026-05-05

# 引导登录
python main.py --login

# 定时监控（每6小时）
python main.py --monitor --interval 6h
```

### Docker

```bash
docker-compose up -d
# 访问 http://localhost:18888
```

## 🏗 架构

```
hotel-compare/
├── main.py                     # CLI 入口
├── config/settings.py          # 配置中心
├── src/
│   ├── browser.py              # Chrome 生命周期管理（DrissionPage）
│   ├── search.py               # 酒店搜索（搜索引擎 → 携程 ID）
│   ├── platforms/
│   │   ├── base.py             # 采集器基类
│   │   ├── ctrip.py            # 携程
│   │   ├── meituan.py          # 美团
│   │   ├── fliggy.py           # 飞猪
│   │   ├── domestic.py         # 去哪儿 / 抖音 / 京东 / 路客
│   │   └── international.py    # Agoda / Booking / Expedia
│   ├── parser/
│   │   └── extractor.py        # DeepSeek LLM 房型解析器
│   ├── matcher/
│   │   └── room_matcher.py     # N-gram 房型匹配器
│   ├── comparator/
│   │   └── engine.py           # 比价引擎
│   ├── notifier/
│   │   └── feishu.py           # 飞书通知
│   └── web/
│       ├── app.py              # Flask 后端
│       └── templates/
│           └── dashboard.html  # 仪表盘前端
└── data/history/               # 历史比价数据
```

## 🔧 关键设计决策

| 问题 | 方案 | 原因 |
|------|------|------|
| 反爬绕过 | DrissionPage 接管已有 Chrome | 复用用户登录态，无需模拟输入密码 |
| 房型解析 | DeepSeek 官方 API | 准确率远超正则，处理各平台不同格式 |
| 房型匹配 | N-gram 字符相似度 | 免下载 120MB 模型，中文房名匹配效果好 |
| 无头运行 | `--headless` + `--remote-allow-origins=*` | DrissionPage 兼容旧版 headless 协议 |

## 📋 依赖

- Python ≥ 3.10
- [DrissionPage](https://github.com/g1879/DrissionPage) — 浏览器自动化
- [Flask](https://flask.palletsprojects.com/) — Web 服务
- [DeepSeek API](https://platform.deepseek.com/) — LLM 解析
- Chrome / Chromium ≥ 120

## 📄 License

MIT
