/* ============================================================
   Network Intel Design System — data + i18n
   Plain JS global (loaded after React UMD, before babel files).
   Exposes: window.LangCtx (React context), window.NIDS
   (dict + token tables + specimen samples), window.dsT helper.
   ============================================================ */
(function () {
  // ---- React contexts (React UMD already loaded) ----
  window.LangCtx = React.createContext('zh');

  // ---- i18n dictionary (dot-path keys) ----
  const DICT = {
    zh: {
      brand:{ sub:"设计系统", ver:"v3 · 2026.06" },
      ui:{ theme:"主题", lang:"语言", contents:"目录" },
      toc:{ overview:"概览", color:"颜色", type:"字体排印", space:"间距 & 圆角", elevation:"层级 & 边框", motion:"动效", icon:"图标", comp:"组件", states:"状态", skeleton:"骨架屏 & 加载", responsive:"响应式", i18n:"国际化" },
      hero:{
        eye:"NETWORK INTEL · 内部竞品 & 舆情情报站",
        title_a:"Dossier ", title_b:"设计系统",
        desc:"为「竞品 + 舆情」情报前端定义的一套克制、数据优先的编辑式语言。基于 Manrope 与单一深常绿主色，统一日报 / 周报 / 归档三类视图的 token、组件、状态与加载行为。",
        chips:["亮 / 暗双主题","中 / 英 i18n","骨架屏 + 动态加载","响应式 ≥360px","WCAG AA 对比"]
      },
      color:{
        title:"颜色", lead:"单一深常绿主色承载身份，语义色分「竞品视角」与「自家视角」两套，中性色为暖灰。所有色值随主题切换，tint 由 color-mix 在表面色上生成。",
        brand:"主色 · 品牌身份", impact:"语义色 · 竞品视角", self:"语义色 · 自家视角（v2）", senti:"情感极性", neutralH:"中性 · 暖灰阶", note:"暗色模式下语义色整体提亮一档以维持对比；tint 自动跟随表面色重算，无需手动维护两套。"
      },
      type:{
        title:"字体排印", lead:"Manrope 全字重，标题紧排（字距收紧、行高近 100%），正文 1.6 行高。数字一律用 tabular-nums 等宽对齐，便于表格与指标读数。",
        scale:"字阶", weight:"字重", numic:"等宽数字", numNote:"指标、价格、日期、计数全部启用 tabular-nums，避免跳动。",
        s_display:"展示标题", s_h1:"页面标题", s_h2:"区块标题", s_lead:"导语", s_body:"正文", s_sum:"摘要正文", s_meta:"元信息", s_mono:"等宽标注"
      },
      space:{
        title:"间距 & 圆角", lead:"8 点基准栅格，留白集中在 8 / 16 / 24。圆角分级：标签 3–4px、卡片 7–10px、洞察区块 14px、药丸全圆。", spacing:"间距阶", radius:"圆角阶"
      },
      elevation:{
        title:"层级 & 边框", lead:"卡片默认无投影——靠 1px 发丝边框与内边距成形。投影仅用于浮层（菜单 / 弹出）。",
        card:"卡片 · 发丝边框", pop:"浮层 · 弹出投影", border:"边框", borderNote:"默认 1px var(--border)，强调用 var(--border-strong)，聚焦用主色 1px + 3px 光环。"
      },
      motion:{
        title:"动效", lead:"克制、无回弹。三档时长配统一缓动曲线；进场用 fade-up，骨架屏用 shimmer。点击卡片可预览。",
        micro:"微交互", base:"默认（默认过渡）", drawer:"抽屉 / 弹窗", shimmer:"骨架 Shimmer", fadeup:"进场 Fade-up", click:"点击预览 →", easeNote:"统一缓动 cubic-bezier(0.16, 1, 0.3, 1)；尊重 prefers-reduced-motion。"
      },
      icon:{ title:"图标", lead:"24px 画板、1.8px 描边、圆角线帽的线性图标集（产品中以 Lucide 替代，品牌标使用 Omada 原生 SVG）。绝不用 emoji 或 Unicode 字符当图标。" },
      comp:{
        title:"组件", lead:"情报前端的核心构件。每个都给出实时样例 + token 标注。",
        src:"来源徽章", srcDesc:"字形识别来源 + 可信度分层标注（一手官方 / 社区二手）。",
        impact:"研判徽章", impactDesc:"竞品卡片用 威胁 / 机会 / 中性；自家卡片用 待修复 / 功能需求 / 优势确认（v2）。",
        research:"研判框", researchDesc:"高亮的策展判断块，按研判类型着色，关键词加重。",
        senti:"情感元标签", sentiDesc:"舆情卡片可显示情感极性 / 相关性 / 切换意图（来自 omada-sentiment-monitor，v3）。",
        cite:"出处行", citeDesc:"每条结论底部强制的可点击出处：编号 + 域名 + 可信度 + 日期 + 查看原文。",
        entry:"情报卡片", entryDesc:"完整 ledger 行：左侧索引轨 + 来源 + 研判 + 标题 + 标签 + 摘要 + 研判框 + 出处行。",
        lead:"导语 + 计数", leadDesc:"Opus 策展导语，{{cite}} 渲为可点上标；下方计数条汇总信号分布。",
        strategy:"市场策略洞察（v3）", strategyDesc:"周报独有的置顶战略区，文字论述型、比卡片更重，结论嵌可点溯源。",
        sechead:"区块头 + 色调", secheadDesc:"四类板块各有色调：自家(绿) / 竞品(红) / 竞品舆情(橙) / 行业(灰)。",
        table:"Store 表格", tableDesc:"价格 / 库存变化表，降价绿、涨价红、库存药丸。"
      },
      states:{
        title:"状态", lead:"交互组件的完整状态：默认 / 悬停 / 聚焦 / 禁用，加内容态：加载 / 空 / 错误。",
        rest:"默认", hover:"悬停", focus:"聚焦", disabled:"禁用", loading:"加载中", empty:"空状态", error:"错误",
        primary:"主按钮", ghost:"幽灵按钮", emptyText:"今日无重大竞品动态", errorText:"report.json 拉取失败 · 重试"
      },
      skeleton:{
        title:"骨架屏 & 动态加载", lead:"报告内容异步加载：先渲染与最终布局同构的骨架占位（shimmer），数据到位后内容以 fade-up 错峰进场。下方为可反复触发的真实演示。",
        reload:"重新加载", loading:"加载中…", ready:"就绪 · 6 条信号", net:"网络", fast:"快速", slow:"慢速 3G", patternH:"骨架占位形态", patternNote:"骨架与真实卡片同构——同样的索引轨、同样的两行标题占位、同样的间距，避免到位时布局跳动（CLS=0）。", flowH:"加载时序", flow:["1 · 触发请求，状态置忙，渲染骨架","2 · shimmer 循环提示加载中（≥300ms 才显示，避免闪烁）","3 · 数据到位，骨架卸载，卡片 fade-up 错峰进场 45ms 步进"]
      },
      responsive:{
        title:"响应式", lead:"桌面优先（≥1280 为基准工作区），向下优雅降级到平板与移动。栅格、导航与卡片在断点处重排。",
        bpH:"断点", gridH:"布局重排",
        bp:[["桌面","≥1280px","双栏：侧边导航(260–300px) + 内容流，12 栅格 16px 间隔"],["笔记本","1080–1280px","内容收窄，侧栏保留，图表两列"],["平板","640–1080px","侧栏折叠为顶部 TOC，卡片单列，图表降为单列"],["移动","360–640px","索引轨横置，徽章换行，出处行纵向堆叠，字阶下调一档"]]
      },
      i18nSec:{
        title:"国际化", lead:"全部可见文案走 key 驱动字典，运行时切换语言整页即时重渲染。当前内置 中文 / English 两套，结构可扩展更多语言。技术术语（WAN / VLAN / PoE / SSID）保持大写不本地化；数字单位内联不加空格。",
        tryH:"试试切换", tryNote:"点右上角 中 / EN 即可整页切换——本页所有文案均来自字典。", keyH:"字典样例", colKey:"Key", colZh:"中文", colEn:"English", rules:"约定：按钮 / 菜单 / 单元格用句首大写；页面标题 / 列头 / 标签页用 Title Case；不使用感叹号与 emoji。"
      },
      foot:{ name:"Network Intel Design System", note:"内部设计规范 · 仅限 TP-Link 网络产品团队。基于 Omada / Manrope 基础，为竞品 + 舆情情报前端扩展。", live:"查看原型 ↗" }
    },
    en: {
      brand:{ sub:"Design System", ver:"v3 · 2026.06" },
      ui:{ theme:"Theme", lang:"Language", contents:"Contents" },
      toc:{ overview:"Overview", color:"Color", type:"Typography", space:"Spacing & Radius", elevation:"Elevation & Border", motion:"Motion", icon:"Icons", comp:"Components", states:"States", skeleton:"Skeleton & Loading", responsive:"Responsive", i18n:"i18n" },
      hero:{
        eye:"NETWORK INTEL · COMPETITOR & SENTIMENT INTEL",
        title_a:"Dossier ", title_b:"Design System",
        desc:"A restrained, data-first editorial language for a competitor-plus-sentiment intelligence frontend. Built on Manrope and a single deep-evergreen accent, it unifies the tokens, components, states, and loading behavior across daily, weekly, and archive views.",
        chips:["Light / dark themes","zh / en i18n","Skeleton + dynamic load","Responsive ≥360px","WCAG AA contrast"]
      },
      color:{
        title:"Color", lead:"A single deep-evergreen accent carries identity. Semantic colors split into a competitor view and an own-product view; neutrals are warm-grey. Every value reacts to theme, and tints are mixed onto the surface via color-mix.",
        brand:"Accent · brand identity", impact:"Semantic · competitor view", self:"Semantic · own-product view (v2)", senti:"Sentiment polarity", neutralH:"Neutral · warm-grey ramp", note:"In dark mode semantic colors lift one step to keep contrast; tints recompute against the surface automatically — no second palette to maintain."
      },
      type:{
        title:"Typography", lead:"Manrope across all weights. Headings track tight with near-100% line-height; body runs at 1.6. All numerals use tabular-nums for aligned readouts in tables and metrics.",
        scale:"Scale", weight:"Weight", numic:"Tabular numerals", numNote:"Metrics, prices, dates, and counts all enable tabular-nums to avoid jitter.",
        s_display:"Display", s_h1:"Page title", s_h2:"Section title", s_lead:"Lead", s_body:"Body", s_sum:"Summary body", s_meta:"Meta", s_mono:"Mono label"
      },
      space:{
        title:"Spacing & Radius", lead:"An 8-point base grid; padding lands on 8 / 16 / 24. Radii step up: tags 3–4px, cards 7–10px, insight blocks 14px, pills fully round.", spacing:"Spacing scale", radius:"Radius scale"
      },
      elevation:{
        title:"Elevation & Border", lead:"Cards carry no default shadow — they are shaped by a 1px hairline border and internal padding. Shadows are reserved for overlays (menus / popovers).",
        card:"Card · hairline border", pop:"Overlay · popover shadow", border:"Borders", borderNote:"Default 1px var(--border); var(--border-strong) for emphasis; focus is the accent at 1px plus a 3px ring."
      },
      motion:{
        title:"Motion", lead:"Restrained, no bounce. Three durations share one easing curve; entrances use fade-up, skeletons use shimmer. Click a card to preview.",
        micro:"Micro", base:"Base (default transition)", drawer:"Drawer / dialog", shimmer:"Skeleton shimmer", fadeup:"Entrance fade-up", click:"Click to preview →", easeNote:"One easing: cubic-bezier(0.16, 1, 0.3, 1). Respects prefers-reduced-motion."
      },
      icon:{ title:"Icons", lead:"A line icon set on a 24px artboard, 1.8px stroke, rounded caps (Lucide substitutes in product; brand marks use native Omada SVG). Never emoji or Unicode glyphs as icons." },
      comp:{
        title:"Components", lead:"The core building blocks of the intel frontend. Each ships a live specimen plus token annotations.",
        src:"Source badge", srcDesc:"Glyph-identified source plus a credibility tier (first-party official / second-hand community).",
        impact:"Impact badge", impactDesc:"Competitor cards use Threat / Opportunity / Neutral; own-product cards use Needs Fix / Feature Input / Strength (v2).",
        research:"Research note", researchDesc:"A highlighted curation verdict block, tinted by verdict type with a bold keyword.",
        senti:"Sentiment meta", sentiDesc:"Sentiment cards may show polarity / relevance / switch-intent (from omada-sentiment-monitor, v3).",
        cite:"Citation line", citeDesc:"The mandatory clickable provenance at the foot of every claim: number + domain + tier + date + open source.",
        entry:"Intel card", entryDesc:"The full ledger row: left index rail + source + verdict + title + tags + summary + research note + citation line.",
        lead:"Lead + tally", leadDesc:"An Opus-curated lead where {{cite}} renders as a clickable superscript; the tally below sums the signal mix.",
        strategy:"Strategy insight (v3)", strategyDesc:"A weekly-only pinned strategic block — prose-driven, heavier than a card, with clickable provenance in the conclusions.",
        sechead:"Section head + tone", secheadDesc:"Four section tones: own (green) / competitor (red) / competitor-sentiment (amber) / industry (grey).",
        table:"Store table", tableDesc:"Price / stock change table — drops in green, hikes in red, stock as pills."
      },
      states:{
        title:"States", lead:"The full interaction set: rest / hover / focus / disabled, plus content states: loading / empty / error.",
        rest:"Rest", hover:"Hover", focus:"Focus", disabled:"Disabled", loading:"Loading", empty:"Empty", error:"Error",
        primary:"Primary button", ghost:"Ghost button", emptyText:"No major competitor activity today", errorText:"report.json failed to load · retry"
      },
      skeleton:{
        title:"Skeleton & Loading", lead:"Report content loads async: a skeleton isomorphic to the final layout renders first (shimmer), then content fades up in a stagger once data arrives. A repeatable live demo sits below.",
        reload:"Reload", loading:"Loading…", ready:"Ready · 6 signals", net:"Network", fast:"Fast", slow:"Slow 3G", patternH:"Skeleton shape", patternNote:"The skeleton is isomorphic to the real card — same index rail, same two-line title placeholder, same spacing — so nothing shifts on arrival (CLS = 0).", flowH:"Loading sequence", flow:["1 · Request fires, state goes busy, skeleton renders","2 · Shimmer loops (only after ≥300ms, to avoid flashing)","3 · Data arrives, skeleton unmounts, cards fade up in a 45ms stagger"]
      },
      responsive:{
        title:"Responsive", lead:"Desktop-first (≥1280 is the baseline workspace), degrading gracefully to tablet and mobile. Grid, navigation, and cards reflow at each breakpoint.",
        bpH:"Breakpoints", gridH:"Layout reflow",
        bp:[["Desktop","≥1280px","Two columns: side nav (260–300px) + content, 12-col grid at 16px gutter"],["Laptop","1080–1280px","Content narrows, side rail stays, charts two-up"],["Tablet","640–1080px","Side rail collapses to a top TOC, cards single-column, charts single"],["Mobile","360–640px","Index rail goes horizontal, badges wrap, citation stacks, type steps down one"]]
      },
      i18nSec:{
        title:"Internationalization", lead:"Every visible string is key-driven from a dictionary; switching language re-renders the whole page at runtime. zh / en ship today and the structure extends to more locales. Tech acronyms (WAN / VLAN / PoE / SSID) stay uppercase and untranslated; numeric units stay inline with no space.",
        tryH:"Try switching", tryNote:"Hit 中 / EN top-right to switch the entire page — every string here comes from the dictionary.", keyH:"Dictionary sample", colKey:"Key", colZh:"中文", colEn:"English", rules:"Conventions: sentence case for buttons / menus / cells; Title Case for page titles / column heads / tabs; no exclamation marks, no emoji."
      },
      foot:{ name:"Network Intel Design System", note:"Internal design spec · TP-Link networking product team only. Built on the Omada / Manrope foundation, extended for a competitor + sentiment intelligence frontend.", live:"Open prototype ↗" }
    }
  };

  function resolve(obj, key){
    return key.split('.').reduce((o,k)=> (o==null?undefined:o[k]), obj);
  }
  // dsT(lang, key) → string/array, falls back to zh then key
  window.dsT = function(lang, key){
    let v = resolve(DICT[lang], key);
    if (v===undefined) v = resolve(DICT.zh, key);
    return v===undefined ? key : v;
  };

  // ---- token tables (for foundation specimens) ----
  const NIDS = {
    DICT,
    colors:{
      brand:[ {name:"primary", tk:"--color-primary", light:"#0C6151", dark:"#36A88B"} ],
      impact:[
        {name:"threat", tk:"--threat", light:"#B23B4B", dark:"#E0707E"},
        {name:"opportunity", tk:"--opp", light:"#2E8259", dark:"#46B07D"},
        {name:"neutral", tk:"--neutral", light:"#7C8079", dark:"#8A9087"},
      ],
      self:[
        {name:"needs-fix", tk:"--fix", light:"#BE7320", dark:"#E0A152"},
        {name:"feature", tk:"--feat", light:"#2F6DB0", dark:"#5B97E0"},
        {name:"strength", tk:"--strength", light:"#2E8259", dark:"#46B07D"},
      ],
      neutral:[
        {name:"bg-app", tk:"--bg-app", light:"#F4F3EE", dark:"#0D0F0E"},
        {name:"bg-surface", tk:"--bg-surface", light:"#FFFFFF", dark:"#151816"},
        {name:"bg-subtle", tk:"--bg-subtle", light:"#EFEEE7", dark:"#1B1F1C"},
        {name:"border", tk:"--border", light:"#E6E3DA", dark:"#262A26"},
        {name:"border-strong", tk:"--border-strong", light:"#D4D0C4", dark:"#373C37"},
        {name:"fg-primary", tk:"--fg-primary", light:"#191B18", dark:"#E9ECE8"},
        {name:"fg-secondary", tk:"--fg-secondary", light:"#54584F", dark:"#A4ACA3"},
        {name:"fg-tertiary", tk:"--fg-tertiary", light:"#878B81", dark:"#6F776E"},
      ],
    },
    type:[
      {key:"s_display", px:46, wt:800, lh:1.02, ls:"-.03em", sample:"市场情报 Intelligence"},
      {key:"s_h1", px:30, wt:800, lh:1.05, ls:"-.025em", sample:"竞品动作盘点 Dossier"},
      {key:"s_h2", px:20, wt:800, lh:1.1, ls:"-.02em", sample:"Omada 自身舆情"},
      {key:"s_lead", px:19, wt:500, lh:1.45, ls:"-.012em", sample:"今日 UniFi 集中放量。"},
      {key:"s_body", px:16, wt:400, lh:1.6, ls:"0", sample:"双路融合 · 官方源 + Reddit 热帖"},
      {key:"s_sum", px:14.5, wt:400, lh:1.6, ls:"0", sample:"用户报告固件升级失败后自动回滚。"},
      {key:"s_meta", px:12.5, wt:600, lh:1.4, ls:".01em", sample:"community.ui.com · 2026-06-01"},
      {key:"s_mono", px:11, wt:600, lh:1.4, ls:".08em", sample:"REPORT.JSON · DAILY", mono:true},
    ],
    weights:[ {n:"Regular",w:400}, {n:"Medium",w:500}, {n:"SemiBold",w:600}, {n:"Bold",w:700}, {n:"ExtraBold",w:800} ],
    spacing:[ {n:"--sp-1",v:4}, {n:"--sp-2",v:8}, {n:"--sp-3",v:12}, {n:"--sp-4",v:16}, {n:"--sp-5",v:24}, {n:"--sp-6",v:32}, {n:"--sp-7",v:48}, {n:"--sp-8",v:64} ],
    radii:[ {n:"xs",tk:"--radius-xs",v:3}, {n:"sm",tk:"--radius-sm",v:5}, {n:"md",tk:"--radius-md",v:7}, {n:"lg",tk:"--radius-lg",v:10}, {n:"xl",tk:"--radius-xl",v:14}, {n:"pill",tk:"--radius-pill",v:999} ],
    motion:[
      {key:"micro", dur:120, label:"--dur-1"},
      {key:"base", dur:180, label:"--dur-2"},
      {key:"drawer", dur:240, label:"--dur-3"},
    ],
    icons:["activity","swords","chat","factory","target","link","external","search","calendar","clock","share","download","sun","moon","zap","barChart","store","trendUp","eye","up","mail","check","x","wrench","bulb","star","filter","inbox"],
    // specimen samples — bilingual
    samples:{
      self:{
        zh:{ title:"EAP610-Outdoor 固件升级失败回滚", sum:"用户报告 EAP610-Outdoor 固件升级失败，显示 UPGRADING 后自动回滚到旧版本，疑与管理端口配置有关。", note:"EAP610-Outdoor 升级回滚为可复现问题，建议固件团队核查升级流程与管理端口依赖。", tags:["固件bug"] },
        en:{ title:"EAP610-Outdoor firmware update fails to install", sum:"Users report the EAP610-Outdoor firmware update failing — it shows UPGRADING then rolls back to the old version, likely tied to a management-port config.", note:"The rollback is reproducible; route to the firmware team to audit the upgrade flow and management-port dependency.", tags:["firmware bug"] },
        src:"Reddit · r/TPLink_Omada", domain:"reddit.com/r/TPLink_Omada", tier:{zh:"社区一手",en:"community"}, impact:"fix", senti:"neu", rel:0.86, likes:6, comments:9
      },
      competitor:{
        zh:{ title:"UniFi OS — Express 7　v5.1.15", sum:"UniFi Express 7 跟进 UniFi OS 5.1.15 RC，核心系统栈更新。Express 系列是 UniFi 主打的一体化入门网关。", note:"Express 7 是 UniFi 入门一体网关旗舰，固件迭代节奏直接对标 Omada 入门线，需关注其功能补齐速度。", tags:["新品","竞品"] },
        en:{ title:"UniFi OS — Express 7　v5.1.15", sum:"UniFi Express 7 follows UniFi OS 5.1.15 RC with a core stack update. Express is UniFi's flagship all-in-one entry gateway.", note:"Express 7 directly targets Omada's entry line; watch how fast it closes the feature gap.", tags:["new product","competitor"] },
        src:"UniFi · Release", domain:"community.ui.com", tier:{zh:"一手官方",en:"first-party"}, impact:"threat", stage:"RC", views:376, comments:3
      },
      sentiment:{
        zh:{ title:"U5G — 急需手动运营商选择 / 覆盖", sum:"用户强烈要求 UniFi 5G 设备增加手动运营商选择功能，吐槽自动选网在多运营商环境下不可控。", note:"UniFi 5G 选网体验是真实痛点；Omada 若提供手动运营商控制，可作为差异化卖点。", tags:["竞品舆情"] },
        en:{ title:"U5G — manual carrier select / override badly needed", sum:"Users strongly request manual carrier selection on UniFi 5G gear, frustrated that auto-select is uncontrollable across carriers.", note:"Carrier-select is a real pain point; manual control on Omada cellular backup could be a differentiator.", tags:["competitor sentiment"] },
        src:"UniFi · Community", domain:"community.ui.com", tier:{zh:"官方平台",en:"official platform"}, impact:"opportunity", senti:"neg", rel:0.88, intent:true, views:2
      }
    },
    leadSample:{
      zh:{ text:"自家侧 EAP610-Outdoor 固件回滚被多用户反馈{{cite:1}}，社区高热催更 SG2218 PoE 版{{cite:2}}；竞品侧 UniFi OS 全系升 5.1.15 RC{{cite:3}}、5G Backup 正式发布{{cite:4}}。", strong:"自家两记修复信号，竞品两记节奏施压。",
      tally:[["信号 9","t-omada-none"],["自家 3","t-omada"],["威胁 2","t-threat"],["机会 2","t-opp"],["官方源 3","t-accent"]] },
      en:{ text:"On our side, EAP610-Outdoor firmware rollback is widely reported{{cite:1}} and SG2218 PoE is hotly requested{{cite:2}}; on the competitor side, UniFi OS rolls to 5.1.15 RC{{cite:3}} and 5G Backup ships{{cite:4}}.", strong:"Two own-product fixes, two competitor pressure points.",
      tally:[["9 signals","t-omada-none"],["3 own","t-omada"],["2 threat","t-threat"],["2 opp","t-opp"],["3 official","t-accent"]] }
    },
    strategySample:{
      zh:{ period:"本周 · 2026 W22", paras:[
        ["市场格局","UniFi 在低端以 Express 7{{cite:4}} 与 Cloud Gateway Fiber{{cite:5}} 扩面铺量，高端用 U7 Pro Max 降价{{cite:6}} 守住主力价位带，价格战全线铺开。"],
        ["竞品舆情缺口","与放量同步，社区端 6GHz 漫游故障{{cite:7}}与订阅涨价{{cite:8}}持续制造口碑裂缝，已出现成规模的迁移意向。"],
        ["对 Omada 的建议","中期不必正面跟进价格肉搏，应放大「本地优先 / 无订阅」叙事承接流失用户，并把 WiFi7 漫游稳定性做成可公开对标的硬指标。"]
      ], refs:[4,5,6,7,8] },
      en:{ period:"This week · 2026 W22", paras:[
        ["Market shape","UniFi widens the low end with Express 7{{cite:4}} and Cloud Gateway Fiber{{cite:5}}, while cutting the U7 Pro Max{{cite:6}} to hold its core tier — a price war across the line."],
        ["Sentiment gap","In step with the volume push, 6GHz roaming faults{{cite:7}} and subscription hikes{{cite:8}} keep cracking reputation, with switch intent now at scale."],
        ["Recommendation for Omada","Don't fight price head-on mid-term; amplify the local-first, no-subscription narrative to catch churned users, and make WiFi 7 roaming stability a publicly benchmarkable metric."]
      ], refs:[4,5,6,7,8] }
    },
    storeSample:{
      zh:[ ["U7 Pro Max","AP · Wi-Fi 7","$279","$239","-$40","down","in","有货"],["Cloud Gateway Fiber","Gateway · 10G PON",null,"$279","新上架","new","in","有货"],["UniFi Express 7","Gateway · BE9300",null,"$199","新上架","new","low","紧张"] ],
      en:[ ["U7 Pro Max","AP · Wi-Fi 7","$279","$239","-$40","down","in","In stock"],["Cloud Gateway Fiber","Gateway · 10G PON",null,"$279","New","new","in","In stock"],["UniFi Express 7","Gateway · BE9300",null,"$199","New","new","low","Low"] ],
      cols:{ zh:["产品","类别","价格","变化","库存"], en:["Product","Category","Price","Change","Stock"] }
    },
    keySample:[
      ["toc.comp","组件","Components"],
      ["comp.impact","研判徽章","Impact badge"],
      ["states.empty","空状态","Empty"],
      ["skeleton.reload","重新加载","Reload"],
      ["i18nSec.title","国际化","Internationalization"]
    ]
  };

  window.NIDS = NIDS;
})();
