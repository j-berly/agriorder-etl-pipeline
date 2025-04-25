# PDF订单表格智能ETL流程说明

一套自动化的数据处理管线流程，实现如下目标：

- 从订单PDF自动识别并提取表格数据
- 智能纠正表头、补全缺失、处理表格错位
- 产品列名支持模糊匹配（拼写错、缩写、别名等容错）
- 最终将结构化数据输出为标准JSON格式，方便后续系统集成和数据复用

---

## 1. Extract 步骤

**核心任务：** 使用 PaddleOCR（或类似框架）自动从 PDF（以扫描或原始表单为主）提取订单表格。

- 通过表格识别管道（如create_pipeline(pipeline='table_recognition_v2')），输出 HTML 表格。
- 利用 `pd.read_html` 解析表格，获得原始 DataFrame。
- 支持一份PDF多表/多页自动合并。

---

## 2. Transform 步骤

**核心任务：** 对表格进行多轮规范和校正，确保数据质量。

1. **表头标准化与对齐**  
   - 自动识别第一行作为实际表头。
   - 若表头缺失或顺序、分割错误，自动调整为预设标准（如`['項次', '品號', '品名', '数量', '单位', '单价', '小计']`）。

2. **数据行的缺失/错位修正**  
   - 对每一行检查其与标准表头的对齐性。
   - 对明显错位、内容错行的数据，可用规则或大模型（LLM，如Ollama）辅助重新分配到正确表头。
   - 对于缺失项目（如 None/NaN），如必要，支持智能补全；同时，若模型输出为字符串字典，用 ast.literal_eval 或正则解析。

3. **内容纠错与规范**  
   - 支持拼写错误和缩写容错（如品名"mac air"可被归一到"MacBook Air M2"）。
   - 使用 rapidfuzz 进行模糊比对，对比标准答案产品表，返回最优匹配和置信分数。

4. **数据类型标准化**  
   - 自动将可以转为数值的字段（如数量、单价、小计等）转为 int/float，其余字段为字符串。
   - 缺失值（None/NaN等）自动处理，确保后续兼容性及分支逻辑友好。

---

## 3. Load 步骤

**核心任务：** 结构化数据结果落盘

- 所有订单、商品明细等规范字段合成为嵌套 JSON。
- 调用 saveasjson 函数，输出如下结构：

```json
{
  "customer_name": "Tony Wang",
  "order_date": "2025-03-25",
  "items": [
    {
      "product_id": "P001",
      "matched_name": "Apple MacBook Air M2",
      "original_input": "mac air laptop",
      "quantity": 2,
      "match_score": 0.92
    }
  ],
  "status": "completed"
}
```

- 字段语义支持调整（如订单日期、客户名等可手动录入或识别）。

---

## 其他说明与拓展

- **表头自动修正**与**错位问题**通过规则与 LLM Prompt 分流，分别定制不同场景的询问。
- 模糊比对阈值和结果可自定义，低置信度结果自动打标，支持人工校验。
- 整体支持批量多文件、断点落盘调试（可用pickle保存中间DataFrame）。
- LLM 输出务必通过严格 JSON 格式返回，否则需用正则解析或 ast.literal_eval。

---

## 推荐依赖

- paddleocr, pandas, rapidfuzz
- Python 3.11+，含愈规错误处理
- 如用大模型（如Ollama等），需本地或远程API部署对接

---

## 示例流程图

```
PDF 文件
  │
  ├─→ [Extract] PaddleOCR 表格识别 → pd.read_html → 初步DataFrame
  │       ↓
  │─→ [Transform] 表头标准化、缺失/错位修正、拼写/缩写fuzzy match、类型转化
  │       ↓
  └─→ [Load] saveasjson 输出结构化JSON文件
```

---
