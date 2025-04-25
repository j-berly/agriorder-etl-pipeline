from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from typing import List
import os
import tempfile
import uuid


app = FastAPI()


async def save_file_to_tmp(file: UploadFile) -> str:
    # 自动创建唯一临时文件，并安全写入
    contents = await file.read()
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir='./tmp') as f:
        f.write(contents)
        tmp_path = f.name
    return tmp_path


def allowed_content_type(content_type):
    return content_type in ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg']


def write_to_parquet_with_meta(df, metadata: dict, save_path: str):
    # 将DataFrame连同metadata一起写入parquet，可追加或覆盖元数据
    import pyarrow as pa
    import pyarrow.parquet as pq
    table = pa.Table.from_pandas(df.astype(str))
    meta_dict = {k: str(v) for k, v in metadata.items()}
    meta_dict = {k: v.encode('utf8') for k, v in meta_dict.items()}
    # 合入原有meta(如Field名避免冲突)
    old_meta = table.schema.metadata or {}
    merged_meta = old_meta.copy()
    merged_meta.update(meta_dict)

    table = table.replace_schema_metadata(merged_meta)
    pq.write_table(table, save_path)


def write_to_parquet(df, save_path: str):
    # 只写DataFrame，不含元数据
    df.astype(str).to_parquet(save_path)


@app.post("/upload")
async def upload_inputs(file: UploadFile = File(...), order: UploadFile = File(...)):
    """
    上传并保存PDF/图片及订单模板Excel，返回临时路径
    - file: 客户上传的PDF或图片
    - order: 客户上传的标准订单表（一般为Excel）
    """
    if not allowed_content_type(file.content_type):
        raise HTTPException(status_code=400, detail="僅支持PDF、图片格式文件上传！")
    file_path = await save_file_to_tmp(file)
    order_path = await save_file_to_tmp(order)
    return {"file": file_path, "order": order_path}


@app.post("/pdf_extract")
async def pdf_extract(payload: dict):
    """
    第一步：从payload中读取filepath，提取表格和元信息，并写成parquet带meta
    """
    from extract import pdf_to_dataframes_paddle
    filepath = payload.get('filepath')
    if not filepath:
        raise HTTPException(status_code=400, detail="不存在文件！")

    df, metadata = pdf_to_dataframes_paddle(filepath)
    tmp_path = f"./tmp/{uuid.uuid4()}_extract.parquet"
    df.columns = df.columns.map(str)

    write_to_parquet_with_meta(df, metadata, tmp_path)

    return {"extract_path": tmp_path}


@app.post("/pdf_transform")
async def pdf_transform(payload: dict):
    """
    第二步：读取parquet和meta，做字段/头部标准化，写新parquet
    """
    from transform import transform_pipeline_pdf, fuzzy_match_ordermeta
    import pyarrow.parquet as pq
    filepath = payload.get('filepath')
    if not filepath:
        raise HTTPException(status_code=400, detail="不存在文件！")

    table = pq.read_table(filepath)
    orderinfo = {k: v.decode('utf8') for k, v in (table.schema.metadata or {}).items()}
    orderinfo = fuzzy_match_ordermeta(orderinfo)

    df = table.to_pandas()
    df = transform_pipeline_pdf(df)
    tmp_path = filepath.replace('extract', 'transform')
    write_to_parquet_with_meta(df, orderinfo, tmp_path)
    return {"transform_path": tmp_path}


@app.post("/fuzzy")
async def fuzzy(payload: dict):
    """
    第三步：模糊匹配“品名”等字段，存放匹配结果
    - payload需有filepath（明细parquet），orderpath（标准订单excel路径）
    """
    from transform import fuzzy_match_column
    import pyarrow.parquet as pq
    import pandas as pd
    filepath = payload.get('filepath')
    orderpath = payload.get('orderpath')
    if not filepath:
        raise HTTPException(status_code=400, detail="不存在文件！")
    standard_df = pd.read_excel(orderpath)

    df = pq.read_table(filepath).to_pandas()
    matched_df = fuzzy_match_column(df['品名'], standard_df, threshold=80)
    tmp_path = filepath.replace('transform', 'fuzzy')
    write_to_parquet(matched_df, tmp_path)
    return {"fuzzy_path": tmp_path}


@app.post("/load")
async def load(payload: dict):
    """
    第四步：结构化输出。聚合明细、元数据，输出标准JSON
    - payload需有filepath（明细 + 头部parquet），matchpath（品名匹配parquet）
    """
    from load import convert_to_json
    import pyarrow.parquet as pq
    filepath = payload.get('filepath')
    matchpath = payload.get('matchpath')
    if not filepath:
        raise HTTPException(status_code=400, detail="不存在文件！")

    table = pq.read_table(filepath)
    orderinfo = {k: v.decode('utf8') for k, v in (table.schema.metadata or {}).items()}
    df = table.to_pandas()
    matched_df = pq.read_table(matchpath).to_pandas()
    json_load = convert_to_json(orderinfo, df, matched_df)

    return json_load


@app.post("/img_extract")
async def img_extract(payload: dict):
    """
    第一步：从payload中读取filepath，提取表格和元信息，并写成parquet带meta
    """
    from extract import img_to_dataframes_paddle
    filepath = payload.get('filepath')
    if not filepath:
        raise HTTPException(status_code=400, detail="不存在文件！")

    df = img_to_dataframes_paddle(filepath)
    tmp_path = f"./tmp/{uuid.uuid4()}_extract.parquet"
    write_to_parquet(df, tmp_path)
    return {"tmp_path": tmp_path}


@app.post("/img_transform")
async def img_transform(payload: dict):
    """
    第二步：读取parquet和meta，做字段/头部标准化，写新parquet
    """
    from transform import transform_pipeline_img
    import pyarrow.parquet as pq
    filepath = payload.get('filepath')
    if not filepath:
        raise HTTPException(status_code=400, detail="不存在文件！")

    df = pq.read_table(filepath).to_pandas()
    df = transform_pipeline_img(df)

    tmp_path = filepath.replace('extract', 'transform')
    write_to_parquet(df, tmp_path)
    return {"transform_path": tmp_path}


if __name__ == '__main__':
    import uvicorn
    os.makedirs('./tmp', exist_ok=True)
    uvicorn.run(app, host='localhost', port=11000)
