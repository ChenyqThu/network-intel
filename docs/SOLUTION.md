# 竞品 & 舆情情报产品 — 完整方案（内部版）

> 版本 v1.2 · 2026-06-01 · 作者 Jarvis
> **v1.1→v1.2 核心变更**：架构理顺为「**JSON 契约流水线**」——三块数据汇总 → 统一提示词 → Haiku 总结 + Opus 策展 → 固定 JSON → 前端渲染。新增：① 行业源补齐（行业媒体 RSS + 分析师/标准动态）② Haiku/Opus 职责分层 ③ JSON 作为引擎与前端的契约 ④ 发布前人工复核位。
> 决策基线：① 受众=仅内部团队 ② 节奏=日报极简+周报深度 ③ Web=独立轻量站（CF Pages）④ 行业源两者都补 ⑤ JSON 留人工复核位 ⑥ unifi_releases stale 挂 todo 不阻塞主线

---

## 一、背景与目标

当前「每日洞察」是 Lucien 的**个人自用情报流**，混合了 AI/开发者工具/网络行业/竞品/生活等多个主题，输出到飞书群。其中**竞品动态 + 用户舆情**这一块对整个产品团队有外部价值，但目前：

- 埋在个人情报流里，团队拿不到、看不懂筛选逻辑
- 没有独立 web 归档，无法检索历史
- 没有邮件推送，触达不了不看飞书的同事

**目标**：把这块独立成一个**面向内部团队的竞品 & 舆情情报产品**，具备：
1. 独立程序（与个人情报流解耦，独立 cron）
2. 独立 web（可检索的历史归档，CF Pages 轻量站）
3. 独立邮件推送（日报/周报触达团队）
4. 定位 = 行业概况 + 竞品动态 + 用户舆情

**内部定位红利**：受众是内部团队，可以放开写我方视角（「对 Omada 的威胁/机会」直接判断），不需要中立化措辞。

---

## 二、现有家底盘点

### 2A — 个人情报流（已有）

采集层完整，无需重写：

| 数据源 | 脚本 | 竞品/舆情价值 |
|--------|------|--------------|
| Reddit | `fetch_reddit.py` | r/Ubiquiti 标[竞品]、r/TPLink_Omada 标[用户声音] |
| YouTube | `yt_daily_tracker.py` | UniFi 关键词 + KOL 评测/新品 |
| RSS | `fetch_rss.py` | 行业概况底座 |
| 公众号 | `fetch_wechat_biz.py` | 中文行业 |
| X/Twitter | `fetch_x_timeline.py` | 行业/技术 |
| 摘要分类 | `summarize_raw.py` | Haiku 分类 + [竞品]/[用户声音] 标签 |

每日产出：`~/.openclaw/workspace-exec/data/daily-intel/raw/{date}-summary.jsonl`，schema 已标准化（`src/summary/url/tag/category/relevance/key_claim`）。

### 2B — UNIFI_CHANNELS（重大发现，v1.1 核心变更）

`~/Projects/UNIFI_CHANNELS` 是一个**完整的 Ubiquiti 竞品情报平台**（Vue3 + FastAPI + Supabase），已在生产运行。

**9 个 GitHub Action 每天自动抓取：**

| Workflow | 采集内容 | 频率（UTC）| 目标表 |
|----------|---------|-----------|--------|
| scrape-community | community.ui.com 帖子 | 09:00 | `community_posts` |
| scrape-store | store.ui.com 全品类产品、价格、库存 | 06:00 | `store_products` + 变动表 |
| scrape-blog | UniFi 官方博客文章 | 10:00 | `blog_articles` |
| scrape-unifi | UniFi 固件版本 | 08:00 | `unifi_releases`（⚠️ stale） |
| scrape-distributors | 全球 131+ 国分销商网络 | 每日 | `distributors` |
| scrape-installers | 认证安装商 | 每日 | — |
| scrape-jobs | 招聘信息（组织动向） | 每日 | — |
| scrape-sec | 10-Q/10-K 财报 | 每日 | `financial_reports` |
| scrape-techspecs | 产品技术规格 | 每日 | — |

