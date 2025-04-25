import pandas as pd
import json
import re
import numpy as np
from json_extractor import JsonExtractor
from contants import standard_header, column_templates
from llm_call import gemma3
from asteval import Interpreter
from typing import List, Any


ae = Interpreter()


def set_standard_table_header(df: pd.DataFrame) -> pd.DataFrame:
    """
    若行列数满足要求，用标准表头替换，行不够则原样返回。
    """
    df = df.dropna(how='all')
    # 检查df行数和列数是否合理
    if df.shape[1] >= len(standard_header):
        # 用第一行作为表头，替换为标准表头
        df = df.iloc[1:].reset_index(drop=True)  # 丢掉第一行
        df.columns = standard_header[:df.shape[1]]  # 标准名字，防止列数有误
    else:
        # 列数不匹配，不处理，直接返回原始df
        print("警告: 列数不足，未做表头替换！")
    return df


def is_row_cells_aligned(row: List[Any]) -> bool:
    """列数与表头齐、抬头意义对齐"""
    return len(row) == len(standard_header)


def is_row_fully_valid(row: List[Any]) -> bool:
    """每一格都合规、非空（类型模板&非空）"""
    if not is_row_cells_aligned(row):
        return False
    for cell, h in zip(row, standard_header):
        if pd.isnull(cell) or not column_templates[h](cell):
            return False
    return True


def is_row_alignment_wrong_but_elements_ok(row: List[Any]) -> bool:
    """
    - 元素数齐（等于列数）
    - 只是不匹配该列字段特征
    """
    if not is_row_cells_aligned(row):
        return False
    err_cnt = 0
    for val, h in zip(row, standard_header):
        if not column_templates[h](val):
            err_cnt += 1
    # 行长度对齐，允许<=2列不合适即判为错位，否则只内容问题
    return True if err_cnt > 0 else False


def is_row_nan(row: List[Any]) -> bool:
    """有缺失或空值"""
    return any(pd.isnull(cell) or str(cell).strip() == '' for cell in row)


def is_multi_values(row: List[Any]) -> bool:
    """
    检查关键字段中是否有一项含多个值
    row: 单行list
    standard_header: 字段名list
    """
    for field in filter(lambda x: x != '品名', standard_header):
        idx = standard_header.index(field)
        val = str(row[idx])
        # 品號用正则匹配
        if field == '品號':
            codes = re.findall(r'[A-Z][0-9]{6}', val)  # 调整正则以适应实际编号格式
            if len(codes) > 1:
                return True
        else:
            # 其他字段以空格分割为主
            vals = val.strip().split()
            if len(vals) > 1:
                return True
    return False


def split_row(row: List[Any]) -> List[List[Any]]:
    """
    按标准字段顺序对一行进行智能切分成多行
    """
    idx = row[standard_header.index('項次')]
    codes = row[standard_header.index('品號')]
    names = row[standard_header.index('品名')]
    qtys = row[standard_header.index('數量')]
    units = row[standard_header.index('單位')]
    prices = row[standard_header.index('單價')]
    totals = row[standard_header.index('小計')]

    code_list = re.findall(r'[A-Z][0-9]{6}', str(codes))
    name_list = str(names).split()
    qty_list = str(qtys).split()
    unit_list = str(units).split()
    price_list = str(prices).split()
    total_list = str(totals).split()

    n = max(
        len(code_list),
        len(name_list),
        len(qty_list),
        len(unit_list),
        len(price_list),
        len(total_list),
    )
    result = []
    for i in range(n):
        result.append([
            idx if n == 1 else f"{idx}-{i + 1}",
            code_list[i] if i < len(code_list) else '',
            name_list[i] if i < len(name_list) else '',
            qty_list[i] if i < len(qty_list) else '',
            unit_list[i] if i < len(unit_list) else '',
            price_list[i] if i < len(price_list) else '',
            total_list[i] if i < len(total_list) else '',
        ])
    return result


def unfold_multi_value_rows(df: pd.DataFrame) -> pd.DataFrame:
    """
    根据标准字段，把含多个主要字段（如品号、数量、金额等）的行，自动拆为多行。其余行保持不变。
    df: pandas.DataFrame，字段顺序需与standard_header一致
    standard_header: 列名list，如['項次', '品號', '品名', '数量', '单位', '单价', '小计']
    return: 展开后的 DataFrame（列顺序不变）
    """
    all_rows = []
    for row in df.values.tolist():
        if is_multi_values(row):
            all_rows.extend(split_row(row))
        else:
            all_rows.append(list(row))  # 保证都是list
    # 保持原字段顺序
    return pd.DataFrame(all_rows, columns=standard_header)


