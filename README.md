# Network Intel (`nintel`)

> 面向 TP-Link 网络产品团队的内部竞品动态 & 用户舆情情报站
> 每日极简增量 · 每周深度精选 · 聚合 UniFi 官方动态与全网用户声音，并标注对 Omada 的影响

## 这是什么

把现有「每日洞察」里最有外部价值的**竞品 + 舆情**部分，独立成一个面向内部团队的情报产品：

- **独立程序** — 与个人情报流解耦，独立 cron
- **独立 Web** — 可检索的历史归档（CF Pages 轻量站）
- **多端推送** — 飞书群 + 邮件（日报/周报）

## 数据来源

| 来源 | 内容 |
|------|------|
| `UNIFI_CHANNELS` Supabase | UniFi 官方一手源：product_releases / community_posts / store / blog（GitHub Action 每天爬取） |
| 个人情报流 summary.jsonl | Reddit / YouTube / RSS / X 中的竞品/舆情/networking 条目 |

## 文档

| 文档 | 说明 |
|------|------|
| [`docs/SOLUTION.md`](docs/SOLUTION.md) | 完整方案 v1.1（架构、数据源、排期、风险） |
| [`docs/PRD.md`](docs/PRD.md) | 产品需求文档（数据模型、功能需求、§七 Web 设计交付包） |

## 状态

📋 **方案 & PRD 已定稿** — 工程实现（P0）待启动。

## 里程碑

| Phase | 内容 | 状态 |
|-------|------|------|
| P0 | 两路数据消费层 + 入库 | ⏳ 待启动 |
| P1 | Haiku 打标 + 日报 + 飞书推送 | — |
| P2 | CF Pages 站 + 归档 | — |
| P3 | 周报趋势引擎 | — |
| P4 | 邮件通道 | — |
