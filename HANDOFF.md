# 项目交接 (HANDOFF) — Network Intel (`nintel`)

## 0. 先看这个：为什么你"打不开"、目录"没内容"

- 这个全栈项目的**全部代码 + git 历史**目前只存在于一个**临时云端容器**里
  （Claude Code on the web 的沙箱），路径 `/home/claude/Projects/network-intel`。
- 我之前启动的 `localhost:8567` / `:8000` 服务**跑在这个容器内部**，你的机器/浏览器
  访问不到它的 localhost —— 这就是"打不开"的真正原因。服务确实在跑，但只在容器内可达。
- 这个容器**没有配置 git remote**，所以代码没有自动同步到你的仓库 —— 所以你
  `~/Projects/network-intel` 里是空的。

> 解决办法：把代码作为可下载文件交给你，你在**自己机器**上解开来跑（那才是你能打开的 localhost）。

## 1. 你会收到两个文件（本条消息的附件）

1. **`network-intel.bundle`** — 完整 git 仓库（含全部提交历史 + `main`/`feature` 分支）。**推荐**。
2. **`network-intel-src.tar.gz`** — 纯源码归档（仅受 git 跟踪的文件，不含 node_modules/.venv），备用。

## 2. 导入到你自己的项目

### 方式 A — git bundle（推荐，保留历史）
```bash
mkdir -p ~/Projects && cd ~/Projects
git clone /下载路径/network-intel.bundle network-intel
cd network-intel && git log --oneline      # 应看到 3 条提交，分支 main
```
若你已有一个**空的** `~/Projects/network-intel` git 仓库要接收：
```bash
cd ~/Projects/network-intel
git pull /下载路径/network-intel.bundle main
```

### 方式 B — tarball
```bash
mkdir -p ~/Projects/network-intel && cd ~/Projects/network-intel
tar xzf /下载路径/network-intel-src.tar.gz
git init && git add -A && git commit -m "import network-intel"
```

## 3. 在你自己机器上跑起来 + 验证

前置：**Python 3.11**、**Node 18+**、**make**。

```bash
cd ~/Projects/network-intel
make install     # 后端建 venv + 装依赖 + seed；前端 npm install
make api          # 终端1 → FastAPI  http://localhost:8000
make web          # 终端2 → Vite     http://localhost:5173  （这次是你本机，能打开）
make test         # 后端 48 + 前端 32 测试
```

打开 **http://localhost:5173** 验证：
- 首页（日报）：🟢 Omada 自身舆情区在最前（`待修复`/`功能需求` 徽章）、每条卡底**出处行**、
  导语可点 `¹²³` 上标、末尾参考来源。
- 切「周报」：🎯 **市场策略洞察** + **store 动向表** + **数据看板**（趋势/各源/痛点/对比）。
- `/archive` 归档筛选、`/items` 全部条目流；右上主题切换、右下 Tweaks。
- 邮件版：http://localhost:8000/api/reports/2026-W22-weekly/email

如果端口被占：`make web` 改 `cd apps/web && npm run dev -- --port 你的端口`。

## 4. 想在"新开的 Claude Code 会话"里继续

在你本机仓库（已有 remote）里开新会话，把上面解出来的内容 `git add/commit/push` 即可；
之后让那个会话的 Claude 按 `ARCHITECTURE.md` + `docs/CONTRACT.md` + `docs/DECISIONS.md` 继续。
把本文件（HANDOFF.md）直接发给它就能接上下文。

## 5. 这个项目是什么（速览）

- 单一契约 `report.json`（PRD §7.9）驱动一切；schema + 种子在 `contract/`。
- 后端 `apps/api`：Python · FastAPI · SQLite · Pydantic（引擎 ingest/classify/curate/trend/render
  + REST + 邮件渲染 + 人工复核闸门 + 可选 Haiku→Opus LLM 阶段）。**48 测试**。
- 前端 `apps/web`：React · Vite · TypeScript，像素级还原 "Dossier" 设计系统 + v2/v3 新组件
  （Omada 自身舆情区/徽章、情感 meta、置顶市场策略洞察、分区色调），5 个页面。**32 测试**。
- 详见 `README.md` / `ARCHITECTURE.md`。

## 6. 环境真话（不夸大）

- 数据是 **fixture 驱动** —— 真实上游（UNIFI_CHANNELS Supabase、omada-sentiment-monitor
  Notion）的凭证不在此沙箱；连接器已留好 `NINTEL_CONNECTOR_MODE=live` 的接入口。
- 报告内容用的是经核验的 SAMPLE_REPORT 真实数据（链接保留完整 UUID）。
- 后端代码评审用的是高强度 **Opus**（你指定的 Codex/GPT‑5.5 在此沙箱不可用），已在
  `docs/DECISIONS.md` 注明。
