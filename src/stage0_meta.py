"""L0 元数据筛（占位，Phase 1 填实现）。

Phase 1 将做：EXIF 时间/GPS 解析 + OpenCV 拉普拉斯方差判模糊 + 亮度判过暗过曝
+ 离线逆地理编码。废片直接淘汰，几乎不花算力。

Phase 0：占位流转，把 pending 的图全部标成 l0_done，不做真实判断。
"""
from __future__ import annotations

import logging
import sqlite3

from .config import Config
from . import db

log = logging.getLogger(__name__)


def run(conn: sqlite3.Connection, cfg: Config) -> None:
    photos = db.get_pending(conn, "pending")
    log.info("[stage0] L0 元数据筛（占位）：待处理 %d 张", len(photos))
    for row in photos:
        # TODO(Phase 1): 真实 EXIF + 模糊/亮度判断；废片 mark(stage='rejected', l0_reject=...)
        db.mark(conn, row["path"], stage="l0_done")
    log.info("[stage0] 完成（占位，未做真实筛选）")
