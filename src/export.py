"""Phase 4：把 l2_done 入库图导出成 obwiki 式照片库 vault。

产物结构（见 docs/io-contract.md §3）：
  library/
  ├── index.md            # L0 索引：全库句柄一览
  ├── photos/<id>.md      # 每张图：frontmatter=L0 句柄 / 正文=L1 结构化描述
  └── images/<id>.<ext>   # 原图（copy_images=true 复制，否则软链）

<id>：图片内容 sha256 前 N 位（config export.id_len），稳定且去重友好。
related 互链：scene 相同 且 taken_at 相差 ≤ link_window_min 分钟的图互相链接，
带「为什么相关」一句。纯本地逻辑，不调网络/API。
"""
from __future__ import annotations

import hashlib
import json
import logging
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import Config
from . import db

log = logging.getLogger(__name__)


def _photo_id(image_path: str, id_len: int) -> str:
    """图片内容 sha256 前 id_len 位作为稳定 id。"""
    h = hashlib.sha256(Path(image_path).read_bytes()).hexdigest()
    return h[:id_len]


def _parse_taken_at(value: str | None) -> datetime | None:
    """把 DB 里的 taken_at 字符串解析成 datetime（失败返回 None）。"""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def _build_related(entries: list[dict[str, Any]], window_min: int) -> None:
    """就地给每个 entry 填 related：同 scene 且 taken_at 相差 ≤ window_min 分钟。

    每条 related 形如 "a1b2c3d4e5f6 — 同场景(合影)，拍摄相差约 5 分钟"。
    缺 taken_at 的图不参与时间邻近判定（只靠 scene 无法判邻近，跳过）。
    """
    for a in entries:
        ta = a["_taken_dt"]
        rel: list[str] = []
        if ta is None or not a.get("scene"):
            a["related"] = rel
            continue
        for b in entries:
            if b["id"] == a["id"]:
                continue
            if b.get("scene") != a.get("scene"):
                continue
            tb = b["_taken_dt"]
            if tb is None:
                continue
            diff_min = abs((ta - tb).total_seconds()) / 60.0
            if diff_min <= window_min:
                rel.append(f'{b["id"]} — 同场景({a["scene"]})，拍摄相差约 {round(diff_min)} 分钟')
        a["related"] = rel


def _yaml_list(items: list[str]) -> str:
    """渲染成 yaml flow 列表 [a, b]（条目里有特殊字符也安全：用 json 串）。"""
    return "[" + ", ".join(items) + "]"


def _render_entry(e: dict[str, Any]) -> str:
    """渲染单条 photos/<id>.md（frontmatter L0 + 正文 L1）。"""
    desc = e["desc"]
    fm_tags = _yaml_list(desc.get("tags", []) or [])
    related_lines = "".join(f"\n  - {r}" for r in e["related"]) or " []"

    fm = [
        "---",
        f'id: {e["id"]}',
        f'path: images/{e["id"]}.{e["ext"]}',
        f'summary: {desc.get("summary", "")}',
        f'scene: {desc.get("scene", "")}',
        f"tags: {fm_tags}",
        f'taken_at: {e["taken_at"] or ""}',
        f'location: {e["location"] or ""}',
        f'l1_score: {e["l1_score"] if e["l1_score"] is not None else ""}',
        f'quality: {desc.get("quality", "")}',
        f'updated: {datetime.now().date().isoformat()}',
        f"related:{related_lines}",
        "---",
    ]

    subjects = "、".join(desc.get("subjects", []) or [])
    mood = "、".join(desc.get("mood", []) or [])
    suitable = "、".join(desc.get("suitable_for", []) or [])
    body = [
        "",
        "## 语义描述",
        "",
        desc.get("description", ""),
        "",
        "## 结构化字段",
        f"- **主体 (subjects)**: {subjects}",
        f'- **人数 (people_count)**: {desc.get("people_count", "")}',
        f"- **氛围 (mood)**: {mood}",
        f"- **适用场景 (suitable_for)**: {suitable}",
    ]
    return "\n".join(fm + body) + "\n"


def _render_index(entries: list[dict[str, Any]]) -> str:
    """渲染 index.md：L0 句柄一览（可全量扫描）。"""
    lines = [
        "# 照片库索引 (L0)",
        "",
        f"> 共 {len(entries)} 张入库图。渐进式披露：先扫本表 L0 句柄圈候选，",
        "> 再读 `photos/<id>.md` 的 L1 描述，最后才打开 `images/<id>` 原图。",
        "> 协议见 [io-contract](../docs/io-contract.md) §3.2。",
        "",
        "| id | summary | scene | tags | taken_at | location |",
        "|---|---|---|---|---|---|",
    ]
    for e in sorted(entries, key=lambda x: (x["taken_at"] or "", x["id"])):
        d = e["desc"]
        tags = " ".join(d.get("tags", []) or [])
        link = f'[{e["id"]}](photos/{e["id"]}.md)'
        lines.append(
            f'| {link} | {d.get("summary","")} | {d.get("scene","")} '
            f'| {tags} | {e["taken_at"] or ""} | {e["location"] or ""} |'
        )
    return "\n".join(lines) + "\n"


def run(conn: sqlite3.Connection, cfg: Config) -> None:
    rows = db.get_pending(conn, "l2_done")
    if not rows:
        log.info("[export] 无 l2_done 入库图，跳过 vault 导出")
        return

    exp = cfg.export
    out_dir = cfg.resolve(exp.get("dir", "library"))
    photos_dir = out_dir / "photos"
    images_dir = out_dir / "images"
    photos_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    id_len = int(exp.get("id_len", 12))
    copy_images = bool(exp.get("copy_images", True))
    window_min = int(exp.get("link_window_min", 30))

    # 1. 收集所有入库条目（解析 description JSON，算 id，复制/软链原图）
    entries: list[dict[str, Any]] = []
    for row in rows:
        src = Path(row["path"])
        if not src.exists():
            log.warning("[export] 原图丢失，跳过：%s", src)
            continue
        try:
            desc = json.loads(row["description"]) if row["description"] else {}
        except json.JSONDecodeError:
            log.warning("[export] description 非合法 JSON，跳过：%s", src)
            continue

        pid = _photo_id(str(src), id_len)
        ext = src.suffix.lstrip(".").lower() or "jpg"
        dst = images_dir / f"{pid}.{ext}"
        if not dst.exists():
            if copy_images:
                shutil.copy2(src, dst)
            else:
                dst.symlink_to(src.resolve())

        entries.append({
            "id": pid,
            "ext": ext,
            "desc": desc,
            "scene": desc.get("scene"),
            "taken_at": row["taken_at"],
            "location": row["location"],
            "l1_score": row["l1_score"],
            "_taken_dt": _parse_taken_at(row["taken_at"]),
        })

    # 2. 建图间互链（同 scene + 时间邻近）
    _build_related(entries, window_min)

    # 3. 写每条 photos/<id>.md + 总 index.md
    for e in entries:
        (photos_dir / f'{e["id"]}.md').write_text(_render_entry(e), encoding="utf-8")
    (out_dir / "index.md").write_text(_render_index(entries), encoding="utf-8")

    n_links = sum(len(e["related"]) for e in entries)
    log.info(
        "[export] 导出照片库 vault：%d 张 → %s（%s原图，建 %d 条互链）",
        len(entries), out_dir, "复制" if copy_images else "软链", n_links,
    )
