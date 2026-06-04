# 方案：日报管线借鉴 jarvis 的 Layer-1 富化

> 状态：**phase-1（`key_claim` + 信号利用）已实现并提交 `a9e0bdd`**（2026-06-03）。
> **源数据阶段**（Reddit 评论 + YT transcript，经增强上游 omada-sentiment-monitor）= 下次专项；
> **过滤阈值半段**留到专门的"规则/策略"会谈。本文档 2026-06-03 拟定。

## 目标

日报信源是 **A（sentiment-monitor 的 Reddit/YouTube 社区）+ B（UniFi 官方）**。
现状 classify（Haiku）只产出 ≤60 字客观摘要 + category + signal_strength，信号太薄。
借鉴 jarvis 的分源 Layer-1 压缩手法，给 Opus 策展层喂更有纵深的输入——
尤其是竞品情报最需要的**社区共识/争议**信号。

## 参考：jarvis 怎么做的

`~/.openclaw/workspace-exec/scripts/summarize_raw.py`，每个源一套 prompt（`summarize_reddit` /
`summarize_youtube` 最相关），骨架一致：

- **人设锚定**："为网络设备软件解决方案负责人（Omada/UniFi/竞品）做情报筛选"——和本项目受众一致。
- **分源丢弃规则（返回 null）**：Reddit 丢纯招聘/纯 meme/`score<2 且 comments<3`；YouTube 丢娱乐/标题党。
- **源感知摘要结构**：Reddit = 核心(2句) + 社区主流观点(1句) + 争议点/独特洞察(1句)。
- **`key_claim`**：每条抽一句可验证的事实主张/数据点。
- **Reddit 额外**：`sentiment` + `top_insight`（评论区最有价值的一条洞察）。
- 工程：tolerant JSON 解析（直解→剥 fence→正则）+ 多 provider 容错。

## 改造范围（外科式，集中在 classify）

### A. `apps/api/prompts/classify.md` —— 源感知 + 富化
- 按来源分支（Reddit / YouTube / UniFi 官方 / 行业）给出差异化指令（单 prompt 内条件化即可，不必拆多文件）。
- 新增抽取字段：
  - `key_claim`：一句可验证的原子事实/数据点（无则 `""`）。
  - 社区类（Reddit/YouTube）：`community_view`（社区主流反应，1 句）、`top_insight`（最佳/最反共识的一条评论或争议，1 句或 `""`）。
  - `summary` 改为源感知结构（Reddit：事实 + 社区共识 + 争议）。
- 保留：`category`（本项目竞品分类法）、`signal_strength`。

### B. `apps/api/src/nintel/engine/llm.py` —— `_CLASSIFY_SCHEMA` 加字段
- classify 走 `output_config={"format":{"type":"json_schema",...}}` 强结构化输出，
  schema 必须显式列出新字段（`key_claim` / `community_view` / `top_insight`，均可选 string，默认 `""`）。

### C. `apps/api/prompts/curate_daily.md` —— 让 Opus 用上新信号
- 指示策展层据 `community_view` / `top_insight` 判定影响力：区分"个例抱怨" vs "正在形成的社区共识"。
- 用 `key_claim` 做更精准、利于去重的引用。

### D. 管线串接
- 确认 `classify.py` 把新字段写进 item payload（`intel_items.payload`）；`curate_report` 把完整 items 发给 Opus，新字段会自动可见。
- 确认 `select.py` / `shortlist.py` 不会把新字段剥掉。

## 过滤这半部分（规则会谈再定）

> 这部分碰"过滤逻辑"，与用户想单独过的规则重叠，**不在富化这轮做**。

- 把 jarvis 的**分源丢弃规则**加进 classify（丢 meme/招聘/低互动/离题）→ LLM 层智能降噪。
- 然后**放宽 `select.py` 的 Python 热度地板**（用户建议 #1）：LLM 既然能智能降噪，
  粗暴的 `min_heat` 阈值就能调低/去掉。对无热度的源（如 RSS），用相关性闸门替代热度地板。
- 阈值 + 相关性 bar 一起定。

## 时间去重（用户点名："避免重复提及，除非热度大变"）

- 审计 curate 现有的 `prior_coverage`（RAG `COLLECTION_HISTORY`）+ resurface 徽章逻辑：
  实测它是否真的压制了已报道项、且只在热度显著上升时重提。
- `key_claim` 可作跨天稳定去重键。

## YouTube 转录富化（Source A 视频）

**问题**：Source A 的 YouTube 条目（来自 Notion sentiment-monitor）目前**只有标题**（可能有简介），
**没有 transcript**，仅凭标题难判断相关性与影响。

**方案（方向已定 2026-06-03 · 修订）**：Reddit 评论/正文、YT 评论/描述**已在 Notion 页面 body**（监控已写入），
所以 **network-intel 直接读页面 body markdown**（`GET /pages/{id}/markdown`，Notion-Version `2025-09-03`，可一次性读整页），
对 shortlist 后的 ~12-15 项逐个读 → 解析 `<details>` 评论 + selftext + 「## 字幕」→ classify 抽
`community_view`/`top_insight` + 基于 transcript 的实质摘要。**大头在本项目（读 body + 进管线）**；
上游监控只剩"补 YouTube transcript 写进 body"一件小事（见 `omada-sentiment-monitor/HANDOFF-source-enrichment.md`）。
前置：`map_notion_*` 保留 `page["id"]`；本项目已有 `NOTION_TOKEN`，**无需新凭证**。

**关键：取 transcript 前必须先初筛，控制数量与成本**：
- **互动门槛**：按观看量 / 点赞数过滤，低关注视频不取。
- **时间窗口放宽到 ~1 周**：刚发布不到一天的视频一般没什么关注度，放宽窗口让热度沉淀后再判断。
- **数量上限**：限制单次取 transcript 的视频数，避免对大量视频取脚本分析。

**参考 jarvis（已核实 2026-06-03）**：jarvis **不取 transcript**——`yt_daily_*.json` 的视频对象无
transcript/captions 字段（采集 `yt_daily_tracker.py`），`summarize_youtube` 用的是
**title + description + top_comments + statistics**。
- 可借鉴：它的**互动初筛**思路，尤其 `statistics`（观看/点赞）+ **`growth_vs_history`（增速信号，比绝对观看量更能识别"正在起量"的视频）**。
- **transcript 抓取是本项目净新增能力**（YouTube Data API captions 或 youtube-transcript-api），不是从 jarvis 复制。

**待解**：YouTube Data API key；无字幕视频的兜底（回退到简介+评论）；API 配额 / 成本。

## 风险 / 注意

- classify 每条输出 token 略增 → Haiku，成本可忽略。
- json_schema 严格，加字段安全（模型会填）。
- 改完先用 daily kickstart 验证：报告能 build + 新字段有值 + curate 用上了 community_view/top_insight + 无回归，再依赖。

## 触及文件清单

| 文件 | 改动 |
|---|---|
| `apps/api/prompts/classify.md` | 源感知 + 新字段 + （规则会谈）丢弃规则 |
| `apps/api/src/nintel/engine/llm.py` | `_CLASSIFY_SCHEMA` 加字段 |
| `apps/api/prompts/curate_daily.md` | 让 Opus 用 community_view/top_insight/key_claim |
| `apps/api/src/nintel/engine/classify.py` | 新字段串接 |
| `apps/api/src/nintel/engine/select.py` | 热度地板放宽（**规则会谈**） |
| 参考 | `~/.openclaw/workspace-exec/scripts/summarize_raw.py` |
