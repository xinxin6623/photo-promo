"""SQLite 状态机：每张图一条记录，支持断点续跑。

stage 取值：
  pending   入库待处理
  l0_done   通过 L0 元数据筛
  l1_done   通过 L1 SigLIP 粗筛
  l2_done   通过 L2 VLM 精筛（终态，已出文案）
  rejected  任一阶段被淘汰（淘汰原因看对应字段）

断点续跑：每个 stage 只取该阶段的 pending 图处理，跑挂重跑不会重复处理已完成的。
pipeline.db 是派生物，可删重建。
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS photos (
    path        TEXT PRIMARY KEY,   -- 图片绝对路径
    stage       TEXT NOT NULL,      -- pending / l0_done / l1_done / l2_done / rejected
    taken_at    TEXT,               -- EXIF 拍摄时间（Phase 1 填）
    location    TEXT,               -- 逆地理编码地名（Phase 1 填）
    l0_reject   TEXT,               -- L0 淘汰原因 blur/dark/bright/tiny/corrupt，NULL=通过
    l1_score    REAL,               -- SigLIP 宣传适配度分（Phase 2 填）
    verdict     TEXT,               -- VLM 精筛结论+理由（Phase 3 填）
    caption     TEXT,               -- 生成文案（Phase 3 填）
    updated_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_photos_stage ON photos(stage);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db(db_path: str | Path) -> sqlite3.Connection:
    """打开（必要时创建）数据库并建表，返回连接。"""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def upsert_photo(conn: sqlite3.Connection, path: str) -> None:
    """登记一张图。已存在则不覆盖其状态（保证断点续跑幂等）。"""
    conn.execute(
        """
        INSERT INTO photos (path, stage, updated_at)
        VALUES (?, 'pending', ?)
        ON CONFLICT(path) DO NOTHING
        """,
        (path, _now()),
    )
    conn.commit()


def get_pending(conn: sqlite3.Connection, stage: str) -> list[sqlite3.Row]:
    """取某阶段待处理的图。

    stage 传入的是「当前所处阶段」，即上一阶段的完成态：
      stage0 处理 stage='pending'
      stage1 处理 stage='l0_done'
      stage2 处理 stage='l1_done'
    """
    cur = conn.execute(
        "SELECT * FROM photos WHERE stage = ? ORDER BY path", (stage,)
    )
    return cur.fetchall()


def mark(conn: sqlite3.Connection, path: str, **fields) -> None:
    """更新一张图的字段（含 stage 流转）。自动刷新 updated_at。"""
    if not fields:
        return
    fields["updated_at"] = _now()
    cols = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(
        f"UPDATE photos SET {cols} WHERE path = ?",
        (*fields.values(), path),
    )
    conn.commit()


def counts_by_stage(conn: sqlite3.Connection) -> dict[str, int]:
    """各 stage 的图数量，用于进度展示。"""
    cur = conn.execute("SELECT stage, COUNT(*) AS n FROM photos GROUP BY stage")
    return {row["stage"]: row["n"] for row in cur.fetchall()}
