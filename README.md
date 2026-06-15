# photo-promo · 活动照片智能筛选 + 结构化语义描述照片库

从大量活动照片（几千到几万张）里，三层漏斗筛出优质照片，对每张做结构化语义描述，
建成可被后续 agent 渐进式检索的 **obwiki 式独立照片库**。**不生成成稿文案**——
文案/海报由调用本库的 agent 自行生成。

```
L0 元数据筛 (CPU 极快)  →  L1 SigLIP 粗筛 (CPU 零样本)  →  L2 VLM 精筛+结构化描述 (API)  →  导出照片库 vault
损坏/过小/过暗/模糊淘汰     适配度打分留 Top N%            少量图送 VLM，判断+出描述JSON       library/ index+photos+images
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

- 🔌 **出入口契约**（下游 agent 必读）：[docs/io-contract.md](./docs/io-contract.md)
- 📂 项目结构、流水线阶段、当前进度：[INDEX.md](./INDEX.md)
- 🤖 Agent 操作守则：[AGENTS.md](./AGENTS.md)
- 📓 演绎记录：[CHANGELOG.md](./CHANGELOG.md)
- 📐 完整设计方案：[设计方案.md](./设计方案.md)
- ⚙️ 所有可调项：[config.yaml](./config.yaml)
