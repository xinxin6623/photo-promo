# photo-promo · 活动照片智能筛选 + 宣传文案生成

从大量活动照片（几千到几万张）里，三层漏斗自动筛图并生成宣传文案。

```
L0 元数据筛 (CPU 极快)  →  L1 SigLIP 粗筛 (CPU 零样本)  →  L2 VLM 精筛+文案 (API)
损坏/过小/过暗/模糊淘汰     宣传适配度打分留 Top N%        少量图送 VLM，判断+写文案一步到位
```

核心约束：纯 CPU 跑通，四档硬件（CPU/小独显/大独显/Mac）**只改 config 不改代码**；
SQLite 当状态机，跑挂能断点续跑；VLM 默认接火山方舟 Ark。

## 快速开始

```bash
uv sync
cp .env.example .env                 # 填 ARK_API_KEY（L2 才需要）
uv run promo ./tests/fixtures/
```

## 文档

- 📂 项目结构、流水线阶段、当前进度：[INDEX.md](./INDEX.md)
- 🤖 Agent 操作守则：[AGENTS.md](./AGENTS.md)
- 📓 演绎记录：[CHANGELOG.md](./CHANGELOG.md)
- 📐 完整设计方案：[设计方案.md](./设计方案.md)
- ⚙️ 所有可调项：[config.yaml](./config.yaml)
