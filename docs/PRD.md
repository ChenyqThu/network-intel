# Network Intel 竞品情报产品 — PRD

> 版本 v1 · 2026-06-01 · 作者 Jarvis · 内部代号 `nintel`
> 配套方案文档：`docs/SOLUTION.md`（竞品 & 舆情情报产品完整方案 v1.1）
> **本 PRD 面向两类读者**：① 工程实现 ② Web 设计（Claude design）。§七「Web 设计交付包」是给设计师的专用章节。

---

## 一、产品概述

### 1.1 一句话定义
面向 TP-Link 网络产品团队的内部竞品动态 & 用户舆情情报站——每日极简增量、每周深度精选，聚合 UniFi 官方动态与全网用户声音，并给出对 Omada 的影响判断。

### 1.2 解决什么问题

| 痛点 | 现状 | 本产品 |
|------|------|--------|
| 竞品动态分散 | 团队各自零散刷 Reddit/YouTube/官网 | 一处聚合，自动筛选 |
| 舆情无沉淀 | 用户反馈看完即忘 | 结构化入库，趋势可追溯 |
| 缺我方视角 | 信息是中立的，无关联判断 | 每条标注对 Omada 的威胁/机会 |
| 触达不均 | 信息只在个人手里 | Web + 飞书 + 邮件多端触达 |

### 1.3 受众与角色
- **纯内部**：TP-Link 网络产品团队（PM、产品规划、竞品分析、渠道、市场）
- 因为内部定位，**可放开写我方视角和竞品威胁判断**，措辞不需中立化

### 1.4 非目标（明确不做）
- ❌ 不对外公开（无订阅注册、无 SEO、无营销）
- ❌ 不替代 UNIFI_CHANNELS 平台（那是竞品分析师的全维度工具，本产品是策展输出）
- ❌ 不做实时推送（按日/周节奏）
- ❌ 不做用户互动/评论（单向情报发布）

---

## 二、核心概念与数据模型

### 2.1 情报条目（Intel Item）— 核心数据单元

每条情报归一化为统一结构：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 唯一标识（去重用 content_hash） |
| source | enum | unifi_community / unifi_product / unifi_store / blog / reddit / youtube / rss / x |
| date | date | 信号产生日期 |
| title | string | 标题 |
| url | string | 原文完整链接（必填，用于出处行跳转） |
| source_domain | string | 来源域名（如 community.ui.com），出处行显示用 |
| source_tier | enum | official（ui.com 一手）/ community（reddit/yt 二手），可信度分层 |
| cite_id | int | 报告内引用编号（render 时分配，对应末尾参考列表） |
| summary | string | 一句话摘要（LLM 生成） |
| category | enum | industry（行业）/ competitor（竞品）/ sentiment（舆情）/ new_product（新品）/ pricing（定价） |
| signal_strength | enum | high / medium / low |
| omada_impact | enum | threat / opportunity / neutral / unknown |
| impact_note | string | 影响判断的一句话理由（仅 high/medium 时生成） |
| raw_metrics | json | { likes, comments, score, price_change } |

### 2.2 报告（Report）

| 字段 | 说明 |
|------|------|
| report_id | 日期 + 类型（daily/weekly） |
| type | daily（极简）/ weekly（深度） |
| date_range | 覆盖时间范围 |
| items | 关联的情报条目列表 |
| sections | 渲染后的分区内容 |
| stats | 信号量、各源贡献、热度 Top |

---

## 三、功能需求

### 3.1 数据采集（FR-1）
- **FR-1.1** 从 UNIFI_CHANNELS Supabase 增量拉取：product_releases / blog_articles / community_posts / store_variant_history
- **FR-1.2** 从个人情报流 summary.jsonl 过滤竞品/舆情/networking 条目
- **FR-1.3** 两路数据归一化为统一 Intel Item schema，写入 SQLite，按 content_hash 去重

### 3.2 智能加工（FR-2）
- **FR-2.1** Haiku 对每条 item 二次分类（category）
- **FR-2.2** Haiku 判断 omada_impact + 生成 impact_note（仅 high/medium signal）
- **FR-2.3** signal_strength 评分（基于热度指标 + 来源权重）

### 3.3 报告生成（FR-3）
- **FR-3.1 日报**：当天硬信号，竞品动态 + Top 舆情 + ≤3 行业要闻；无信号则单行说明
- **FR-3.2 周报**：五分区（竞品盘点 / 舆情趋势 / store 动向 / 行业风向 / 数据看板），含环比趋势
- **FR-3.3** 双格式渲染：Markdown（飞书）+ HTML（web/邮件）

