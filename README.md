# photo-promo · 活动照片智能筛选 + 宣传文案生成

从大量活动照片（几千到几万张）里，三层漏斗自动筛图并生成宣传文案。

```
L0 元数据筛 (CPU 极快)  →  L1 SigLIP 粗筛 (CPU 零样本)  →  L2 VLM 精筛+文案 (API)
损坏/过小/过暗/模糊淘汰     宣传适配度打分留 Top N%        少量图送 VLM，判断+写文案一步到位
```

核心约束：纯 CPU 跑通，四档硬件（CPU/小独显/大独显/Mac）**只改 config 不改代码**；
SQLite 当状态机，跑挂能断点续跑。

## 快速开始

```bash
uv sync                              # 装依赖
cp .env.example .env                 # 填 ARK_API_KEY（L2 才需要）
uv run promo ./tests/fixtures/       # 跑流水线
```

## 配置

所有档位/模型/阈值/prompt 都在 [`config.yaml`](config.yaml)，VLM 默认接火山方舟 Ark。

## 状态

Phase 0（骨架）已完成：脚手架 + config + SQLite 状态机 + 样例图，可空跑。
各 stage 实现按 Phase 推进，详见 `设计方案.md`。
