# -*- coding: utf-8 -*-
"""纯标准库 PNG 像素扫描：证明折叠前后「哪一栏占了哪段画布」。

为什么要它：几何判据（getBoundingClientRect）只说明浏览器怎么算的，
主公要的是像素证据——截图上每一段到底是什么底色。
本脚本把一行像素按调色板归类：
  P = --paper #f6f2e9（中栏对话流底色）
  C = --card  纸色上叠 50% 白（左右两栏面板底色，约 #faf8f4）
  D = 明显更深的线/字（--line、--ink 等）
再输出连续段的起止，用来核对轨道边界是否落在 240 / 1140。
"""
import struct
import sys
import zlib
from pathlib import Path

PAPER = (246, 242, 233)
CARD = (251, 249, 244)


def decode_png(path: Path):
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "不是 PNG"
    pos = 8
    idat = bytearray()
    width = height = depth = ctype = None
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        kind = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + length]
        if kind == b"IHDR":
            width, height, depth, ctype = struct.unpack(">IIBB", chunk[:10])
        elif kind == b"IDAT":
            idat += chunk
        elif kind == b"IEND":
            break
        pos += 12 + length
    assert depth == 8 and ctype in (2, 6), f"只支持 8bit RGB/RGBA，实为 depth={depth} type={ctype}"
    ch = 3 if ctype == 2 else 4
    raw = zlib.decompress(bytes(idat))
    stride = width * ch
    out = bytearray(height * stride)
    prev = bytearray(stride)
    i = 0
    for y in range(height):
        ft = raw[i]; i += 1
        line = bytearray(raw[i:i + stride]); i += stride
        if ft == 1:          # Sub
            for x in range(ch, stride):
                line[x] = (line[x] + line[x - ch]) & 255
        elif ft == 2:        # Up
            for x in range(stride):
                line[x] = (line[x] + prev[x]) & 255
        elif ft == 3:        # Average
            for x in range(stride):
                a = line[x - ch] if x >= ch else 0
                b = prev[x]
                line[x] = (line[x] + ((a + b) >> 1)) & 255
        elif ft == 4:        # Paeth
            for x in range(stride):
                a = line[x - ch] if x >= ch else 0
                b = prev[x]
                c = prev[x - ch] if x >= ch else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[x] = (line[x] + pr) & 255
        elif ft != 0:
            raise SystemExit(f"未知过滤类型 {ft}")
        out[y * stride:(y + 1) * stride] = line
        prev = line
    return width, height, ch, bytes(out)


def classify(px, bg):
    """离纸色与卡色谁近归谁；两者都差得远就是线或字。"""
    dp = sum((a - b) ** 2 for a, b in zip(px, PAPER))
    dc = sum((a - b) ** 2 for a, b in zip(px, CARD))
    if min(dp, dc) > 900:
        return "D"
    return "P" if dp <= dc else "C"


def segments(width, ch, buf, y, min_len=24):
    stride = width * ch
    runs = []
    cur, start = None, 0
    for x in range(width):
        o = y * stride + x * ch
        tag = classify(buf[o:o + 3], None)
        if tag != cur:
            if cur is not None and x - start >= min_len:
                runs.append((cur, start, x - 1))
            cur, start = tag, x
    if cur is not None and width - start >= min_len:
        runs.append((cur, start, width - 1))
    return runs


def scan(path: str, rows=(200, 450, 700)):
    p = Path(path)
    width, height, ch, buf = decode_png(p)
    print(f"\n== {p.name}  {width}x{height} ==")
    for y in rows:
        if y >= height:
            continue
        runs = segments(width, ch, buf, y)
        desc = "  ".join(f"{t}[{a}-{b}]" for t, a, b in runs)
        print(f"  y={y:<4} {desc}")
    return width, height


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        scan(arg)