### 3.4 发布（FR-4）
- **FR-4.1** 飞书群推送（日报/周报）
- **FR-4.2** CF Pages 静态站发布 + 历史归档
- **FR-4.3** 邮件推送（通道待定，飞书先兜底）

### 3.5 调度（FR-5）
- **FR-5.1** 日报 cron：每天 09:00 PT 采集 → 09:30 推送
- **FR-5.2** 周报 cron：每周一 09:00 PT 采集 → 09:30 推送

---

## 四、内容结构规范

### 4.1 日报内容块
```
标题区：Network Intel · {日期} · 日报
├── ⚔️ 竞品动态（0~3 条）  来源: product_releases / store / blog
├── 🗣️ 用户舆情（1~2 条）  来源: community_posts / reddit 热帖
└── 🏭 行业要闻（≤3 条）   来源: rss / x / youtube
空状态：今日无重大竞品动态
```

### 4.2 周报内容块
```
标题区：Network Intel · {周范围} · 周报
├── 1. ⚔️ 本周竞品动作盘点
│      逐条卡片：标题 / 类型标签 / omada_impact 徽章 / impact_note / 链接
├── 2. 🗣️ 用户舆情趋势
│      Omada vs UniFi 口碑对比 + 高频痛点 Top5 + 环比变化
├── 3. 🏪 store 动向
│      价格/库存/上架变化表
├── 4. 🏭 行业风向
│      趋势条目 + 一句话点评
└── 5. 📊 数据看板
       信号量统计 / 各源贡献饼图 / 热度 Top10
```

---

## 五、技术架构（实现参考）

```
两路数据源 → ingest（归一化+去重）→ SQLite
  → classify（Haiku 打标）→ render（日报/周报）
  → 发布（飞书 / CF Pages / 邮件）
```

- 项目路径：`~/Projects/network-intel/`
- DB：SQLite（nintel.db）
- LLM：CRS haiku（分类）/ sonnet（周报综合）
- Web：Cloudflare Pages（复用 health-worker wrangler）
- 详细目录结构见 `docs/SOLUTION.md` §八

---

## 六、里程碑

| Phase | 内容 | 产出 |
|-------|------|------|
| P0 | 两路数据消费层 + 入库 | nintel.db 有数据 |
| P1 | 打标 + 日报 + 飞书推送 | 日报上线 |
| P2 | CF Pages 站 + 归档 | nintel.chenge.ink |
| P3 | 周报趋势引擎 | 首份周报 |
| P4 | 邮件通道 | 邮件推送 |

---

# 七、Web 设计交付包（给 Claude design）

> 本章节是给设计师的完整 brief，独立可读。设计目标：一个**内部竞品情报站**的完整网页设计。

## 7.1 设计目标

做一个**内部团队用的竞品情报阅读站**——不是营销站，不是 dashboard 工具，而是一个「**高信息密度但读起来舒服**」的情报阅读 + 归档检索站。气质参考：Stratechery / The Information / Linear changelog 这类专业、克制、信息优先的风格。

## 7.2 品牌与调性

- **名称**：Network Intel（可设计 logo/wordmark）
- **气质**：专业、冷静、可信、信息密度高但不杂乱
- **不要**：花哨动效、营销感、卡通插画、过度渐变
- **配色建议**：以中性灰 + 一个克制的主色（深蓝/墨绿系，呼应「网络/企业」气质）；威胁/机会标注用语义色（红=threat / 绿=opportunity / 灰=neutral）
- **暗色模式**：建议支持（情报站常长时间阅读）
- **国际化**：中英文混排友好（内容中英都有），字体选型要兼顾

## 7.3 页面清单（需设计的页面）

### 页面 1：首页 / 最新报告（Home）
- 顶部：产品名 + 最新日报日期 + 切换日报/周报 tab
- 主体：最新一期报告的完整内容（日报或周报）
- 侧边/底部：历史报告入口

### 页面 2：日报详情（Daily Report）
- 三大内容块：竞品动态 / 用户舆情 / 行业要闻（见 §4.1）
- 每条情报是一张**情报卡片**（见 7.4 组件）
- 极简，一屏可览

### 页面 3：周报详情（Weekly Report）
- 五分区（见 §4.2），信息量大，需要清晰的分区导航/锚点
- 包含数据可视化区（饼图/趋势图/Top榜）
- 「本周竞品动作盘点」是核心区，需要重点设计卡片样式

### 页面 4：归档/检索（Archive）
- 历史报告列表（按日期倒序）
- 筛选器：日期范围 / 报告类型（日/周）/ 主题（竞品/舆情/行业）/ 来源
- 可选：全文检索框

