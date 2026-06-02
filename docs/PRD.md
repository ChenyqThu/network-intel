# Network Intel 竞品情报产品 — PRD

> 版本 v1 · 2026-06-01 · 作者 Jarvis · 内部代号 `nintel`
> 配套方案文档：`docs/SOLUTION.md`（竞品 & 舆情情报产品完整方案 v1.1）
> **本 PRD 面向两类读者**：① 工程实现 ② Web 设计（Claude design）。§七「Web 设计交付包」是给设计师的专用章节。

---

## 一、产品概述

### 1.1 一句话定义
面向 TP-Link 网络产品团队的内部情报站——每日极简增量、每周深度精选，同时监控 **Omada 自身舆情**（自家产品的 bug/好评/功能请求/口碑）、**竞品动态**（UniFi 新品/固件/定价）与 **行业概况**，并对每条信号给出对 Omada 的意义判断。

> ⚠️ **定位边界（重要）**：本产品**不是纯竞品跟踪**。舆情有两类，缺一不可：
> 1. **Omada 自身舆情** — r/TPLink_Omada / r/Omada_Networks / YouTube 上对自家产品的真实声音（固件 bug、功能请求、好评、痛点、流失信号）——这是日报一直有的 `[用户声音]`
> 2. **竞品舆情** — UniFi 用户痛点 / Omada vs UniFi 对比
> 两类同样重要：自身舆情是产品改进输入，竞品舆情是市场机会识别。

### 1.2 解决什么问题

| 痛点 | 现状 | 本产品 |
|------|------|--------|
| Omada 自身舆情散落 | 自家产品 bug/请求散在 r/TPLink_Omada 无人汇总 | 自动采集入库，产品改进闭环 |
| 竞品动态分散 | 团队各自零散刷 Reddit/YouTube/官网 | 一处聚合，自动筛选 |
| 舆情无沉淀 | 用户反馈看完即忘 | 结构化入库，趋势可追溯 |
| 缺我方视角 | 信息是中立的，无关联判断 | 每条标注对 Omada 的意义（自身：修复/需求；竞品：威胁/机会） |
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
| source | enum | omada_community / unifi_community / unifi_product / unifi_store / blog / reddit / youtube / rss / x |
| **subject** | enum | **omada_self（Omada 自身）/ competitor（竞品）/ industry（行业）** —— 信号谈的是谁，决定进哪个板块 |
| date | date | 信号产生日期 |
| title | string | 标题 |
| url | string | 原文完整链接（必填，用于出处行跳转） |
| source_domain | string | 来源域名（如 community.ui.com），出处行显示用 |
| source_tier | enum | official（ui.com 一手）/ community（reddit/yt 二手），可信度分层 |
| cite_id | int | 报告内引用编号（render 时分配，对应末尾参考列表） |
| summary | string | 一句话摘要（LLM 生成） |
| category | enum | 细分类：bug / feature_request / praise / pain_point / new_product / pricing / firmware / industry_trend 等 |
| signal_strength | enum | high / medium / low |
| omada_impact | enum | threat / opportunity / neutral / **needs_fix / feature_input / strength_confirm** / unknown |
| impact_note | string | 影响判断的一句话理由（仅 high/medium 时生成） |

> ⚠️ **subject 是新增的核心字段**：区分「信号谈的是 Omada 自己还是竞品」。omada_impact 语义随 subject 变：
> - subject=omada_self 时：`needs_fix`（自家 bug，需修）/ `feature_input`（功能请求，需求输入）/ `strength_confirm`（好评，优势确认）
> - subject=competitor 时：`threat`（威胁）/ `opportunity`（机会）/ `neutral`
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

### 3.2 策展引擎（FR-2，统一提示词驱动的两阶 LLM）
- **FR-2.1 Haiku 逐条总结**：对每条 item 生成摘要 + 初步分类（category）+ 提取热度指标
- **FR-2.2 Opus 策展**：从 Haiku 结果中选哪几条入报 + 排序 + 判 omada_impact + 写 impact_note + 合成顶部导语 + 分配 cite_id
- **FR-2.3** 两阶均走**统一提示词**（维护于 `prompts/`），口径一致可迭代
- **FR-2.4** 输出固定 `report.json`（Schema 见 §7.9）——引擎唯一产物

### 3.2b 人工复核（v1.2 新增）
- `report.json` 生成后落盘到待发目录，发布前可人工编辑（删误判条目/改 impact/调顺序）
- 复核模式可配：自动发布 / 人工确认后发布（内部重要报告默认后者）

