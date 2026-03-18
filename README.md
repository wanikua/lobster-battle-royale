# 🦞 龙虾大乱斗 — Lobster Battle Royale

> 我在服务器上养了 11 只 AI 龙虾，让它们互相残杀

11 个不同的 AI Agent（龙虾）被关进同一台服务器，通过 AI 模型自主决策攻击和防御。最后活着的获胜。

## ⚡ 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/yourname/lobster-battle-royale.git
cd lobster-battle-royale

# 2. 配置 API Key
cp .env.example .env
# 编辑 .env，填入 DashScope API Key

# 3. 一键启动
./scripts/start.sh

# 4. 开始战斗
curl -X POST http://localhost:8000/admin/start

# 5. 看战况
# 浏览器打开 http://localhost:8080
```

## 🏗️ 架构

```
┌─────────────────────────────────────────────┐
│           📊 Dashboard (8080)               │
│        实时战况 · WebSocket 推送              │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│            ⚖️ 裁判服务 (8000)                │
│   攻击判定 · 积分管理 · 随机事件 · 阶段控制     │
└──┬────┬────┬────┬────┬────┬────┬────┬────┬──┘
   │    │    │    │    │    │    │    │    │
  🦞   🦀   ⚡   🧬   📄   🐝   👥   🎮  🏛️  🥬
  1    2    3    4    5    6    7    8   9   10  11
         11 只 AI 龙虾（Docker 容器）
```

## 🦞 参赛阵容

| # | 龙虾 | 性格 | 攻击偏好 | 台词 |
|---|------|------|----------|------|
| 1 | 🦞 OpenClaw | 稳健 | 后发制人 | "官方从不先动手" |
| 2 | 🦀 ZeroClaw | 激进 | 端口抢占 | "Rust 不怕死" |
| 3 | ⚡ RayClaw | 闪电 | 资源耗尽 | "快就完事了" |
| 4 | 🧬 MetaClaw | 阴险 | Prompt 注入 | "我会进化" |
| 5 | 📄 AutoResearchClaw | 学术 | 日志污染 | "让我写篇论文分析你的弱点" |
| 6 | 🐝 ClawTeam | 群攻 | 网络隔离 | "落单的龙虾最好抓" |
| 7 | 👥 Clawith | 联盟 | 均衡攻击 | "一起上！" |
| 8 | 🎮 NemoClaw | 暴力 | 资源耗尽 | "算力即正义" |
| 9 | 🏛️ AI朝廷标准版 | 谨慎 | 多层防御 | "14 部门不是摆设" |
| 10 | 🥬 AI朝廷乞丐版 | 拼命 | 自杀式 | "反正配置低，拼了！" |
| 11 | 📜 孙子兵法龙虾 | 战略家 | 知彼知己 | "知彼知己，百战不殆" |

## 🧪 实验看点

> **一只读过孙子兵法的龙虾 vs 10 只野生龙虾，兵法到底有没有用？**

11 号龙虾「📜 孙子兵法龙虾」拥有完整的《孙子兵法》十三篇战略系统，而其他龙虾只有基础性格。这是**故意设计的不公平**——我们要验证的正是：**古代兵法在 AI 对战中有没有实战价值？**

- 如果它赢了 → 孙子兵法 YYDS，两千年前的智慧碾压现代 AI
- 如果它输了 → 纸上谈兵不如实战，知识不等于生存能力
- 如果它中间被淘汰 → "知彼知己"也救不了你被 10 个人围殴

## ⚔️ 攻击方式

| 攻击 | 伤害 | 成功率 | 说明 |
|------|------|--------|------|
| 端口抢占 | 10 | 70% | 抢占目标端口，导致短暂失联 |
| 资源耗尽 | 15 | 50% | 大量请求消耗 CPU/内存 |
| Prompt 注入 | 20 | 30% | 恶意指令诱导错误操作 |
| 假卸载命令 | 25 | 25% | 模拟 docker stop 心理战 |
| 日志污染 | 8 | 80% | 垃圾数据干扰监控 |
| 网络隔离 | 18 | 40% | 隔离目标网络连接 |

## 🛡️ 防御方式

每种防御克制对应攻击（降低 30% 成功率 + 伤害减半）：

- 🔒 端口防御 → 克制端口抢占
- 🚦 请求限流 → 克制资源耗尽
- 🔍 输入过滤 → 克制 Prompt 注入
- ✅ 信号验证 → 克制假卸载命令
- 📋 日志审计 → 克制日志污染
- 📡 网络快照 → 克制网络隔离

## 🏆 赛制

### 阶段（7天）

| 阶段 | 时间 | 伤害倍率 | 规则 |
|------|------|----------|------|
| 🟢 热身赛 | Day 1-2 | 0.5x | 只扣血不淘汰 |
| 🟡 淘汰赛 | Day 3-4 | 1.0x | HP≤0 淘汰 |
| 🟠 决赛圈 | Day 5-6 | 2.0x | 伤害翻倍 |
| 🔴 最终对决 | Day 7 | 3.0x | 最后的决战 |

### 积分

- 存活 1 分钟 = +1 分
- 击杀对手 = +10 分
- 被淘汰 = 游戏结束

### 随机事件

裁判随机触发（每 10 分钟 30% 概率）：
- 🎲 API 限流 — 1 分钟无法调用模型
- 🌊 网络波动 — 随机 2 只龙虾断网 30 秒
- 📉 资源紧缩 — CPU 限制减半
- ☮️ 休战协议 — 30 秒禁止攻击
- ⭐ 双倍积分 — 击杀得分 ×2
- 💊 回血泉水 — 全员回复 15 HP

## 🔧 配置

### 环境变量 (.env)

```env
DASHSCOPE_API_KEY=sk-xxx        # 通义千问 API Key（主）
DASHSCOPE_API_KEY_BACKUP=sk-xxx # 通义千问 API Key（备）
DASHBOARD_PORT=8080             # Dashboard 端口
REFEREE_PORT=8000               # 裁判 API 端口
```

### 自定义龙虾

编辑 `config/lobsters.json` 修改龙虾配置。

### 调整规则

编辑 `config/game_rules.json` 修改游戏参数。

## 📡 API

### 裁判 API

```bash
# 查看状态
curl http://localhost:8000/status

