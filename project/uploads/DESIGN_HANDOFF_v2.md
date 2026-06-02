# Network Intel — 设计 Handoff v2

> 给 Claude design · 2026-06-01
> 基于当前 demo 截图 review，整理「哪里做对了」和「哪里需要改」

---

## 一、你做对的（保持不变）

先说好消息：**最关键的几件事全部落地了，非常好**。

### ✅ 卡片底部出处行（Citation Line）
```
[1] community.ui.com  一手官方  2026-06-01  查看原文 >
```
这正是我们要的——**独立成行、编号可见、域名可见、日期可见、可点击跳转**。这是整个产品策展感的核心，你做对了。

### ✅ 导语上标溯源
导语里「UniFi OS 全系列升级 5.1.15 RC¹」的 `¹ ² ³` 上标已经实现，且标注了「OPUS 策展」来源——这是「策展判断 vs AI 无源断言」的分水岭，落地了。

### ✅ Impact 研判框
「威胁研判」和「机会研判」的高亮文本框，在卡片内独立成区块，醒目但不喧宾夺主——正确。

### ✅ 来源可信度分层
「一手官方 vs 官方平台 vs 社区二手」的文字标注已经在出处行体现，正确。

### ✅ 整体结构
Header（日期/生成时间/report.json · daily/分享/导出）+ Stats bar（信号N/威胁N/机会N）+ 左侧导航 + 分区卡片流 — 整体信息架构是对的。

---

## 二、需要修改的地方

### 🔴 修改 1（最重要）：缺少「Omada 自身舆情」板块，放在第一位

**当前设计的板块结构：**
```
01 竞品动态
02 用户舆情   ← 这里只有 UniFi 痛点 + Reddit r/Ubiquiti，全是竞品视角
03 行业要闻
```

**应该改成：**
```
01 🟢 Omada 自身舆情   ← 新增，放最前面
02 ⚔️ 竞品动态
03 🗣️ 竞品舆情与对比   ← 原来的「用户舆情」改名，明确是竞品视角
04 🏭 行业要闻
```

**为什么：**
这个产品不是纯竞品跟踪，是「**照镜子 + 看对手**」双视角。「Omada 自身舆情」监控的是我们自己产品在 r/TPLink_Omada / r/Omada_Networks / YouTube 上的真实反馈——固件 bug、功能请求、好评、痛点、流失信号——这是产品团队最该优先看的，是改进输入，不是竞品对比。

把「Omada 自身舆情」放**第一区**，竞品相关放后面。

---

### 🔴 修改 2：Omada 自身舆情的 impact badge 语义不同

对于 `subject=omada_self` 的卡片，impact badge 不再是「威胁/机会/中性」，而是：

| badge | 颜色 | 含义 |
|-------|------|------|
| 🔧 **待修复** | 橙色/琥珀色 | 自家 bug，需要工程修复 |
| 💡 **功能需求** | 蓝色 | 用户功能请求，可作为产品输入 |
| ⭐ **优势确认** | 绿色 | 真实好评，确认竞争优势 |

对应的研判框文案也换成「**修复建议**」「**需求信号**」「**优势确认**」而不是「威胁研判」「机会研判」。

**只有竞品卡片（subject=competitor）才用「威胁/机会/中性」**，当前设计的语义是对的，只需要给 omada_self 卡片加新的三种 badge。

---

### 🟡 修改 3：「用户舆情」板块改名 + 描述修正

当前设计：
```
02 用户舆情
   双路融合 · 官方社区 + Reddit 热帖
```

改成（竞品视角明确）：
```
03 🗣️ 竞品舆情与对比
   UniFi 社区痛点 + Reddit r/Ubiquiti · 对 Omada 的差异化机会
```

「用户舆情」这个名字太模糊，容易和「Omada 自身舆情」混淆。竞品舆情的副标题要点明它的定位：我们在看 UniFi 用户在抱怨什么、对比两边的差距。

---

### 🟡 修改 4：板块图标更新

按新的四板块，建议图标更新：