**Supabase 实测数据（2026-06-01 本地 psql 验证）：**

| 表 | 行数 | 新鲜度 | 策展价值 |
|----|------|--------|----------|
| community_posts | 9,480 | 🟢 今天还在更新（近7天 +385） | 🔥🔥 用户舆情核心 |
| product_releases | 3,912 | 🟢 今天更新 | 🔥🔥 新品发布 |
| store_products | 全量 | 🟢 每天更新 | 🔥 定价/上架监控 |
| blog_articles | 50 | 🟡 最近 05-21 | 官方博客 |
| unifi_releases | 3,633 | 🔴 卡在 2026-02-12 | ⚠️ stale，固件版本线暂缺 |

> ⚠️ **unifi_releases stale**：`scrape-unifi` workflow 疑似 2 月后失效，已记录为独立 todo，不阻塞主线。

**连接方式**：凭证在 `~/Projects/UNIFI_CHANNELS/.env`（`DATABASE_URL`），本机 psql 直连已验证。

**架构影响**：原方案「自建 UniFi 官方源采集器」整个删除，改为直接消费 Supabase，采集成本归零，数据质量更高。

---

## 三、产品定义

**名称（暂定）**：Network Intel（内部代号 `nintel`）

**一句话**：面向 TP-Link 网络产品团队的竞品动态 & 用户舆情情报站，每日极简增量、每周深度精选。

**内容三支柱：**

| 支柱 | 主要数据源 |
|------|-----------|
| 🏭 行业概况（Wi-Fi/网络/SMB 市场趋势、技术风向） | Reddit r/networking、RSS、X/Twitter、YouTube |
| ⚔️ 竞品动态（UniFi 新品/固件/定价/定位/渠道动作） | UNIFI_CHANNELS: product_releases + store_products + blog_articles |
| 🗣️ 用户舆情（Omada vs UniFi 真实评价、痛点、口碑） | UNIFI_CHANNELS: community_posts + Reddit r/Ubiquiti + YouTube 评论 |

---

## 四、数据源设计（v1.1 重写）

### 来源 A：个人情报流 summary.jsonl（复用，含两类舆情）

直接读现有 summary.jsonl，过滤条件：
- **Omada 自身舆情（subject=omada_self，重要）**：src=reddit 且 subreddit 含 `TPLink_Omada`/`Omada_Networks`（日报标 `[用户声音]`）；src=youtube 且标题/正文含 Omada。这是自家产品的 bug/功能请求/好评/痛点/流失信号
- **竞品舆情（subject=competitor）**：src=reddit 且 subreddit 含 `Ubiquiti`（标 `[竞品]`）；src=youtube 且标题含 UniFi/Ubiquiti
- **行业（subject=industry）**：category = networking；src = rss/x 的行业条目

> ⚠️ 本产品不是纯竞品跟踪。**Omada 自身舆情是与竞品舆情并重的一级维度**，日报里一直有（r/TPLink_Omada `[用户声音]`）。自身舆情是产品改进输入（bug/功能请求），竞品舆情是市场机会识别。

### 来源 B：UNIFI_CHANNELS Supabase（v1.1 核心新增）

psql 直连，按 created_at/published_at 增量消费：

- **竞品新品（高价值）**：`product_releases` 按 release_date 增量拉取
- **官方博客**：`blog_articles` 按 published_at 增量拉取（表有现成 canonical_url）
- **用户舆情（热帖筛选）**：`community_posts` 按 published_at 增量，过滤 like_count > 50 或 comment_count > 20
- **定价/上架变动**：`store_variant_history` 按 changed_at 增量

> ⚠️ community URL 拼接铁律：`community.ui.com/{releases|questions|stories}/{slug}/{完整 UUID}`，不能截断/省略 ID（SPA 站，curl 全返 200，验证须浏览器渲染）。

### 来源 C：行业概况补齐（v1.2 新增）

当前「行业概况」只有 Lenny RSS + r/networking + X 零散，**太薄，不对口**（Lenny 是 PM newsletter）。两层补齐：

