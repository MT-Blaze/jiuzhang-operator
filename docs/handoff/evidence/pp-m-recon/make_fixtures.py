"""侦查夹具：纯图真卷 → RapidOCR 行框 → 数学密集行裁公式块（300dpi）。"""
import sys, os, io
sys.path.insert(0, r"E:\jiuzhang\jiuzhang-operator")
import numpy as np
import cv2
import pypdfium2
from PIL import Image
from app.core.content import scan_text
from app.core.ingest.recognize import ocr

PDF = r"E:\jiuzhang\jiuzhang-operator\.system_generated\model-config-card\data_final\pending_sources\20261118-223910_c45feb_东北师大附中2023-2024高一上学期第一次月考试题.pdf"
OUT = r"E:\jiuzhang\jiuzhang-operator\.system_generated\pp-m-recon\fixtures"
DPI = 300
os.makedirs(OUT, exist_ok=True)

def math_ratio(text):
    chars = [c for c in text if not c.isspace()]
    if not chars:
        return 0.0
    good = sum(1 for c in chars if scan_text._is_math_char(c) and not scan_text._is_cjk(c))
    return good / len(chars)

engine = ocr._engine("small")
doc = pypdfium2.PdfDocument(PDF)
cands = []
for pno in range(len(doc)):
    page = doc[pno]
    bmp = page.render(scale=DPI / 72.0)
    from app.core.ingest.render import pdf as pdf_render
    png = pdf_render._png_from_bitmap(bmp, bytes(bmp.buffer))
    bmp.close(); page.close()
    arr = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR)
    img = Image.open(io.BytesIO(png))
    rows = ocr._rows(engine, arr)
    for r in rows:
        text = r["text"]
        w, h = r["x1"] - r["x0"], r["y1"] - r["y0"]
        if len(text) < 5 or w < 40 or h < 14:
            continue
        if math_ratio(text) < 0.95 or not scan_text._is_strong_math(list(text)):
            continue
        if not (200 < w < 1600):
            continue
        cands.append({"page": pno + 1, "text": text, "score": r["score"],
                      "box": [r["x0"], r["y0"], r["x1"], r["y1"]],
                      "img": img.crop((int(r["x0"]) - 2, int(r["y0"]) - 2,
                                       int(r["x1"]) + 2, int(r["y1"]) + 2))})
doc.close()
print("candidates:", len(cands))
WANT = ["A={x∈ N|−√3≤x≤√3}", "B. ∀x∈ R, x²−2x+1≤0", "A. {a| a≥2}",
        "A. αkB =(−∞,−1)∪(2,+∞)", "≤x²+y²≤8"]
final = []
for want in WANT:
    for item in cands:
        if item["text"] == want:
            final.append(item)
            break
lines = ['source_pdf = "%s"' % os.path.basename(PDF), "dpi = %d" % DPI,
         'engine = "rapidocr-small"', ""]
for i, item in enumerate(final, 1):
    name = "f%d.png" % i
    item["img"].save(os.path.join(OUT, name))
    t = item["text"].replace("\\", "\\\\").replace('"', '\\"')
    lines += ["[[fixture]]", 'file = "%s"' % name, "page = %d" % item["page"],
              'text = "%s"' % t, "width = %d" % item["img"].width,
              "height = %d" % item["img"].height, ""]
    print(name, item["img"].size, repr(item["text"][:60]))
with open(os.path.join(OUT, "fixtures.toml"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))
print("done", len(final))