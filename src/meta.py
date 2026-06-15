"""L0 元数据筛的纯逻辑：EXIF 时间/GPS、图像质量检测、离线逆地理编码。

都是无副作用的纯函数，stage0_meta.py 负责编排和写 DB。
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
import exifread
import numpy as np

log = logging.getLogger(__name__)


# ============ EXIF 时间 ============

# 文件名兜底：匹配 20260615 / 2026-06-15 / 2026_06_15_103045 等
_FNAME_DATE = re.compile(r"(20\d{2})[-_]?(\d{2})[-_]?(\d{2})(?:[-_ ]?(\d{2})[-_:]?(\d{2})[-_:]?(\d{2}))?")


def parse_taken_at(path: str, tags: dict[str, Any]) -> str | None:
    """拍摄时间：EXIF DateTimeOriginal 为主，文件名解析兜底。返回 ISO 字符串或 None。"""
    raw = tags.get("EXIF DateTimeOriginal") or tags.get("Image DateTime")
    if raw:
        # EXIF 标准格式 "YYYY:MM:DD HH:MM:SS"
        try:
            dt = datetime.strptime(str(raw), "%Y:%m:%d %H:%M:%S")
            return dt.isoformat()
        except ValueError:
            pass

    # 兜底：从文件名解析
    m = _FNAME_DATE.search(Path(path).name)
    if m:
        y, mo, d = m.group(1), m.group(2), m.group(3)
        hh, mm, ss = m.group(4) or "00", m.group(5) or "00", m.group(6) or "00"
        try:
            dt = datetime(int(y), int(mo), int(d), int(hh), int(mm), int(ss))
            return dt.isoformat()
        except ValueError:
            return None
    return None


# ============ EXIF GPS ============

def _ratio_to_float(r) -> float:
    """exifread 的 Ratio 转 float。"""
    return float(r.num) / float(r.den) if r.den else 0.0


def _dms_to_decimal(dms, ref: str) -> float:
    """度分秒 + 方向 ref(N/S/E/W) → 十进制度。"""
    deg = _ratio_to_float(dms[0])
    minute = _ratio_to_float(dms[1])
    sec = _ratio_to_float(dms[2])
    val = deg + minute / 60.0 + sec / 3600.0
    if ref in ("S", "W"):
        val = -val
    return val


def parse_gps(tags: dict[str, Any]) -> tuple[float, float] | None:
    """从 EXIF 提取 (lat, lon)，无 GPS 返回 None。"""
    lat = tags.get("GPS GPSLatitude")
    lat_ref = tags.get("GPS GPSLatitudeRef")
    lon = tags.get("GPS GPSLongitude")
    lon_ref = tags.get("GPS GPSLongitudeRef")
    if not (lat and lat_ref and lon and lon_ref):
        return None
    try:
        return (
            _dms_to_decimal(lat.values, str(lat_ref)),
            _dms_to_decimal(lon.values, str(lon_ref)),
        )
    except (AttributeError, IndexError, ZeroDivisionError):
        return None


def read_exif(path: str) -> dict[str, Any]:
    """读 EXIF tags，失败返回空 dict。"""
    try:
        with open(path, "rb") as f:
            return exifread.process_file(f, details=False)
    except Exception as e:  # noqa: BLE001 — 读 EXIF 失败不应中断流水线
        log.debug("读 EXIF 失败 %s: %s", path, e)
        return {}


# ============ 离线逆地理编码 ============

_rg = None  # 懒加载，首次用时才载入城市索引


def reverse_geocode(lat: float, lon: float) -> str | None:
    """GPS → 地名（纯离线）。返回 "城市, 国家" 或 None。"""
    global _rg
    if _rg is None:
        import reverse_geocoder as rg

        _rg = rg
    try:
        res = _rg.search((lat, lon), mode=1)  # mode=1 单点，避免起多进程
        if res:
            r = res[0]
            parts = [r.get("name"), r.get("admin1"), r.get("cc")]
            return ", ".join(p for p in parts if p)
    except Exception as e:  # noqa: BLE001
        log.debug("逆地理编码失败 (%s,%s): %s", lat, lon, e)
    return None


# ============ 图像质量检测 ============

def assess_quality(path: str, l0_cfg: dict[str, Any]) -> str | None:
    """检测图像质量。返回淘汰原因 corrupt/tiny/blur/dark/bright，通过则 None。

    判断顺序：损坏 → 尺寸 → 亮度（过暗/过曝）→ 模糊。
    """
    img = cv2.imread(path)
    if img is None:
        return "corrupt"

    h, w = img.shape[:2]
    if w < l0_cfg.get("min_width", 0) or h < l0_cfg.get("min_height", 0):
        return "tiny"

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    mean_brightness = float(np.mean(gray))
    if mean_brightness < l0_cfg.get("dark_threshold", 0):
        return "dark"
    if mean_brightness > l0_cfg.get("bright_threshold", 255):
        return "bright"

    # 拉普拉斯方差：越低越模糊
    blur_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    if blur_var < l0_cfg.get("blur_threshold", 0):
        return "blur"

    return None
