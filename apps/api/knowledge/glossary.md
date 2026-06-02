# Network Intel 术语表 (Glossary)

供 RAG `background` 集合检索，帮助 classify/curate 校准措辞与判断。请勿在报告中复述背景文本本身。

## 固件阶段 (Firmware stages)
- **EA / Early Access**：早期访问，尝鲜版，缺陷较多。
- **RC / Release Candidate**：发布候选，接近正式，仍可能回滚。
- **GA / General Availability**：正式发布，面向所有用户。

## WAN 冗余 / 蜂窝备份
- **WAN failover**：主线路中断时自动切换到备用线路（如 5G）。
- **5G Backup**：以 5G 蜂窝网络作为 WAN 备份，保障断网连续性。UniFi 已推出即插式 5G Backup。
- **manual carrier select**：手动选择/锁定蜂窝运营商，多运营商环境下的关键体验点。

## PoE / 交换
- **PoE / PoE+ / PoE++**：通过网线供电（15.4W / 30W / 60-100W）。SG2218 等交换机的 PoE 版本是社区高频诉求。

## 舆情字段
- **sentiment**：pos | neg | neu，单条信号的情感倾向。
- **relevance**：0..1，与我方（Omada）相关度。
- **switch_intent**：用户表达出从竞品迁移/更换品牌的意图，是高价值的市场信号。

## 什么算"拐点"(turning point)
一条已报道过的信号，若出现以下之一，值得再次报道：
1. **热度激增**：互动量（赞+评/播放）相对上次显著跳升。
2. **情绪反转**：sentiment 从正转负或负转正。
3. **切换意图新出现**：此前无、本次出现 switch_intent。
拐点意味着事件进入新阶段，而非简单重复，应以"更新/升级"的口吻表述。
