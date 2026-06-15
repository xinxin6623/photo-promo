# photo-promo 出入口对接契约 (I/O Contract)

> 本文件定义 photo-promo 作为「**结构化语义描述照片库**」的**输入**和**输出**契约。
> 上游：把活动照片目录喂进来。下游：后续 agent 按本契约**渐进式披露**检索照片库。
> 设计思路借鉴 obwiki（自包含 vault + L0→L1→L2 渐进披露 + 链接密度），但**独立**于 `~/baidu/obwiki`。
>
> **🚧 字段标 `[可调]` 的是待 James 拍板的默认值**，按 obwiki 思路下的合理默认起草，可直接改。

---

## 1. 这个工程是什么 / 不是什么

| 是 | 不是 |
|---|---|
| 照片**筛选** + **结构化语义描述** + 建**可检索照片库** | ❌ 文案 / 海报 / 推文生成器 |
| 照片库的 **ingest 闭环**（粗筛→描述→建索引/互链） | ❌ 检索服务 / 向量数据库 / 在线 API |
| 产出**独立 vault**，交付给任意下游 agent | ❌ 写进个人知识库 `~/baidu/obwiki` |

下游 agent 拿本库的结构化信息**自行**生成文案/海报等——那是调用方的事，不在本工程范围。

---

## 2. 入口契约（上游 → 本工程）

### 调用方式
```bash
uv run promo <photos_dir> [-c config.yaml]
```
- `<photos_dir>`：活动照片目录，**递归扫描**。支持 `.jpg/.jpeg/.png/.webp/.bmp/.tiff/.heic`。
- 幂等 & 断点续跑：同一目录重复跑只处理未完成的图（SQLite `stage` 字段过滤）。
- 重跑全库：删 `pipeline.db` 后再跑。

### 输入假设
- 照片可有可无 EXIF；有 `DateTimeOriginal` / GPS 则自动提取时间/地名，无则留空（不报错）。
- 所有筛选阈值、模型、Top N%、VLM 配置都在 `config.yaml`，**改配置不改代码**。

---

## 3. 出口契约（本工程 → 下游 agent）

### 3.1 产物总览

两份产物，下游按需选用：

1. **SQLite 主库** `pipeline.db`：全量状态（含被淘汰的图及原因），是单一真相源。
2. **照片库 vault** `library/`：obwiki 式，**这是给下游 agent 的主出口**。

```
library/
├── index.md              # L0 索引：全库句柄一览，可全量扫描
├── photos/
│   ├── <id>.md           # 每张入库图一个描述条目（frontmatter=L0，正文=L1）
│   └── ...
└── images/
    └── <id>.<ext>        # 入库原图（L2）；[可调] 复制 or 软链
```
`<id>`：[可调] 默认用图片内容 hash 前 12 位（稳定、去重友好），或 `YYYYMMDD-序号`。

### 3.2 渐进式披露三层（下游检索协议，物理强制）

> 下游 agent **必须**按 L0→L1→L2 顺序下钻，不要一次把全库灌进上下文。

| 层 | 在哪 | 内容 | 何时加载 |
|---|---|---|---|
| **L0 句柄** | `index.md` + 各 `<id>.md` 的 frontmatter | id / 相对路径 / 一句话 summary / scene / tags / taken_at / location | 永远可全量扫描（几十 token/条） |
| **L1 描述** | `photos/<id>.md` 正文 | 完整结构化语义描述（见 §3.3） | L0 命中候选后按需读 |
| **L2 原图** | `images/<id>.<ext>` | 原始图片像素 | 反思门控选中后才打开（要复看/真要用图时） |

**检索范式**（下游 agent 照做）：
1. grep / 扫 `index.md` 的 L0 句柄 → 按 scene/tags/time/location 圈候选。
2. 读候选的 L1 描述 → 反思「够不够回答当前需求」，够了就停。
3. 仍需确认画面细节 → 才打开 L2 原图。

### 3.3 单条描述 schema（L1 核心，`photos/<id>.md`）

```markdown
---
# ===== L0 句柄（可全量扫描）=====
id: a1b2c3d4e5f6
path: images/a1b2c3d4e5f6.jpg      # 相对 library/ 的原图路径
summary: 互动体验区参会者围观演示，氛围热烈    # 一句话，[可调] ≤30 字
scene: 互动体验区                   # 场景类型（受控词表，见下）
tags: [人物, 多人, 室内, 演示, 积极]   # 可检索关键词
taken_at: 2026-06-15T10:30:45      # 来自 EXIF，可空
location: Beijing, Beijing, CN      # 离线逆地理编码，可空
l1_score: 0.62                      # SigLIP 适配度（排序参考）
quality: high                       # [可调] high|medium（VLM 精筛评级）
updated: 2026-06-15
related: []                         # 图间互链（同活动/场景/人物），见 §3.4
---

## 语义描述

<VLM 输出的一段自然语言画面描述，供语义检索/embedding>

## 结构化字段
- **主体 (subjects)**: 参会者(多人)、演示屏、讲解员
- **人数 (people_count)**: ~8
- **氛围 (mood)**: 积极、专注
- **适用场景 (suitable_for)**: [官网, 活动报道, 社媒]   # [可调]
- **画面要点**: 主体清晰、光线明亮、构图完整
```

**受控词表**（`config.yaml` 可扩展）：
- `scene` `[可调]`：开场签到 / 主舞台演讲 / 互动体验区 / 圆桌讨论 / 茶歇交流 / 颁奖 / 合影 / 展台 / 其他
- `mood` `[可调]`：积极 / 专注 / 热烈 / 轻松 / 正式
- `suitable_for` `[可调]`：官网 / 活动报道 / 社媒 / 内部汇报 / 宣传册

### 3.4 图间互链（链接密度北极星）

obwiki 纪律：价值正比于**链接密度**，不是照片数。
- `related` 列同一活动/场景/人物的图 id，每条带一句"为什么相关"（[可调] 格式：`<id> — 同场茶歇连拍`）。
- 建链时机：Phase 4 导出时按 taken_at 邻近 + scene 相同自动建初版，evolve 阶段精修。

### 3.5 精筛门槛 `[可调，待拍板]`

**默认：保留精筛**——L2 让 VLM 先判「是否适合入库(带理由)」，不合格的**不进 vault**（仍留在 `pipeline.db` 标 rejected + 理由，可回溯）。
- 备选：只描述不筛，L1 过来的全入库，质量高低交下游自判。

---

## 4. SQLite 状态机字段（`pipeline.db`，全量真相源）

下游若想拿"被淘汰的图及原因"做分析，直接查 `pipeline.db` 的 `photos` 表。stage 取值与字段含义见 [`src/db.py`](../src/db.py)。`library/` 是它的**入库子集导出**。

---

## 5. evolve（阶段治理，本工程 Phase 5 / 人在环）

对应 obwiki evolve 闭环，对已建成的 vault 做：
- 连拍/重复去重（ADD/UPDATE/MERGE/**NOOP**；**DELETE 只提议，人确认**）
- 重打分、补 scene/tags、补 `related` 互链
- 受控词表演化（新增 scene/mood 类别）

---

## 6. 变更纪律

- 改本契约（schema / 三层结构 / 词表）= 改对外 API，必须同步更新本文件 + `config.yaml` + `AGENTS.md` 硬规则。
- 标 `[可调]` 的项确定后，去掉标记并在 `CHANGELOG.md` 记一条 `#docs scope:io-contract`。
