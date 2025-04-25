
# transform 节点说明

## 1. 功能简介
本节点用于接收上游（如“extract节点”或OCR接口）提取的表格（一般为parquet/json格式）及其元信息，对其进行标准化清洗、结构化、字段格式还原等操作，并返回可用的数据明细、订单头信息等。

适用于 n8n 工作流自动化场景下的多格式发票、订单等表单 ETL。

---

## 2. 输入数据约定

- **Content-Type**: application/json
- **Body** :  
  ```json
  {
    "tmp_path": "./tmp/abc123_extract.parquet"
  }
  ```
  或（如需传递原始data，可扩展）:
  ```json
  {
    "parquet_path": "...",
    "orderinfo": {...}
  }
  ```

---

## 3. 功能步骤说明

1. **读取 parquet 文件/表格**（如带全部转为str，可自动还原）
2. **从`parquet`元数据分离订单头信息**（orderinfo 字段）
3. **表格表头标准化**、拆分多值行、错行或缺失智能补全
4. **金额、数量等字段自动转换回 float**
5. **返回标准明细表与meta**

---

## 4. HTTP 接口定义

- 路径示例：`/pdf_transform`
- 方法：POST
- POST Body 示例:
  ```json
  {
    "tmp_path": "./tmp/xxx_extract.parquet"
  }
  ```

### 返回数据
```json
{
  "orderinfo": {"订单号": "...", "日期": "..."},
  "data": [
    {"品名": "...", "品號": "...", "price": 123.0, "quantity": 5.0, ...},
    ...
  ]
}
```
> **注：** 字段类型均已恢复为float/int/str等原始格式（如原文件已全部转str，transform中已恢复）

---