**C-1 行业媒体 RSS（高频底座，量大低成本）**——加入 fetch_rss 源列表：
- The Register（networking 板块）/ CRN / Channel Futures / SDxCentral / Network World / The Verge networking
- 面向渠道与企业网络的专业媒体，覆盖 SMB/MSP 生态

**C-2 分析师 / 标准组织（低频高信号）**：
- Wi-Fi Alliance / IEEE 802.11 标准动态（Wi-Fi 7/8 进展）
- Gartner / IDC 网络设备市场新闻稿
- 竞品 + 主要玩家财报/季报要点（Ubiquiti 已有 UNIFI_CHANNELS SEC 源；Cisco/HPE Aruba/锐捷另补）

> 实现上 C-1 走现有 `fetch_rss.py` 扩展 feed 列表（零新架构）；C-2 部分走 RSS，无 RSS 的用周期性 web_search 补。行业源产出同样归一化入 Intel Item schema。

### 数据融合统一 schema

```json
{
  "source": "unifi_community | reddit | youtube | unifi_product | unifi_store | blog",
  "date": "2026-06-01",
  "title": "...",
  "url": "...",
  "summary": "一句话摘要",
  "category": "industry | competitor | sentiment | new_product | pricing",
  "signal_strength": "high | medium | low",
  "omada_impact": "threat | opportunity | neutral | unknown",
  "raw_metrics": { "likes": 0, "comments": 0, "score": 0 }
}
```

> `omada_impact` 字段由 Haiku 判断，是内部定位红利的核心字段——对外产品不会有这个标注。

---

## 五、架构设计（v1.2 — JSON 契约流水线）

> v1.2 把架构理顺成一条流水线：**三块数据汇总 → 统一提示词 → Haiku 总结 + Opus 策展 → 固定 JSON → 前端渲染**。下方旧版数据流图保留作参考，核心新增在图后「JSON 契约 / 两阶 LLM / 人工复核」三段。

```
数据来源层
  [个人情报流 summary.jsonl]        [UNIFI_CHANNELS Supabase]
  Reddit/YT/RSS/WeChat/X           psql 增量拉取
  已有 [竞品]/[舆情] 标签           product_releases (3912行)
                                   community_posts (9480行, 日更)
                                   store_products + 价格变动
                                   blog_articles
         │                               │
         └──────────────┬────────────────┘
                        ▼
  报告引擎  ~/Projects/network-intel/
    1. ingest.py     两路数据归一化 → 统一 schema → SQLite 增量入库
    2. classify.py   Haiku 二次分类 + omada_impact 打标
    3. trend.py      周报趋势计算（环比/热度/新竞品动作）
    4. render.py     日报(极简) / 周报(深度) 两套 Jinja2 模板渲染
                        │
          ┌─────────────┴─────────────┐
          ▼                           ▼
  发布层 ① Web                  发布层 ② 邮件
  CF Pages 独立轻量站            日报/周报 HTML 邮件
  nintel.chenge.ink              通道选型见 §七
  历史归档 + 检索
```

### v1.2 流水线（权威架构）

```
【数据汇总层】三块数据归一化为 Intel Item
  行业概况            用户舆情              竞品动态
  RSS/分析师/标准     community_posts       product_releases
  (来源 A+C)         + Reddit/YT (来源A)   + blog + store (来源B)
         └────────────────┬──────────────────┘
                          ▼
  ingest.py  三块归一化 → SQLite 增量入库 + 去重
                          │
                          ▼
【策展引擎层】统一提示词驱动的两阶 LLM
  ① Haiku 逐条总结  — 体力活：摘要/分类/热度提取（所有 item）
  ② Opus 策展      — 脑力活：选哪几条/排序/omada_impact 判断/
                      写 impact_note/合成导语/分配 cite_id（仅高价值集）
                          │
                          ▼
  【固定 report.json：引擎最终产物 = 前后端契约】
   结构化 / 含完整引用 / 可离线验证
                          │
         ┌────────────────┤ ←← 【人工复核位】发布前可编辑 JSON
         ▼                ▼      (删误判/改impact/调序)
  【前端渲染】          【其他消费者】
  CF Pages 读 json     飞书推送 / 邮件
  渲染日报/周报         同读同一份 JSON
```

