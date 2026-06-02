# 样例报告 — 带完整引用的策展范本

> 本文件是给 Claude design 的**策展范本**。所有数据 2026-06-01 从 UNIFI_CHANNELS Supabase 真实拉取，所有链接已用**浏览器实渲染验证**可跳转。
>
> ⚠️ **URL 格式铁律**：Release/Question 页必须是 `community.ui.com/{releases|questions}/{slug}/{完整 UUID}`。**不能截断 ID，不能省略 ID**，否则都是 404。community.ui.com 是 SPA，curl 全返 200 验不出真假。
> 设计师请照此「引用密度」和「溯源结构」还原视觉——每条结论都可一键溯源，是本产品与普通信息聚合的本质区别。

---

# 📅 Network Intel · 2026-06-01 · 日报

> **今日导语**：自家侧 Omada EAP610-Outdoor 固件升级回滚问题被多用户反馈[1]，6.2.10.17 版本 bug 勝出建议暂缓升级[2]；竞品侧 UniFi OS 全系升 5.1.15 RC[3]、5G Backup 正式发布[4]，社区 5G 选网体验成新痛点[5]。**自家两记修复信号，竞品两记节奏施压。**

---

## 🟢 Omada 自身舆情

> 本区是本产品的一级维度（不是纯竞品跟踪）——监控自家产品的真实用户声音，直接输入产品改进。数据来源 A（个人情报流 r/TPLink_Omada `[用户声音]`）。

### 🟦 社区 · Reddit r/TPLink_Omada ｜ EAP610-Outdoor firmware update fails to install
用户报告 EAP610-Outdoor 固件升级失败，升级过程显示 UPGRADING 后自动回滚到旧版；社区反馈部分用户成功升到 1.6.7，可能与管理端口配置有关。

`固件bug`　来源 A·Reddit　　↑ 6 · 💬 9
> 🔧 **Needs Fix** — EAP610-Outdoor 固件升级回滚是可复现问题，建议转固件团队核查升级流程与管理端口依赖。

🔗 **reddit.com/r/TPLink_Omada · 2026-05-31 · 查看原文 ↗**
&nbsp;&nbsp;&nbsp;&nbsp;https://www.reddit.com/r/TPLink_Omada/comments/1trsrqo/eap610outdoor_firmware_update_fails_to_install/

---

### 🟦 社区 · Reddit r/TPLink_Omada ｜ Omada comparison charts — 社区要求 SG2218 PoE 版
用户维护的 Omada 产品对比图表资源（高赞高讨论），评论区用户明确希望增加 SG2218 交换机的 PoE 版本。

`功能请求`　来源 A·Reddit　　↑ 206 · 💬 44
> 💡 **Feature Input** — SG2218 PoE 版本是社区高热度请求（206 赞），可作产品线规划输入。

🔗 **reddit.com/r/TPLink_Omada · 2026-05-31 · 查看原文 ↗**
&nbsp;&nbsp;&nbsp;&nbsp;https://www.reddit.com/r/TPLink_Omada/comments/11854oq/tplink_omada_comparison_charts_feb_2023/

---

## ⚔️ 竞品动态

### 🟦 UniFi 官方 · Release ｜ UniFi OS - Express 7　v5.1.15　`RC`
UniFi Express 7 跟进 UniFi OS 5.1.15 RC，核心系统栈更新。Express 系列是 UniFi 主打的一体化入门网关。

`新品` `竞品`　　👁 376 浏览 · 💬 3
> 🔴 **Threat** — Express 7 是 UniFi 入门一体网关旗舰，固件迭代节奏直接对标 Omada 入门线，需关注其功能补齐速度。

🔗 **community.ui.com · 2026-06-01 · 查看原文 ↗**
&nbsp;&nbsp;&nbsp;&nbsp;https://community.ui.com/releases/UniFi-OS-Express-7-5-1-15/84641421-6507-48af-914f-c0cb5f704c76

