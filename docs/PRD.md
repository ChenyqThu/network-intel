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
| url | string | 原文链接 |
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
- 日期 + 原文链接

> 设计重点：omada_impact 徽章是本产品的灵魂，要醒目但不喧宾夺主。

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

## 7.6 内容样例（供设计填充真实感）

**情报卡片样例 1（竞品新品）：**
- 来源：UniFi Store
- 标题：UniFi Express 7 上线
- 摘要：$199 的 Wi-Fi 7 一体网关，定位家庭/小微办公
- 标签：新品 / 竞品
- Impact：🔴 Threat — 直接对标 Omada 入门网关，价格更激进
- 热度：store 新上架

**情报卡片样例 2（用户舆情）：**
- 来源：Reddit r/Ubiquiti
- 标题：「从 UniFi 换到 Omada 三个月体验」
- 摘要：用户吐槽 UniFi 订阅涨价，转 Omada 后满意但抱怨 App 体验
- 标签：舆情
- Impact：🟢 Opportunity — UniFi 订阅涨价是我方拉新窗口，但需补 App 体验
- 热度：👍 382 · 💬 147

## 7.7 设计交付物期望
- 完整页面高保真设计（首页 / 日报 / 周报 / 归档）
- 核心组件库（情报卡片各状态 / 徽章 / 看板组件）
- 亮色 + 暗色两套
- 可直接交付前端实现的规范（间距/字号/色值）

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
