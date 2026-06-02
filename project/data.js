/* ============================================================
   Network Intel — dataset (report.json contract, PRD §7.9)
   Daily 2026-06-01 = real, browser-verified content from
   docs/SAMPLE_REPORT.md. Two-source fusion:
     来源 B · UNIFI_CHANNELS Supabase (release/blog/community)
     来源 A · 个人情报流 summary.jsonl (Reddit/YouTube)
   ============================================================ */
(function () {
  // source registry: identity (glyph+label) + credibility tier
  const SRC = {
    unifi_release:   { label:"UniFi 官方", chan:"Release",   domain:"community.ui.com", tier:"official",  tierLabel:"一手官方", glyph:"unifi" },
    blog:            { label:"UniFi 官方", chan:"Blog",      domain:"blog.ui.com",      tier:"official",  tierLabel:"一手官方", glyph:"unifi" },
    unifi_community: { label:"UniFi 社区", chan:"Community", domain:"community.ui.com", tier:"official",  tierLabel:"官方平台", glyph:"unifi" },
    unifi_store:     { label:"UniFi Store",chan:"Store",     domain:"store.ui.com",     tier:"official",  tierLabel:"一手官方", glyph:"unifi" },
    unifi_product:   { label:"UniFi Store",chan:"Store",     domain:"store.ui.com",     tier:"official",  tierLabel:"一手官方", glyph:"unifi" },
    reddit:          { label:"Reddit",     chan:"r/Ubiquiti",domain:"reddit.com/r/Ubiquiti", tier:"community", tierLabel:"社区二手", glyph:"reddit" },
    youtube:         { label:"YouTube",    chan:"",          domain:"youtube.com",      tier:"community", tierLabel:"社区二手", glyph:"youtube" },
    rss:             { label:"RSS",        chan:"行业",       domain:"rss",              tier:"community", tierLabel:"社区二手", glyph:"rss" },
    x:               { label:"X",          chan:"",          domain:"x.com",            tier:"community", tierLabel:"社区二手", glyph:"x" },
  };
  function norm(it){
    const s = SRC[it.source] || {};
    return Object.assign({
      source_domain:s.domain, source_tier:s.tier, source_label:(it.source_label||`${s.label} · ${it.chan||s.chan}`),
      chan:(it.chan||s.chan), tier_label:(it.tier_label||s.tierLabel), glyph:s.glyph,
    }, it);
  }

  const rawItems = [
    /* ===== REAL daily 2026-06-01 (SAMPLE_REPORT, browser-verified URLs) ===== */
    {
      id:"d1", source:"unifi_release", date:"2026-06-01", provenance:"B",
      title:"UniFi OS — Express 7　v5.1.15", stage:"RC",
      url:"https://community.ui.com/releases/UniFi-OS-Express-7-5-1-15/84641421-6507-48af-914f-c0cb5f704c76",
      badges:["新品","竞品"], category:"new_product", omada_impact:"threat",
      summary:"UniFi Express 7 跟进 UniFi OS 5.1.15 RC，核心系统栈更新。Express 系列是 UniFi 主打的一体化入门网关。",
      impact_note:"Express 7 是 UniFi 入门一体网关旗舰，固件迭代节奏直接对标 Omada 入门线，需关注其功能补齐速度。",
      metrics:{ views:376, comments:3 },
    },
    {
      id:"d2", source:"blog", date:"2026-05-21", provenance:"B",
      title:"Introducing UniFi 5G Backup",
      url:"https://blog.ui.com/article/introducing-unifi-5g-backup",
      badges:["新品","竞品"], category:"new_product", omada_impact:"threat",
      summary:"UniFi 推出 5G 备份方案，PoE 即插，为网关提供 5G failover 连接，补齐 WAN 冗余短板。",
      impact_note:"5G Backup 直接补齐 UniFi 在 WAN 冗余 / 断网备份上的短板，Omada 网关线在企业连续性场景需对标。",
      metrics:{ note:"官方博客发布" },
    },
    {
      id:"d3", source:"unifi_community", date:"2026-06-01", provenance:"B",
      title:"U5G — manual carrier select / override badly needed!",
      url:"https://community.ui.com/questions/U5G-manual-carrier-select-override-badly-needed/eb165625-81e2-46b9-8dac-01d7e8339e99",
      badges:["舆情"], category:"sentiment", omada_impact:"opportunity",
      summary:"用户强烈要求 UniFi 5G 设备增加手动运营商选择 / 覆盖功能，吐槽当前自动选网在多运营商环境下不可控。",
      impact_note:"UniFi 5G 选网体验是真实痛点；Omada 若在 5G / 蜂窝备份方案中提供手动运营商控制，可作为差异化卖点。",
      metrics:{ views:2 },
    },
    {
      id:"d4", source:"reddit", date:"2026-05-31", provenance:"A",
      title:"Overall impressed, U7 Pro XG is hot garbage",
      url:"https://www.reddit.com/r/Ubiquiti/comments/1ts70er/overall_impressed_u7_pro_xg_is_hot_garbage/",
      badges:["舆情"], category:"sentiment", omada_impact:"opportunity",
      summary:"用户升级 10Gb 网络后对 Ubiquiti 整体满意，但抓出 U7 Pro XG AP 信号覆盖极差，换到 E7 才解决。高热度讨论。",
      impact_note:"UniFi 旗舰 AP 信号表现与定价不匹配是反复出现的舆情；Omada 高端 AP 可在「覆盖一致性」上做文章。",
      metrics:{ likes:152, comments:80 },
    },
    {
      id:"d5", source:"reddit", date:"2026-05-31", provenance:"A",
      title:"Got tired of their slow internet so I upgraded it",
      url:"https://www.reddit.com/r/Ubiquiti/comments/1trzyy3/got_tired_of_their_slow_internet_so_i_upgraded_it/",
      badges:["舆情","竞品"], category:"sentiment", omada_impact:"neutral",
      summary:"用户在酒店把 Aruba 设备换成 Ubiquiti 方案，网速从 5Mbps 提升到 100+Mbps。高热度帖。",
      impact_note:"Aruba → Ubiquiti 的迁移案例，反映 SMB 市场对性价比方案的持续需求；Omada 同样是 Aruba Instant On 的替代选项，可关注该类换机场景。",
      metrics:{ likes:553, comments:82 },
    },
    {
      id:"d6", source:"youtube", chan:"Unified IT", date:"2026-05-31", provenance:"A",
      title:"UniFi 网络架构与基础知识系列",
      url:"https://www.youtube.com/watch?v=SDcPaKXC_u8",
      badges:["行业"], category:"industry", omada_impact:"neutral",
      summary:"KOL 频道系统介绍 UniFi 网络架构，高播放高认可，反映 UniFi 生态的内容营销势能。",
      impact_note:"UniFi 的 KOL / 社区内容生态是其品牌护城河，Omada 可参考其教程化内容运营。",
      metrics:{ views:7083, likes:468 },
    },

    /* ===== broader pool for weekly / archive / all-items ===== */
    {
      id:"w1", source:"unifi_store", date:"2026-05-30", provenance:"B",
      title:"UniFi Express 7 上线 — $199 Wi-Fi 7 一体网关",
      url:"https://store.ui.com/us/en/products/unifi-express-7",
      badges:["新品","竞品"], category:"new_product", omada_impact:"threat",
      summary:"Ubiquiti 上架 Express 7：BE9300 Wi-Fi 7、内置 UniFi OS，定位家庭与小微办公的一体化网关，售价 $199。",
      impact_note:"直接对标 Omada 入门级网关 + AP 组合，价格更激进、安装更傻瓜化。建议评估入门 SKU 的捆绑定价。",
      metrics:{ note:"new listing" },
    },
    {
      id:"w2", source:"unifi_product", date:"2026-05-28", provenance:"B",
      title:"UniFi 推出 Cloud Gateway Fiber（10G PON）",
      url:"https://store.ui.com/us/en/products/ucg-fiber",
      badges:["新品","竞品"], category:"new_product", omada_impact:"threat",
      summary:"面向 FTTH 部署的 10G PON 网关，集成 ONU 与路由，瞄准运营商与多住户场景，$279。",
      impact_note:"切入我方尚薄弱的 PON / 运营商网关市场。需评估 Omada 在 GPON 网关侧的产品缺口。",
      metrics:{ note:"new listing" },
    },
    {
      id:"w3", source:"blog", date:"2026-05-28", provenance:"B",
      title:"UniFi Network 10.5 GA — DPI 重构与 IPv6 全面默认",
      url:"https://blog.ui.com/article/introducing-unifi-network-10-5",
      badges:["固件","竞品"], category:"competitor", omada_impact:"neutral",
      summary:"官方博客发布 Network 10.5 正式版：重写的 DPI 引擎、IPv6 默认开启、Zone-Based Firewall GA。",
      impact_note:"Zone-Based Firewall 转正补齐了企业侧短板，与 Omada SDN 的防火墙能力差距缩小，需跟进路线图对齐。",
      metrics:{ note:"官方博客发布" },
    },
    {
      id:"w4", source:"unifi_store", date:"2026-05-30", provenance:"B",
      title:"U7 Pro Max 降价 $40，多区域同步调整",
      url:"https://store.ui.com/us/en/products/u7-pro-max",
      badges:["定价","竞品"], category:"pricing", omada_impact:"threat",
      summary:"旗舰 AP U7 Pro Max 从 $279 下调至 $239，美 / 欧 / 澳三区同步。Store 变动记录显示为长期价。",
      impact_note:"高端 AP 价格下探挤压 EAP772 价位带。渠道侧需关注分销商报价跟随情况。",
      metrics:{ note:"-$40" },
    },
    {
      id:"w5", source:"unifi_community", date:"2026-05-29", provenance:"B",
      title:"大量用户报告 U7 系列 6GHz 漫游掉线",
      url:"https://community.ui.com/questions/",
      badges:["舆情"], category:"sentiment", omada_impact:"opportunity",
      summary:"community.ui.com 一周内多个高热帖反映 10.4 固件后 6GHz 漫游不稳、客户端粘滞，官方尚未给出修复时间。",
      impact_note:"竞品稳定性口碑受损窗口。我方应确保 WiFi7 漫游测试数据可公开，并在论坛温和引导。",
      metrics:{ comments:213 },
    },
    {
      id:"w6", source:"reddit", date:"2026-05-29", provenance:"A",
      title:"「从 UniFi 换到 Omada 三个月体验」",
      url:"https://www.reddit.com/r/Ubiquiti/",
      badges:["舆情"], category:"sentiment", omada_impact:"opportunity",
      summary:"r/Ubiquiti 高赞长帖：用户因 UniFi 订阅与云端策略涨价转投 Omada，硬件满意但抱怨手机 App 体验与 OTA 速度。",
      impact_note:"UniFi 订阅涨价是我方拉新窗口期。痛点集中在 App 体验——应作为下季度 App 迭代的输入。",
      metrics:{ likes:382, comments:147 },
    },
    {
      id:"w7", source:"reddit", date:"2026-05-26", provenance:"A",
      title:"「UniFi 的多站点管理对 MSP 还是太弱」",
      url:"https://www.reddit.com/r/Ubiquiti/",
      badges:["舆情"], category:"sentiment", omada_impact:"opportunity",
      summary:"MSP 用户吐槽 UniFi 缺乏成熟的多租户与计费，被迫自建脚本；评论区点名 Omada PRO 的白标多租户。",
      impact_note:"Omada PRO 的 MSP 定位获自发认可，可强化 MSP 渠道叙事与白标卖点。",
      metrics:{ likes:201, comments:64 },
    },
    {
      id:"w8", source:"reddit", date:"2026-05-29", provenance:"A",
      title:"r/networking：「中小企业放弃订阅制控制器的趋势」",
      url:"https://www.reddit.com/r/networking/",
      badges:["行业"], category:"industry", omada_impact:"opportunity",
      summary:"讨论帖汇总多家 SMB 因 SaaS 网络管理年费上涨回归本地 / 一次性授权方案，UniFi 与 Omada 同被点名为替代选项。",
      impact_note:"行业级顺风——「去订阅化」叙事利好我方授权模式，值得做成内容。",
      metrics:{ likes:156, comments:89 },
    },
    {
      id:"w9", source:"rss", source_label:"RSS · Wi-Fi Alliance", date:"2026-05-28", provenance:"A",
      title:"Wi-Fi 8（802.11bn）首批草案聚焦确定性时延",
      url:"https://www.wi-fi.org/",
      badges:["行业"], category:"industry", omada_impact:"neutral",
      summary:"IEEE 公布 Wi-Fi 8 早期方向：不再堆速率，转向可靠性与确定性低时延（UHR），面向工业与 AR/VR。",
      impact_note:null,
      metrics:{ note:"行业草案" },
    },
    {
      id:"w10", source:"youtube", chan:"Crosstalk Solutions", date:"2026-05-30", provenance:"A",
      title:"「2026 SMB 网络该选谁」UniFi / Omada / Aruba 横评",
      url:"https://www.youtube.com/@CrosstalkSolutions",
      badges:["竞品","行业"], category:"competitor", omada_impact:"opportunity",
      summary:"知名 KOL 横评三家，认为 Omada 在纯本地部署与一次性授权上对预算敏感客户更友好。",
      impact_note:"第三方背书强化了我方「无订阅、本地优先」卖点，可用于渠道与市场素材。",
      metrics:{ views:48200 },
    },
  ].map(norm);

  const byId = Object.fromEntries(rawItems.map(i => [i.id, i]));

  // ---- daily report (latest) ----
  const dailyReport = {
    report_id:"2026-06-01-daily", type:"daily", date:"2026-06-01",
    dateLabel:"2026 年 6 月 1 日 · 日报",
    generated:"09:30 PT 生成", source_line:"report.json · daily",
    lead:"今日 UniFi 集中放量——UniFi OS 全系列升级 5.1.15 RC{{cite:1}}，5G Backup 正式发布{{cite:2}}；社区侧 5G 选网体验成为新痛点{{cite:3}}，旗舰 E7 / U7 Pro XG 信号表现持续被质疑{{cite:4}}；同时有用户从 Aruba 迁移到 Ubiquiti{{cite:5}}。",
    lead_strong:"两记硬信号施压，两记差异化机会。",
    sections:[
      { key:"competitor", title:"竞品动态", icon:"swords",  desc:"UniFi 官方新品 / 固件 / 发布动作", items:["d1","d2"] },
      { key:"sentiment",  title:"用户舆情", icon:"chat",    desc:"双路融合 · 官方社区 + Reddit 热帖", items:["d3","d4","d5"] },
      { key:"industry",   title:"行业要闻", icon:"factory", desc:"KOL / 媒体 · 生态与内容势能", items:["d6"] },
    ],
    citeOrder:["d1","d2","d3","d4","d5","d6"],
    tally:{ signals:6, threat:2, opp:2, neutral:2, official:3 },
  };

  // ---- weekly report (latest) ----
  const weeklyReport = {
    report_id:"2026-W22-weekly", type:"weekly",
    rangeLabel:"2026 年第 22 周", date_range:"2026-05-25 — 2026-05-31",
    generated:"周一 09:30 PT 生成", source_line:"report.json · weekly",
    lead:"本周 UniFi 在低端发力（Express 7{{cite:1}} / Cloud Gateway Fiber{{cite:2}}）同时高端降价（U7 Pro Max −$40{{cite:3}}），价格战意图明显；社区端 6GHz 漫游故障{{cite:4}}与订阅涨价持续制造我方拉新窗口{{cite:5}}。",
    lead_strong:"低端围堵 + 高端降价，价格战全面铺开。",
    sections:[
      { key:"competitor", title:"本周竞品动作盘点", icon:"swords",  desc:"UniFi 新品 / 固件 / 定价 / 渠道", items:["w1","w2","w3","w4"] },
      { key:"sentiment",  title:"用户舆情趋势",     icon:"chat",    desc:"双路融合 · Omada vs UniFi 口碑", items:["w5","w6","w7"] },
      { key:"industry",   title:"行业风向",         icon:"factory", desc:"趋势条目 + 一句话点评", items:["w8","w9","w10"] },
    ],
    citeOrder:["w1","w2","w4","w5","w6","w3","w7","w8","w9","w10"],
    store:[
      { product:"U7 Pro Max", cat:"AP · Wi-Fi 7", from:279, to:239, change:"-$40", dir:"down", stock:"in" },
      { product:"Cloud Gateway Fiber", cat:"Gateway · 10G PON", from:null, to:279, change:"新上架", dir:"new", stock:"in" },
      { product:"UniFi Express 7", cat:"Gateway · BE9300", from:null, to:199, change:"新上架", dir:"new", stock:"low" },
      { product:"U6+", cat:"AP · Wi-Fi 6", from:99, to:99, change:"缺货", dir:"flat", stock:"out" },
      { product:"USW Pro Max 24 PoE", cat:"Switch", from:649, to:599, change:"-$50", dir:"down", stock:"in" },
    ],
    dashboard:{
      signals:14, signalsDelta:+3, threats:3, opps:6, neutral:5,
      newCompetitor:2, newCompetitorDelta:+1, avgHeat:118, avgHeatDelta:-8,
      sources:[
        { key:"unifi_community", label:"UniFi 官方源", count:6, color:"var(--color-primary)" },
        { key:"reddit",          label:"Reddit",      count:4, color:"color-mix(in oklab, var(--color-primary) 55%, var(--bg-app))" },
        { key:"youtube",         label:"YouTube",     count:2, color:"var(--fg-tertiary)" },
        { key:"rss",             label:"RSS / X",     count:2, color:"var(--border-strong)" },
      ],
      sentimentTrend:[
        { wk:"W15", omada:54, unifi:62 },{ wk:"W16", omada:55, unifi:60 },
        { wk:"W17", omada:57, unifi:61 },{ wk:"W18", omada:58, unifi:56 },
        { wk:"W19", omada:60, unifi:53 },{ wk:"W20", omada:61, unifi:51 },
        { wk:"W21", omada:63, unifi:50 },{ wk:"W22", omada:66, unifi:47 },
      ],
      vs:{ omada:66, unifi:47 },
      pains:[
        { name:"6GHz 漫游 / 粘滞", count:213, of:213 },
        { name:"订阅 & 云端涨价", count:168, of:213 },
        { name:"手机 App 体验", count:141, of:213 },
        { name:"多租户 / MSP 能力弱", count:96, of:213 },
        { name:"旗舰 AP 信号覆盖", count:80, of:213 },
      ],
      topHeat:[
        { id:"w6", v:529 },{ id:"w7", v:265 },{ id:"w8", v:245 },
        { id:"w5", v:213 },{ id:"w10", v:48200, fmt:"views" },
      ],
    },
  };

  // ---- archive ----
  const archive = [
    { id:"2026-06-01-daily",  type:"daily",  date:"2026-06-01", title:"UniFi 集中放量：Express 7 RC + 5G Backup + 选网痛点", excerpt:"两记硬信号施压，两记差异化机会。竞品 2 · 舆情 3 · 行业 1。", signals:6, threats:2, opps:2, themes:["competitor","sentiment","new_product","industry"] },
    { id:"2026-W22-weekly",   type:"weekly", date:"2026-05-31", title:"第 22 周深度：低端围堵 + 高端降价，价格战全面铺开", excerpt:"Express 7 / Cloud Gateway Fiber + U7 Pro Max 降价。舆情拉新窗口持续。", signals:14, threats:3, opps:6, themes:["competitor","sentiment","pricing","industry"] },
    { id:"2026-05-30-daily",  type:"daily",  date:"2026-05-30", title:"U7 Pro Max 降价 $40 · KOL 横评利好我方", excerpt:"高端 AP 价格下探；Crosstalk 横评强化本地优先卖点。", signals:4, threats:1, opps:2, themes:["pricing","competitor"] },
    { id:"2026-05-29-daily",  type:"daily",  date:"2026-05-29", title:"6GHz 漫游故障发酵 · 去订阅化趋势", excerpt:"竞品稳定性口碑受损窗口；r/networking 去订阅讨论。", signals:5, threats:0, opps:3, themes:["sentiment","industry"] },
    { id:"2026-05-28-daily",  type:"daily",  date:"2026-05-28", title:"Cloud Gateway Fiber（10G PON）切入运营商市场", excerpt:"竞品补 PON 网关短板，我方存在产品缺口。", signals:3, threats:1, opps:0, themes:["new_product","industry"] },
    { id:"2026-05-27-daily",  type:"daily",  date:"2026-05-27", title:"U6+ 多区域缺货 · 渠道替换窗口", excerpt:"入门 AP 断货超两周，建议备货同价位 EAP。", signals:2, threats:0, opps:1, themes:["pricing","sentiment"] },
    { id:"2026-W21-weekly",   type:"weekly", date:"2026-05-24", title:"第 21 周深度：订阅涨价余波 + MSP 口碑分化", excerpt:"UniFi 订阅政策持续发酵；Omada PRO 多租户获自发认可。", signals:12, threats:2, opps:5, themes:["sentiment","competitor","pricing"] },
    { id:"2026-05-23-daily",  type:"daily",  date:"2026-05-23", title:"今日无重大竞品动态", excerpt:"仅 1 条行业要闻，无硬信号。", signals:1, threats:0, opps:0, themes:["industry"], empty:true },
    { id:"2026-W20-weekly",   type:"weekly", date:"2026-05-17", title:"第 20 周深度：Network 10.5 Beta + 防火墙补强", excerpt:"竞品企业侧能力补齐；社区对 DPI 重构反馈两极。", signals:11, threats:2, opps:3, themes:["competitor","sentiment"] },
  ];

  window.NI = {
    SRC, items:rawItems, byId, dailyReport, weeklyReport, archive,
    CAT:{
      industry:{ zh:"行业", en:"Industry" }, competitor:{ zh:"竞品", en:"Competitor" },
      sentiment:{ zh:"舆情", en:"Sentiment" }, new_product:{ zh:"新品", en:"New Product" },
      pricing:{ zh:"定价", en:"Pricing" },
    },
  };
})();
