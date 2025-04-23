from paddleocr import PaddleOCR
from PIL import Image
from typing import List
import fitz
import easyocr
import certifi
import os
os.environ['SSL_CERT_FILE'] = certifi.where()

# --- OCR 初始化 ---
reader_easyocr = easyocr.Reader(['ch_tra', 'en'])
ocr_trad = PaddleOCR(use_angle_cls=True, lang='chinese_cht')


def pdf_to_images(pdf_bytes: bytes) -> List[Image.Image]:
    """
    把一份PDF bytes转为每页PIL Image
    """
    doc = fitz.open(stream=pdf_bytes, filetype='pdf')
    imgs = []
    for page in doc:
        pix = page.get_pixmap(dpi=300)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        imgs.append(img)
    return imgs


def ocr_paddle_func(img: Image.Image):
    import numpy as np
    res = ocr_trad.ocr(np.array(img), cls=True)
    items = []
    for item in res:
        box, (text, conf) = item
        if not text.strip():
            continue
        x, y = box[0]  # 取左上角x1、顶部y1
        _, y2 = box[2]  # 取右上角x2，下顶y2
        mid_y = (y + y2) / 2
        items.append({'text': text, 'x': x, 'y': mid_y})

    # 按y分组聚类为行
    items = sorted(items, key=lambda t: t['y'])
    rows = []
    current_row = []
    current_y = None
    for item in items:
        if current_y is None or abs(item['y'] - current_y) < row_gap:
            current_row.append(item)
            current_y = item['y']
        else:
            # 断行
            rows.append(current_row)
            current_row = [item]
            current_y = item['y']
    if current_row:
        rows.append(current_row)

    # 每行内再按x排序
    table = []
    for row in rows:
        row_sorted = sorted(row, key=lambda t: t['x'])
        table.append([cell['text'] for cell in row_sorted])
    return table


def ocr_tesseract_func(img: Image.Image):
    import pytesseract
    return pytesseract.image_to_string(img, lang='chi_sim+eng')


def ocr_easyocr_func(img: Image.Image):
    # EasyOCR 需要文件或ndarray
    import numpy as np
    res = reader_easyocr.readtext(np.array(img))
    return "\n".join([i[1] for i in res])

