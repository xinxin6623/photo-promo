"""L1 SigLIP 粗筛：宣传适配度打分 + 保留 Top N%。

对所有 l0_done 的图打分写 l1_score，按分数排序保留 Top N%（流转 l1_done），
其余淘汰（stage='rejected'，l1_score 已记录便于回溯）。
打分逻辑在 siglip.py，本文件只做编排和写 DB。
"""
from __future__ import annotations

import logging
import math
import sqlite3

from .config import Config
from . import db
from .siglip import SiglipScorer, resolve_device

log = logging.getLogger(__name__)


def run(conn: sqlite3.Connection, cfg: Config) -> None:
    photos = db.get_pending(conn, "l0_done")
    log.info("[stage1] L1 SigLIP 粗筛：待处理 %d 张", len(photos))
    if not photos:
        log.info("[stage1] 无待处理图，跳过")
        return

    l1 = cfg.l1
    scorer = SiglipScorer(
        model_name=l1.get("model", "google/siglip2-base-patch16-224"),
        device=resolve_device(cfg.hardware, l1.get("device")),
        prompt_file=cfg.resolve(l1.get("prompt_file", "prompts/l1_screen.txt")),
    )

    # 1. 逐张打分写 l1_score
    scored: list[tuple[str, float]] = []
    for i, row in enumerate(photos, 1):
        s = scorer.score(row["path"])
        db.mark(conn, row["path"], l1_score=s)
        scored.append((row["path"], s))
        log.debug("[stage1] (%d/%d) %.4f  %s", i, len(photos), s, row["path"])

    # 2. 按分数降序，保留 Top N%（至少 1 张）
    scored.sort(key=lambda x: x[1], reverse=True)
    top_percent = float(l1.get("top_percent", 20))
    keep = max(1, math.ceil(len(scored) * top_percent / 100))

    for idx, (path, _s) in enumerate(scored):
        stage = "l1_done" if idx < keep else "rejected"
        db.mark(conn, path, stage=stage)

    log.info(
        "[stage1] 完成：打分 %d 张，保留 Top %.0f%% = %d 张入选，%d 张淘汰",
        len(scored), top_percent, keep, len(scored) - keep,
    )
