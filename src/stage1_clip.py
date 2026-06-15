"""L1 SigLIP 粗筛（占位，Phase 2 填实现）。

Phase 2 将做：加载 SigLIP 2（CPU 优先，onnxruntime 量化，保底退回 open_clip），
用 prompts/l1_screen.txt 的文本给每张图打「宣传适配度」分，保留 Top N%。

Phase 0：占位流转，把 l0_done 的图全部标成 l1_done，不做真实打分。
"""
from __future__ import annotations

import logging
import sqlite3

from .config import Config
from . import db

log = logging.getLogger(__name__)


def run(conn: sqlite3.Connection, cfg: Config) -> None:
    photos = db.get_pending(conn, "l0_done")
    log.info("[stage1] L1 SigLIP 粗筛（占位）：待处理 %d 张", len(photos))
    for row in photos:
        # TODO(Phase 2): SigLIP 打分写 l1_score；非 Top N% 的 mark(stage='rejected')
        db.mark(conn, row["path"], stage="l1_done")
    log.info("[stage1] 完成（占位，未做真实打分）")
