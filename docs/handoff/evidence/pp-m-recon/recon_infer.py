"""侦查真测：PP-M ONNX CPU 推理＋解码口径验证（paddlex 3.7.2 口径原创实现）。
用法: python recon_infer.py [n]  —— n=跑几块夹具，默认 1。单块超 120s 判分钟级停跑。
"""
import sys, os, time, re, io
sys.path.insert(0, r"E:\jiuzhang\jiuzhang-operator")
import numpy as np
import cv2
import yaml
from PIL import Image, ImageOps

ROOT = r"E:\jiuzhang\jiuzhang-operator"
MODEL = os.path.join(ROOT, "engines", "formula", "models", "pp_formulanet_plus_m.onnx")
YML = os.path.join(ROOT, "engines", "formula", "models", "pp_formulanet_plus_m_inference.yml")
FIX = os.path.join(ROOT, ".system_generated", "pp-m-recon", "fixtures")

cfg = yaml.safe_load(open(YML, encoding="utf-8"))
tok = cfg["PostProcess"]["character_dict"]["fast_tokenizer_file"]
VOCAB = {i: t for t, i in tok["model"]["vocab"].items()}
SPECIAL = {t["id"] for t in tok["added_tokens"]}

def bytes_to_unicode():
    bs = list(range(ord("!"), ord("~") + 1)) + list(range(ord("¡"), ord("¬") + 1)) \
        + list(range(ord("®"), ord("ÿ") + 1))
    cs = bs[:]
    n = 0
    for b in range(256):
        if b not in bs:
            bs.append(b); cs.append(256 + n); n += 1
    return dict(zip(bs, [chr(c) for c in cs]))

BYTE_ENC = bytes_to_unicode()
BYTE_DEC = {v: k for k, v in BYTE_ENC.items()}

def crop_margin(img):
    data = np.array(img.convert("L")).astype(np.uint8)
    mx, mn = int(data.max()), int(data.min())
    if mx == mn:
        return img
    data = (data - mn) / (mx - mn) * 255
    gray = 255 * (data < 200).astype(np.uint8)
    coords = cv2.findNonZero(gray)
    if coords is None:
        return img
    a, b, w, h = cv2.boundingRect(coords)
    return img.crop((a, b, w + a, h + b))

def preprocess(png_bytes):
    img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    img = crop_margin(img)
    if img.height == 0 or img.width == 0:
        return None
    short = 384
    w, h = img.size
    if w <= h:
        nw, nh = short, int(short * h / w)
    else:
        nw, nh = int(short * w / h), short
    img = img.resize((nw, nh), resample=2)
    img.thumbnail((384, 384))
    dw, dh = 384 - img.width, 384 - img.height
    pad = (dw // 2, dh // 2, dw - dw // 2, dh - dh // 2)
    arr = np.array(ImageOps.expand(img, pad)).astype(np.float32)
    arr = (arr / 255.0 - 0.7931) / 0.1738
    return arr[:, :, 0][np.newaxis, np.newaxis, :, :]

def normalize_space(s):
    text_reg = r"(\\(operatorname|mathrm|text|mathbf)\s?\*? {.*?})"
    letter = r"[a-zA-Z]"
    noletter = r"[\W_^\d]"
    names = []
    for x in re.findall(text_reg, s):
        pattern = r"(\\[a-zA-Z]+)\s(?=\w)|\\[a-zA-Z]+\s(?=})"
        for m in re.findall(pattern, x[0]):
            if m not in ("\\operatorname", "\\mathrm", "\\text", "\\mathbf") and m.strip():
                s = s.replace(m, m + "XXXXXXX")
                s = s.replace(" ", "")
                names.append(s)
    if names:
        s = re.sub(text_reg, lambda match: str(names.pop(0)), s)
    news = s
    while True:
        s = news
        news = re.sub(r"(?!\\ )(%s)\s+?(%s)" % (noletter, noletter), r"\1\2", s)
        news = re.sub(r"(?!\\ )(%s)\s+?(%s)" % (noletter, letter), r"\1\2", news)
        news = re.sub(r"(%s)\s+?(%s)" % (letter, noletter), r"\1\2", news)
        if news == s:
            break
    return s.replace("XXXXXXX", " ")

def post_process(text):
    text = re.sub(r"\\text\s*{([^{}]*[\u4e00-\u9fff]+[^{}]*)}", r"\1", text)
    text = text.replace('"', "")
    return normalize_space(text)

def decode(ids):
    ids = list(ids)
    if 2 in ids:
        ids = ids[:ids.index(2)]
    raw = bytearray()
    for i in ids:
        i = int(i)
        if i in SPECIAL:
            continue
        token = VOCAB.get(i)
        if token is None:
            continue
        for ch in token:
            b = BYTE_DEC.get(ch)
            if b is not None:
                raw.append(b)
    text = raw.decode("utf-8", errors="replace")
    return post_process(text)

def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    import onnxruntime as ort
    t0 = time.perf_counter()
    sess = ort.InferenceSession(MODEL, providers=["CPUExecutionProvider"])
    load_s = time.perf_counter() - t0
    inp = sess.get_inputs()[0]
    out = sess.get_outputs()[0]
    print("load %.1fs | input %s %s %s | output %s %s" % (
        load_s, inp.name, inp.shape, inp.type, out.name, out.shape))
    files = sorted(f for f in os.listdir(FIX) if f.endswith(".png"))[:n]
    for name in files:
        png = open(os.path.join(FIX, name), "rb").read()
        x = preprocess(png)
        t1 = time.perf_counter()
        pred = sess.run([out.name], {inp.name: x})[0]
        dt = time.perf_counter() - t1
        ids = np.array(pred[0]).reshape(-1)
        latex = decode(ids)
        print("%s infer %.2fs tokens=%d eos=%s" % (name, dt, len(ids), 2 in ids))
        print("  latex: %s" % latex[:200])
        if dt > 120:
            print("STOP-MINUTE-LEVEL: 单块 %.1fs 分钟级，按卡停跑" % dt)
            return
    print("done")

if __name__ == "__main__":
    main()