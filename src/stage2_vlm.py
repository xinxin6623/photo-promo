"""L2 VLM 精筛 + 结构化语义描述（Phase 3 实现）。

把 l1_done 的图按 l1_score 降序取前 top_n 张，逐张发给 VLMProvider，一次调用
同时做「是否适合入库（带理由）」判断 + 输出结构化语义描述 JSON（schema 见
docs/io-contract.md §3.3）：
  - verdict.fit=True 且（无门槛 或 通过门槛）→ stage='l2_done'，写 description（终态入库）
  - verdict.fit=False 且 require_quality_gate=True → stage='rejected'，记 verdict 理由
  - require_quality_gate=False（只描述不筛）→ 全部 l2_done，质量交下游自判

照片库 vault 的导出（library/）放到 Phase 4，本 stage 只写 DB。
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
    if not photos:
        log.info("[stage2] 无待处理图，跳过")
        return

    l2 = cfg.l2
    top_n = int(l2.get("top_n", 50))
    gate = bool(l2.get("require_quality_gate", True))

    # 按 l1_score 降序取前 top_n（送 API 的少量精华图，省钱）
    ranked = sorted(photos, key=lambda r: (r["l1_score"] or 0.0), reverse=True)
    selected = ranked[:top_n]
    log.info(
        "[stage2] L2 VLM 精筛+结构化描述：l1_done %d 张，送 API %d 张（top_n=%d，门槛=%s）",
        len(photos), len(selected), top_n, "开" if gate else "关",
    )

    provider = get_provider(cfg)
    kept = rejected = 0
    for i, row in enumerate(selected, 1):
        context = {"taken_at": row["taken_at"], "location": row["location"]}
        result = provider.score_and_describe(row["path"], context=context)
        verdict = result.get("verdict") or {}
        fit = bool(verdict.get("fit", True))

        if gate and not fit:
            db.mark(
                conn, row["path"],
                stage="rejected",
                verdict=json.dumps(verdict, ensure_ascii=False),
            )
            rejected += 1
            log.debug("[stage2] (%d/%d) 淘汰：%s — %s", i, len(selected), row["path"], verdict.get("reason"))
        else:
            db.mark(
                conn, row["path"],
                stage="l2_done",
                verdict=json.dumps(verdict, ensure_ascii=False),
                description=json.dumps(result, ensure_ascii=False),
            )
            kept += 1
            log.debug("[stage2] (%d/%d) 入库：%s", i, len(selected), row["path"])

    # 未进入 top_n 的 l1_done 图保持原状（下次跑或调大 top_n 时再处理）
    log.info("[stage2] 完成：入库 %d 张，淘汰 %d 张", kept, rejected)
