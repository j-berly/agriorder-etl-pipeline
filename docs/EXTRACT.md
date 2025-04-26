# Extract：PaddleOCR 表格与订单信息提取（FastAPI接口）

## 简介

本模块聚焦于订单PDF和图片的自动表格与头部信息抽取。通过 PaddleOCR/TableOCR，将扫描件或图片文件结构化识别为 DataFrame 并落盘为 Parquet，便于下游 ETL 自动化（如 n8n）与数据分析。PDF还同时萃取订单元数据（如时间、公司、联系人等）。

---

## 功能说明

- **图片和PDF分开入口，单一职责，调用清晰**
- **识别后结构化为DataFrame，并保存为 Parquet 文件**，方便大规模数据接入与分析。
- **PDF会同时返回/保存订单 metadata**（如订单号、时间、买家等关键字段）。

---

## FastAPI 主要接口

### 1. PDF 表格与头部信息抽取

**POST `/pdf_extract`**

- **入参**：
  - `filepath`：PDF文件在服务器的路径（如通过文件上传获得后文件存储路径）
- **处理：**
  - PaddleOCR/Table 功能，抽出全部表格和单据头部信息
  - 萃取单据元信息（如订单号/下单日期等）
  - 表格数据与元数据一并写入Parquet 文件（命名与原文件对应）
- **出参**：
  - parquet 路径

#### Demo

```python
POST /pdf_extract
Content-Type: application/json
{
  "filepath": "/data/invoice_2023.pdf"
}
```

### 2. 图片表格信息抽取

**POST `/img_extract`**

- **入参**：
  - `filepath`：图片文件在服务器的路径
- **处理：**
  - PaddleOCR/Table 识别图片表格
  - 写成 Parquet 文件
- **出参**：
  - parquet 路径

#### Demo

```python
POST /img_extract
Content-Type: application/json
{
  "filepath": "/data/photo_001.png"
}
```

---

## 结果说明

- 表格内容返回为 pandas DataFrame 可用的 JSON 对象，并已持久化存储为 Parquet 文件（高效后端数仓格式）。
- PDF如有，返回/保存结构包含 metadata：如订单号、下单时间、买方等关键头部信息

---

## 依赖环境

- Python 3.11+
- paddleocr, pandas, fastapi, uvicorn, pyarrow 等

---

## 部署/集成

- 可结合 Webhook 自动上传，分离存储与识别，集成于 n8n等自动工单/流程平台
- 详细调用/异步批量能力，可见 api 代码注释。

---

**本目录即 PaddleOCR+FastAPI 订单提取核心模块**  
_如需自定义字段及表头配置，详见`contants.py`的代码以及样例。_

---