### 3.3 报告生成（FR-3）
- **FR-3.1 日报**：当天硬信号，竞品动态 + Top 舆情 + ≤3 行业要闻；无信号则单行说明
- **FR-3.2 周报**：五分区（竞品盘点 / 舆情趋势 / store 动向 / 行业风向 / 数据看板），含环比趋势
- **FR-3.3** 前端读同一份 `report.json` 渲染：Web / 飞书 / 邮件三端不重复渲染逻辑

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
├── 🟢 Omada 自身舆情（0~3 条） subject=omada_self
│     来源: r/TPLink_Omada / r/Omada_Networks / YouTube
│     重点：固件 bug / 功能请求 / 高热痛点 / 明显好评
├── ⚔️ 竞品动态（0~3 条）     subject=competitor
│     来源: product_releases / store / blog / UniFi 舆情
└── 🏭 行业要闻（≤3 条）       subject=industry
      来源: rss / 分析师 / x / youtube
空状态：某板块无信号则该板块折叠或单行说明
```

> 日报三板块并列：**Omada 自身舆情放最前**（自家产品问题优先看），然后竞品，最后行业。

### 4.2 周报内容块
```
标题区：Network Intel · {周范围} · 周报
├── 1. 🟢 本周 Omada 自身舆情（subject=omada_self）
│      固件 bug 汇总 / 高频功能请求 Top5 / 好评亮点 / 流失信号
│      → 这是产品团队最该看的一区，直接输入需求/修复优先级
├── 2. ⚔️ 本周竞品动作盘点
│      UniFi 新品/固件/定价，逐条 + omada_impact 徽章 + impact_note
├── 3. 🗣️ 竞品舆情与对比
│      Omada vs UniFi 口碑对比 + UniFi 痛点 + 环比变化
├── 4. 🏪 store 动向
│      价格/库存/上架变化表
├── 5. 🏭 行业风向
│      趋势条目 + 一句话点评
└── 6. 📊 数据看板
       信号量统计 / 各源贡献饼图 / Omada vs UniFi 舆情量对比 / 热度 Top10
```

> 周报把 **Omada 自身舆情独立为第一区**——这是产品团队的核心价值（bug汇总+功能请求是直接的产品输入），不能淹在竞品对比里。

---

## 五、技术架构（v1.2 — JSON 契约流水线）

```
三块数据汇总（行业 + 舆情 + 竞品）
  → ingest（归一化 + 去重）→ SQLite
  → 统一提示词 → Haiku 逐条总结 + Opus 策展
  → 固定 report.json（引擎产物 = 前后端契约）
  → [人工复核位] → 前端渲染（web / 飞书 / 邮件 同读一份 JSON）