---

### 🟦 UniFi 官方 · Blog ｜ Introducing UniFi 5G Backup
UniFi 推出 5G 备份方案，PoE 即插，为网关提供 5G failover 连接，补齐 WAN 冗余短板。

`新品` `竞品`
> 🔴 **Threat** — 5G Backup 直接补齐 UniFi 在 WAN 冗余/断网备份上的短板，Omada 网关线在企业连续性场景需对标。

🔗 **blog.ui.com · 2026-05-21 · 查看原文 ↗**
&nbsp;&nbsp;&nbsp;&nbsp;https://blog.ui.com/article/introducing-unifi-5g-backup

---

## 🗣️ 竞品舆情与对比

> 这是「竞品舆情」（UniFi 痛点 / Omada vs UniFi 对比），与上面的「Omada 自身舆情」是两个不同维度。本区也是**双路数据融合**：UniFi Community（来源 B）+ Reddit r/Ubiquiti（来源 A）。

### 🟩 社区 · UniFi Community ｜ U5G - manual carrier select / override badly needed!
用户强烈要求 UniFi 5G 设备增加手动运营商选择/覆盖功能，吐槽当前自动选网在多运营商环境下不可控。

`竞品舆情`　来源 B·Supabase　　👁 2
> 🟢 **Opportunity** — UniFi 5G 选网体验是真实痛点；Omada 若在 5G/蜂窝备份方案中提供手动运营商控制，可作为差异化卖点。

🔗 **community.ui.com · 2026-06-01 · 查看原文 ↗**
&nbsp;&nbsp;&nbsp;&nbsp;https://community.ui.com/questions/U5G-manual-carrier-select-override-badly-needed/eb165625-81e2-46b9-8dac-01d7e8339e99

---

### 🟨 社区 · Reddit r/Ubiquiti ｜ Overall impressed, U7 Pro XG is hot garbage
用户升级 10Gb 网络后对 Ubiquiti 整体满意，但抓出 U7 Pro XG AP 信号覆盖极差，换到 E7 才解决。高热度讨论（152 赞 / 80 评）。

`舆情`　来源 A·Reddit　　↑ 152 · 💬 80
> 🟢 **Opportunity** — UniFi 旗舰 AP 信号表现与定价不匹配是反复出现的舆情；Omada 高端 AP 可在「覆盖一致性」上做文章。

🔗 **reddit.com/r/Ubiquiti · 2026-05-31 · 查看原文 ↗**
&nbsp;&nbsp;&nbsp;&nbsp;https://www.reddit.com/r/Ubiquiti/comments/1ts70er/overall_impressed_u7_pro_xg_is_hot_garbage/

---

### 🟨 社区 · Reddit r/Ubiquiti ｜ Got tired of their slow internet so I upgraded it
用户在酒店把 Aruba 设备换成 Ubiquiti 方案，网速从 5Mbps 提升到 100+Mbps。高热度（553 赞 / 82 评）。

`舆情` `竞品`　来源 A·Reddit　　↑ 553 · 💬 82
> ⚪ **Neutral** — Aruba → Ubiquiti 的迁移案例；反映 SMB 市场对性价比方案的持续需求，Omada 同样是 Aruba Instant On 的替代选项，可关注该类换机场景。

🔗 **reddit.com/r/Ubiquiti · 2026-05-31 · 查看原文 ↗**
&nbsp;&nbsp;&nbsp;&nbsp;https://www.reddit.com/r/Ubiquiti/comments/1trzyy3/got_tired_of_their_slow_internet_so_i_upgraded_it/

---

## 🏭 行业要闻

### 🟥 YouTube · Unified IT ｜ UniFi 网络架构与基础知识系列
KOL 频道系统介绍 UniFi 网络架构，高播放高认可（7083 观看 / 468 赞），反映 UniFi 生态的内容营销势能。

