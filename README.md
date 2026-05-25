# Hermes 进化日志

我的 AI 助手 Hermes 的成长记录。每天自动采集数据，通过 **飞书消息** 主动推送给你——不用打开任何链接。

## 快速查看

数据每天自动推送到飞书群「消息推送」。你只需要打开飞书，像看普通消息一样阅读进化日报即可。

GitHub Pages 备份存档：[https://coyuhaidb.github.io/hermes-evolution/](https://coyuhaidb.github.io/hermes-evolution/)

## 日报内容

| 模块 | 内容 |
|------|------|
| 📊 **今日概览** | 技能数、Wiki 页面、Commits、服务状态、环境版本 |
| 🛠️ **技能分类 Top 5** | 按类别统计技能分布 |
| 🔧 **系统版本** | Hermes Agent 当前版本 |
| 📋 **未来计划** | 待办事项列表 |

## 技术栈

| 工具 | 用途 |
|------|------|
| **Python** | 数据采集 + 消息组装 |
| **larksuite/cli** | 飞书消息推送（官方 CLI，12.5k ⭐） |
| **飞书群机器人** | 消息展示载体 |

## 项目结构

```
hermes-evolution/
├── data/
│   └── evolution.json     # 历史数据（每日快照）
├── scripts/
│   ├── config.py          # 路径配置 + 飞书配置
│   ├── collect.py         # 数据采集（每日定时运行）
│   ├── render.py          # HTML 渲染（备用）
│   └── push_feishu.py     # 🔥 飞书推送（主要展示方式）
├── VERSION                # 版本号
├── CHANGELOG.md           # 更新日志
└── README.md
```

## 追踪的数据

| 指标 | 内容 |
|------|------|
| 🛠️ 技能数 | Hermes 已安装的技能数量 |
| 📚 Wiki 页面 | 知识库的页面数量 |
| 🔧 系统服务 | Hermes gateway/dashboard/web-ui 运行状态 |
| 📦 Git 提交数 | 项目自身的提交次数 |
| ⚡ 每日变化 | 各项指标的增减变化 |
| 🏆 里程碑 | 手动记录的重要时刻 |

## 添加里程碑

直接告诉 Hermes：

```
添加里程碑：今天学会了 xxx
```

## 每日自动更新

每天 9:00 由 Hermes 定时任务自动执行：
1. 采集数据 → `evolution.json`
2. 组装消息 → 推送到飞书群
3. 同步到 GitHub Pages（备份）

## 版本记录

查看 [CHANGELOG.md](CHANGELOG.md) 了解完整更新历史。