### 页面 5（可选）：情报条目流（All Items）
- 不分报告，纯时间流展示所有情报条目
- 强筛选 + 标签过滤，给想「自己挖」的深度用户

## 7.4 核心组件设计

### 组件 A：情报卡片（Intel Card）— 最重要
单条情报的展示单元，需要承载：
- 来源徽章（UniFi 官方 / Reddit / YouTube / 博客…，不同来源不同视觉标识）
- 标题（可点击跳原文）
- 一句话摘要
- 分类标签（竞品/舆情/新品/定价/行业）
- **omada_impact 徽章**（threat 红 / opportunity 绿 / neutral 灰）+ impact_note 提示
- 热度指标（👍 赞 / 💬 评论 / ↑ score）
- **【强制】显式出处行（Citation Line）** — 见 §7.8，这是策展产品的灵魂

> ⚠️ **设计红线（v1 评审踩坑修正）**：每张卡片**必须有一条独立、醒目、可点击的「出处行」**，明确展示 `来源域名 · 日期 · 查看原文↗`。
> **不要**把原文链接做成标题旁一个易忽略的小 ↗ 图标——那不是策展，是信息聚合。策展报告的核心价值是「每条结论可一键溯源验证」，出处必须是卡片上的一等视觉元素，不能藏。
>
> 同时 omada_impact 徽章是本产品的判断价值，要醒目但不喧宾夺主。出处行（可信度）+ impact 徽章（判断力）= 策展的两个支柱，缺一不可。

### 组件 B：威胁/机会徽章（Impact Badge）
三态语义徽章：🔴 Threat / 🟢 Opportunity / ⚪ Neutral，hover/点击展开 impact_note。

### 组件 C：来源徽章（Source Badge）
区分 UniFi 官方源（community/store/blog/product）vs 社区源（Reddit/YouTube/X），官方源应有更「权威」的视觉权重。

### 组件 D：数据看板组件（周报用）
- 信号量统计卡
- 各源贡献饼图
- 舆情环比趋势线图
- 痛点 Top5 / 热度 Top10 榜单

### 组件 E：报告头部（Report Header）
日期、类型、覆盖范围、一句话本期摘要、分享/导出按钮。

## 7.5 交互需求
- 日报/周报 tab 切换
- 归档页筛选器（多维）
- 情报卡片点击 → 跳转原文（新窗口）
- impact_note 的展开/折叠（hover 或点击）
- 暗色/亮色切换
- 响应式：桌面优先（内部团队主要在电脑看），但移动端可读

## 7.6 内容样例（真实数据，2026-06-01 从 Supabase 拉取，链接均已验证可跳转）

> ⚠️ 设计师请用**这些真实数据 + 真实链接**做设计，不要用占位 lorem/假链接。每条都标了完整出处行，这才是设计要还原的「策展范本」。完整带引用的样例报告见 `docs/SAMPLE_REPORT.md`。

**情报卡片样例 1（竞品新品 / 固件发布）：**
- 来源徽章：🟦 UniFi 官方 · Release
- 标题：UniFi OS - Express 7　v5.1.15　`RC`
- 摘要：UniFi Express 7 发布 5.1.15 RC 版，UniFi OS 核心栈更新
- 标签：新品 / 竞品
- 热度：👁 376 浏览 · 💬 3
- Impact：🔴 Threat — Express 7 是 UniFi 主打的一体化入门网关，固件迭代节奏直接对标 Omada 入门线
- **出处行**：`🔗 community.ui.com · 2026-06-01 · 查看原文 ↗`
  → https://community.ui.com/releases/UniFi-OS-Express-7-5-1-15/8464

**情报卡片样例 2（官方博客 / 新品）：**
- 来源徽章：🟦 UniFi 官方 · Blog
- 标题：Introducing UniFi 5G Backup
- 摘要：UniFi 推出 5G 备份方案，PoE 即插，为网关提供 5G failover
- 标签：新品 / 竞品
- Impact：🔴 Threat — 5G 备份补齐了 UniFi 在 WAN 冗余上的短板，Omada 网关线需关注
- **出处行**：`🔗 blog.ui.com · 2026-05-21 · 查看原文 ↗`
  → https://blog.ui.com/article/introducing-unifi-5g-backup

