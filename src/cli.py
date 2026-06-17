"""promo 入口：扫描目录入库 → stage0 → stage1 → stage2。

每个 stage 从 DB 取该阶段待处理的图，跑挂重跑只处理未完成的（断点续跑）。
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .config import load_config
from . import db
from . import stage0_meta, stage1_clip, stage2_vlm, export

# 支持的图片扩展名
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".heic"}


def scan_and_register(conn, photos_dir: Path) -> int:
    """递归扫描目录里的图片，登记进 DB。返回本次目录里发现的图片总数。"""
    count = 0
    for p in sorted(photos_dir.rglob("*")):
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
            db.upsert_photo(conn, str(p.resolve()))
            count += 1
    return count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="promo",
        description="活动照片智能筛选 + 结构化语义描述照片库（L0 元数据筛 → L1 SigLIP 粗筛 → L2 VLM 精筛+描述）",
    )
    parser.add_argument("photos_dir", help="待处理照片目录（递归扫描）")
    parser.add_argument("-c", "--config", default="config.yaml", help="配置文件路径（默认 config.yaml）")
    parser.add_argument("-v", "--verbose", action="store_true", help="输出调试日志")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s",
    )
    log = logging.getLogger("promo")

    photos_dir = Path(args.photos_dir)
    if not photos_dir.is_dir():
        log.error("目录不存在：%s", photos_dir)
        return 1

    cfg = load_config(args.config)

    conn = db.init_db(cfg.db_path)
    log.info("数据库：%s | 硬件档位：%s", cfg.db_path, cfg.hardware)

    n = scan_and_register(conn, photos_dir)
    log.info("扫描 %s：发现 %d 张图，已入库", photos_dir, n)

    # 三层漏斗依次跑（断点续跑：各 stage 内部只取未完成的）
    stage0_meta.run(conn, cfg)
    stage1_clip.run(conn, cfg)
    stage2_vlm.run(conn, cfg)

    # Phase 4：把 l2_done 入库图导出成 library/ 照片库 vault
    export.run(conn, cfg)

    log.info("各阶段统计：%s", db.counts_by_stage(conn))
    conn.close()
    log.info("完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