def assign_row_via_llm(row, model_qa_func):
    prompt = f"""
    表頭: {standard_header}
    數據: {row}
    - 這行的內容順序可能與表頭錯位，請你根據表頭意義，將每一項內容**正確對應到它應所在的列**。不需要猜測或補充缺失內容，只需修正錯位。 
    - 輸出結果嚴格為 JSON（屬性名稱和字串都用雙引號），不要解釋說明。
    """
    return model_qa_func(prompt)


def fill_row_via_llm(row, llm_func):
    prompt = f"""
    表頭: {standard_header}
    數據: {row}
    - 這行內容有部分資料缺失（如 None、空白、null 等）。請你結合常識與上下文，**大膽、合理推測並補全所有缺失項**，如果確實無法推斷則置為 null。 
    - 輸出結果嚴格為 JSON（屬性名稱和字串都用雙引號），不要解釋說明。
    """
    return llm_func(prompt)


def extract_meta_fields_via_llm(meta_dict, model_qa_func):
    prompt = f"""
    已知以下字典型單據資訊：
    {meta_dict}
    
    請你只輸出符合下述要求的JSON：
    {{
     "customer_name": "...",
     "order_date": "...",
     "status": "completed 或 pending"
    }}
    要求：
    - 從輸入內容中準確抽取出「請款對象/客戶名稱/客戶名稱/收件者」為customer_name，「訂單日期/訂單日期/下單日期」為order_date，「狀態/訂單狀態」為status。
    - status值務必規範，僅允許"completed"（已完成/處理中/已結清等）、"pending"（進行中/待處理/未結清等）這兩個枚舉字串，選其一最合理匹配。
    - 如果無法提取到任何字段，則把字段值設為null。輸出必須是合法JSON。
    - 輸出結果嚴格為 JSON（屬性名稱和字串都用雙引號），不要解釋說明。
    """
    return model_qa_func(prompt)


def parse_goods_via_llm(goodstext, model_qa_func):
    prompt = f"""
    你是訂單商品解析助手。請嚴格按照標準 ['項次', '品號', '品名', '數量', '單位', '單價', '小計'] 結構化抽取下述商品資訊：
    - 遇到複合數量（如「12×1242瑰」），請僅將可供計算的部分（如「12×1242」）填入「數量」欄，不要包括非數值或單位部分（如「瑰」）。
    - 沒有的欄位請留空。
    - 錯字自動更正。
    - 只返回嚴格 JSON 數組，屬性名和字串都用雙引號。
    - 不要計算乘積，也不要解釋，只提取和結構化。
    請按此格式解析以下商品資訊：  
    {goodstext}
    """
    return model_qa_func(prompt)


def extract_json_from_response(response_text: str) -> dict:
    """
    从LLM/接口返回中提取json内容，支持markdown块或直接文本。
    """
    # 匹配```json ... ```或``` ... ```之间内容
    match = re.search(r'```(?:json)?\s*([$${][\s\S]+?[$$}])\s*```', response_text)
    if match:
        json_str = match.group(1).strip()
    else:
        # 如果没有代码块就直接处理整体
        json_str = response_text.strip()

    # 用json.loads解析
    try:
        return json.loads(json_str)
    except Exception as e:
        print("JSON解析失败:", e)
        raise


def smart_to_float(val: Any) -> float:
    """
    针对数量、金额等字段，安全解析字符串/混合表达式为数值，不能解析返回 nan。
    """
    try:
        if val is None:
            return np.nan
        v = str(val).replace(',', '').strip()
        if v == '' or v.lower() == 'nan':
            return np.nan
        for s, r in [
            ('×', '*'), ('x', '*'), ('X', '*'),
            ('＋', '+'), ('－', '-'), ('（', '('), ('）', ')'),
        ]:
            v = v.replace(s, r)
        if re.fullmatch(r'\d+', v):
            return float(v)
        try:
            res = ae(v)
            if isinstance(res, (int, float)) and not isinstance(res, bool):
                return float(res)
            else:
                return np.nan  # 不能解析则返回NaN
        except Exception:
            return np.nan
    except Exception:
        return np.nan


