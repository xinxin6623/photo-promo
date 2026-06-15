"""L2 VLM 精筛 + 结构化语义描述（占位，Phase 3 填实现）。

Phase 3 将做：通过 VLMProvider 把 l1_done 的少量图发给 VLM，一次调用同时做
「是否适合入库（带理由）」判断 + 输出结构化语义描述 JSON（schema 见
docs/io-contract.md §3.3）；不合格的不入库（标 rejected），合格的写 description。
照片库 vault 的导出（library/）放到 Phase 4。

Phase 0：占位流转，把 l1_done 的图标成 l2_done，写占位 verdict/description，不调 API。
"""
from __future__ import annotations

import json
import logging
import sqlite3

from .config import Config
from . import db
from .providers import get_provider

log = logging.getLogger(__name__)


def run(conn: sqlite3.Connection, cfg: Config) -> None:
    photos = db.get_pending(conn, "l1_done")
    log.info("[stage2] L2 VLM 精筛+结构化描述（占位）：待处理 %d 张", len(photos))

    provider = get_provider(cfg)
    for row in photos:
        # TODO(Phase 3): 真实调用 provider.score_and_describe；
        #   按 verdict.fit 决定入库(l2_done) / 淘汰(rejected, require_quality_gate 控制)
        result = provider.score_and_describe(row["path"], context={})
        db.mark(
            conn,
            row["path"],
            stage="l2_done",
            verdict=json.dumps(result.get("verdict"), ensure_ascii=False),
            description=json.dumps(result, ensure_ascii=False),
        )
    log.info("[stage2] 完成（占位，未真实调 API）")