**核心设计：JSON 是契约**
- 引擎只产出结构化 `report.json`，前端只管渲染 —— 彻底解耦
- 前端改版不动引擎，引擎换源不动前端
- JSON 固定 → 前端可拿假 JSON 先做，引擎可离线验证
- 同一份 JSON 驱动 web/飞书/邮件三端，不重复渲染逻辑

**两阶 LLM 职责分层**
- **Haiku（便宜×量大）**：逐条摘要、初步分类、热度提取——所有 item 都过一遍
- **Opus（贵×判断）**：从 Haiku 结果中选/排序/判 omada_impact/写 impact_note/合成导语/挂 cite_id——只处理筛选后的高价值集，控成本

**人工复核位（v1.2 新增）**
- Opus 出 `report.json` 后，发布前可人工编辑（删误判条目/改 impact/调顺序），再渲染
- 内部竞品报告的 impact 判断会被同事当真，留个人工闸门更稳
- 实现：JSON 落盘到待发目录 → 可选人工 review → 确认后触发 publish（自动/手动可配）

**设计原则**：
- 采集层零修改，UNIFI_CHANNELS 和个人情报流各自独立运行
- 报告引擎独立新项目，独立 cron，不污染任何现有项目
- UNIFI_CHANNELS 作纯粹数据源，不往里加功能（它有自己的 Vue 前端和使用场景）
- Web 是独立 CF Pages 站，读 JSON 渲染，不嵌入 UNIFI_CHANNELS Vue 平台

---

## 六、报告形态

### 日报（极简 · 每天 09:30 PT）

控制在一屏，只发硬信号：

```
📅 Network Intel · 2026-06-01

⚔️ 竞品动态
· [新品] UniFi XYZ 上线 — $149，定位 SMB 接入层
· [发布] UniFi Network 10.5 GA — 主要功能：...

🗣️ 用户舆情
· r/Ubiquiti 今日最热：「Omada vs UniFi 选哪个」(↑382 | 147评论)
  → 主要痛点：Omada 缺少 xxx 功能

🏭 行业要闻（≤3条）
· ...
```

无硬信号时只发「今日无重大竞品动态」一行，不灌水。

### 周报（深度 · 每周一 09:30 PT）

五部分结构化：

1. **本周竞品动作盘点** — UniFi 新品/固件/定价/渠道，逐条 + 对 Omada 影响判断（high/medium/low threat）
2. **用户舆情趋势** — 本周 Omada vs UniFi 口碑对比，高频痛点 Top5，环比变化
3. **store 动向** — 本周价格/库存/上架变化，关键品类
4. **行业风向** — 本周值得关注的趋势 + 一句话点评
5. **数据看板** — 本周信号量、各源贡献、热度 Top 10

---

## 七、发布通道

### Web — CF Pages 独立轻量站

- 独立项目，不嵌入 UNIFI_CHANNELS（两者解耦）
- 复用 `health-worker` 的 wrangler/CF 基建（已有 wrangler.toml）
- 域名 nintel.chenge.ink
- 功能：日报/周报归档列表 + 按日期/主题/来源筛选

### 邮件通道（三个选项）

| 方案 | 推荐度 | 说明 |
|------|-------|------|
| A. 内部 SMTP（TP-Link 邮件服务器） | ⭐⭐⭐ 首选 | 正规、内部信任、可群发；需 IT 申请发信账号 |
| B. 独立 ESP（Resend/SendGrid） | ⭐⭐ 备选 | 即开即用；内部邮件走外网需评估合规 |
| C. 飞书群机器人兜底 | ⭐⭐⭐ 先用这个 | 零成本，即时触达，IT 审批期间过渡 |

> 建议：先用飞书群跑起来（C），同步走内部 SMTP 申请（A）。邮件不阻塞产品上线。

---

## 八、技术选型与目录

