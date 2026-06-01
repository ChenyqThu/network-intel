# 样例报告 — 带完整引用的策展范本

> 本文件是给 Claude design 的**策展范本**。所有数据 2026-06-01 从 UNIFI_CHANNELS Supabase 真实拉取，所有链接已用**浏览器实渲染验证**可跳转。
>
> ⚠️ **URL 格式铁律**：Release/Question 页必须是 `community.ui.com/{releases|questions}/{slug}/{完整 UUID}`。**不能截断 ID，不能省略 ID**，否则都是 404。community.ui.com 是 SPA，curl 全返 200 验不出真假。
> 设计师请照此「引用密度」和「溯源结构」还原视觉——每条结论都可一键溯源，是本产品与普通信息聚合的本质区别。

---

# 📅 Network Intel · 2026-06-01 · 日报

> **今日导语**：UniFi 今天集中放量——UniFi OS 全系列升级 5.1.15 RC[1]，Express 7 同步跟进[2]；社区侧 5G 选网体验成为新痛点[3]。**一记节奏施压，一记差异化机会。**

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

## 🗣️ 用户舆情

### 🟩 社区 · UniFi Community ｜ U5G - manual carrier select / override badly needed!
用户强烈要求 UniFi 5G 设备增加手动运营商选择/覆盖功能，吐槽当前自动选网在多运营商环境下不可控。

`舆情`　　👁 2
> 🟢 **Opportunity** — UniFi 5G 选网体验是真实痛点；Omada 若在 5G/蜂窝备份方案中提供手动运营商控制，可作为差异化卖点。

🔗 **community.ui.com · 2026-06-01 · 查看原文 ↗**
&nbsp;&nbsp;&nbsp;&nbsp;https://community.ui.com/questions/U5G-manual-carrier-select-override-badly-needed/eb165625-81e2-46b9-8dac-01d7e8339e99

---

## 🏭 行业要闻

- UniFi Network 10.4 正式发布，新增 e-BGP、5G 遥测等企业级特性[4]
- （RSS / YouTube 行业条目按当日填充，≤3 条）

---

## 参考来源（References）

```
[1] UniFi OS - Dream Machines / Cloud Gateways / Express 7 等全系列 v5.1.15 (RC)
    community.ui.com · 2026-06-01
    https://community.ui.com/releases/UniFi-OS-Express-7-5-1-15/84641421-6507-48af-914f-c0cb5f704c76
[2] UniFi OS - Express 7 v5.1.15 (RC)
    community.ui.com · 2026-06-01
    https://community.ui.com/releases/UniFi-OS-Express-7-5-1-15/84641421-6507-48af-914f-c0cb5f704c76
[3] U5G - manual carrier select / override badly needed!
    community.ui.com · 2026-06-01
    https://community.ui.com/questions/U5G-manual-carrier-select-override-badly-needed/eb165625-81e2-46b9-8dac-01d7e8339e99
[4] Introducing UniFi Network 10.4
    blog.ui.com · 2026-05-19
    https://blog.ui.com/article/introducing-unifi-network-10-4
```

---

# 设计师注意事项（Sample → Design 映射）

1. **每张卡片底部那条 `🔗 域名 · 日期 · 查看原文 ↗` 是强制元素**——它必须是卡片上醒目、独立、可点击的一行，不是标题旁的小图标。这是 v1 设计要修正的核心。
2. **来源域名要可见**——读者凭 `community.ui.com` / `blog.ui.com`（一手官方）vs `reddit.com`（二手社区）即可判断可信度。官方源建议更高视觉权重。
3. **导语里的 `[1] [2] [3]` 上标可点击**——跳到对应卡片或末尾参考列表。LLM 合成判断绝不无源。
4. **末尾「参考来源」是独立组件**——编号 + 标题 + 来源 + 日期 + 完整 URL，便于核查导出。
5. **omada_impact 徽章 + impact_note** 与出处行并存——一个给「判断力」，一个给「可信度」，两者都是策展的支柱。

> 数据来源说明：以上为 2026-06-01 真实数据；正式产品中卡片由 render 引擎按 Intel Item schema 自动生成，cite_id 自动编号。
