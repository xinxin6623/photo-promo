# photo-promo · CHANGELOG

> 每次动了什么记一条。详细记录写在各自模块目录下，根目录 CHANGELOG 是**强标签化的检索索引**。
>
> **如本项目下有子项目**：本 CHANGELOG **只记录跨多个子项目的同时操作**；单一子项目操作记在该子项目自己的 CHANGELOG 里。详见 [`docs/trio-protocol.md`](./docs/trio-protocol.md) §5 子项目嵌套（max-depth = 3）。

## 格式规范（严格）

```
## YYYY-MM-DD #<type> scope:<name> [#<extra-tag>...] - <一句话主题>

- Why: <一句话动机，不复述 what>
- 详见: <path 或 commit hash>
```

**硬约束**：
- 日期必须 ISO 格式 `YYYY-MM-DD`
- 类型标签必须以 `#` 开头，从下面字典选一个为主标签
- 作用域必须 `scope:<name>` 形式，name 用 kebab-case；多模块改动用多个 `scope:`
- Why 一行不超过 80 字符
- **不贴 diff、不复述 what**——那些进 commit 或模块自己的文档

## 类型标签字典

| 标签 | 含义 |
|---|---|
| `#feat` | 新功能 |
| `#fix` | bug 修复 |
| `#refactor` | 重构（无行为变化） |
| `#perf` | 性能优化 |
| `#docs` | 文档变更 |
| `#test` | 测试相关 |
| `#chore` | 构建/依赖/工具链/初始化 |
| `#archive` | 归档/弃用 |
| `#breaking` | 破坏性变更（叠加） |
| `#deprecated` | 标记弃用（叠加） |
| `#wip` | 进行中（叠加） |

## 项目阶段

- [x] Phase 0 骨架 — 脚手架 + config + SQLite 状态机 + 样例图
- [x] Phase 1 L0 元数据筛 — EXIF/GPS + 模糊/亮度/尺寸 + 离线逆地理编码
- [x] Phase 2 L1 SigLIP 粗筛 — 宣传适配度打分留 Top N%
- [x] Phase 3 L2 VLM 精筛+结构化语义描述 — 火山方舟 Ark，一次调用判断+出描述 JSON
- [x] Phase 4 串联+导出照片库 vault — 一条命令跑全链路，导出 library/ + 图间互链
- [ ] Phase 5（可选）硬件适配 + evolve（重打分/去重/补链）

## 检索示例

```bash
grep -E "^## .* #feat .* scope:stage0" CHANGELOG.md   # L0 相关新功能
grep "#breaking" CHANGELOG.md                          # 所有破坏性变更
grep "^## 2026-06" CHANGELOG.md                        # 2026 年 6 月所有动作
```

---

## 2026-06-15 #docs scope:io-contract #breaking - 范围调整：照片库取代文案生成

- Why: 工程定位改为产出结构化语义描述照片库，文案由下游 agent 自行生成
- 详见: docs/io-contract.md / 设计方案.md §0+§6 / AGENTS.md 硬规则 8-9

## 2026-06-15 #feat scope:stage1 - Phase 2 L1 SigLIP 粗筛

- Why: CPU 零样本给图打宣传适配度净分，几万张里只留 Top N% 进 API 精筛省钱
- 详见: src/siglip.py / src/stage1_clip.py / prompts/l1_screen.txt

## 2026-06-15 #docs scope:trio - 三件套标准化

- Why: 接入 standard-v3 三件套，让 agent/skill 能按标准流程处理本项目并同步看板
- 详见: AGENTS.md frontmatter / docs/trio-protocol.md

## 2026-06-15 #feat scope:stage0 - Phase 1 L0 元数据筛

- Why: 几乎不花算力先砍掉废片，EXIF 时间/位置为后续文案三要素打底
- 详见: 639d8fb / src/meta.py / src/stage0_meta.py

## 2026-06-15 #chore scope:init - Phase 0 项目骨架

- Why: 三层漏斗脚手架 + SQLite 状态机 + config 中枢，让各 stage 可独立填实现
- 详见: 6fe30fe / src/

## 2026-06-17 #feat scope:export - Phase 4 导出照片库 vault

- Why: 把 l2_done 入库图落成 obwiki 式 vault，供下游 agent L0→L1→L2 渐进检索
- 详见: src/export.py（hash id / 复制原图 / 同 scene+时间邻近建 related / index.md）

## 2026-06-17 #fix scope:provider-ark - prompt 含 JSON 示例致 str.format 报 KeyError

- Why: prompt 里 JSON schema 的 {} 被 str.format 当占位符，真机首调即崩
- 详见: src/providers/ark.py（改用 .replace 只换 {taken_at}/{location}）

## 2026-06-17 #feat scope:stage2 scope:provider-ark - Phase 3 L2 VLM 精筛+结构化描述

- Why: l1_done 少量精华图走 Ark 一次拿 verdict+结构化描述 JSON，按门槛决定入库
- 详见: src/providers/ark.py / src/stage2_vlm.py（top_n 截断 + require_quality_gate）

<!-- 新条目加在这里上方，保持最新在最上 -->