```
~/Projects/network-intel/
├── connectors/
│   ├── supabase_reader.py     # UNIFI_CHANNELS Supabase 增量拉取
│   └── summary_reader.py      # 读取个人情报流 summary.jsonl
├── engine/
│   ├── ingest.py              # 两路数据归一化 → SQLite 增量入库
│   ├── classify.py            # Haiku 二次分类 + omada_impact 打标
│   ├── trend.py               # 周报趋势计算（环比、热度变化）
│   └── render.py              # 日报/周报 Jinja2 模板渲染
├── publish/
│   ├── deploy_web.sh          # 推送 CF Pages
│   └── send_feishu.py         # 飞书群推送（日报/周报）
├── templates/
│   ├── daily.md.j2
│   ├── daily.html.j2
│   ├── weekly.md.j2
│   └── weekly.html.j2
├── data/
│   └── nintel.db              # SQLite：标准化入库 + 去重 + 历史
├── cron/
│   ├── daily.sh               # 每天 09:00 PT 采集 → 09:30 推送
│   └── weekly.sh              # 每周一 09:00 PT → 09:30 推送周报
└── config.yaml                # 数据源开关、接收群列表、关键词配置
```

技术栈：
- LLM：CRS haiku（分类/摘要）/ sonnet（周报趋势综合）
- DB：SQLite（轻量、可检索、便于周报环比）
- Supabase 连接：psql + python-dotenv，读 UNIFI_CHANNELS/.env 的 `DATABASE_URL`
- 模板：Jinja2，HTML 兼容主流邮件客户端
- Web 部署：Cloudflare Pages，复用 health-worker wrangler 基建

---

## 九、排期（v1.1 修订）

| Phase | 内容 | 预估 | 关键产出 |
|-------|------|------|---------|
| P0 | 写两路数据消费层（supabase_reader + summary_reader）+ ingest 入库 | 0.5 天 | nintel.db 有历史数据，两路来源验证通 |
| P1 | classify.py（Haiku 打标 + omada_impact）+ 日报 render + 飞书推送 | 0.5 天 | 日报可在飞书推送，人工验收效果 |
| P2 | CF Pages 独立站（deploy_web.sh + HTML 模板）+ 日报上线 | 0.5 天 | nintel.chenge.ink 可访问历史日报 |
| P3 | 周报趋势引擎（trend.py）+ 周报模板 + cron 接入 | 1 天 | 首份深度周报自动生成 |
| P4 | 邮件通道（内部 SMTP 申请 + send_mail.py） | 依赖 IT 审批 | 邮件推送上线 |

> v1.1 优化：P0 从「写爬虫」变成「写消费层」，工作量缩减约 60%，数据质量更高。P0+P1+P2 合计 1.5 天出 MVP。

---

## 十、风险与 Todo

| 项 | 等级 | 说明 |
|----|------|------|
| 邮件发信权限 | 🟡 中 | 内部 SMTP 需 IT 审批；飞书群先兜底 |
| Supabase 访问稳定性 | 🟢 低 | 本机 psql 直连已验证 |
| unifi_releases stale | 🟡 中 | scrape-unifi workflow 卡在 2 月 → **独立 todo，不阻塞主线** |
| 周报冷启动 | 🟢 低 | community_posts 有 9480 行历史数据可回溯 |
| UNIFI_CHANNELS 边界 | 🟢 低 | 明确：只当数据源，不加功能，两者解耦 |

---

## 十一、Jarvis 建议

1. **P0 优先写 Supabase 消费层** — 数据根基，现在成本极低（直连已通，表结构已知）
2. **community_posts 是最被低估的数据资产** — 9480 行、每天 +50、包含热度，配合 omada_impact 标注能产出真正有价值的「用户舆情趋势」
3. **用飞书群先跑，不等邮件** — IT 批邮件期间产品已能积累 2~3 周数据
4. **周报 > 日报（质量视角）** — 日报是「不断流」的存在感，真正值得打磨的是周报的 omada_impact 分析层
5. **unifi_releases 修复不急** — 固件版本是竞品节奏硬信号，等主线稳后单独 debug scrape-unifi workflow

---

> **下一步**：方案确认后，即可启动 P0——写 supabase_reader.py + summary_reader.py + ingest.py，验通两路数据消费，出首份入库结果。

---

**飞书文档**：https://www.feishu.cn/docx/Jpcod1qAfoaM7zxT03Qcy7n1nHf