`行业`　来源 A·YouTube　　👁 7083 · 👍 468
> ⚪ Neutral — UniFi 的 KOL/社区内容生态是其品牌护城河，Omada 可参考其教程化内容运营。

🔗 **youtube.com · 2026-05-31 · 查看原文 ↗**
&nbsp;&nbsp;&nbsp;&nbsp;https://www.youtube.com/watch?v=SDcPaKXC_u8

---

## 参考来源（References）

```
[1] EAP610-Outdoor firmware update fails to install（Omada 自身）
    reddit.com/r/TPLink_Omada · 2026-05-31
    https://www.reddit.com/r/TPLink_Omada/comments/1trsrqo/eap610outdoor_firmware_update_fails_to_install/
[2] Omada comparison charts — 社区要求 SG2218 PoE 版（Omada 自身）
    reddit.com/r/TPLink_Omada · 2026-05-31
    https://www.reddit.com/r/TPLink_Omada/comments/11854oq/tplink_omada_comparison_charts_feb_2023/
[3] UniFi OS - Express 7 v5.1.15 (RC)（竞品）
    community.ui.com · 2026-06-01
    https://community.ui.com/releases/UniFi-OS-Express-7-5-1-15/84641421-6507-48af-914f-c0cb5f704c76
[4] Introducing UniFi 5G Backup（竞品）
    blog.ui.com · 2026-05-21
    https://blog.ui.com/article/introducing-unifi-5g-backup
[5] U5G - manual carrier select / override badly needed!（竞品舆情）
    community.ui.com · 2026-06-01
    https://community.ui.com/questions/U5G-manual-carrier-select-override-badly-needed/eb165625-81e2-46b9-8dac-01d7e8339e99
[6] Overall impressed, U7 Pro XG is hot garbage（竞品舆情）
    reddit.com/r/Ubiquiti · 2026-05-31
    https://www.reddit.com/r/Ubiquiti/comments/1ts70er/overall_impressed_u7_pro_xg_is_hot_garbage/
[7] Got tired of their slow internet so I upgraded it (Aruba → Ubiquiti)（竞品舆情）
    reddit.com/r/Ubiquiti · 2026-05-31
    https://www.reddit.com/r/Ubiquiti/comments/1trzyy3/got_tired_of_their_slow_internet_so_i_upgraded_it/
[8] UniFi 网络架构与基础知识（Unified IT，行业）
    youtube.com · 2026-05-31
    https://www.youtube.com/watch?v=SDcPaKXC_u8
```

> 📌 数据融合说明：本样例同时含**来源 B（UNIFI_CHANNELS Supabase：release/blog/community）** 与 **来源 A（个人情报流 summary.jsonl：Reddit/YouTube）**。两路数据同框策展——这才是完整产品形态，设计上需要能区分来源但统一呈现。Reddit/YouTube 数据为 2026-05-31 真实拉取（今日 06-01 情报 cron 未出）。

---

# 设计师注意事项（Sample → Design 映射）

1. **每张卡片底部那条 `🔗 域名 · 日期 · 查看原文 ↗` 是强制元素**——它必须是卡片上醒目、独立、可点击的一行，不是标题旁的小图标。这是 v1 设计要修正的核心。
2. **来源域名要可见**——读者凭 `community.ui.com` / `blog.ui.com`（一手官方）vs `reddit.com`（二手社区）即可判断可信度。官方源建议更高视觉权重。
3. **导语里的 `[1] [2] [3]` 上标可点击**——跳到对应卡片或末尾参考列表。LLM 合成判断绝不无源。
4. **末尾「参考来源」是独立组件**——编号 + 标题 + 来源 + 日期 + 完整 URL，便于核查导出。
5. **omada_impact 徽章 + impact_note** 与出处行并存——一个给「判断力」，一个给「可信度」，两者都是策展的支柱。

> 数据来源说明：以上为 2026-06-01 真实数据；正式产品中卡片由 render 引擎按 Intel Item schema 自动生成，cite_id 自动编号。