def smart_convert(val: Any) -> Any:
    """
    尝试将val解析成float或int，不能则原值返回。
    """
    try:
        v = str(val).replace(',', '').strip()
        if v == '' or v.lower() == 'nan':
            return 0
        elif '.' in v:
            return float(v)
        else:
            return int(v)
    except ValueError:
        return val


def fuzzy_match_ordermeta(ordermeta: dict) -> dict:
    """
    用LLM标准化订单meta信息JSON。
    """
    ordermeta = extract_meta_fields_via_llm(ordermeta, gemma3)
    ordermeta = JsonExtractor.extract_valid_json(ordermeta)
    return ordermeta


def fuzzy_match_column(input_series: pd.Series, standard_df, threshold: int = 80) -> pd.DataFrame:
    """
    input_series: pd.Series, 待比对内容（如品名）
    standard_list: list, 标准品名（来自 excel）
    threshold: 匹配分数低于此数值标记为低分待人工确认

    return: result_df, 含原内容、标准匹配、分数和低分警告的DataFrame
    """
    from rapidfuzz import process, fuzz
    results = []
    standard_names = standard_df['品名'].dropna().astype(str).unique().tolist()
    for val in input_series:
        match, score, _ = process.extractOne(
            query=str(val), choices=standard_names, scorer=fuzz.WRatio, score_cutoff=None
        )
        is_low = score < threshold
        sub = standard_df.loc[standard_df['品名'] == match, '品號']
        product_id = sub.values[0] if len(sub) > 0 else None
        results.append({
            "original_input": val,
            "matched_name": match,
            "match_score": float(round(score / 100, 2)),
            "需人工确认": "是" if is_low else "",
            "product_id": product_id
        })
    return pd.DataFrame(results)


def transform_pipeline_pdf(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    PDF提取表格清洗总流程：
      - 检查/标准化表头
      - 拆分多值行
      - 行级检查纠错（合规直接入库、不全或错位自动用LLM补全）
      - 金额、数量自动转数值
      - 全表applymap最后处理
    """
    df = set_standard_table_header(df_raw)
    df = unfold_multi_value_rows(df)
    fixed_rows = []
    for row in df.values.tolist():
        # 1. 完全合规，直接入库
        if is_row_fully_valid(row):
            fixed_rows.append(row)
        # 2. 内容对齐错位了，可进LLM做重分配
        elif is_row_alignment_wrong_but_elements_ok(row):
            assigned = assign_row_via_llm(row, gemma3)
            assigned = JsonExtractor.extract_valid_json(assigned)
            assigned = assigned[0] if isinstance(assigned, list) else assigned
            fixed_rows.append([assigned.get(h, 0) for h in standard_header])
        # 3. 长度齐全但有nan/null、空字符串，进LLM补准确值
        elif is_row_nan(row):
            assigned = fill_row_via_llm(row, gemma3)
            assigned = JsonExtractor.extract_valid_json(assigned)
            fixed_rows.append([assigned.get(h, 0) for h in standard_header])
        # 4. 其它无法判断，直接用原始row填充（或可日志输出）
        else:
            print(f"警告：异常行，无法判断，原样保存: {row}")
            fixed_rows.append(row)
    df = pd.DataFrame(fixed_rows, columns=standard_header)
    df = df.rename(columns={'數量': 'quantity', '小計': 'price'})
    df["price"] = df["price"].apply(smart_to_float)
    df["quantity"] = df["quantity"].apply(smart_to_float)

    df = df.applymap(smart_convert)
    return df


def transform_pipeline_img(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    图片提取表格主要流程：解析整列文本用LLM强转为结构化表格，再做数值清洗
    """
    df = set_standard_table_header(df_raw)
    goodstext = df.iloc[:, 0].astype(str).tolist()
    result = parse_goods_via_llm(goodstext, gemma3)
    result = JsonExtractor.extract_valid_json(result)
    df = pd.DataFrame(result)

    df = df.rename(columns={'數量': 'quantity', '小計': 'price'})
    df["price"] = df["price"].apply(smart_to_float)
    df["quantity"] = df["quantity"].apply(smart_to_float)

    df = df.applymap(smart_convert)
    return df