| 板块 | 图标 | 颜色暗示 |
|------|------|----------|
| Omada 自身舆情 | 🟢（绿圆）或 📊 | 绿色系（自家、积极） |
| 竞品动态 | ⚔️ | 红色系（警惕、竞争） |
| 竞品舆情与对比 | 🗣️ | 橙色系（信号、洞察） |
| 行业要闻 | 🏭 | 灰色系（背景、趋势） |

---

### 🟡 修改 5：report.json `sections` 字段新增 `omada_self`

**给前端开发的 JSON 结构变化**（对应 PRD §7.9）：

```json
"sections": [
  {
    "key": "omada_self",
    "title": "Omada 自身舆情",
    "icon": "🟢",
    "items": ["item_id_1", "item_id_2"]
  },
  {
    "key": "competitor",
    "title": "竞品动态",
    "icon": "⚔️",
    "items": ["item_id_3", "item_id_4"]
  },
  {
    "key": "sentiment",
    "title": "竞品舆情与对比",
    "icon": "🗣️",
    "items": ["item_id_5", "item_id_6"]
  },
  {
    "key": "industry",
    "title": "行业要闻",
    "icon": "🏭",
    "items": ["item_id_7"]
  }
]
```

每条 Intel Item 现在有 `subject` 字段（`omada_self` / `competitor` / `industry`），前端用它决定进哪个 section，以及 impact badge 用哪套语义。

---

## 三、真实数据样例（Omada 自身舆情卡片）

设计新板块时，用这两条真实数据：

**卡片样例 A（待修复 bug）：**
- 来源徽章：🟩 社区 · Reddit r/TPLink_Omada
- 标题：EAP610-Outdoor firmware update fails to install
- 摘要：用户报告 EAP610-Outdoor 固件升级失败，显示 UPGRADING 后自动回滚到旧版本
- 标签：固件bug
- 热度：↑ 6 · 💬 9
- **Impact Badge：🔧 待修复**
- 修复建议：EAP610-Outdoor 升级回滚为可复现问题，建议固件团队核查升级流程与管理端口依赖
- 出处行：🔗 reddit.com/r/TPLink_Omada · 2026-05-31 · 查看原文 ↗
- URL：https://www.reddit.com/r/TPLink_Omada/comments/1trsrqo/eap610outdoor_firmware_update_fails_to_install/

**卡片样例 B（功能请求）：**
- 来源徽章：🟩 社区 · Reddit r/TPLink_Omada
- 标题：Omada comparison charts — 社区要求 SG2218 增加 PoE 版本
- 摘要：社区维护的 Omada 产品对比图表（高赞高讨论），评论区明确要求 SG2218 交换机的 PoE 版本
- 标签：功能请求
- 热度：↑ 206 · 💬 44
- **Impact Badge：💡 功能需求**
- 需求信号：SG2218 PoE 版本是社区高热度请求（206 赞），可作为产品线规划输入
- 出处行：🔗 reddit.com/r/TPLink_Omada · 2026-05-31 · 查看原文 ↗
- URL：https://www.reddit.com/r/TPLink_Omada/comments/11854oq/tplink_omada_comparison_charts_feb_2023/

---

## 四、完整报告 JSON 样例（新四板块结构）

完整样例见：`docs/SAMPLE_REPORT.md`

关键变化：
- `sections[0]` = `omada_self`（新，最先渲染）
- `sections[1]` = `competitor`
- `sections[2]` = `sentiment`（原 `用户舆情`，改名）
- `sections[3]` = `industry`
- item 里新增 `subject` 字段，`omada_impact` 对 omada_self 用新 enum：`needs_fix` / `feature_input` / `strength_confirm`

---

## 五、不需要改的

- 整体暗色主题和色调 ✅
- 卡片出处行格式 ✅
- 导语上标溯源 ✅
- Impact 研判高亮框 ✅
- 来源可信度标注（一手官方 / 官方平台 / 社区二手）✅
- 左侧导航 + stats bar ✅
- 参考来源列表 ✅
- 分享/导出/report.json 显示 ✅

---

> 完整 PRD 见 `docs/PRD.md`（§4 报告结构 + §7.4~§7.9 设计规范）
> 完整方案见 `docs/SOLUTION.md`
> 带引用的真实数据样例见 `docs/SAMPLE_REPORT.md`
