# AGENTS.md · 给 Claude Code / Codex 的操作守则

## 这是什么项目
活动照片智能筛选 + 宣传文案生成。三层漏斗：L0 元数据筛 → L1 SigLIP 粗筛 → L2 VLM 精筛+文案。
完整背景见 `设计方案.md`，当前进度见 `README.md`。

## 核心原则（必须遵守）
1. **只改 config 不改代码**：四档硬件（cpu/small_gpu/large_gpu/mac）、模型、阈值、prompt 全在 `config.yaml`。新增可调项加到 config，不要硬编码进代码。
2. **模型走接口抽象**：VLM 实现都继承 `src/providers/base.py` 的 `VLMProvider`，新接一家只加 provider，不动调用方。
3. **prompt 抽成文件**：粗筛/文案 prompt 放 `prompts/`，方便反复调，不要内联进 .py。
4. **一次只改一个 stage**：stage0/1/2 各自独立可单跑。改 L1 就别动 L0。
5. **SQLite 是状态机**：每张图一条记录，跑挂重跑只处理未完成的（按 `stage` 字段过滤）。`pipeline.db` 是派生物，可删重建。

## 开发约定
- Python 3.11+，用 `uv` 管依赖（`uv add` / `uv run`），不要用裸 pip。
- 依赖按 Phase 增量加，别一次装一大坨。
- 密钥从环境变量读（`ARK_API_KEY`），不写进 yaml，不提交 `.env`。
- 回复用中文，简洁直接。

## 跑起来
```bash
uv sync
uv run promo ./tests/fixtures/
```