**情报卡片样例 3（用户舆情 / 痛点）：**
- 来源徽章：🟩 社区 · UniFi Community
- 标题：U5G - manual carrier select / override badly needed!
- 摘要：用户强烈要求 UniFi 5G 设备增加手动运营商选择，吐槽自动选网不可控
- 标签：舆情
- 热度：👁 2
- Impact：🟢 Opportunity — UniFi 5G 选网体验是痛点，Omada 若做蜂窝备份可作为差异化卖点
- **出处行**：`🔗 community.ui.com · 2026-06-01 · 查看原文 ↗`
  → https://community.ui.com/questions/U5G-manual-carrier-select-override-badly-needed/eb165625-81e2-46b9-8dac-01d7e8339e99

## 7.7 设计交付物期望
- 完整页面高保真设计（首页 / 日报 / 周报 / 归档）
- 核心组件库（情报卡片各状态 / 徽章 / **出处行** / 看板组件 / 引用列表）
- 亮色 + 暗色两套
- 可直接交付前端实现的规范（间距/字号/色值）

## 7.8 引用与溯源规范（Citation & Sourcing）— 策展产品的灵魂

> 这是 v1 设计评审最大的缺失项。一份策展报告与普通信息聚合的本质区别 = **每条结论可溯源、可一键跳转验证**。本节是强制规范。

### 7.8.1 卡片出处行（Citation Line）— 强制
每张情报卡片**底部必须有一条独立的出处行**，三段式结构：

```
🔗 {来源域名}  ·  {日期}  ·  查看原文 ↗
   community.ui.com   2026-06-01    （整行或「查看原文」可点击，新窗口打开）
```

- **来源域名**显式展示（community.ui.com / blog.ui.com / reddit.com / youtube.com）——让读者一眼判断「一手官方」还是「二手社区」的可信度层级
- **日期**显式展示
- **链接可点击**，新窗口打开原文
- 视觉上独立成行，**不允许**只做成标题旁的小图标

### 7.8.2 来源可信度分层（视觉权重）
出处行的来源域名应有视觉分层，呼应来源徽章：
- **一手官方**（ui.com 系：community/blog/store/release）→ 较高视觉权重（如蓝色实心徽章 + 「官方」标识）
- **二手社区**（reddit/youtube/x）→ 中性视觉权重

### 7.8.3 合成结论的溯源（导语/趋势判断）— 强制
LLM 生成的综合判断（如日报导语「今日两记硬信号，一记威胁一记机会」、周报趋势结论）**必须挂来源编号**：

```
今日两记硬信号：UniFi OS 全线升 5.1.15 RC[1]，5G Backup 正式发布[2]——
一记节奏施压、一记补齐 WAN 冗余短板。
```

- 正文用上标 `[1] [2]` 编号，**点击可跳转**到对应卡片或参考列表项
- 这是「策展判断 vs AI 无源断言」的分水岭——任何合成结论都不能是无源的

### 7.8.4 报告末尾参考列表（References）— 强制
每份报告（日报/周报）末尾**统一汇总一个参考文献列表**，编号与正文上标对应：

```
参考来源
[1] UniFi OS - Express 7 v5.1.15 (RC) — community.ui.com — 2026-06-01
    https://community.ui.com/releases/UniFi-OS-Express-7-5-1-15/8464
[2] Introducing UniFi 5G Backup — blog.ui.com — 2026-05-21
    https://blog.ui.com/article/introducing-unifi-5g-backup
[3] U5G - manual carrier select badly needed — community.ui.com — 2026-06-01
    https://community.ui.com/questions/U5G-manual-carrier-select-override-badly-needed/eb165625-...
```

- 便于整体核查、导出、转发
- 设计上需要一个清晰的「参考列表」组件

### 7.8.5 数据契约要求（给工程）
为支撑上述设计，每条 Intel Item 必须携带：
- `url`（原文完整链接，必填，可点击）
- `source_domain`（如 community.ui.com，用于出处行展示）
- `source_tier`（official / community，用于可信度分层）
- `cite_id`（报告内引用编号，render 时分配）
- `date`（显示日期）

> 这些字段会写进 §2.1 Intel Item schema（见下方更新）。

---

## 八、开放问题
1. 邮件通道：内部 SMTP（需 IT）vs 飞书群兜底——倾向飞书先跑
2. 接收范围：具体哪个飞书群 / 邮件组？需订阅名单
3. Web 是否需要登录鉴权（纯内部，但 CF Pages 公网可达）→ 建议加简单 access 控制或 Cloudflare Access
4. 域名：nintel.chenge.ink 还是内部子域？

---

> PRD 完成。配合 `docs/SOLUTION.md` v1.1，§七 可直接交付 Claude design 启动网页设计。工程侧 P0 随时可启动。

---

**飞书文档**：https://www.feishu.cn/docx/TXrNdLo7uoc8mfx9NIec45Z7n8c
