"""本地 YOLO 的 ONNX 运行时：解码页图、前处理、推理与后处理。

只被 ``layout_yolo`` 调用。``onnxruntime`` / ``numpy`` 都是懒加载：
没装运行库时上层走降级路线，底座绝不因为缺一个可选依赖起不来。
"""

from __future__ import annotations

import struct
import zlib
from typing import Any

INPUT_SIZE = 1024
CONF_THRESHOLD = 0.25
IOU_THRESHOLD = 0.45

# DocLayout-YOLO 的类别表；abandon 是页眉页脚，直接丢弃。
LABELS = {
    0: "标题", 1: "正文", 2: "", 3: "图片", 4: "图注",
    5: "表格", 6: "表注", 7: "表脚注", 8: "公式", 9: "公式注",
}
SKIP_CLASSES = {2}


class RuntimeErrorYolo(Exception):
    """推理侧失败；上层据此换下一档模型/硬件。"""


def load_session(model_path: str, providers: list[str]) -> Any:
    try:
        import onnxruntime as ort  # noqa: PLC0415 - 懒加载
    except Exception as exc:  # noqa: BLE001
        raise RuntimeErrorYolo(f"onnxruntime 不可用：{exc}") from exc
    if not providers:
        providers = ["CPUExecutionProvider"]
    try:
        return ort.InferenceSession(model_path, providers=providers)
    except Exception as exc:  # noqa: BLE001 - 显存不足/算子不支持都算本档失败
        raise RuntimeErrorYolo(f"加载模型失败（{', '.join(providers)}）：{exc}") from exc


def infer_regions(session: Any, raw: bytes, width: float,
                  height: float) -> list[dict[str, Any]]:
    """一张页图 → 原图像素坐标的题块；坐标口径与 ``page_render`` 完全一致。"""
    if not raw:
        return []
    try:
        import numpy as np  # noqa: PLC0415 - 懒加载
    except Exception as exc:  # noqa: BLE001
        raise RuntimeErrorYolo(f"numpy 不可用：{exc}") from exc
    pixels = png_pixels(raw)
    source = np.frombuffer(pixels, dtype=np.uint8).reshape((int(height), int(width), 3))
    tensor, scale, pad_x, pad_y = letterbox(source, INPUT_SIZE)
    input_meta = (session.get_inputs() or [None])[0]
    input_name = getattr(input_meta, "name", None) or "images"
    try:
        outputs = session.run(None, {input_name: tensor})
    except Exception as exc:  # noqa: BLE001 - 单页推理失败交给下一档
        raise RuntimeErrorYolo(f"推理失败（{', '.join(session.get_providers())}）：{exc}") from exc
    boxes = decode_output(np, outputs, INPUT_SIZE)
    kept = non_max_suppression(np, boxes)
    regions: list[dict[str, Any]] = []
    for x1, y1, x2, y2, score, class_id in kept:
        label = LABELS.get(int(class_id), "")
        if int(class_id) in SKIP_CLASSES:
            continue
        left = (float(x1) - pad_x) / scale
        top = (float(y1) - pad_y) / scale
        right = (float(x2) - pad_x) / scale
        bottom = (float(y2) - pad_y) / scale
        left, top = max(0.0, left), max(0.0, top)
        right, bottom = min(float(width), right), min(float(height), bottom)
        if right - left < 8 or bottom - top < 8:
            continue
        regions.append({
            "no": len(regions) + 1,
            "x": round(left, 1), "y": round(top, 1),
            "w": round(right - left, 1), "h": round(bottom - top, 1),
            "label": label, "text": "", "score": round(float(score), 4),
        })
    return regions


def png_pixels(raw: bytes) -> bytes:
    """8 位 PNG → RGB 像素；页图由 pypdfium2 渲染，只认非隔行扫描。"""
    if raw[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeErrorYolo("页图不是 PNG")
    position, width, height = 8, 0, 0
    depth = color = interlace = 0
    palette = b""
    chunks = bytearray()
    while position + 8 <= len(raw):
        length = struct.unpack(">I", raw[position:position + 4])[0]
        kind = raw[position + 4:position + 8]
        data = raw[position + 8:position + 8 + length]
        position += 12 + length
        if kind == b"IHDR":
            width, height, depth, color, _, _, interlace = struct.unpack(">IIBBBBB", data[:13])
        elif kind == b"PLTE":
            palette = data
        elif kind == b"IDAT":
            chunks.extend(data)
        elif kind == b"IEND":
            break
    if not width or not height or depth != 8 or interlace:
        raise RuntimeErrorYolo("只支持 8 位非隔行 PNG")
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color)
    if channels is None:
        raise RuntimeErrorYolo(f"不认识的 PNG 颜色类型：{color}")
    try:
        inflated = zlib.decompress(bytes(chunks))
    except zlib.error as exc:
        raise RuntimeErrorYolo(f"PNG 解压失败：{exc}") from exc
    stride = width * channels
    if len(inflated) < (stride + 1) * height:
        raise RuntimeErrorYolo("PNG 像素数据不完整")
    rows: list[bytearray] = []
    previous = bytearray(stride)
    offset = 0
    for _ in range(height):
        filter_type = inflated[offset]
        line = bytearray(inflated[offset + 1:offset + 1 + stride])
        offset += stride + 1
        _unfilter(line, previous, filter_type, channels)
        rows.append(line)
        previous = line
    rgb = bytearray()
    for line in rows:
        for index in range(width):
            if color == 3:
                base = line[index] * 3
                rgb.extend(palette[base:base + 3] or b"\x00\x00\x00")
            else:
                base = index * channels
                if color in (0, 4):
                    value = line[base]
                    rgb.extend((value, value, value))
                else:
                    rgb.extend(line[base:base + 3])
    return bytes(rgb)


