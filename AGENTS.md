---
trio: standard-v3
trio-initialized: 2026-06-15
status: active
desc: 活动照片三层漏斗筛选+宣传文案生成
---

<!--
status / desc 是 TaskBoard 看板字段：
  status: active | paused | done
  desc:   ≤30 字一句话项目描述
看板完整契约见 TaskBoard 项目 02 §1.1b；一键产出全套用 /outkanban。
-->

# photo-promo · Agent 操作守则

> **上来先读这份**，再看 [`INDEX.md`](./INDEX.md) 找模块和导航。
>
> **通用三件套协议**见 [`docs/trio-protocol.md`](./docs/trio-protocol.md)（文档维护节奏 / Handoff 写入 / 子项目嵌套 / 记忆三条线边界 / 语言规则 / 跨项目反例）。**本文件只列本项目专属守则**。
>
> **`trio: standard-v3`** = 本项目按当前标准维护三件套。

## 这是什么项目

从大量活动照片（几千到几万张）里，三层漏斗自动筛图并生成宣传文案：
**L0 元数据筛**（CPU 极快，淘汰废片）→ **L1 SigLIP 粗筛**（CPU 零样本打适配度分）→ **L2 VLM 精筛+文案**（API，少量图一步到位）。
完整背景见 `设计方案.md`，当前进度见 `INDEX.md` 顶部 + `CHANGELOG.md`。

## 上手三步

1. 读 [`INDEX.md`](./INDEX.md)，看项目结构、流水线阶段和当前接力点。
2. 改某个 stage 前先读它的源文件头部 docstring（写明该 stage 职责 + 哪个 Phase 实现）。
3. 看 `config.yaml`（所有可调项）和 `.env.example`（密钥）。

## 项目专属硬规则

> 通用守则（语言 / 节奏 / Handoff / 子项目 / 记忆边界）见 `docs/trio-protocol.md`。本段只列**本项目专属**约束。

1. **只改 config 不改代码**：四档硬件（cpu/small_gpu/large_gpu/mac）、模型、阈值、prompt 全在 `config.yaml`。新增可调项加到 config，不要硬编码进代码。
2. **模型走接口抽象**：VLM 实现都继承 `src/providers/base.py` 的 `VLMProvider`，新接一家只加 provider 文件，不动调用方。
3. **prompt 抽成文件**：粗筛/文案 prompt 放 `prompts/`，方便反复调，不要内联进 `.py`。
4. **一次只改一个 stage**：stage0/1/2 各自独立可单跑。改 L1 就别动 L0。
5. **SQLite 是状态机**：每张图一条记录，跑挂重跑只处理未完成的（按 `stage` 字段过滤）。`pipeline.db` 是派生物，可删重建。
6. **依赖按 Phase 增量加**：`uv add`，别一次装一大坨重依赖。
7. **密钥从环境变量读**（`ARK_API_KEY`），不写进 yaml，不提交 `.env`。

<!-- 在此追加本项目工作中沉淀的专属硬规则（活文档，随时更新） -->

## 目录命名约定

| 子目录 | 用途 |
|---|---|
| `src/` | 主代码：cli 编排 + config + db 状态机 + stage0/1/2 + providers |
| `src/providers/` | VLMProvider 抽象 + 各家实现（ark 等） |
| `prompts/` | L1 粗筛 / L2 文案 prompt 文本 |
| `tests/fixtures/` | 样例图（`_gen.py` 可重建）|
| `out/` | 运行时输出（selected/ 精选图 + captions.md），git 忽略 |
| `docs/` | 通用三件套协议 `trio-protocol.md` |

## 项目专属"不要做的事"

> 通用反例见 `docs/trio-protocol.md` §9。本段只列**本项目专属**反例。

- ❌ 自动提交 secrets / 凭证 / `.env`
- ❌ 把阈值、模型名、prompt 硬编码进 stage 代码（必须走 config）
- ❌ 替用户做 `git push` / 任何不可逆操作（必须先问）

<!-- 在此追加本项目工作中沉淀的专属反例 -->
