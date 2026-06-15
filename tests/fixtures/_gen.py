"""生成 5 张样例图，覆盖不同尺寸/亮度/内容，供后续 stage 验链路。

运行：uv run python tests/fixtures/_gen.py
（生成的 .jpg/.png 提交进仓库，本脚本可保留以便重建）
"""
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).parent


def text_img(size, bg, fg, text, name):
    img = Image.new("RGB", size, bg)
    d = ImageDraw.Draw(img)
    d.text((20, 20), text, fill=fg)
    img.save(HERE / name)


def main():
    # 1. 正常明亮的「合格」图
    text_img((1280, 960), (200, 220, 240), (30, 30, 30), "sample 1 - bright normal", "sample1.jpg")
    # 2. 偏暗（模拟过暗废片）
    text_img((1280, 960), (15, 15, 20), (90, 90, 90), "sample 2 - dark", "sample2.jpg")
    # 3. 过曝（接近全白）
    text_img((1280, 960), (250, 250, 250), (230, 230, 230), "sample 3 - overexposed", "sample3.jpg")
    # 4. 尺寸过小（模拟应被 L0 淘汰）
    text_img((320, 240), (180, 200, 180), (20, 20, 20), "small", "sample4_small.png")
    # 5. 另一张正常图（不同色调）
    text_img((1600, 1067), (210, 190, 170), (40, 30, 20), "sample 5 - warm tone", "sample5.jpg")

    print("已生成 5 张样例图到", HERE)


if __name__ == "__main__":
    main()
