"""L0 元数据筛：EXIF 时间/GPS + 离线逆地理编码 + OpenCV 模糊/亮度/尺寸/损坏。

废片直接淘汰（mark stage='rejected' + l0_reject 原因），几乎不花算力。
通过的图记录 taken_at / location，流转到 l0_done。
纯逻辑在 meta.py，本文件只做编排和写 DB。
"""
from __future__ import annotations

import logging
import sqlite3

from .config import Config
from . import db, meta

log = logging.getLogger(__name__)


def run(conn: sqlite3.Connection, cfg: Config) -> None:
    photos = db.get_pending(conn, "pending")
    log.info("[stage0] L0 元数据筛：待处理 %d 张", len(photos))

    l0_cfg = cfg.l0
    rejected = 0
    for row in photos:
        path = row["path"]

        # 1. 质量检测（损坏/尺寸/亮度/模糊）——废片直接淘汰，不再读 EXIF
        reason = meta.assess_quality(path, l0_cfg)
        if reason:
            db.mark(conn, path, stage="rejected", l0_reject=reason)
            rejected += 1
            log.debug("[stage0] 淘汰 %s（%s）", path, reason)
            continue

        # 2. 通过的图：解析 EXIF 时间 + GPS → 地名
        tags = meta.read_exif(path)
        taken_at = meta.parse_taken_at(path, tags)
        location = None
        gps = meta.parse_gps(tags)
        if gps:
            location = meta.reverse_geocode(*gps)

        db.mark(conn, path, stage="l0_done", taken_at=taken_at, location=location)

    passed = len(photos) - rejected
    log.info("[stage0] 完成：通过 %d 张，淘汰 %d 张", passed, rejected)