```

- 项目路径：`~/Projects/network-intel/`
- DB：SQLite（nintel.db）
- LLM分层：**Haiku** 逐条摘要/分类/热度（量大） + **Opus** 策展选择/排序/impact 判断/合成导语（筛选后高价值集）
- **契约**：引擎只产 `report.json`，前端只渲染；Schema 定义见 §7.9
- 人工复核：Opus 出 JSON 后可人工编辑再发（默认可配自动/手动）
- Web：Cloudflare Pages（复用 health-worker wrangler），读 JSON 渲染
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
  → https://community.ui.com/releases/UniFi-OS-Express-7-5-1-15/84641421-6507-48af-914f-c0cb5f704c76

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
    https://community.ui.com/releases/UniFi-OS-Express-7-5-1-15/84641421-6507-48af-914f-c0cb5f704c76
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

### 7.8.6 ⚠️ URL 拼接铁律（工程必读，踩坑记录）
community.ui.com 是 SPA，**任何 URL 都返 HTTP 200**（连 404 页也是 200 壳）——`curl` 根本验不出链接真假，**必须用浏览器实渲染看 title 是否 404**。
正确格式（源于 UNIFI_CHANNELS scraper 代码 + 浏览器实测）：

| 类型 | 正确格式 | 反例（都 404） |
|------|---------|------------|
| Release | `community.ui.com/releases/{slug}/{完整 release_id UUID}` | 截断 ID（/8464）✖️ 、省略 ID ✖️ |
| Question | `community.ui.com/questions/{slug}/{完整 post_id UUID}` | 省略 ID ✖️ |
| Story | `community.ui.com/stories/{slug}/{完整 id}` | 省略 ID ✖️ |
| Blog | `blog.ui.com/article/{slug}` | —（blog 有现成 canonical_url 字段，直接用） |

- **数据库里有完整 UUID**：product_releases.release_id / community_posts.post_id，拼 URL 时用完整 UUID，不要截断
- blog_articles 表有现成 `canonical_url`，直接读，不用拼

## 7.9 report.json 契约 Schema（前后端渲染契约）— 最重要

> 这是引擎与前端的**唯一接口**。引擎产出这个 JSON，前端照这个 JSON 渲染。设计师可拿这个结构直接做渲染设计，工程可拿这个结构定 render 输出。两边都以此为准。

```json
{
  "report_id": "2026-06-01-daily",
  "type": "daily",                      // daily | weekly
  "date": "2026-06-01",
  "date_range": "2026-06-01",           // 周报为 "2026-05-26~06-01"
  "generated_at": "2026-06-01T09:30:00-07:00",
  "lead": {                              // 顶部导语（Opus 合成）
    "text": "今日两记硬信号：UniFi OS 全线升 5.1.15 RC{{cite:1}}，5G Backup 正式发布{{cite:2}}——一记节奏施压、一记补齐 WAN 冗余。",
    "cite_refs": [1, 2]                  // 导语引用的 cite_id，{{cite:N}} 占位符前端渲为可点上标
  },
  "sections": [
    {
      "key": "omada_self",              // omada_self | competitor | sentiment | industry | store (周报)
      "title": "Omada 自身舆情",
      "icon": "🟢",
      "items": ["<intel_item.id>", ...]   // 引用 items 数组里的 id，保持顺序=展示顺序
    },
    {
      "key": "competitor",
      "title": "竞品动态",
      "icon": "⚔️",
      "items": ["<intel_item.id>", ...]
    }
  ],
  "items": [                             // 所有被选中的情报条目（Opus 筛选后）
    {
      "id": "unifi_release_84641421",
      "cite_id": 1,                       // 报告内引用编号，与参考列表对应
      "subject": "competitor",            // omada_self | competitor | industry（决定进哪个 section）
      "source": "unifi_community",        // 枚举见 §2.1
      "source_domain": "community.ui.com",
      "source_tier": "official",          // official | community（可信度分层）
      "source_label": "UniFi 官方 · Release",  // 来源徽章显示文本
      "title": "UniFi OS - Express 7  v5.1.15",
      "badges": ["新品", "竞品"],            // 分类标签
      "stage": "RC",                      // 可选：固件阶段 GA/RC/EA
      "summary": "UniFi Express 7 发布 5.1.15 RC，UniFi OS 核心栈更新",
      "category": "new_product",          // 见 §2.1
      "omada_impact": "threat",           // threat | opportunity | neutral | unknown
      "impact_note": "Express 7 是 UniFi 主打一体化入门网关，固件节奏对标 Omada 入门线",
      "metrics": { "views": 376, "comments": 3, "likes": null, "score": null },
      "date": "2026-06-01",
      "url": "https://community.ui.com/releases/UniFi-OS-Express-7-5-1-15/84641421-6507-48af-914f-c0cb5f704c76"
    }
  ],
  "references": [                         // 末尾参考列表（与 cite_id 一一对应）
    {
      "cite_id": 1,
      "title": "UniFi OS - Express 7 v5.1.15 (RC)",
      "source_domain": "community.ui.com",
      "date": "2026-06-01",
      "url": "https://community.ui.com/releases/UniFi-OS-Express-7-5-1-15/84641421-6507-48af-914f-c0cb5f704c76"
    }
  ],
  "stats": {                             // 数据看板（周报重点）
    "total_items": 12,
    "by_source": { "unifi_community": 5, "reddit": 4, "blog": 1, "youtube": 2 },
    "by_impact": { "threat": 3, "opportunity": 4, "neutral": 5 },
    "top_hot": [ { "id": "...", "title": "...", "score": 553 } ]
  }
}
```

**前端渲染约定**：
- `lead.text` 里的 `{{cite:N}}` 占位符→ 渲为可点击上标，跳到对应 item 或 reference
- `sections[].items` 是 id 引用，按数组顺序渲染（Opus 已排好序）
- 每个 item 底部渲出出处行：`🔗 {source_domain} · {date} · 查看原文 ↗` → `url`
- `source_tier=official` 的 item 给更高视觉权重
- `references` 渲为末尾参考列表
- 日报只用 competitor/sentiment/industry 三 section；周报额外含 store + stats 看板

**为什么这么设计**：items 扣为扁平数组 + sections 用 id 引用，是为了同一条情报可被多处引用（如既在竞品区又被导语引用）而不重复；cite_id 统一编号保证溯源一致。

---

## 八、开放问题
1. 邮件通道：内部 SMTP（需 IT）vs 飞书群兜底——倾向飞书先跑
2. 接收范围：具体哪个飞书群 / 邮件组？需订阅名单
3. Web 是否需要登录鉴权（纯内部，但 CF Pages 公网可达）→ 建议加简单 access 控制或 Cloudflare Access
4. 域名：nintel.chenge.ink 还是内部子域？

---

> PRD（v1.2）完成。配合 `docs/SOLUTION.md` v1.2 + `docs/SAMPLE_REPORT.md`，§七（含 §7.8 引用规范 + §7.9 JSON 契约）可直接交付 Claude design。工程侧 P0 随时可启动。

---

**飞书文档**：https://www.feishu.cn/docx/TXrNdLo7uoc8mfx9NIec45Z7n8c
