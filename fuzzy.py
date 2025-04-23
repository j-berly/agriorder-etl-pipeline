import pandas as pd
from rapidfuzz import process, fuzz


df = pd.read_excel('/Users/berly/Downloads/Customer Order Data.xlsx')
std_goods = df['品名'].fillna('').tolist()

# 2. OCR识别表（比如 List[Dict] 或 DataFrame）
ocr_goods = [...]  # [{"商品名称": "苹果", "单位": "箱"}, ...]

match_results = []
for item in ocr_goods:
    query = item['商品名称']
    match, score, _ = process.extractOne(query, std_goods, scorer=fuzz.ratio)
    match_results.append({
        'ocr': query,
        'matched_standard': match,
        'score': score
    })
print(match_results)