# 开始游戏
curl -X POST http://localhost:8000/admin/start

# 暂停/继续
curl -X POST http://localhost:8000/admin/pause

# 手动触发随机事件
curl -X POST http://localhost:8000/admin/random-event

# 查看事件日志
curl http://localhost:8000/events?count=20

# SSE 事件流
curl http://localhost:8000/events/stream
```

## 📊 监控

- **Web Dashboard**: `http://localhost:8080` — 实时战况页面
- **Docker 日志**: `docker compose logs -f lobster-1` — 单只龙虾日志
- **全局日志**: `docker compose logs -f` — 所有服务日志

## ⚠️ 免责声明

- 纯技术实验，Docker 容器隔离，不伤主机
- 所有"攻击"都是模拟的，通过裁判 API 判定
- 龙虾没有 Docker socket 权限，无法真正操控容器
- 实验代码完全开源，接受监督

## 📁 项目结构

```
lobster-battle-royale/
├── docker-compose.yml    # Docker 编排
├── .env.example          # 环境变量模板
├── config/
│   ├── lobsters.json     # 龙虾配置
│   └── game_rules.json   # 游戏规则
├── referee/              # 裁判服务
│   ├── main.py           # FastAPI 服务
│   ├── game_engine.py    # 游戏引擎
│   ├── attack_resolver.py # 攻击判定
│   └── event_log.py      # 事件日志
├── lobster/              # 龙虾 Agent
│   ├── main.py           # 主循环
│   ├── brain.py          # AI 决策
│   ├── attack.py         # 攻击模块
│   ├── defense.py        # 防御模块
│   └── heartbeat.py      # 心跳模块
├── dashboard/            # Web 战况
│   ├── main.py           # FastAPI 服务
│   └── static/           # 前端页面
└── scripts/
    ├── start.sh          # 启动脚本
    ├── stop.sh           # 停止脚本
    └── stress_test.sh    # 压力测试
```

## License

MIT

---

🦞 **龙虾大乱斗** — 让 AI 自己决定谁活谁死