def _unfilter(line: bytearray, previous: bytearray, filter_type: int, bpp: int) -> None:
    if filter_type == 0:
        return
    for index in range(len(line)):
        left = line[index - bpp] if index >= bpp else 0
        up = previous[index]
        if filter_type == 1:
            line[index] = (line[index] + left) & 0xFF
        elif filter_type == 2:
            line[index] = (line[index] + up) & 0xFF
        elif filter_type == 3:
            line[index] = (line[index] + ((left + up) >> 1)) & 0xFF
        elif filter_type == 4:
            up_left = previous[index - bpp] if index >= bpp else 0
            line[index] = (line[index] + _paeth(left, up, up_left)) & 0xFF


def _paeth(left: int, up: int, up_left: int) -> int:
    estimate = left + up - up_left
    distances = (abs(estimate - left), abs(estimate - up), abs(estimate - up_left))
    return (left, up, up_left)[distances.index(min(distances))]


def letterbox(source: Any, size: int) -> tuple[Any, float, float, float]:
    """等比缩放 + 灰边补齐，返回 NCHW float32 张量与回算参数。"""
    import numpy as np  # noqa: PLC0415 - 懒加载

    height, width = source.shape[0], source.shape[1]
    scale = min(size / float(width), size / float(height))
    drawn_w, drawn_h = max(1, int(round(width * scale))), max(1, int(round(height * scale)))
    pad_x, pad_y = (size - drawn_w) / 2.0, (size - drawn_h) / 2.0
    canvas = np.full((size, size, 3), 114, dtype=np.uint8)
    xs = np.clip(((np.arange(drawn_w) + 0.5) / scale - 0.5), 0, width - 1)
    ys = np.clip(((np.arange(drawn_h) + 0.5) / scale - 0.5), 0, height - 1)
    x0 = np.floor(xs).astype(np.int64)
    y0 = np.floor(ys).astype(np.int64)
    x1 = np.minimum(x0 + 1, width - 1)
    y1 = np.minimum(y0 + 1, height - 1)
    wx = (xs - x0)[None, :, None]
    wy = (ys - y0)[:, None, None]
    top = source[y0][:, x0] * (1 - wx) + source[y0][:, x1] * wx
    bottom = source[y1][:, x0] * (1 - wx) + source[y1][:, x1] * wx
    resized = top * (1 - wy) + bottom * wy
    left, top_pad = int(round(pad_x)), int(round(pad_y))
    canvas[top_pad:top_pad + drawn_h, left:left + drawn_w] = resized.astype(np.uint8)
    tensor = canvas[:, :, ::-1].transpose(2, 0, 1).astype(np.float32) / 255.0
    return tensor[None, ...], scale, float(left), float(top_pad)


def decode_output(np: Any, outputs: Any, size: int) -> Any:
    """兼容端到端 [1,N,6] 与原始 [1,4+nc,N]/[1,N,4+nc] 两种导出。"""
    if not outputs:
        return np.zeros((0, 6), dtype=np.float32)
    array = np.asarray(outputs[0], dtype=np.float32)
    if array.ndim == 3:
        array = array[0]
    if array.ndim != 2:
        return np.zeros((0, 6), dtype=np.float32)
    if array.shape[0] < array.shape[1]:
        array = array.T
    columns = array.shape[1]
    if columns == 6:
        rows = array
    elif columns >= 5:
        centers, wh, scores = array[:, :2], array[:, 2:4], array[:, 4:]
        class_ids = scores.argmax(axis=1)
        confidence = scores.max(axis=1)
        x1 = centers[:, 0] - wh[:, 0] / 2
        y1 = centers[:, 1] - wh[:, 1] / 2
        x2 = centers[:, 0] + wh[:, 0] / 2
        y2 = centers[:, 1] + wh[:, 1] / 2
        rows = np.stack([x1, y1, x2, y2, confidence, class_ids.astype(np.float32)], axis=1)
    else:
        return np.zeros((0, 6), dtype=np.float32)
    rows = rows[rows[:, 4] >= CONF_THRESHOLD]
    if rows.size and float(rows[:, :4].max()) <= 2.0:
        rows[:, :4] *= float(size)
    return rows


def non_max_suppression(np: Any, rows: Any) -> list[tuple]:
    kept: list[tuple] = []
    for class_id in set(int(row[5]) for row in rows):
        group = [row for row in rows if int(row[5]) == class_id]
        group.sort(key=lambda row: float(row[4]), reverse=True)
        while group:
            best = group.pop(0)
            kept.append(tuple(float(value) for value in best))
            group = [row for row in group if _iou(best, row) <= IOU_THRESHOLD]
    kept.sort(key=lambda row: (row[1], row[0]))
    return kept


def _iou(first: Any, second: Any) -> float:
    x1, y1 = max(float(first[0]), float(second[0])), max(float(first[1]), float(second[1]))
    x2 = min(float(first[2]), float(second[2]))
    y2 = min(float(first[3]), float(second[3]))
    overlap = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    first_area = max(0.0, float(first[2]) - float(first[0])) * max(0.0, float(first[3]) - float(first[1]))
    second_area = max(0.0, float(second[2]) - float(second[0])) * max(0.0, float(second[3]) - float(second[1]))
    union = first_area + second_area - overlap
    return overlap / union if union > 0 else 0.0
