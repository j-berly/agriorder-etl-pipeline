import pandas as pd


def is_null(x):
    # 判断是否为 None 或 pandas 的 NaN
    return x is None or (isinstance(x, float) and pd.isna(x))


standard_header = ['項次', '品號', '品名', '數量', '單位', '單價', '小計']

column_templates = {
    '項次': lambda x: is_null(x) or (str(x).isdigit() and len(str(x)) <= 4),
    '品號': lambda x: is_null(x) or (isinstance(x, str) and any(ch.isalpha() for ch in str(x))),
    '品名': lambda x: is_null(x) or (isinstance(x, str) and any('\u4e00' <= ch <= '\u9fff' for ch in str(x))),
    '數量': lambda x: is_null(x) or str(x).replace('.', '', 1).isdigit(),  # 支持小数点，比如"1.5"
    '單位': lambda x: is_null(x) or (isinstance(x, str) and len(x) <= 4),
    '單價': lambda x: is_null(x) or str(x).replace('.', '', 1).isdigit(),
    '小計': lambda x: is_null(x) or str(x).replace('.', '', 1).isdigit(),
}
