"""生成样例图，覆盖 L0 各分支，供后续 stage 验链路。

运行：uv run python tests/fixtures/_gen.py
（生成的图提交进仓库，本脚本保留以便重建）

设计：sample1/sample5 是有纹理的「合格图」（足够边缘，过 blur 阈值），其中
sample1 写入 EXIF 拍摄时间 + 北京 GPS，用来验证 EXIF/逆地理编码路径；
sample2 过暗、sample3 过曝、sample4 尺寸过小，应被 L0 淘汰。
"""
import io
from pathlib import Path

import numpy as np
import piexif
from PIL import Image

HERE = Path(__file__).parent


def textured(size, base, seed):
    """生成有随机纹理的图（足够边缘，不会被判纯模糊）。"""
    rng = np.random.default_rng(seed)
    h, w = size[1], size[0]
    arr = rng.integers(0, 60, (h, w, 3), dtype=np.uint8) + np.array(base, dtype=np.uint8)
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    # 叠几条高对比线条，进一步抬高拉普拉斯方差
    arr[h // 3, :, :] = 255
    arr[:, w // 2, :] = 0
    return Image.fromarray(arr, "RGB")


def deg_to_dms_rational(deg):
    """十进制度 → EXIF GPS 度分秒 rational。"""
    d = int(deg)
    m = int((deg - d) * 60)
    s = round((deg - d - m / 60) * 3600 * 100)
    return [(d, 1), (m, 1), (s, 100)]


def exif_with_gps(dt="2026:06:15 10:30:45", lat=39.9042, lon=116.4074):
    """构造带拍摄时间 + 北京 GPS 的 EXIF bytes。"""
    exif = {
        "0th": {piexif.ImageIFD.DateTime: dt},
        "Exif": {piexif.ExifIFD.DateTimeOriginal: dt},
        "GPS": {
            piexif.GPSIFD.GPSLatitudeRef: "N",
            piexif.GPSIFD.GPSLatitude: deg_to_dms_rational(lat),
            piexif.GPSIFD.GPSLongitudeRef: "E",
            piexif.GPSIFD.GPSLongitude: deg_to_dms_rational(lon),
        },
    }
    return piexif.dump(exif)


def main():
    # 1. 合格图 + EXIF 时间 + 北京 GPS（验 EXIF/逆地理编码路径）
    img1 = textured((1280, 960), (180, 190, 200), seed=1)
    img1.save(HERE / "sample1.jpg", exif=exif_with_gps())

    # 2. 过暗
    Image.fromarray(
        np.full((960, 1280, 3), 12, dtype=np.uint8), "RGB"
    ).save(HERE / "sample2.jpg")

    # 3. 过曝
    Image.fromarray(
        np.full((960, 1280, 3), 248, dtype=np.uint8), "RGB"
    ).save(HERE / "sample3.jpg")

    # 4. 尺寸过小
    textured((320, 240), (180, 200, 180), seed=4).save(HERE / "sample4_small.png")

    # 5. 合格图（无 EXIF，验文件名兜底场景由后续覆盖；这里仅验质量通过）
    textured((1600, 1067), (200, 180, 160), seed=5).save(HERE / "sample5.jpg")

    print("已生成 5 张样例图到", HERE)


if __name__ == "__main__":
    main()
