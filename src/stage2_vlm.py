"""L2 VLM 精筛 + 文案（占位，Phase 3 填实现）。

Phase 3 将做：通过 VLMProvider 把 l1_done 的少量图发给 VLM，一次调用同时做
「是否真适合宣传（带理由）」判断 + 生成文案（含时间/位置/场景细节），
精选图软链/复制到 out/selected/，文案写 out/captions.md。

Phase 0：占位流转，把 l1_done 的图标成 l2_done，写占位 verdict/caption，不调 API。
"""
from __future__ import annotations

import logging
import sqlite3

from .config import Config
from . import db
from .providers import get_provider

log = logging.getLogger(__name__)


def run(conn: sqlite3.Connection, cfg: Config) -> None:
    photos = db.get_pending(conn, "l1_done")
    log.info("[stage2] L2 VLM 精筛+文案（占位）：待处理 %d 张", len(photos))

    provider = get_provider(cfg)
    for row in photos:
        # TODO(Phase 3): 真实调用 provider.score_and_caption；按 verdict 决定是否入选
        result = provider.score_and_caption(row["path"], context={})
        db.mark(
            conn,
            row["path"],
            stage="l2_done",
            verdict=result.get("verdict"),
            caption=result.get("caption"),
        )
    log.info("[stage2] 完成（占位，未真实调 API）")
