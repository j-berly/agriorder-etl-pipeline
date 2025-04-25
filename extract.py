import os.path
import pandas as pd


def img_to_dataframes_paddle(img_path: str) -> pd.DataFrame:
    """
    OCR图片为表格，并转为DataFrame。

    参数:
        img_path: str 或 bytes
            图片文件路径（字符串）或图片二进制流

    返回:
        pd.DataFrame：提取到的文本原文表格，每行为一个OCR文本单元，字段名'raw'
    """
    from paddlex import create_pipeline
    pipeline = create_pipeline(pipeline="OCR")

    output = pipeline.predict(
        input=img_path,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )
    rec_texts = []
    for res in output:
        rec_texts.extend(res['rec_texts'])
    dataframes = pd.DataFrame(rec_texts, columns=['raw'])
    return dataframes


def pdf_to_dataframes_paddle(pdf_path: str) -> pd.DataFrame:
    """
    OCR PDF为表格，并转为DataFrame，自动合并PDF单头信息。

    参数:
        pdf_path: str
            PDF文件路径

    返回:
        pd.DataFrame：合并了订单头部信息的表格，每行含表格结构字段与订单头信息
    """
    from paddlex import create_pipeline
    from typing import Dict

    pipeline = create_pipeline(pipeline="table_recognition_v2")
    output = pipeline.predict(input=pdf_path, use_doc_orientation_classify=False, use_doc_unwarping=False)
    dataframes = []  # 用于存储所有表格df
    orderinfo: Dict[str, str] = {}  # 订单头关键信息

    for res in output:
        # 假如有多table，找出本页表格和总OCR
        table_res_list = res.json['res']['table_res_list']
        table_res = set(table_res_list[0]['table_ocr_pred']['rec_texts']) if table_res_list else {}
        overall_res = set(res['overall_ocr_res']['rec_texts'])
        # 找出属于header的信息（非表格单元，且含“:”分隔）
        orderinfo.update({item.partition(':')[0].strip(): item.partition(':')[2].strip()
                          for item in overall_res.difference(table_res) if ':' in item})

        # 从每个htmlstr提取表格df
        for htmlstr in res.html.values():
            dfs = pd.read_html(htmlstr)
            dataframes.extend(dfs)
    if len(dataframes) == 0:
        return pd.DataFrame()  # 没有结果返回空表
    dataframes = pd.concat(dataframes, ignore_index=True)
    return dataframes, orderinfo


def pdf_to_dataframes_google(pdf_path):
    import fitz
    from google.cloud import vision
    client = vision.ImageAnnotatorClient()
    doc = fitz.open(pdf_path)
    dataframes = []
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=300)
        pix.save(f'inputs/{os.path.basename(pdf_path)}_{i + 1}.png')

        with open(f'inputs/{os.path.basename(pdf_path)}_{i + 1}.png', 'rb') as img_file:
            image = vision.Image(content=img_file.read())

        response = client.document_text_detection(image=image)
        document = response.full_text_annotation

        words_with_bbox = []
        for _page in document.pages:
            for block in _page.blocks:
                for paragraph in block.paragraphs:
                    for word in paragraph.words:
                        # 获取字内容
                        wtext = ''.join([symbol.text for symbol in word.symbols])
                        # 获取 bbox: 4 个点的 [{x:, y:}, ...]
                        vertices = word.bounding_box.vertices
                        word_bbox = [(v.x, v.y) for v in vertices]
                        words_with_bbox.append({'text': wtext, 'bbox': word_bbox})
                        word_center = (
                        (word_bbox[0][0] + word_bbox[2][0]) // 2, (word_bbox[0][1] + word_bbox[2][1]) // 2)
